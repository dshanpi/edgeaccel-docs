"""Run one official QRCode AX650 model through AXCL and save real detections."""
import argparse
import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

import axengine
import cv2
import numpy as np
from PIL import Image

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--weight', required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--images', nargs='*')
a = p.parse_args()
folder = a.model_dir.resolve()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
weight = folder / 'model/AX650' / a.weight
assert weight.is_file() and weight.resolve().is_relative_to(folder / 'model/AX650')
name = weight.name
family = ('DEIMv2' if name.startswith('deim') else 'Nanodet' if name.startswith('nanodet')
          else 'v5' if name.startswith('yolov5') else '26' if name.startswith('yolo26') else 'v8')
module_name = 'QRCode_axmodel_infer_' + family
file = folder / 'python' / (module_name + '.py')
source = file.read_text(encoding='utf-8')
# The imported vendor classes must create card sessions explicitly.
if family != 'DEIMv2':
    parameter = 'model_path' if family == 'v5' else 'model'
    old = f'axe.InferenceSession({parameter})'
    new = f'axe.InferenceSession({parameter}, providers=["AXCLRTExecutionProvider"])'
    if old in source:
        assert source.count(old) == 1
        backup = file.with_suffix('.py.upstream')
        if not backup.exists():
            backup.write_text(source, encoding='utf-8')
        file.write_text(source.replace(old, new), encoding='utf-8')
    else:
        assert new in source, 'Unexpected vendor source version'
sys.path.insert(0, str(folder / 'python'))
vendor = importlib.import_module(module_name)
decoder = vendor.QRCodeDecoder()
record = {'weight': 'model/AX650/' + name, 'family': family,
          'weightSha256': hashlib.sha256(weight.read_bytes()).hexdigest(),
          'provider': 'AXCLRTExecutionProvider', 'samples': []}
def save():
    (out / 'qrcode-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
start = time.monotonic()
if family == 'DEIMv2':
    session = axengine.InferenceSession(str(weight), providers=['AXCLRTExecutionProvider'])
    size = session.get_inputs()[0].shape[2]
    processor = vendor.PostProcessor(use_focal_loss=True, num_classes=1, num_top_queries=100)
    processor.deploy()
elif family == 'v5':
    detector = vendor.Yolov5QRcodeDetector(str(weight))
    session = detector.model
elif family == 'Nanodet':
    detector = vendor.NanoDetONNXInfer(str(weight), imgsz=[416, 416])
    session = detector.session
else:
    detector = vendor.YOLOV8Detector(str(weight), imgsz=[640, 640])
    session = detector.session
record['loadSeconds'] = time.monotonic() - start
record['inputs'] = [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)} for x in session.get_inputs()]
record['outputs'] = [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)} for x in session.get_outputs()]
save()
images = [folder / 'images' / s for s in a.images] if a.images else sorted((folder / 'images').glob('*.jpg'))
assert images
for file in images:
    assert file.resolve().is_relative_to(folder / 'images')
    original = cv2.imread(str(file))
    assert original is not None
    start = time.monotonic()
    if family == 'DEIMv2':
        boxes, _ = vendor.process_image(session, Image.open(file).convert('RGB'), processor, size, 'femto')
    elif family == 'v5':
        tensor = detector.preprocess_image(original, img_size=[640, 640])
        values = detector.model_inference(tensor)
        assert all(np.isfinite(v).all() for v in values)
        boxes, _ = detector.postprocess(values, tensor.shape, original.copy())
    else:
        boxes, _ = detector.detect_objects(str(file), str(out))
    # Decode from the original pixels, before drawing boxes.
    decoded = []
    for crop in decoder.crop_qr_regions(original, boxes):
        decoded += decoder.decode_qrcode_pyzbar(crop['image'])
    elapsed = time.monotonic() - start
    reference = decoder.decode_qrcode_pyzbar(original)
    coordinate_boxes = [list(b[1:5]) if family == 'Nanodet' else list(b) for b in boxes]
    preview = original.copy()
    for index, b in enumerate(coordinate_boxes):
        x1, y1, x2, y2 = map(int, b)
        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 220, 0), 2)
        cv2.putText(preview, f'QR {index + 1}', (max(0, x1), max(18, y1)), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 90, 255), 2)
    assert cv2.imwrite(str(out / (file.stem + '.jpg')), preview)
    sample = {'file': file.name, 'inputSha256': hashlib.sha256(file.read_bytes()).hexdigest(),
              'boxes': [[int(v) for v in b] for b in coordinate_boxes],
              'decoded': [{'data': x['data'], 'type': x['type']} for x in decoded],
              'wholeImageCpuDecoded': [{'data': x['data'], 'type': x['type']} for x in reference],
              'seconds': elapsed}
    record['samples'].append(sample)
    save()
    print(file.name, 'boxes', len(boxes), 'decoded', len(decoded), flush=True)
record['exitCode'] = 0
save()
