"""Run the fixed official FireRedASR Python pipeline through AXCL."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import axengine
import numpy as np
import soundfile as sf

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--audio', type=Path)
a = p.parse_args()
root, out = a.model_dir.resolve(), a.output.resolve()
assert not out.exists(), 'Choose a new output directory'
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
digest = lambda v: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()
source_hashes = {
    'openai/firered_asr.py': '1a2776dbd9a338cbe8e02b858daadf0e107d93ab0b39ea9921623978942488a8',
    'openai/fsmn_vad_post.py': '983c4eeeba36e8e3a5276dd97cea0ce84628684a69bed581a9a9a92ff414e3f9',
}
for name, expected in source_hashes.items():
    assert sha(root/name) == expected, 'Official source version differs: ' + name
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
out.mkdir(parents=True)
report = {'modelId': 'FireRedASR-AED', 'provider': 'AXCLRTExecutionProvider', 'completed': False,
          'sourceHashes': source_hashes, 'sessions': [], 'samples': [],
          'settings': {'maxDur': 10, 'maxSteps': 128, 'fsmnThreshold': .6, 'minSpeechMs': 1000},
          'configHashes': {n: sha(root/n) for n in ['axmodel/cmvn.ark', 'axmodel/dict.txt', 'axmodel/pe.npy', 'fsmn_vad/am.mvn', 'wav/text']}}
current = 0
raw_arrays = {}
chunks = []
vad_rows = []


def save():
    (out/'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


original_session = axengine.InferenceSession


class Measured:
    def __init__(self, path, **kwargs):
        assert not kwargs
        t = time.perf_counter()
        self.engine = original_session(path, providers=['AXCLRTExecutionProvider'])
        self.name = Path(path).name
        self.record = {'model': str(Path(path).resolve().relative_to(root)), 'weightSha256': sha(Path(path)),
                       'loadSeconds': time.perf_counter()-t, 'allFinite': True, 'runMilliseconds': [], 'calls': [],
                       'inputs': [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)} for x in self.engine.get_inputs()],
                       'outputs': [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)} for x in self.engine.get_outputs()]}
        report['sessions'].append(self.record)
        save()

    def get_inputs(self):
        return self.engine.get_inputs()

    def get_outputs(self):
        return self.engine.get_outputs()

    def run(self, names, feeds):
        for m in self.engine.get_inputs():
            v = feeds[m.name]
            assert v.shape == tuple(m.shape) and v.dtype == np.dtype(m.dtype), (m.name, v.shape, v.dtype, m.shape, m.dtype)
            assert np.isfinite(v).all() or ('mask' in m.name.lower() and not np.isnan(v).any() and not np.isposinf(v).any())
        t = time.perf_counter()
        values = self.engine.run(names, feeds)
        ms = (time.perf_counter()-t)*1000
        output_info = []
        for meta, v in zip(self.engine.get_outputs(), values):
            finite = bool(np.isfinite(v).all())
            allowed_mask = 'mask' in meta.name.lower() and not np.isnan(v).any() and not np.isposinf(v).any()
            assert finite or allowed_mask, (meta.name, 'Unexpected non-finite output')
            output_info.append({'name': meta.name, 'shape': list(v.shape), 'dtype': str(v.dtype), 'sha256': digest(v),
                                'allFinite': finite, 'negativeInfinityCount': int(np.isneginf(v).sum())})
        # allFinite describes model features/logits/cache; legal -inf attention masks are separately reported.
        self.record['runMilliseconds'].append(ms)
        row = {'sampleIndex': current, 'inputHashes': {k: digest(v) for k,v in feeds.items()}, 'outputs': output_info}
        self.record['calls'].append(row)
        key = f'{self.name}_{len(self.record["calls"])}'
        if self.name == 'encoder.axmodel':
            raw_arrays[key+'_features'] = feeds['encoder_input'].copy()
            raw_arrays[key+'_length'] = feeds['encoder_input_lengths'].copy()
        elif self.name == 'decoder_loop.axmodel':
            raw_arrays[key+'_logits'] = values[0].copy()
            row['chosenToken'] = int(np.argmax(values[0][0,0]))
        else:
            raw_arrays[key+'_features'] = feeds['speech'].copy()
            raw_arrays[key+'_scores'] = values[0].copy()
        return values


sys.path.insert(0, str(root/'openai'))
spec = importlib.util.spec_from_file_location('verified_firered_asr', root/'openai/firered_asr.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original_vad = module.vad_segments


def record_vad(*args, **kwargs):
    segments = original_vad(*args, **kwargs)
    vad_rows.append({'segmentsMs': [[int(s), int(e)] for s,e in segments],
                     'speechMs': int(sum(e-s for s,e in segments))})
    return segments


module.vad_segments = record_vad
axengine.InferenceSession = Measured
try:
    runner = module.FireredASR(str(root/'axmodel/encoder.axmodel'), str(root/'axmodel/decoder_loop.axmodel'),
        str(root/'fsmn_vad/fsmn_vad_10s_fp32.axmodel'), str(root/'fsmn_vad/am.mvn'),
        str(root/'axmodel/cmvn.ark'), str(root/'axmodel/dict.txt'), str(root/'axmodel/pe.npy'))
    original_chunk = runner._transcribe_chunk

    def record_chunk(chunk):
        ids = original_chunk(chunk)
        chunks.append({'samples': len(chunk), 'tokenIds': ids, 'hitEos': bool(ids and ids[-1] == 4),
                       'output': runner._detok(ids)})
        return ids

    runner._transcribe_chunk = record_chunk
    refs = {}
    for line in (root/'wav/text').read_text('utf-8').splitlines():
        if line.strip():
            key, value = line.split(maxsplit=1)
            refs[key] = value
    shutil.copy2(root/'wav/text', out/'reference-text.txt')
    files = [a.audio.resolve()] if a.audio else sorted((root/'wav').glob('*.wav'))
    assert files
    silence = out/'silence-3s.wav'
    sf.write(silence, np.zeros(48000, dtype=np.float32), 16000, subtype='PCM_16')
    requests = [(f, 'official' if not a.audio else 'custom') for f in files] + [(files[0], 'repeat'), (silence, 'silence')]
    for audio, kind in requests:
        current += 1
        raw_arrays, chunks, vad_rows = {}, [], []
        info = sf.info(audio)
        assert 0 < info.duration <= 60, 'Use a clip within 60 seconds'
        saved = out/f'input-{current}.wav'
        shutil.copy2(audio, saved)
        starts = [len(s['calls']) for s in report['sessions']]
        t = time.perf_counter()
        text = runner.transcribe(str(audio))
        elapsed = time.perf_counter()-t
        raw = out/f'raw-{current}.npz'
        np.savez_compressed(raw, **raw_arrays)
        row = {'kind': kind, 'input': audio.name, 'audioFile': saved.name, 'audioSha256': sha(saved),
               'audioSeconds': info.duration, 'sampleRate': info.samplerate, 'channels': info.channels,
               'reference': refs.get(audio.stem), 'output': text, 'processSeconds': elapsed, 'rtf': elapsed/info.duration,
               'vad': vad_rows, 'chunks': chunks, 'rawFile': raw.name, 'rawSha256': sha(raw),
               'sessionCalls': [len(s['calls'])-start for s,start in zip(report['sessions'],starts)]}
        report['samples'].append(row)
        save()
        print(json.dumps(row,ensure_ascii=False),flush=True)
    report['completed'] = True
    save()
finally:
    axengine.InferenceSession = original_session
