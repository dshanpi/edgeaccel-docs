"""Run the official MobileSAM point/box examples on AXCL and preserve actual masks."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import axengine
import cv2
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root, out = a.model_dir.resolve(), a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
report = {'modelId': 'MobileSAM', 'provider': 'AXCLRTExecutionProvider',
          'completed': False, 'sessions': [], 'results': []}
def save():
    (out / 'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

original_session = axengine.InferenceSession
class MeasuredSession:
    def __init__(self, path):
        start = time.perf_counter()
        self.session = original_session(path, providers=['AXCLRTExecutionProvider'])
        self.record = {'model': Path(path).relative_to(root).as_posix(),
                       'loadSeconds': time.perf_counter() - start,
                       'inputs': [{'name': m.name, 'shape': list(m.shape), 'dtype': str(m.dtype)} for m in self.session.get_inputs()],
                       'outputs': [{'name': m.name, 'shape': list(m.shape)} for m in self.session.get_outputs()],
                       'runMilliseconds': [], 'allFinite': True}
        report['sessions'].append(self.record)
        save()
    def __getattr__(self, name):
        return getattr(self.session, name)
    def run(self, names, feeds):
        for meta in self.session.get_inputs():
            v = feeds[meta.name]
            assert list(v.shape) == list(meta.shape) and v.dtype == np.dtype(meta.dtype), (meta.name, v.shape, v.dtype)
        start = time.perf_counter()
        values = self.session.run(names, feeds)
        self.record['runMilliseconds'].append((time.perf_counter() - start) * 1000)
        self.record['allFinite'] &= all(np.isfinite(v).all() for v in values)
        save()
        assert self.record['allFinite'], 'Non-finite AXCL output'
        return values

axengine.InferenceSession = MeasuredSession
sys.path.insert(0, str(root / 'python_ax'))
from sam_encoder import SAMEncoder
from sam_decoder import SAMDecoder
encoder = SAMEncoder(str(root / 'ax_model/mobile_sam_encoder_650.axmodel'))
decoder = SAMDecoder(str(root / 'ax_model/mobile_sam_decoder_650.axmodel'))
cases = [('test.jpg', [(910,641), (1488,607), (579,704)],
          [(750,211,380,940), (479,482,191,518), (1345,333,289,701), (1,357,311,751)]),
         ('truck.jpg', [(500,375)],
          [(1375,550,275,250), (75,275,1650,575), (425,600,275,275), (1240,675,160,75)])]
for image_name, points, boxes in cases:
    source = root / 'images' / image_name
    image = cv2.imread(str(source))
    assert image is not None
    h, w = image.shape[:2]
    name = source.stem
    cv2.imwrite(str(out / f'{name}-input.png'), image)
    embeddings, scale = encoder.encode(image)
    repeated, repeated_scale = encoder.encode(image)
    assert scale == repeated_scale
    encoder_equal = all(np.array_equal(x,y) for x,y in zip(embeddings,repeated))
    assert encoder_equal
    del repeated
    for mode, prompts in [('point', points), ('box', boxes)]:
        for i, prompt in enumerate(prompts):
            kwargs = {mode: prompt, 'scale': scale}
            values = decoder.decode(embeddings[0], **kwargs)
            repeat = decoder.decode(embeddings[0], **kwargs)
            equal = all(np.array_equal(x,y) for x,y in zip(values,repeat))
            assert equal
            scores, masks = values
            index = int(scores.argmax())
            mask = masks[:,index,:,:][0]
            # Same threshold-before-resize and top-left crop as official main.py.
            mask_u8 = np.where(mask > 0, 255, 0).astype(np.uint8)
            mask_u8 = cv2.resize(mask_u8, (max(w,h), max(w,h)), interpolation=cv2.INTER_LINEAR)[:h,:w]
            assert mask_u8.shape == (h,w)
            stem = f'{name}-{mode}-{i}'
            cv2.imwrite(str(out / f'{stem}-mask.png'), mask_u8)
            drawn = image.copy()
            if mode == 'point':
                cv2.circle(drawn, tuple(prompt), 10, (0,255,0), -1)
            else:
                x,y,bw,bh = prompt
                cv2.rectangle(drawn, (x,y), (x+bw,y+bh), (0,255,0), 2)
            overlay = np.zeros_like(image)
            overlay[mask_u8 > 0] = (0,255,0)
            cv2.imwrite(str(out / f'{stem}-overlay.png'), cv2.addWeighted(drawn,1,overlay,.5,0))
            np.savez_compressed(out / f'{stem}-raw.npz', scores=scores, masks=masks)
            report['results'].append({'image': image_name, 'imageSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'inputShape': list(image.shape), 'mode': mode, 'prompt': list(prompt), 'scale': scale,
                'selectedMask': index, 'predictedScores': scores.tolist(), 'maskPixels': int(np.count_nonzero(mask_u8)),
                'maskFraction': float(np.count_nonzero(mask_u8)/(h*w)), 'encoderRepeatExact': encoder_equal,
                'decoderRepeatExact': equal, 'stem': stem})
            save()
report['completed'] = True
save()
print(json.dumps(report,ensure_ascii=False))
