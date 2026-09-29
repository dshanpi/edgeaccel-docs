"""Inflect-Micro-v2-zh: official CPU acoustic pipeline + explicit AXCL vocoder."""
import argparse
import datetime
import gc
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path

import axengine
import numpy as np
import soundfile as sf


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--text', help='Use one custom sentence instead of four fixed examples')
    p.add_argument('--voice', choices=['female', 'male'], default='female')
    a = p.parse_args()
    root, out = a.model_dir.resolve(), a.output.resolve()
    source = root / 'python/infer_board.py'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != '9e73ed6ea0434c52f1542290302314ef9646fd66ae508f937ae7ed7d5df4c9ff':
        raise ValueError('Use the documented fixed upstream revision')
    out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('inflect_official', source)
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)
    provider = 'AXCLRTExecutionProvider'
    if provider not in axengine.get_available_providers():
        raise RuntimeError('AXCLRTExecutionProvider unavailable')
    record = {'modelId': 'Inflect-Micro-v2-zh', 'provider': provider,
              'revision': 'f5af82ee9c1cac911584ccd91f759ab54258e0a1',
              'sourceSha256': digest, 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'noiseScale': 0.0, 'seed': 0, 'sessions': [], 'samples': [], 'completed': False}
    # Fixed official graphs refer to export-time names, while the repository renamed data files.
    # Use isolated aliases without modifying or converting the downloaded graph/weights.
    exports = {
        'female': ('acoustic_melgan_ls10.onnx.data', 'dd29ee96d0edd2ea5c8a26719587119a244c4ff88ea9c45aa0dcd29ed4346da2', '31adeb8505258fe29aa47b02f499b68fcea7374e73a9a727bf7c775e99d610de'),
        'male': ('acoustic_melgan_male.onnx.data', 'd8b23d7bd1ee40c0b6b477591d26feace219d81a31bda13bd5af85b4eebcf4bf', 'd44066a764bbe76c48f292a2a220cf12157469b7152b3fac4ab91828e9566e23')}
    acoustic_paths = {}
    record['externalDataAliases'] = []
    for voice, (alias, graph_sha, data_sha) in exports.items():
        graph = root / f'models/acoustic_{voice}.onnx'
        data = graph.with_suffix('.onnx.data')
        assert hashlib.sha256(graph.read_bytes()).hexdigest() == graph_sha
        assert hashlib.sha256(data.read_bytes()).hexdigest() == data_sha
        destination = out / 'runtime' / voice
        destination.mkdir(parents=True)
        acoustic_paths[voice] = destination / graph.name
        shutil.copy2(graph, acoustic_paths[voice])
        (destination / alias).symlink_to(data)
        record['externalDataAliases'].append({'voice': voice, 'referencedName': alias,
                                             'source': data.relative_to(root).as_posix(),
                                             'graphSha256': graph_sha, 'dataSha256': data_sha})

    def save():
        (out / 'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')

    class Measured:
        def __init__(self, path, backend, load_path=None):
            start = time.perf_counter()
            if backend == provider:
                self.session = axengine.InferenceSession(str(path), providers=[provider])
            else:
                self.session = official.load_acoustic(str(load_path or path))
            actual = self.session.get_providers()
            assert actual == backend or actual == [backend], actual
            self.row = {'model': path.relative_to(root).as_posix(), 'provider': backend,
                        'loadSeconds': time.perf_counter() - start,
                        'weightSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'inputs': [{'name': v.name, 'shape': list(v.shape),
                                    'dtype': str(getattr(v, 'dtype', getattr(v, 'type', '')))}
                                   for v in self.session.get_inputs()],
                        'outputs': [{'name': v.name, 'shape': list(v.shape)} for v in self.session.get_outputs()],
                        'runMilliseconds': [], 'calls': [], 'allFinite': True}
            record['sessions'].append(self.row)
            save()

        def run(self, names, feed):
            assert all(np.isfinite(v).all() for v in feed.values())
            start = time.perf_counter()
            values = self.session.run(names, feed)
            ms = (time.perf_counter() - start) * 1000
            finite = all(np.isfinite(v).all() for v in values)
            self.row['allFinite'] &= bool(finite)
            self.row['runMilliseconds'].append(ms)
            self.row['calls'].append({'inputs': {k: list(v.shape) for k, v in feed.items()},
                                      'outputs': [list(v.shape) for v in values],
                                      'allFinite': bool(finite)})
            save()
            assert finite, 'Non-finite inference output'
            return values

    inputs = [(a.voice, a.text)] if a.text else [
        ('female', '今天中午我想吃一碗牛肉面。'),
        ('female', '人工智能技术正在改变我们的生活方式。'),
        ('male', '请问最近的医院在哪里。'),
        ('male', '欢迎使用算力卡，接下来开始语音合成。')]
    # Validate the official frontend before loading any model, avoiding silent truncation.
    prepared = []
    for voice, text in inputs:
        sentences = official.split_sentences(text)
        counts = [len(official.text_to_sequence(s)) * 2 + 1 for s in sentences]
        assert sentences and all(0 < n <= official.MAX_SENT_TOKENS for n in counts), counts
        prepared.append((voice, text, sentences, counts))
    acoustic = vocoder = None
    try:
        vocoder = Measured(root / 'models/bigvgan_base.axmodel', provider)
        assert vocoder.row['inputs'][0]['shape'] == [1, 100, 512]
        loaded_voice = None
        for index, (voice, text, sentences, counts) in enumerate(prepared, 1):
            if voice != loaded_voice:
                acoustic = None
                gc.collect()
                acoustic = Measured(root / f'models/acoustic_{voice}.onnx', 'CPUExecutionProvider', acoustic_paths[voice])
                loaded_voice = voice
            start_calls = len(vocoder.row['calls'])
            start = time.perf_counter()
            raw, frames = official.synthesize(acoustic, vocoder, text, noise_scale=0.0, seed=0)
            seconds = time.perf_counter() - start
            assert raw.ndim == 1 and raw.size > 0 and np.isfinite(raw).all()
            peak = float(np.abs(raw).max())
            assert peak > 1e-8, 'Silent output'
            wav = raw / (peak + 1e-8) * 0.95  # Same normalization as upstream main().
            name = f'{index:02d}-{voice}'
            sf.write(out / (name + '-raw.wav'), raw, 24000, subtype='FLOAT')
            sf.write(out / (name + '.wav'), wav, 24000, subtype='PCM_16')
            row = {'name': name, 'voice': voice, 'text': text, 'sentences': sentences,
                   'tokenCountsWithBlanks': counts, 'generationSeconds': seconds,
                   'durationSeconds': len(wav) / 24000, 'sampleRate': 24000, 'channels': 1,
                   'melFramesAfterProcessing': int(frames), 'vocoderCalls': len(vocoder.row['calls']) - start_calls,
                   'rawPeak': peak, 'peak': float(np.abs(wav).max()), 'allFinite': True,
                   'clippedFraction': float(np.mean(np.abs(wav) >= 1)),
                   'rawSha256': hashlib.sha256((out / (name + '-raw.wav')).read_bytes()).hexdigest(),
                   'previewSha256': hashlib.sha256((out / (name + '.wav')).read_bytes()).hexdigest()}
            row['realTimeFactor'] = seconds / row['durationSeconds']
            record['samples'].append(row)
            save()
            print(json.dumps(row, ensure_ascii=False), flush=True)
        record['completed'] = True
    except BaseException as e:
        record['error'] = repr(e)
        raise
    finally:
        acoustic = vocoder = None
        gc.collect()
        record['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
