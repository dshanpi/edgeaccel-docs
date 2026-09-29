"""Run the pinned RNNoise SDK on an AXCL card; save audio and measured outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import wave

import axengine
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.model_dir.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    provider = 'AXCLRTExecutionProvider'
    if provider not in axengine.get_available_providers():
        raise RuntimeError('AXCLRTExecutionProvider is unavailable')
    sys.path.insert(0, str(root / 'python'))
    from rnnoise_sdk import RNNoiseDenoiser

    report = {'task': 'rnnoise', 'provider': provider, 'completed': False,
              'sampleRate': 48000, 'frameSize': 480, 'sessions': [], 'results': []}

    def save():
        (out / 'deployment-result.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    original = axengine.InferenceSession

    class MeasuredSession:
        def __init__(self, model_path, **kwargs):
            assert kwargs['providers'] == [provider]
            self.session = original(model_path, **kwargs)
            self.record = {'model': str(Path(model_path).relative_to(root)),
                           'inputs': [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)}
                                      for x in self.session.get_inputs()],
                           'outputs': [{'name': x.name, 'shape': list(x.shape)}
                                       for x in self.session.get_outputs()],
                           'runMilliseconds': [], 'allFinite': True}
            report['sessions'].append(self.record)
            save()

        def __getattr__(self, name):
            return getattr(self.session, name)

        def run(self, names, feeds):
            assert all(np.isfinite(value).all() for value in feeds.values())
            start = time.perf_counter()
            values = self.session.run(names, feeds)
            self.record['runMilliseconds'].append((time.perf_counter() - start) * 1000)
            if not all(np.isfinite(value).all() for value in values):
                self.record['allFinite'] = False
                save()
                raise ValueError('AXCL returned NaN or Inf')
            if len(self.record['runMilliseconds']) % 50 == 0:
                save()
            return values

    def wav(name, pcm):
        # Preserve the same amplitude scale for every input and output.
        quantized = np.clip(np.rint(pcm), -32768, 32767).astype('<i2')
        with wave.open(str(out / name), 'wb') as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(48000)
            handle.writeframes(quantized.tobytes())

    axengine.InferenceSession = MeasuredSession
    try:
        source = root / 'python/sample_speech.pcm'
        pcm = np.fromfile(source, dtype='<f4')
        assert len(pcm) > 0 and len(pcm) % 480 == 0 and np.isfinite(pcm).all()
        report['source'] = {'path': 'python/sample_speech.pcm',
                            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                            'samples': len(pcm), 'seconds': len(pcm) / 48000}
        rng = np.random.default_rng(20260927)
        noise = rng.standard_normal(len(pcm)).astype(np.float32)
        noise *= np.sqrt(np.mean(pcm.astype(np.float64) ** 2) /
                         np.mean(noise.astype(np.float64) ** 2)) / (10 ** (6 / 20))
        report['noiseRecipe'] = {'seed': 20260927, 'addedNoisePowerDbBelowSource': 6,
                                'note': 'Synthetic noise relative to the source power; source is not an independently verified clean reference.'}
        denoiser = RNNoiseDenoiser(str(root / 'rnnoise_ax650/model.axmodel'), providers=[provider])
        for label, signal in [('official', pcm), ('added-noise', pcm + noise),
                              ('silence', np.zeros_like(pcm))]:
            wav(label + '-input.wav', signal)
            generated, times, frame_calls, vads = [], [], [], []
            for repeat in range(2):
                denoiser.reset()
                before = len(report['sessions'][0]['runMilliseconds'])
                start = time.perf_counter()
                audio, probabilities = denoiser.process(signal)
                times.append(time.perf_counter() - start)
                frame_calls.append(len(report['sessions'][0]['runMilliseconds']) - before)
                assert audio.shape == signal.shape and np.isfinite(audio).all()
                assert np.isfinite(probabilities).all()
                assert (probabilities >= 0).all() and (probabilities <= 1).all()
                audio.astype('<f4').tofile(out / f'{label}-repeat-{repeat+1}.pcm')
                np.save(out / f'{label}-vad-{repeat+1}.npy', probabilities)
                generated.append(audio.copy())
                vads.append(probabilities.copy())
            wav(label + '-output.wav', generated[0])
            row = {'name': label, 'samples': len(signal), 'seconds': len(signal) / 48000,
                   'frames': len(signal) // 480, 'processSeconds': times, 'npuCallsPerRepeat': frame_calls,
                   'repeatedOutputEqual': bool(np.array_equal(generated[0], generated[1])),
                   'repeatedVadEqual': bool(np.array_equal(vads[0], vads[1])),
                   'outputPeak': float(np.max(np.abs(generated[0]))),
                   'outputRms': float(np.sqrt(np.mean(generated[0].astype(np.float64) ** 2))),
                   'vadAbove05Frames': int(np.count_nonzero(vads[0] > 0.5)),
                   'vadMin': float(vads[0].min()), 'vadMax': float(vads[0].max()),
                   'wavClippedSamples': int(np.count_nonzero(np.abs(generated[0]) > 32767)),
                   'input': label + '-input.wav', 'output': label + '-output.wav'}
            report['results'].append(row)
            save()
            print(json.dumps(row), flush=True)
        report['completed'] = True
        save()
    finally:
        axengine.InferenceSession = original


if __name__ == '__main__':
    main()
