"""SmolVLM-256M AX650 p128 weights, explicit AXCL single-image inference.

Prompt functions are extracted from the hash-checked official tokenizer.
Prefill/decode follow techshoww/ax-llm d9c086761d77681506912d60d22477429113708c.
"""
import argparse
import ast
import datetime
import gc
import hashlib
import json
from pathlib import Path
import shutil
import time
import axengine
import cv2
import numpy as np
from ml_dtypes import bfloat16
from transformers import AutoTokenizer
from transformers.tokenization_utils_base import AddedToken

MID = 'SmolVLM-256M-Instruct'
REVISION = 'a41ab40883f156fd50bb3371acdfaed626ca38d6'
PROVIDER = 'AXCLRTExecutionProvider'
TOKENIZER_SHA = '087efdcc ec3c19927fd3de56d5b31cb6f1ed5b0f56e427cb9555f2b62ade1254'.replace(' ', '')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest_array = lambda x: hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-new-tokens', type=int, default=160)
    p.add_argument('--question')
    p.add_argument('--image', type=Path)
    a = p.parse_args()
    assert 1 <= a.max_new_tokens <= 512 and (not a.image or a.question)
    root, out = a.model_dir.resolve(), a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    assert PROVIDER in axengine.get_available_providers()
    source = root/'smolvlm_tokenizer_512.py'
    assert sha(source) == TOKENIZER_SHA
    text = source.read_text()
    changes = [{'before': "path = 'smolvlm_tokenizer'", 'after': 'path = '+repr(str(root/'smolvlm_tokenizer'))},
               {'before': 'trust_remote_code=True', 'after': 'trust_remote_code=False'},
               {'before': 'use_fast=False)', 'after': 'use_fast=False, local_files_only=True)'}]
    for change in changes:
        assert text.count(change['before']) == 1
        text = text.replace(change['before'], change['after'])
    names = {'_prompt_split_image', '_prompt_single_image', 'get_image_prompt_string', 'Tokenizer_Http'}
    tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert len(nodes) == 4
    module = ast.Module(body=nodes, type_ignores=[])
    used = ast.unparse(module)
    (out/'tokenizer-definitions-used.py').write_text(used, encoding='utf-8')
    namespace = {'AutoTokenizer': AutoTokenizer, 'AddedToken': AddedToken}
    exec(compile(module, str(source), 'exec'), namespace)
    tokenizer = namespace['Tokenizer_Http']()
    assert tokenizer.eos_id == 49279 and tokenizer.bos_id == 1
    assert len(tokenizer.tokenizer) == 49280
    weights = root/'smolvlm-256m-ax650'
    embedding = weights/'model.embed_tokens.weight.bfloat16.bin'
    assert embedding.stat().st_size == 49280*576*2
    embeds = np.memmap(embedding, dtype=bfloat16, mode='r', shape=(49280, 576))
    record = {'modelId': MID, 'revision': REVISION, 'provider': PROVIDER, 'completed': False,
              'sessions': [], 'samples': [], 'maxNewTokens': a.max_new_tokens,
              'tokenizerSourceSha256': TOKENIZER_SHA, 'tokenizerChanges': changes,
              'tokenizerUsedSourceSha256': sha(out/'tokenizer-definitions-used.py'),
              'tokenizerFiles': {p.relative_to(root).as_posix(): sha(p) for p in (root/'smolvlm_tokenizer').rglob('*') if p.is_file()},
              'runtimeReference': {'repo': 'techshoww/ax-llm', 'revision': 'd9c086761d77681506912d60d22477429113708c',
                                   'path': 'src/runner/LLM.hpp', 'sha256': 'aff0f2c6effbdeb36e859f9535907bb13b829d5f1827997746509f5f114e4576'},
              'embedding': {'file': embedding.relative_to(root).as_posix(), 'shape': [49280, 576], 'format': 'bfloat16', 'sha256': sha(embedding)},
              'sampling': {'method': 'greedy', 'temperatureEnabled': False, 'repetitionPenaltyEnabled': False},
              'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def save():
        (out/'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    class Session:
        def __init__(self, filename, groups=(0,)):
            path = weights/filename
            started = time.perf_counter()
            self.session = axengine.InferenceSession(str(path), providers=[PROVIDER])
            assert self.session.get_providers() in (PROVIDER, [PROVIDER])
            self.ins = {g: {x.name: x for x in self.session.get_inputs(g)} for g in groups}
            self.outs = {g: self.session.get_outputs(g) for g in groups}
            self.row = {'model': path.relative_to(root).as_posix(), 'weightSha256': sha(path), 'provider': PROVIDER,
                        'loadSeconds': time.perf_counter()-started, 'runMilliseconds': [], 'allFinite': True,
                        'shapeGroups': {str(g): {'calls': 0, 'inputs': {k: {'shape': list(x.shape), 'dtype': str(x.dtype)} for k, x in self.ins[g].items()},
                                               'outputs': {x.name: {'shape': list(x.shape), 'dtype': str(x.dtype)} for x in self.outs[g]}} for g in groups}}
            record['sessions'].append(self.row); save()

        def zeros(self, name, group=0):
            x = self.ins[group][name]
            return np.zeros(x.shape, dtype=x.dtype)

        def run(self, feed, group=0):
            assert set(feed) == set(self.ins[group])
            for name, value in feed.items():
                expected = self.ins[group][name]
                assert list(value.shape) == list(expected.shape), (name, value.shape, expected.shape)
                assert value.dtype == np.dtype(expected.dtype), (name, value.dtype, expected.dtype)
                assert np.isfinite(value).all()
            started = time.perf_counter()
            values = self.session.run(None, {k: np.ascontiguousarray(v) for k, v in feed.items()}, shape_group=group)
            self.row['runMilliseconds'].append((time.perf_counter()-started)*1000)
            finite = bool(all(np.isfinite(v).all() for v in values)); self.row['allFinite'] &= finite
            self.row['shapeGroups'][str(group)]['calls'] += 1
            assert finite, self.row['model']
            return {x.name: value.copy() for x, value in zip(self.outs[group], values)}

    layers = []
    vit = post = None
    try:
        vit = Session('SmolVLM-256M-Instruct_vision_nhwc.axmodel')
        post = Session('llama_post.axmodel')
        for i in range(30): layers.append(Session(f'llama_p128_l{i}_together.axmodel', (0, 1)))
        assert set(vit.ins[0]) == {'pixel_values'} and list(vit.ins[0]['pixel_values'].shape) == [1, 512, 512, 3]
        assert set(post.ins[0]) == {'input'} and np.prod(post.ins[0]['input'].shape) == 576
        for layer in layers:
            for group in (0, 1):
                assert set(layer.ins[group]) == {'K_cache', 'V_cache', 'indices', 'input', 'mask'}
                assert set(x.name for x in layer.outs[group]) == {'K_cache_out', 'V_cache_out', 'output'}
            assert list(layer.ins[0]['input'].shape) == [1, 1, 576]
            assert list(layer.ins[1]['input'].shape) == [1, 128, 576]
            assert list(layer.ins[0]['K_cache'].shape) == [1, 1023, 192]
            assert list(layer.ins[0]['mask'].shape) == [1, 1, 1024]
            assert list(layer.ins[1]['mask'].shape) == [1, 128, 128]
        cases = [{'question': 'Describe this image in one sentence.', 'image': root/'ssd_car.jpg'},
                 {'question': 'What color is the main bus? Answer with one word.', 'image': root/'ssd_car.jpg'},
                 {'question': 'Describe this image in one sentence.', 'image': root/'ssd_car.jpg'},
                 {'question': 'What is 2 + 3? Reply with only the number.', 'image': None}]
        if a.question: cases = [{'question': a.question, 'image': a.image.resolve() if a.image else None}]
        for si, sample in enumerate(cases, 1):
            counts = [len(s['runMilliseconds']) for s in record['sessions']]
            row = {'input': sample['question'], 'images': []}
            started = time.perf_counter()
            tokens = tokenizer.encode_vpm(sample['question']) if sample['image'] else tokenizer.encode(sample['question'])
            assert len(tokens) <= 128 and all(0 <= token < 49280 for token in tokens)
            length = len(tokens)
            row.update(inputTokenIds=tokens, inputTokens=length, imageTokenId=49190)
            data = np.array(embeds[tokens], copy=True)
            if sample['image']:
                source_image = sample['image']
                bgr = cv2.imread(str(source_image)); assert bgr is not None
                pixels = cv2.cvtColor(cv2.resize(bgr, (512, 512), interpolation=cv2.INTER_LINEAR), cv2.COLOR_BGR2RGB)[None]
                begin = time.perf_counter()
                values = vit.run({'pixel_values': pixels})
                assert len(values) == 1
                feature = next(iter(values.values()))
                assert feature.shape == (1, 64, 576)
                feature = feature.astype(bfloat16)
                row['imageEncodeSeconds'] = time.perf_counter()-begin
                positions = np.flatnonzero(np.array(tokens) == 49190)
                assert len(positions) == 64 and np.array_equal(positions, np.arange(positions[0], positions[0]+64))
                data[positions] = feature[0]
                filename = f'input-{si}'+source_image.suffix.lower(); shutil.copy2(source_image, out/filename)
                row['images'].append({'file': filename, 'source': source_image.name, 'sha256': sha(source_image), 'pixelTensorSha256': digest_array(pixels)})
                row.update(imageTokenOffset=int(positions[0]), imageFeatureSha256=digest_array(feature))
                np.savez(out/f'vision-{si}.npz', pixels=pixels, features=feature.view(np.uint16))
            else: assert 49190 not in tokens
            row['prefillEmbeddingSha256'] = digest_array(data)
            k_cache = [layer.zeros('K_cache') for layer in layers]
            v_cache = [layer.zeros('V_cache') for layer in layers]
            padded = np.zeros((1, 128, 576), dtype=bfloat16); padded[0, :length] = data
            begin = time.perf_counter()
            for i, layer in enumerate(layers):
                feed = {name: layer.zeros(name, 1) for name in layer.ins[1]}
                feed['input'][:] = padded
                feed['indices'].reshape(-1)[:length] = np.arange(length)
                feed['mask'][:] = np.where(np.tri(128, dtype=bool), 0., -65536.)[None].astype(bfloat16)
                values = layer.run(feed, 1)
                assert values['K_cache_out'].shape == (1, 128, 192)
                assert values['V_cache_out'].shape == (1, 128, 192)
                k_cache[i][:, :128] = values['K_cache_out']; v_cache[i][:, :128] = values['V_cache_out']
                padded = values['output']; assert padded.shape == (1, 128, 576)
            row['prefillSeconds'] = time.perf_counter()-begin
            logit_digests = []

            def choose(hidden):
                assert hidden.size == 576
                value = hidden.reshape(post.ins[0]['input'].shape)
                logits = next(iter(post.run({'input': value}).values()))
                assert logits.size == 49280
                logit_digests.append(digest_array(logits))
                return int(np.argmax(logits.astype(np.float32)))

            generated = [choose(padded[:, length-1])]
            row['firstTokenSeconds'] = time.perf_counter()-started
            mask = layers[0].zeros('mask'); mask[:] = -65536
            mask[:, :, :length] = 0; mask[:, :, -1] = 0
            while generated[-1] != tokenizer.eos_id and len(generated) < a.max_new_tokens:
                position = length+len(generated)-1
                if position >= 1023: break
                hidden = np.array(embeds[generated[-1]], copy=True).reshape(1, 1, 576)
                for i, layer in enumerate(layers):
                    indices = layer.zeros('indices'); indices[:] = position
                    values = layer.run({'K_cache': k_cache[i], 'V_cache': v_cache[i], 'indices': indices, 'input': hidden, 'mask': mask})
                    assert values['K_cache_out'].shape == (1, 1, 192)
                    k_cache[i][:, position:position+1] = values['K_cache_out']; v_cache[i][:, position:position+1] = values['V_cache_out']
                    hidden = values['output']
                mask[:, :, position] = 0
                generated.append(choose(hidden))
            hit_eos = generated[-1] == tokenizer.eos_id
            row.update(outputTokenIds=generated, output=tokenizer.tokenizer.decode(generated, skip_special_tokens=True),
                       hitEos=hit_eos, stopReason='eos' if hit_eos else 'length' if len(generated) == a.max_new_tokens else 'context',
                       generatedTokens=len(generated), generationSeconds=time.perf_counter()-started,
                       logitSha256=logit_digests, sessionCalls=[len(s['runMilliseconds'])-count for s, count in zip(record['sessions'], counts)])
            assert row['output'].strip() and '\ufffd' not in row['output']
            record['samples'].append(row); save(); print(json.dumps(row, ensure_ascii=False), flush=True)
        if not a.question:
            first, repeat = record['samples'][0], record['samples'][2]
            record['repeat'] = {key: first[key] == repeat[key] for key in ['inputTokenIds', 'outputTokenIds', 'logitSha256', 'imageFeatureSha256', 'prefillEmbeddingSha256']}
        record['completed'] = True
    except BaseException as exc:
        record['error'] = repr(exc); raise
    finally:
        layers.clear(); vit = post = None; gc.collect()
        record['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat(); save()


if __name__ == '__main__':
    main()
