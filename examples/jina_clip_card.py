"""Compare multilingual captions with official Jina-CLIP-v2 AXCL encoders."""
import argparse
import hashlib
import importlib
import json
import os
import sys
import time
import types
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import axengine
import numpy as np
import torch
from PIL import Image
from transformers import AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument('--model-dir', type=Path, required=True)
p.add_argument('--processor-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--image', type=Path)
p.add_argument('--text', action='append')
a = p.parse_args()
root, code, out = a.model_dir.resolve(), a.processor_dir.resolve(), a.output.resolve()
assert not out.exists(), 'Choose a new result directory'
processor_hashes = {'processing_clip.py': '4e876fe55882f664bf59e354fb0cf29ac6b542f35cafaa4b681b506730c4ed92',
                    'transform.py': '3dbae796192429c203db6840ade96f4a57397e47719675fd28266f7c301906ca'}
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, value in processor_hashes.items():
    assert sha(code / name) == value, 'Processor version differs: ' + name
source = root / 'run_axmodel.py'
assert sha(source) == '4180135298358cc8d0903b7e084e8f98091c69a11420d94c6a050895c34dfaa4'
package = types.ModuleType('jina_verified_processor')
package.__path__ = [str(code)]
sys.modules[package.__name__] = package
JinaCLIPImageProcessor = importlib.import_module(package.__name__ + '.processing_clip').JinaCLIPImageProcessor
helpers = {'__name__': 'jina_official_helpers', 'truncate_dim': 512}
exec(compile(source.read_text('utf-8'), str(source), 'exec'), helpers)
assert 'AXCLRTExecutionProvider' in axengine.get_available_providers()
torch.set_num_threads(2)
tokenizer = AutoTokenizer.from_pretrained(str(root / 'jina-clip-v2'), local_files_only=True, trust_remote_code=False)
texts = a.text or ['beautiful sunset over the beach', '蓝蓝的天空和海面，在夕阳的照射下，显得非常美丽',
                  '一群人在沙滩上散步', 'A red car parked on a city street.', '一只猫坐在书桌上。',
                  'Snow-covered mountains under a cloudy sky.']
image_path = (a.image or root / 'beach1.jpg').resolve()
im = Image.open(image_path).convert('RGB')
out.mkdir(parents=True)
im.save(out / 'input.png')
report = {'modelId': 'jina-clip-v2', 'provider': 'AXCLRTExecutionProvider', 'completed': False,
          'sourceSha256': sha(source), 'processorRevision': '39e6a55ae971b59bea6e44675d237c99762e7ee2',
          'processorHashes': processor_hashes, 'inputImageSha256': sha(image_path), 'savedImageSha256': sha(out / 'input.png'),
          'texts': texts, 'embeddingDimensions': 512, 'textContext': 50, 'inputTokenIds': [],
          'sessions': [], 'variants': []}

def save():
    (out / 'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

class Measured:
    def __init__(self, weight):
        t = time.perf_counter()
        self.session = axengine.InferenceSession(str(root / weight), providers=['AXCLRTExecutionProvider'])
        self.record = {'model': weight, 'weightSha256': sha(root / weight), 'loadSeconds': time.perf_counter() - t,
                       'allFinite': True, 'runMilliseconds': [],
                       'inputs': [{'name': m.name, 'shape': list(m.shape), 'dtype': str(m.dtype)} for m in self.session.get_inputs()],
                       'outputs': [{'name': m.name, 'shape': list(m.shape)} for m in self.session.get_outputs()]}
        report['sessions'].append(self.record)
        self.raw = []

    def get_inputs(self):
        return self.session.get_inputs()

    def run(self, names, feeds):
        for m in self.session.get_inputs():
            assert feeds[m.name].shape == tuple(m.shape) and feeds[m.name].dtype == np.dtype(m.dtype), (m.name, feeds[m.name].shape, m.shape)
        t = time.perf_counter()
        result = self.session.run(names, feeds)
        self.record['runMilliseconds'].append((time.perf_counter() - t) * 1000)
        assert all(np.isfinite(v).all() for v in result)
        self.raw.append(result[0].copy())
        return result

text_session = Measured('text_encoder.axmodel')
text_embeddings = []
pad_token = tokenizer.get_added_vocab()['<pad>']
for text in texts:
    tokens = tokenizer([text], return_tensors='pt', padding=True, max_length=512, truncation=False).input_ids
    assert tokens.shape[1] <= 50, 'Caption exceeds 50 tokens; shorten it'
    ids = torch.nn.functional.pad(tokens, (0, 50 - tokens.shape[1]), value=pad_token).numpy().astype(np.int32)
    report['inputTokenIds'].append(ids[0].tolist())
    text_embeddings.append(helpers['run_text_encoder'](text_session, ids)[0])
repeat_text = helpers['run_text_encoder'](text_session, np.array([report['inputTokenIds'][0]], dtype=np.int32))[0]
report['textRepeatExact'] = np.array_equal(text_session.raw[0], text_session.raw[-1])
text_embeddings = np.stack(text_embeddings)
arrays = {'text': text_embeddings, 'raw_text': np.concatenate(text_session.raw), 'repeat_text': repeat_text}
for size, weight in [(512, 'image_encoder.axmodel'), (224, 'image_encoder_224x224.axmodel')]:
    # Same pinned official processor/config; override only image size for the 224 model.
    config = json.loads((root / 'jina-clip-v2/preprocessor_config.json').read_text('utf-8'))
    config['size'] = size
    processor = JinaCLIPImageProcessor(**config)
    pixels = processor([im]).pixel_values.numpy()
    image_session = Measured(weight)
    embeddings = [helpers['run_image_encoder'](image_session, pixels) for _ in range(2)]
    scores = text_embeddings @ embeddings[0][0]
    order = np.argsort(-scores).tolist()
    arrays[f'image_{size}'] = embeddings[0]
    arrays[f'raw_image_{size}'] = image_session.raw[0]
    arrays[f'repeat_image_{size}'] = image_session.raw[1]
    arrays[f'pixels_{size}'] = pixels
    report['variants'].append({'size': size, 'weight': weight, 'inputShape': list(pixels.shape),
                               'repeatExact': np.array_equal(*image_session.raw),
                               'scores': scores.tolist(), 'descendingOrder': order,
                               'pixelSha256': hashlib.sha256(pixels.tobytes()).hexdigest()})
    save()
    print(size, [(texts[i], float(scores[i])) for i in order], flush=True)
    del image_session
np.savez_compressed(out / 'embeddings.npz', **arrays)
report['embeddingFileSha256'] = sha(out / 'embeddings.npz')
report['completed'] = True
save()
