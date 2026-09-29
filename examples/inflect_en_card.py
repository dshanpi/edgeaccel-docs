"""Run fixed official Inflect Micro/Nano English SDKs with explicit AXCL sessions."""
import argparse
import datetime
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

import axengine
import numpy as np
import onnxruntime as ort
import soundfile as sf

MODELS = {
    'micro': ('inflect_micro_v2', '5f32b245c249374bb5b6c1b6c1fb7b78f2dd37c2',
              'aaf3fdbd2e2c36aa1a70de42a0687b9031c1e973f987ef1c987b2ef10dc75fe1', 'models/ax650'),
    'nano': ('inflect_nano_v2', 'b57a7ddf5bed32338a79153a43479ea9eee3cde2',
             'daac49a85169578f850d4ce63f7c4a42bad840ef604caf4fd93cfed8eca500ea', 'models'),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', choices=MODELS, required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--text', help='Synthesize one short English input instead of four examples')
    a = p.parse_args()
    mid, revision, source_sha, subdir = MODELS[a.variant]
    root, out = a.model_dir.resolve(), a.output.resolve()
    package = root / 'python/inflect_tts_sdk'
    source = package / 'tts_engine.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha, 'Use the documented fixed revision'
    provider = 'AXCLRTExecutionProvider'
    assert provider in axengine.get_available_providers(), 'AXCL provider unavailable'
    out.mkdir(parents=True, exist_ok=False)
    # The Nano SDK also imports text from runtime; add its actual package directory.
    sys.path[:0] = [str(package), str(package / 'runtime')]
    spec = importlib.util.spec_from_file_location('inflect_official', source)
    official = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(official)
    record = {'modelId': mid, 'revision': revision, 'provider': provider,
              'sourceSha256': source_sha, 'completed': False, 'sessions': [], 'cpuSessions': [],
              'samples': [], 'speed': 1.0, 'variation': 0.667, 'seed': 0,
              'dependencies': {m: importlib.metadata.version(m) for m in
                               ['numpy', 'onnxruntime', 'soundfile', 'phonemizer', 'num2words', 'Unidecode', 'espeakng-loader']},
              'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def save():
        (out / 'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')

    ax_factory, cpu_factory = axengine.InferenceSession, ort.InferenceSession
    decoded = []
    engine = None

    class Measured:
        def __init__(self, path, backend, *args, **kwargs):
            path = Path(path)
            kwargs['providers'] = [backend]
            start = time.perf_counter()
            self.session = (ax_factory if backend == provider else cpu_factory)(str(path), *args, **kwargs)
            actual = self.session.get_providers()
            assert actual == backend or actual == [backend], actual
            self.row = {'model': path.relative_to(root).as_posix(), 'provider': backend,
                        'weightSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'loadSeconds': time.perf_counter() - start,
                        'inputs': [{'name': v.name, 'shape': list(v.shape),
                                    'dtype': str(getattr(v, 'dtype', getattr(v, 'type', '')))}
                                   for v in self.session.get_inputs()],
                        'outputs': [{'name': v.name, 'shape': list(v.shape)} for v in self.session.get_outputs()],
                        'allFinite': True, 'runMilliseconds': [], 'calls': []}
            record['sessions' if backend == provider else 'cpuSessions'].append(self.row)
            save()

        def __getattr__(self, name):
            return getattr(self.session, name)

        def run(self, names, feed):
            assert all(np.isfinite(v).all() for v in feed.values()), 'Non-finite model input'
            start = time.perf_counter()
            values = self.session.run(names, feed)
            ms = (time.perf_counter() - start) * 1000
            finite = bool(all(np.isfinite(v).all() for v in values))
            self.row['allFinite'] &= finite
            self.row['runMilliseconds'].append(ms)
            row = {'inputs': {k: list(v.shape) for k, v in feed.items()},
                   'outputs': [list(v.shape) for v in values], 'allFinite': finite}
            if self.row['model'].endswith('inflect_decoder.axmodel'):
                frames = int(np.count_nonzero(feed['y_mask']))
                raw = np.asarray(values[0][0, 0, :frames * engine.hop_length]).copy()
                assert 0 < frames <= 500 and raw.size > 0
                decoded.append(raw)
                row.update(melFrames=frames, rawPeak=float(np.abs(raw).max()),
                           rawClippedFraction=float(np.mean(np.abs(raw) >= 1)))
            self.row['calls'].append(row)
            save()
            assert finite, 'Non-finite model output'
            return values

    texts = [a.text] if a.text else ['Hello world.',
        'The weather today is sunny with a gentle breeze.',
        'The robot is ready. Please press start.', 'The price is 12 dollars.']
    try:
        prepared = []
        for text in texts:
            sentences = re.split(r'(?<=[.!?;:])\s+', ' '.join(text.split()))
            frontend = [official.run_vits_frontend(s) for s in sentences if s]
            counts = [2 * len(official.cleaned_text_to_sequence(f.phoneme_text)) + 1 for f in frontend]
            assert counts and all(0 < n <= 200 for n in counts), ('Input exceeds 200 tokens', counts)
            prepared.append((text, frontend, counts))
        axengine.InferenceSession = lambda path, *args, **kwargs: Measured(path, provider, *args, **kwargs)
        ort.InferenceSession = lambda path, *args, **kwargs: Measured(path, 'CPUExecutionProvider', *args, **kwargs)
        engine = official.InflectTTSEngine(model_dir=root / subdir)
        assert len(record['sessions']) == 2 and len(record['cpuSessions']) == 1
        axengine.InferenceSession, ort.InferenceSession = ax_factory, cpu_factory
        if a.variant == 'nano':
            original_decode = engine._decode

            def guarded_decode(z_p, y_mask, mel_len):
                if not 0 < mel_len <= engine.max_mel:
                    raise ValueError(f'Audio too long: {mel_len} frames > {engine.max_mel}; use a shorter sentence')
                return original_decode(z_p, y_mask, mel_len)
            engine._decode = guarded_decode
        for index, (text, frontend, counts) in enumerate(prepared, 1):
            decoded.clear()
            start = time.perf_counter()
            sr, wav = engine.synthesize(text, speed=1.0, variation=0.667, seed=0)
            seconds = time.perf_counter() - start
            assert wav.ndim == 1 and wav.size > 0 and np.isfinite(wav).all()
            assert len(decoded) == len(frontend)
            raw = np.concatenate([part for i, segment in enumerate(decoded)
                                  for part in ([np.zeros(round(sr * 0.08), dtype=np.float32), segment] if i else [segment])])
            assert np.array_equal(wav, np.clip(raw, -1.0, 1.0)), 'Output differs from official clip/concatenation'
            peak = float(np.abs(wav).max())
            assert peak > 1e-8, 'Silent output'
            name = f'{index:02d}-english'
            sf.write(out / (name + '-raw.wav'), raw, sr, subtype='FLOAT')
            sf.write(out / (name + '.wav'), wav, sr, subtype='PCM_16')
            row = {'name': name, 'text': text,
                   'frontend': [{'normalized': f.normalized_text, 'phonemes': f.phoneme_text} for f in frontend],
                   'tokenCountsWithBlanks': counts, 'segments': len(decoded),
                   'generationSeconds': seconds, 'durationSeconds': len(wav) / sr,
                   'realTimeFactor': seconds / (len(wav) / sr), 'sampleRate': sr, 'channels': 1,
                   'allFinite': True, 'peak': peak, 'rawPeak': float(np.abs(raw).max()),
                   'rawUniqueValues': int(len(np.unique(raw))), 'clippedFraction': float(np.mean(np.abs(raw) >= 1)),
                   'rawSha256': hashlib.sha256((out / (name + '-raw.wav')).read_bytes()).hexdigest(),
                   'previewSha256': hashlib.sha256((out / (name + '.wav')).read_bytes()).hexdigest()}
            record['samples'].append(row)
            save()
            print(json.dumps(row, ensure_ascii=False), flush=True)
        record['completed'] = True
    except BaseException as e:
        record['error'] = repr(e)
        raise
    finally:
        axengine.InferenceSession, ort.InferenceSession = ax_factory, cpu_factory
        engine = None
        gc.collect()
        record['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
