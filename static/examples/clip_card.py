"""Fixed CLIP/CN-CLIP image-text examples on AXCL.

Preprocessing and vocabulary rules follow AXERA-TECH/CLIP-ONNX-AX650-CPP
commit 8a330cf1c3f7a881ba222f92d6485e5b6894f8d3 (axcl_runner).
This example tests the supplied labels, not arbitrary-text BPE tokenization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import axengine
import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', type=Path, required=True)
    parser.add_argument('--sample-dir', type=Path, required=True,
                        help='Pinned CLIP-ONNX-AX650-CPP checkout containing images/')
    parser.add_argument('--language', choices=['en', 'zh'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, samples, out = args.model_dir.resolve(), args.sample_dir.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    provider = 'AXCLRTExecutionProvider'
    if provider not in axengine.get_available_providers():
        raise RuntimeError('AXCLRTExecutionProvider unavailable')
    chinese = args.language == 'zh'
    labels = ['小鸟', '猫咪', '狗子'] if chinese else ['bird', 'cat', 'dog']
    text_file = 'cnclip_vit_l14_336px_text_u16.axmodel' if chinese else 'clip_vit_l14_336px_text_encoder_u16.axmodel'
    image_files = ['cnclip_vit_l14_336px_vision_u16.axmodel', 'cnclip_vit_l14_336px_vision_u16u8.axmodel'] if chinese else ['clip_vit_l14_336px_image_encoder_all_u16_fc_u8.axmodel']
    vocab_file = 'cn_vocab.txt' if chinese else 'vocab.txt'
    vocab = {}
    # Match C++ getline('\n'): U+2028 is a real CN-CLIP vocabulary token,
    # so str.splitlines() would silently shift every later token ID.
    lines = (root / vocab_file).read_bytes().decode('utf-8').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    for index, word in enumerate(lines):
        vocab.setdefault(word, index)
    report = {'task': 'clip', 'provider': provider, 'completed': False, 'language': args.language,
              'labels': labels, 'sessions': [], 'results': [],
              'sampleSource': {'repo': 'AXERA-TECH/CLIP-ONNX-AX650-CPP',
                               'revision': '8a330cf1c3f7a881ba222f92d6485e5b6894f8d3'},
              'inputs': [], 'tokens': []}

    def save():
        (out / 'deployment-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    class Session:
        def __init__(self, filename):
            self.session = axengine.InferenceSession(str(root / filename), providers=[provider])
            self.inputs = self.session.get_inputs()
            assert len(self.inputs) == 1
            self.record = {'model': filename,
                           'inputs': [{'name': x.name, 'shape': list(x.shape), 'dtype': str(x.dtype)} for x in self.inputs],
                           'outputs': [{'name': x.name, 'shape': list(x.shape)} for x in self.session.get_outputs()],
                           'runMilliseconds': [], 'allFinite': True}
            report['sessions'].append(self.record)
            save()

        def run(self, array):
            assert list(array.shape) == list(self.inputs[0].shape)
            assert array.dtype == np.dtype(self.inputs[0].dtype)
            assert np.isfinite(array).all()
            start = time.perf_counter()
            values = self.session.run(None, {self.inputs[0].name: np.ascontiguousarray(array)})
            self.record['runMilliseconds'].append((time.perf_counter() - start) * 1000)
            if not all(np.isfinite(x).all() for x in values):
                self.record['allFinite'] = False
                save()
                raise ValueError('Non-finite AXCL output')
            assert len(values) == 1 and values[0].shape == (1, 768)
            save()
            return values[0][0].copy()

    text = Session(text_file)
    length = 52 if chinese else 77
    assert list(text.inputs[0].shape) == [1, length]
    text_features = []
    for label in labels:
        if chinese:
            words = []
            for word in label.split(' '):
                words.extend([vocab[word]] if word in vocab else [vocab[c] for c in word])
            ids = [101, *words, 102]
        else:
            ids = [49406, *[vocab[word + '</w>'] for word in label.split(' ')], 49407]
        assert len(ids) <= length
        tensor = np.zeros((1, length), dtype=np.int32)
        tensor[0, :len(ids)] = ids
        outputs = [text.run(tensor) for _ in range(2)]
        assert np.array_equal(*outputs), 'Text embedding repeat differs'
        text_features.append(outputs[0])
        report['tokens'].append({'text': label, 'ids': ids, 'paddedLength': length})
    text_features = np.stack(text_features)
    np.save(out / 'text-features.npy', text_features)
    names = ['bird.jpg', 'cat.jpg', 'dog-chai.jpeg']
    images = []
    for name in names:
        path = samples / 'images' / name
        source = cv2.imread(str(path))
        assert source is not None
        cv2.imwrite(str(out / (Path(name).stem + '-input.png')), source)
        images.append(source)
        report['inputs'].append({'path': 'images/' + name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'height': source.shape[0], 'width': source.shape[1]})
    for filename in image_files:
        image_session = Session(filename)
        assert list(image_session.inputs[0].shape) == [1, 3, 336, 336]
        vectors = []
        for image in images:
            rgb = cv2.cvtColor(cv2.resize(image, (336, 336), interpolation=cv2.INTER_LINEAR), cv2.COLOR_BGR2RGB)
            mean = np.array([0.48145466, 0.4578275, 0.40821073], np.float32) * np.float32(255)
            inverse_std = np.float32(1) / (np.array([0.26862954, 0.26130258, 0.27577711], np.float32) * np.float32(255))
            tensor = ((rgb.astype(np.float32) - mean) * inverse_std).transpose(2, 0, 1)[None]
            outputs = [image_session.run(tensor) for _ in range(2)]
            assert np.array_equal(*outputs), 'Image embedding repeat differs'
            vectors.append(outputs[0])
        vectors = np.stack(vectors)
        np.save(out / (Path(filename).stem + '-features.npy'), vectors)
        image_norm = np.linalg.norm(vectors, axis=1, keepdims=True)
        text_norm = np.linalg.norm(text_features, axis=1, keepdims=True)
        assert (image_norm > 0).all() and (text_norm > 0).all()
        cosine = (vectors / image_norm) @ (text_features / text_norm).T
        logits = cosine * np.float32(100)
        scores = np.exp(logits - logits.max(axis=1, keepdims=True))
        scores /= scores.sum(axis=1, keepdims=True)
        assert np.isfinite(scores).all()
        row = {'imageModel': filename, 'textModel': text_file, 'imageNames': names,
               'cosine': cosine.tolist(), 'imageChoiceSoftmax': scores.tolist(),
               'topLabels': [labels[i] for i in scores.argmax(axis=1)],
               'expectedLabels': labels, 'allTopLabelsMatch': bool(np.array_equal(scores.argmax(axis=1), np.arange(3))),
               'repeatedEmbeddingsEqual': True, 'embeddingDimension': 768}
        report['results'].append(row)
        save()
        print(json.dumps(row, ensure_ascii=False), flush=True)
        del image_session
    report['completed'] = True
    save()


if __name__ == '__main__':
    main()
