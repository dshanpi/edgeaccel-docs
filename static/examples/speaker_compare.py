"""Compare the three official 3D-Speaker samples with the AXCL backend.

FBank settings follow modelscope/3D-Speaker speakerlab/process/processor.py:
80 bins, 16 kHz, dither=0, mean normalization before crop/padding.
Only the trailing missing frames are padded; existing speech is preserved.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import axengine as axe
import numpy as np
import soundfile as sf
import torch
import torchaudio.compliance.kaldi as kaldi


def cosine(a, b):
    a, b = a.ravel(), b.ravel()
    assert np.isfinite(a).all() and np.isfinite(b).all()
    assert np.linalg.norm(a) > 0 and np.linalg.norm(b) > 0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, default=Path('.'))
    p.add_argument('--out', type=Path, default=Path('speaker-result.json'))
    p.add_argument('--reference', action='store_true', help='Also compare the same inputs with the matching CPU ONNX models')
    args = p.parse_args()
    torch.set_num_threads(2)
    wavs = ['speaker1_a_cn_16k.wav', 'speaker1_b_cn_16k.wav', 'speaker2_a_cn_16k.wav']
    features, inputs = [], []
    for name in wavs:
        path = args.model_dir / 'wavs' / name
        audio, sr = sf.read(path, dtype='float32', always_2d=True)
        assert sr == 16000 and len(audio) > 0, (name, sr)
        waveform = torch.from_numpy(audio[:, 0].copy()).unsqueeze(0)
        feat = kaldi.fbank(waveform, num_mel_bins=80, sample_frequency=16000, dither=0)
        feat = (feat - feat.mean(0, keepdim=True)).numpy()
        features.append(feat)
        inputs.append({'file': name, 'sampleRate': sr, 'channels': audio.shape[1], 'seconds': len(audio)/sr,
                       'fbankFrames': len(feat), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    record = {'inputs': inputs, 'provider': 'AXCLRTExecutionProvider', 'models': []}
    for model in ['ecapa-tdnn', 'res2netv2']:
        start = time.perf_counter()
        session = axe.InferenceSession(str(args.model_dir / 'ax650' / (model + '.axmodel')),
                                       providers=['AXCLRTExecutionProvider'])
        load_ms = (time.perf_counter() - start)*1000
        meta = session.get_inputs()[0]
        shape = list(meta.shape)
        assert shape in ([1, 360, 80], [1, 360, 80, 1]), shape
        frames = shape[1]
        tensors = [np.pad(f[:frames], ((0, max(0, frames-len(f))), (0, 0)))[None].astype(np.float32) for f in features]
        vectors, times = [], []
        for tensor in tensors:
            start = time.perf_counter()
            ax_input = tensor[..., None] if len(shape) == 4 else tensor
            vectors.append(session.run(None, {meta.name: ax_input})[0])
            times.append((time.perf_counter() - start)*1000)
        item = {'model': model, 'inputShape': shape, 'outputShape': list(vectors[0].shape),
                'loadMilliseconds': load_ms, 'runMilliseconds': times,
                'sameSpeaker': cosine(vectors[0], vectors[1]),
                'differentSpeaker': cosine(vectors[0], vectors[2]),
                'embeddings': [v.ravel().tolist() for v in vectors]}
        if args.reference:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            cpu = ort.InferenceSession(str(args.model_dir/(model+'.onnx')), sess_options=options,
                                       providers=['CPUExecutionProvider'])
            cpu_shape = cpu.get_inputs()[0].shape
            assert len(cpu_shape) in (3, 4), cpu_shape
            refs = [cpu.run(None, {cpu.get_inputs()[0].name: t[:, None] if len(cpu_shape) == 4 else t})[0] for t in tensors]
            item['onnxInputShape'] = cpu_shape
            item['onnxComparison'] = {'embeddingCosine': [cosine(a,b) for a,b in zip(vectors, refs)],
                                      'sameSpeaker': cosine(refs[0], refs[1]),
                                      'differentSpeaker': cosine(refs[0], refs[2])}
            del cpu
        record['models'].append(item)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({k:v for k,v in item.items() if k!='embeddings'}, ensure_ascii=False), flush=True)
        del session


if __name__ == '__main__':
    main()
