"""Fixed-label ViT/Chinese-CLIP bundles on AXCL; no arbitrary text claim."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import axengine
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms

SHA = {
    'zh': ['6f33786ab988ca22dbc883c9fa6ebfa842a425445e4dac945c30069a6d9d5cf8', '6278e99001c198082b59219b163f7136d3049bca223be9176678ac6031348cde'],
    'en': ['3717a2c6d1a3740ae9ddd2c65d5ff8dbbd016d84e6ec59bac7699766c9918d84', 'f9cc5b33883ed3bfec3fa7c4a34fac0af7e8764c284db4d12dbf923fd21eff97'],
}
VOCAB_SHA = {'zh': '45bbac6b341c319adc98a532532882e91a9cefc0329aa57bac9ae761c27b291c', 'en': 'e30e57b6f1e47616982ef898d8922be24e535b4fa3d0110477b3a6f02ebbae7d'}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--sample-dir', type=Path, required=True)
    p.add_argument('--language', choices=['zh', 'en'], required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root, source, out = a.model_dir.resolve(), a.sample_dir.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cn = a.language == 'zh'
    mid = 'ViT-L-14-336-CN__axera' if cn else 'ViT-L-14-336__axera'
    labels = ['小鸟', '猫咪', '狗子'] if cn else ['bird', 'cat', 'dog']
    cfg = json.loads((root/'config.json').read_text())
    prep = json.loads((root/'visual/preprocess_cfg.json').read_text())
    assert prep['size'] == [336, 336] and prep['mode'] == 'RGB'
    assert prep['interpolation'] == 'bicubic' and prep['resize_mode'] == 'shortest'
    assert cfg['text_cfg']['context_length'] == (52 if cn else 77)
    assert cfg['text_cfg']['vocab_size'] == (21128 if cn else 49408)
    vocab_path = source/('cn_vocab.txt' if cn else 'vocab.txt')
    assert sha(vocab_path) == VOCAB_SHA[a.language]
    lines = vocab_path.read_bytes().decode('utf-8').split('\n')
    if lines[-1] == '': lines.pop()
    vocab = {}
    for i, token in enumerate(lines): vocab.setdefault(token, i)
    # Use C++ getline semantics: U+2028 is itself a vocabulary entry.
    provider = 'AXCLRTExecutionProvider'
    assert provider in axengine.get_available_providers()
    report = {'modelId': mid, 'provider': provider, 'completed': False,
              'labels': labels, 'language': a.language, 'sessions': [], 'tokens': [], 'results': [], 'inputs': [],
              'sampleSource': {'repo': 'AXERA-TECH/CLIP-ONNX-AX650-CPP', 'revision': '8a330cf1c3f7a881ba222f92d6485e5b6894f8d3'},
              'vocabulary': {'file': vocab_path.name, 'sha256': sha(vocab_path), 'lines': len(lines), 'scope': 'Official C++ fixed-label rules; no arbitrary-text BPE/WordPiece claim'},
              'config': cfg, 'preprocessConfig': prep,
              'bundleConfigurationHashes': {n: sha(root/n) for n in ['config.json', 'visual/preprocess_cfg.json', 'textual/tokenizer_config.json']},
              'bundledTokenizerUsed': False,
              'tokenizerNote': 'Chinese bundle CLIP tokenizer IDs exceed declared vocab; use official matched CN vocabulary.' if cn else 'Fixed candidate IDs from official C++ vocabulary, with zero-padding.'}
    raw = {}

    def save():
        (out/'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    class Session:
        def __init__(self, name, digest):
            assert sha(root/name) == digest
            self.session = axengine.InferenceSession(str(root/name), providers=[provider])
            self.inputs = self.session.get_inputs()
            assert len(self.inputs) == 1
            self.record = {'model': name, 'weightSha256': digest, 'runMilliseconds': [], 'allFinite': True,
                           'inputs': [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)} for x in self.inputs]}
            report['sessions'].append(self.record)

        def run(self, value):
            assert list(value.shape) == list(self.inputs[0].shape)
            assert value.dtype == np.dtype(self.inputs[0].dtype) and np.isfinite(value).all()
            start = time.perf_counter()
            result = self.session.run(None, {self.inputs[0].name: np.ascontiguousarray(value)})
            self.record['runMilliseconds'].append((time.perf_counter()-start)*1000)
            assert len(result) == 1 and result[0].shape == (1, 768)
            self.record['allFinite'] &= bool(np.isfinite(result[0]).all())
            save()
            assert self.record['allFinite']
            return result[0][0].copy()

    text = Session('textual/model.axmodel', SHA[a.language][0])
    vectors = []
    for label in labels:
        words = ([vocab[label]] if label in vocab else [vocab[c] for c in label]) if cn else [vocab[label+'</w>']]
        ids = [101, *words, 102] if cn else [49406, *words, 49407]
        assert min(ids) >= 0 and max(ids) < cfg['text_cfg']['vocab_size']
        tensor = np.zeros((1, cfg['text_cfg']['context_length']), np.int32)
        tensor[0, :len(ids)] = ids
        pair = np.stack([text.run(tensor), text.run(tensor)])
        assert np.array_equal(pair[0], pair[1])
        vectors.append(pair)
        report['tokens'].append({'text': label, 'ids': ids, 'paddedLength': tensor.shape[1]})
    raw['textRaw'] = np.stack(vectors)
    text_vectors = raw['textRaw'][:, 0]
    image_session = Session('visual/model.axmodel', SHA[a.language][1])
    assert list(image_session.inputs[0].shape) == [1, 3, 336, 336]
    crop = transforms.Compose([transforms.Resize(336, interpolation=transforms.InterpolationMode.BICUBIC), transforms.CenterCrop(336)])
    names = ['bird.jpg', 'cat.jpg', 'dog-chai.jpeg']
    images = []
    for name in names:
        path = source/'images'/name
        bgr = cv2.imread(str(path)); assert bgr is not None
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb).save(out/(Path(name).stem+'-input.png'))
        images.append(rgb)
        report['inputs'].append({'path': 'images/'+name, 'sha256': sha(path), 'height': rgb.shape[0], 'width': rgb.shape[1]})
    for method in ['bundle-bicubic-center-crop', 'official-cpp-direct-resize']:
        pairs, tensors = [], []
        for name, rgb in zip(names, images):
            pixels = np.array(crop(Image.fromarray(rgb))) if method.startswith('bundle') else cv2.resize(rgb, (336, 336), interpolation=cv2.INTER_LINEAR)
            Image.fromarray(pixels).save(out/(Path(name).stem+'-'+method+'.png'))
            mean = np.array(prep['mean'], np.float32)*np.float32(255)
            inverse_std = np.float32(1)/(np.array(prep['std'], np.float32)*np.float32(255))
            tensor = ((pixels.astype(np.float32)-mean)*inverse_std).transpose(2, 0, 1)[None]
            pair = np.stack([image_session.run(tensor), image_session.run(tensor)])
            assert np.array_equal(pair[0], pair[1])
            pairs.append(pair); tensors.append(tensor)
        raw[method+'Raw'] = np.stack(pairs)
        raw[method+'Inputs'] = np.concatenate(tensors)
        vision = raw[method+'Raw'][:, 0]
        vn, tn = np.linalg.norm(vision, axis=1, keepdims=True), np.linalg.norm(text_vectors, axis=1, keepdims=True)
        assert (vn > 0).all() and (tn > 0).all()
        cosine = (vision/vn)@(text_vectors/tn).T
        logits = cosine*np.float32(100)
        scores = np.exp(logits-logits.max(axis=1, keepdims=True)); scores /= scores.sum(axis=1, keepdims=True)
        row = {'method': method, 'cosine': cosine.tolist(), 'candidateSoftmax': scores.tolist(), 'topLabels': [labels[i] for i in cosine.argmax(axis=1)],
               'repeatedEmbeddingsEqual': True, 'imageNames': names, 'allTopLabelsMatch': bool(np.array_equal(cosine.argmax(axis=1), np.arange(3)))}
        report['results'].append(row); save(); print(json.dumps(row, ensure_ascii=False), flush=True)
    np.savez(out/'embeddings.npz', **raw)
    report['rawSha256'] = sha(out/'embeddings.npz')
    report['completed'] = True; save()


if __name__ == '__main__':
    main()
