"""Run the pinned Deformable-DETR sample through AXCL with its official preprocessing."""
import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path

import axengine
import numpy as np
from PIL import ImageDraw, ImageFont

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--threshold', type=float, default=0.6)
a = p.parse_args()
root, out = a.model_dir.resolve(), a.output.resolve()
assert 0 <= a.threshold <= 1
out.mkdir(parents=True, exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
spec = importlib.util.spec_from_file_location('official_detr', root / 'src/inference.py')
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)
start = time.perf_counter()
session = axengine.InferenceSession(str(root / 'output/detr.axmodel'), providers=['AXCLRTExecutionProvider'])
load_seconds = time.perf_counter() - start
meta = session.get_inputs()[0]
layout = 'NCHW' if meta.shape[1] == 3 else 'NHWC'
h, w = meta.shape[2:4] if layout == 'NCHW' else meta.shape[1:3]
tensor, raw, transform = upstream.preprocess_normalized(str(root / 'assets/bus.jpg'), h, w, layout)
assert list(tensor.shape) == list(meta.shape) and tensor.dtype == np.dtype(meta.dtype), (meta.shape, meta.dtype, tensor.dtype)
raw.save(out / 'input.png')
record = {'modelId': 'Deformable-Detr', 'provider': 'AXCLRTExecutionProvider',
          'loadSeconds': load_seconds, 'threshold': a.threshold, 'completed': False,
          'input': {'name': meta.name, 'shape': list(meta.shape), 'dtype': str(meta.dtype)},
          'inputImageSha256': hashlib.sha256((root / 'assets/bus.jpg').read_bytes()).hexdigest(),
          'normalizationEnabled': upstream.NORMALIZATION_ENABLED, 'results': []}
previous = None
for repeat in range(3):
    start = time.perf_counter()
    outputs = session.run(None, {meta.name: tensor})
    milliseconds = (time.perf_counter() - start) * 1000
    assert len(outputs) == 2 and all(np.isfinite(v).all() for v in outputs)
    dets, labels = outputs[0][0], outputs[1][0]
    assert dets.ndim == 2 and dets.shape[1] == 5 and len(dets) == len(labels)
    assert np.all((dets[:, 4] >= 0) & (dets[:, 4] <= 1))
    keep = dets[:, 4] >= a.threshold
    detections = []
    drawn = raw.copy()
    draw = ImageDraw.Draw(drawn)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 18)
    except OSError:
        font = ImageFont.load_default()
    for det, label in zip(dets[keep], labels[keep]):
        label = int(label)
        assert 0 <= label < len(upstream.CLASSES)
        box = det[:4] / transform['scale']
        box[0::2] = np.clip(box[0::2], 0, raw.width)
        box[1::2] = np.clip(box[1::2], 0, raw.height)
        assert box[2] >= box[0] and box[3] >= box[1]
        name = upstream.CLASSES[label]
        detections.append({'label': name, 'classId': label, 'score': float(det[4]), 'box': box.tolist()})
        draw.rectangle(box.tolist(), outline='lime', width=3)
        x, y = float(box[0]), float(box[1])
        draw.rectangle([x, y-20, x+100, y], fill='lime')
        draw.text((x+2, y-20), f'{name} {det[4]:.2f}', fill='black', font=font)
    equal = None if previous is None else all(np.array_equal(v, prev) for v, prev in zip(outputs, previous))
    record['results'].append({'inferenceMilliseconds': milliseconds, 'allFinite': True,
                              'rawEqualPrevious': equal, 'detections': detections,
                              'outputShapes': [list(v.shape) for v in outputs]})
    np.savez_compressed(out / f'raw-{repeat+1}.npz', **{f'output_{i}': v for i, v in enumerate(outputs)})
    previous = [v.copy() for v in outputs]
    drawn.save(out / f'output-{repeat+1}.png')
    (out / 'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
record['completed'] = True
(out / 'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False))
