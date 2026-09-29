"""Run official WeNet AXCL offline/online CTC and attention rescoring."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import time
import wave
from pathlib import Path

import axengine
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--config-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--audio', type=Path)
a = p.parse_args()
root, cfg, out = a.model_dir.resolve(), a.config_dir.resolve(), a.output.resolve()
assert not out.exists(), 'Choose a new output directory'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source = root / 'ax_common.py'
assert sha(source) == '734d450822be1034ebb59d257549f4d75b60490001750a2ce2f6fd30913a88a1'
config_hashes = {'train.yaml': '6712b5556e303de48c98f08d14841f03dbc5e5dc91e3bc5e7f6119b5f2256f11',
                 'units.txt': 'c5146cef40588dcea3ef679c9c05d4eaeb2c37b5369002094369a5722d284de6'}
for name, digest in config_hashes.items():
    assert sha(cfg / name) == digest, 'Configuration version differs: ' + name
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
audio = (a.audio or root / 'demo.wav').resolve()
with wave.open(str(audio)) as wav:
    audio_seconds = wav.getnframes() / wav.getframerate()
    assert wav.getframerate() == 16000 and wav.getnchannels() == 1 and wav.getsampwidth() == 2, 'Use 16 kHz mono PCM16 WAV'
assert 0 < audio_seconds <= 10, 'Use a short audio clip within the offline model window'
out.mkdir(parents=True)
shutil.copy2(audio, out / 'input.wav')
report = {'modelId': 'WeNet', 'provider': 'AXCLRTExecutionProvider', 'completed': False,
          'sourceSha256': sha(source), 'configHashes': config_hashes,
          'inputAudioSha256': sha(audio), 'audioSeconds': audio_seconds,
          'sessions': [], 'samples': []}
current = 0

def save():
    (out / 'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

original_session = axengine.InferenceSession

class Measured:
    def __init__(self, path, providers=None, **kwargs):
        assert providers == ['AXCLRTExecutionProvider']
        t = time.perf_counter()
        self.session = original_session(path, providers=providers, **kwargs)
        self.record = {'model': str(Path(path).resolve().relative_to(root)), 'weightSha256': sha(Path(path)),
                       'loadSeconds': time.perf_counter() - t, 'allFinite': True, 'runMilliseconds': [], 'calls': [],
                       'inputs': [{'name': m.name, 'shape': list(m.shape), 'dtype': str(m.dtype)} for m in self.session.get_inputs()],
                       'outputs': [{'name': m.name, 'shape': list(m.shape)} for m in self.session.get_outputs()]}
        report['sessions'].append(self.record)

    def get_inputs(self):
        return self.session.get_inputs()

    def get_outputs(self):
        return self.session.get_outputs()

    def run(self, names, feeds):
        for m in self.session.get_inputs():
            assert feeds[m.name].shape == tuple(m.shape) and feeds[m.name].dtype == np.dtype(m.dtype), (m.name, feeds[m.name].shape, str(feeds[m.name].dtype), m.shape, str(m.dtype))
        t = time.perf_counter()
        values = self.session.run(names, feeds)
        elapsed = (time.perf_counter() - t) * 1000
        assert all(np.isfinite(v).all() for v in values)
        self.record['runMilliseconds'].append(elapsed)
        self.record['calls'].append({'sampleIndex': current,
             'inputHashes': {k: hashlib.sha256(v.tobytes()).hexdigest() for k, v in feeds.items()},
             'outputs': [{'name': name, 'shape': list(v.shape), 'dtype': str(v.dtype),
                          'sha256': hashlib.sha256(v.tobytes()).hexdigest()} for name, v in zip(names, values)]})
        return values

spec = importlib.util.spec_from_file_location('verified_wenet_ax_common', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
axengine.InferenceSession = Measured
try:
    runner = module.WenetAXRunner(str(cfg / 'train.yaml'), str(cfg / 'units.txt'),
        encoder_offline_path=str(root / 'axmodel/encoder_offline/encoder_offline.axmodel'),
        encoder_online_path=str(root / 'axmodel/encoder_online/encoder_online.axmodel'),
        decoder_path=str(root / 'axmodel/decoder/decoder.axmodel'), provider='AXCLRTExecutionProvider')
    # Load all three before sample timing. Loading alone does not count as coverage.
    loaded = [runner.offline_encoder, runner.online_encoder, runner.decoder]
    feats = runner.compute_feats(str(audio))
    assert np.isfinite(feats).all() and feats.shape[1] <= 1024
    np.save(out / 'features.npy', feats)
    report['featureShape'] = list(feats.shape)
    report['featureSha256'] = sha(out / 'features.npy')
    for online in [False, True]:
        for mode in ['ctc_prefix_beam_search', 'attention_rescoring']:
            for repeat in [1, 2]:
                current += 1
                t = time.perf_counter()
                text = runner.transcribe(str(audio), online=online, mode=mode)
                duration = time.perf_counter() - t
                assert text.strip()
                row = {'online': online, 'mode': mode, 'repeat': repeat, 'output': text,
                       'processSeconds': duration, 'rtf': duration / audio_seconds}
                report['samples'].append(row)
                save()
                print(row, flush=True)
    report['completed'] = True
    save()
finally:
    axengine.InferenceSession = original_session
