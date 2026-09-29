"""InternVL3.5-1B: fixed upstream Python pipeline with explicit AXCL sessions."""
import argparse
import datetime
import gc
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import axengine
import numpy as np
from ml_dtypes import bfloat16
from transformers import AutoConfig, AutoTokenizer

MID = 'InternVL3_5-1B'
REVISION = 'ead75a3befa5b9c17b97bc0093c34db1b72c1d99'
PROVIDER = 'AXCLRTExecutionProvider'
SOURCE_HASHES = {
    'infer_axmodel.py': '649000c110674ee5e3210e1505bf74174715ea5562bf6b75a02c81ef5865449b',
    'utils/infer_func.py': 'fdef099d637b350bcb4c843c1b0a294bcbcd75927ce85f69306976c7e8ef6d9e',
}
SYSTEM = '你是由上海人工智能实验室联合商汤科技开发的书生多模态大模型, 英文名叫 InternVL3, 是一个有用无害的人工智能助手, 擅长思考和回答用户的问题. 请你在回答问题时使用简体中文.'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-new-tokens', type=int, default=96)
    p.add_argument('--question', help='Run one custom question instead of fixed samples')
    p.add_argument('--image', type=Path, help='Optional image for the custom question')
    p.add_argument('--first-only', action='store_true', help='Run the first fixed sample')
    a = p.parse_args()
    assert 1 <= a.max_new_tokens <= 256
    assert not a.image or a.question, '--image requires --question'
    root, out = a.model_dir.resolve(), a.output.resolve()
    assert PROVIDER in axengine.get_available_providers()
    for rel, digest in SOURCE_HASHES.items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest, rel
    out.mkdir(parents=True, exist_ok=False)
    used = out / 'source'; used.mkdir()
    # These imports are unused by the upstream AXMODEL path. Avoid loading CPU model/export tooling.
    changes = [{'before': 'from transformers import AutoProcessor, AutoModelForImageTextToText\n', 'after': ''},
               {'before': 'import onnx\n', 'after': ''}]
    source_text = (root / 'infer_axmodel.py').read_text()
    for change in changes:
        assert source_text.count(change['before']) == 1
        source_text = source_text.replace(change['before'], change['after'])
    source_path = used / 'infer_axmodel_used.py'; source_path.write_text(source_text)
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('internvl35_official', source_path)
    official = importlib.util.module_from_spec(spec); spec.loader.exec_module(official)
    import utils.infer_func as inference
    tokenizer_path = root / 'internvl3-5_tokenizer'
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    config = AutoConfig.from_pretrained(tokenizer_path, trust_remote_code=True, local_files_only=True)
    cfg = config.llm_config
    embeds = np.load(root / 'internvl3-5_axmodel/model.embed_tokens.weight.npy', mmap_mode='r')
    assert embeds.ndim == 2 and embeds.shape[1] == cfg.hidden_size
    assert tokenizer.convert_tokens_to_ids('<img>') == 151669
    image_context = tokenizer.convert_tokens_to_ids('<IMG_CONTEXT>')
    eos_ids = cfg.eos_token_id if isinstance(cfg.eos_token_id, list) else [cfg.eos_token_id]
    eos_ids = list(set([i for i in eos_ids if i is not None] + [tokenizer.eos_token_id]))
    record = {'modelId': MID, 'revision': REVISION, 'provider': PROVIDER, 'completed': False,
              'sessions': [], 'samples': [], 'sourceHashes': SOURCE_HASHES, 'sourceChanges': changes,
              'usedSourceSha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
              'maxNewTokens': a.max_new_tokens, 'imageTiles': 1, 'imageTokensPerTile': 256,
              'modelConfig': {'hiddenSize': cfg.hidden_size, 'layers': cfg.num_hidden_layers,
                              'headDim': cfg.head_dim, 'kvHeads': cfg.num_key_value_heads},
              'eosTokenIds': eos_ids, 'embeddingShape': list(embeds.shape),
              'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def save():
        (out / 'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')

    factory = axengine.InferenceSession

    class Measured:
        def __init__(self, path):
            path = Path(path)
            start = time.perf_counter()
            self.session = factory(str(path), providers=[PROVIDER])
            actual = self.session.get_providers()
            assert actual == PROVIDER or actual == [PROVIDER], actual
            self.row = {'model': path.relative_to(root).as_posix(), 'provider': PROVIDER,
                        'loadSeconds': time.perf_counter() - start,
                        'weightSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'allFinite': True, 'runMilliseconds': [], 'shapeGroups': {}}
            record['sessions'].append(self.row); save()

        def run(self, names, feed, shape_group=0):
            assert all(np.isfinite(v).all() for v in feed.values())
            start = time.perf_counter()
            values = self.session.run(names, feed, shape_group=shape_group)
            self.row['runMilliseconds'].append((time.perf_counter() - start) * 1000)
            finite = bool(all(np.isfinite(v).all() for v in values)); self.row['allFinite'] &= finite
            key = str(shape_group)
            if key not in self.row['shapeGroups']:
                self.row['shapeGroups'][key] = {'calls': 0,
                    'inputs': {k: {'shape': list(v.shape), 'dtype': str(v.dtype)} for k, v in feed.items()},
                    'outputs': [{'shape': list(v.shape), 'dtype': str(v.dtype)} for v in values]}
            self.row['shapeGroups'][key]['calls'] += 1
            assert finite, 'Non-finite inference output: ' + self.row['model']
            return values

    class OutputLimit(Exception):
        pass

    inputs = [{'question': '图中是什么动物？只用一个词回答。', 'image': 'examples/image_0.jpg'},
              {'question': '请用一句中文描述图片中看见的内容。', 'image': 'examples/image_1.jpg'},
              {'question': '2加3等于多少？只回答数字。', 'image': None}]
    if a.question:
        inputs = [{'question': a.question, 'image': str(a.image.resolve()) if a.image else None}]
    elif a.first_only:
        inputs = inputs[:1]
    manager = vit = None
    try:
        inference.InferenceSession = Measured
        manager = inference.InferManager(cfg, str(root / 'internvl3-5_axmodel'), max_seq_len=2047)
        vit = Measured(root / 'vit-models/internvl_vit_model_1x3x448x448.axmodel')
        original_post = manager.post_process
        generated = []

        def counted_post(logits, *args, **kwargs):
            if len(generated) >= a.max_new_tokens:
                raise OutputLimit()
            result = original_post(logits, *args, **kwargs)
            generated.append(int(result[0]))
            return result
        manager.post_process = counted_post
        for index, sample in enumerate(inputs, 1):
            for cache in manager.k_caches + manager.v_caches:
                cache.fill(0)
            generated.clear(); np.random.seed(0)
            call_start = [len(s['runMilliseconds']) for s in record['sessions']]
            started = time.perf_counter()
            row = {'input': sample['question'], 'images': []}
            features = []
            if sample['image']:
                image_path = root / sample['image']
                pixel_values = official.load_image(str(image_path), input_size=448, max_num=1)
                pixels = pixel_values.numpy()
                assert list(pixels.shape) == [1, 3, 448, 448]
                t = time.perf_counter()
                features.append(vit.run(None, {'image': pixels})[0].copy())
                row['imageEncodeSeconds'] = time.perf_counter() - t
                filename = f'input-{index}' + image_path.suffix.lower()
                shutil.copy2(image_path, out / filename)
                row['images'].append({'file': filename, 'source': sample['image'],
                                      'sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
                                      'pixelTensorSha256': hashlib.sha256(pixels.tobytes()).hexdigest()})
            prompt = '<|im_start|>system\n' + SYSTEM + '<|im_end|>\n<|im_start|>user\n' + sample['question']
            for _ in features:
                prompt += '\n<img>' + '<IMG_CONTEXT>' * 256 + '</img>\n'
            prompt += '<|im_end|>\n<|im_start|>assistant\n'
            token_ids = tokenizer.encode(prompt)
            assert 0 < len(token_ids) <= 1023, 'Prefill context limit exceeded'
            assert len(token_ids) % 128 != 0, 'This upstream prefill implementation needs a nonempty last chunk'
            row.update(prompt=prompt, inputTokenIds=token_ids.copy(), inputTokens=len(token_ids))
            assert token_ids.count(image_context) == 256 * len(features)
            prefill_data = np.take(embeds, token_ids, axis=0).astype(bfloat16)
            positions = np.where(np.array(token_ids) == 151669)[0].tolist()
            assert len(positions) == len(features)
            for pos, feature in zip(positions, features):
                assert feature.shape == (1, 256, cfg.hidden_size)
                prefill_data[pos + 1:pos + 257] = feature[0]
            t = time.perf_counter()
            token_ids = manager.prefill(tokenizer, token_ids, prefill_data, slice_len=128)
            row['prefillSeconds'] = time.perf_counter() - t
            row['firstTokenSeconds'] = time.perf_counter() - started
            stop = 'eos'
            if generated[-1] not in eos_ids:
                try:
                    manager.decode(tokenizer, token_ids, embeds, slice_len=128, eos_token_id=eos_ids, stream=False)
                except OutputLimit:
                    stop = 'length'
                else:
                    if generated[-1] not in eos_ids:
                        stop = 'context'
            row['generationSeconds'] = time.perf_counter() - started
            row.update(outputTokenIds=generated.copy(), output=tokenizer.decode(generated, skip_special_tokens=True),
                       stopReason=stop, hitEos=stop == 'eos', generatedTokens=len(generated),
                       sessionCalls=[len(s['runMilliseconds']) - count for s, count in zip(record['sessions'], call_start)])
            assert row['output'].strip(), 'Empty model response'
            record['samples'].append(row); save()
            print(json.dumps(row, ensure_ascii=False), flush=True)
        record['completed'] = all(s['hitEos'] for s in record['samples'])
        assert record['completed'], 'One or more responses did not reach EOS'
    except BaseException as e:
        record['error'] = repr(e); raise
    finally:
        inference.InferenceSession = factory
        manager = vit = None
        gc.collect()
        record['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat(); save()


if __name__ == '__main__':
    main()
