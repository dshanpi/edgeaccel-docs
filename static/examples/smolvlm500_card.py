"""Official SmolVLM2-500M Python single-image workflow with explicit AXCL."""
import argparse
import ast
import datetime
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time
import axengine
import numpy as np
import torch
from ml_dtypes import bfloat16
from PIL import Image
from torchvision.transforms import Resize
from transformers import AutoConfig, AutoProcessor
from transformers.models.smolvlm.modeling_smolvlm import SmolVLMVisionEmbeddings

MID = 'SmolVLM2-500M-Video-Instruct-python'
REV = '42557bc3bff11187d71d001e43e8cb011a1fbf7b'
PROVIDER = 'AXCLRTExecutionProvider'
SOURCES = {'infer_axmodel.py': '88168f9c9792061a283a2015dad3669bae8306083cdbb1c3c93df5ce4032989a',
           'utils/infer_func.py': '7dba76637c19151eb4c732c69d6f65314812ac493c843e8cf98741e84ef052d9'}
PICKLE_SHA = 'cab5d95b958d2cd6173c887bd98cab7accda22e8d321f7c348464e428b59f675'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def arrsha(value):
    if isinstance(value, torch.Tensor): value = value.detach().float().cpu().numpy()
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-new-tokens', type=int, default=160)
    p.add_argument('--question')
    p.add_argument('--image', type=Path)
    a = p.parse_args(); assert 1 <= a.max_new_tokens <= 512
    assert not a.image or a.question
    root, out = a.model_dir.resolve(), a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    assert PROVIDER in axengine.get_available_providers()
    for name, digest in SOURCES.items(): assert sha(root/name) == digest
    cpupath = root/'embeds/SmolVLMVisionEmbeddings.pkl'; assert sha(cpupath) == PICKLE_SHA
    # Static pickle inspection found only these torch module classes plus default
    # tensor rebuild/storage/OrderedDict globals. Keep restricted loading enabled.
    with torch.serialization.safe_globals([SmolVLMVisionEmbeddings, torch.nn.Conv2d, torch.nn.Embedding, set]):
        cpu_embed = torch.load(cpupath, map_location='cpu', weights_only=True)
    assert isinstance(cpu_embed, SmolVLMVisionEmbeddings)
    cpu_embed.eval(); torch.set_num_threads(2)
    processor = AutoProcessor.from_pretrained(root/'smolvlm2_tokenizer', local_files_only=True)
    config = AutoConfig.from_pretrained(root/'smolvlm2_tokenizer', local_files_only=True)
    tokenizer = processor.tokenizer; cfg = config.text_config
    embeds_path = root/'smolvlm2_axmodel/model.embed_tokens.weight.npy'
    embeds = np.load(embeds_path, mmap_mode='r', allow_pickle=False)
    assert embeds.shape == (49280, 960) and cfg.hidden_size == 960 and cfg.num_hidden_layers == 32
    names = {'run_vision_model', 'get_image_features', 'inputs_merger'}
    nodes = [n for n in ast.parse((root/'infer_axmodel.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(nodes) == 3
    module = ast.Module(body=nodes, type_ignores=[])
    (out/'official-functions-used.py').write_text(ast.unparse(module))
    record = {'modelId': MID, 'revision': REV, 'provider': PROVIDER, 'completed': False, 'sessions': [], 'samples': [],
              'sourceHashes': SOURCES, 'usedFunctionsSha256': sha(out/'official-functions-used.py'),
              'cpuEmbedding': {'file': cpupath.relative_to(root).as_posix(), 'sha256': PICKLE_SHA, 'restrictedWeightsOnlyLoad': True, 'calls': []},
              'embedding': {'file': embeds_path.relative_to(root).as_posix(), 'sha256': sha(embeds_path), 'shape': list(embeds.shape), 'dtype': str(embeds.dtype)},
              'processorFiles': {f.relative_to(root).as_posix(): sha(f) for f in (root/'smolvlm2_tokenizer').rglob('*') if f.is_file()},
              'maxNewTokens': a.max_new_tokens, 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def save():
        (out/'deployment-result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    def cpu_embedding(**kwargs):
        start = time.perf_counter()
        with torch.inference_mode(): result = cpu_embed(**kwargs)
        assert torch.isfinite(result).all()
        record['cpuEmbedding']['calls'].append({'seconds': time.perf_counter()-start,
            'inputShapes': {k: list(v.shape) for k,v in kwargs.items()}, 'outputShape': list(result.shape),
            'outputFloat32Sha256': arrsha(result), 'allFinite': True})
        return result

    official = {'torch': torch, 'np': np, 'embeddings': cpu_embedding, 'device': 'cpu'}
    exec(compile(module, str(root/'infer_axmodel.py'), 'exec'), official)
    spec = importlib.util.spec_from_file_location('smolvlm500_inference', root/'utils/infer_func.py')
    inference = importlib.util.module_from_spec(spec); spec.loader.exec_module(inference)
    factory = axengine.InferenceSession

    class Measured:
        def __init__(self, path):
            path = Path(path); started = time.perf_counter()
            self.session = factory(str(path), providers=[PROVIDER])
            assert self.session.get_providers() in (PROVIDER, [PROVIDER])
            self.row = {'model': path.relative_to(root).as_posix(), 'provider': PROVIDER,
                        'weightSha256': sha(path), 'loadSeconds': time.perf_counter()-started,
                        'allFinite': True, 'runMilliseconds': [], 'shapeGroups': {}}
            record['sessions'].append(self.row); save()

        def run(self, names, feed, shape_group=0):
            meta = {x.name: x for x in self.session.get_inputs(shape_group)}
            assert set(meta) == set(feed)
            if self.row['model'] == 'vit_model/vision_model.axmodel' and set(feed) == {'input'}:
                value, expected = feed['input'], meta['input']
                if expected.shape[0] == 1 and value.shape[0] > 1:
                    assert list(value.shape[1:]) == list(expected.shape[1:])
                    self.row.setdefault('visionBatchSplits', []).append({'requestedShape': list(value.shape), 'individualBatch': 1})
                    parts = [self.run(names, {'input': value[i:i+1]}, shape_group) for i in range(value.shape[0])]
                    return [np.concatenate([part[j] for part in parts], axis=0) for j in range(len(parts[0]))]
            for name, value in feed.items():
                assert list(value.shape) == list(meta[name].shape), (name, value.shape, meta[name].shape)
                assert value.dtype == np.dtype(meta[name].dtype)
                assert np.isfinite(value).all()
            start = time.perf_counter()
            values = self.session.run(names, {k: np.ascontiguousarray(v) for k,v in feed.items()}, shape_group=shape_group)
            self.row['runMilliseconds'].append((time.perf_counter()-start)*1000)
            finite = bool(all(np.isfinite(v).all() for v in values)); self.row['allFinite'] &= finite; assert finite
            key = str(shape_group)
            if key not in self.row['shapeGroups']:
                self.row['shapeGroups'][key] = {'calls': 0, 'inputs': {k: {'shape': list(v.shape), 'dtype': str(v.dtype)} for k,v in feed.items()},
                                               'outputs': [{'shape': list(v.shape), 'dtype': str(v.dtype)} for v in values]}
            self.row['shapeGroups'][key]['calls'] += 1
            return [v.copy() for v in values]

    class OutputLimit(Exception): pass
    cases = [{'input': 'Describe this image in one sentence.', 'image': root/'assets/bee.jpg'},
             {'input': 'What color are the flower petals? Answer briefly.', 'image': root/'assets/bee.jpg'},
             {'input': 'Describe this image in one sentence.', 'image': root/'assets/bee.jpg'}]
    if a.question: cases = [{'input': a.question, 'image': a.image.resolve() if a.image else root/'assets/bee.jpg'}]
    manager = encoder = None
    try:
        inference.InferenceSession = Measured
        manager = inference.InferManager(cfg, str(root/'smolvlm2_axmodel'))
        encoder = Measured(root/'vit_model/vision_model.axmodel')
        chosen, logit_hashes = [], []
        original_post = manager.post_process

        def counted_post(logits, *args, **kwargs):
            if len(chosen) >= a.max_new_tokens: raise OutputLimit()
            result = original_post(logits, *args, **kwargs)
            chosen.append(int(result[0])); logit_hashes.append(arrsha(logits)); return result
        manager.post_process = counted_post
        for i, case in enumerate(cases, 1):
            for cache in manager.k_caches+manager.v_caches: cache.fill(0)
            chosen.clear(); logit_hashes.clear(); np.random.seed(0)
            call_starts = [len(s['runMilliseconds']) for s in record['sessions']]
            start = time.perf_counter()
            image = Image.open(case['image']).convert('RGB'); image = Resize((512,512))(image)
            messages = [{'role': 'user', 'content': [{'type': 'image', 'image': image}, {'type': 'text', 'text': case['input']}]}]
            inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors='pt').to('cpu', dtype=torch.bfloat16)
            ids = inputs['input_ids']; tokens = ids[0].tolist(); original_tokens = tokens.copy()
            assert 0 < len(tokens) < 2559 and len(tokens)%128 != 0
            vector = np.take(embeds, tokens, axis=0)[None]
            vector = torch.from_numpy(vector).to(dtype=torch.bfloat16)
            with torch.inference_mode():
                feature = official['get_image_features'](encoder, inputs['pixel_values'], inputs['pixel_attention_mask'])
                merged = official['inputs_merger'](ids, vector, feature).float().cpu().numpy().astype(bfloat16)
            filename = 'input-'+str(i)+case['image'].suffix.lower(); shutil.copy2(case['image'], out/filename)
            row = {'input': case['input'], 'images': [{'file': filename, 'source': case['image'].name, 'sha256': sha(case['image'])}],
                   'inputTokenIds': original_tokens, 'inputTokens': len(original_tokens), 'imageTokenCount': tokens.count(49190),
                   'pixelValuesShape': list(inputs['pixel_values'].shape), 'imageFeatureShape': list(feature.shape),
                   'pixelValuesFloat32Sha256': arrsha(inputs['pixel_values']), 'imageFeatureFloat32Sha256': arrsha(feature),
                   'prefillEmbeddingSha256': arrsha(merged), 'preprocessingSeconds': time.perf_counter()-start}
            tokens = manager.prefill(tokenizer, tokens, merged[0], slice_len=128)
            row['firstTokenSeconds'] = time.perf_counter()-start
            stop = 'eos'
            if chosen[-1] != tokenizer.eos_token_id:
                try: manager.decode(tokenizer, tokens, embeds, slice_len=128)
                except OutputLimit: stop = 'length'
                else:
                    if chosen[-1] != tokenizer.eos_token_id: stop = 'context'
            row.update(output=tokenizer.decode(chosen, skip_special_tokens=True), outputTokenIds=chosen.copy(),
                       logitSha256=logit_hashes.copy(), generatedTokens=len(chosen), hitEos=stop=='eos', stopReason=stop,
                       generationSeconds=time.perf_counter()-start,
                       sessionCalls=[len(s['runMilliseconds'])-n for s,n in zip(record['sessions'],call_starts)])
            assert row['output'].strip() and '\ufffd' not in row['output']
            record['samples'].append(row); save(); print(json.dumps(row, ensure_ascii=False), flush=True)
        if not a.question:
            first, repeat = record['samples'][0], record['samples'][2]
            record['repeat'] = {k: first[k]==repeat[k] for k in ['inputTokenIds','outputTokenIds','logitSha256','imageFeatureFloat32Sha256','prefillEmbeddingSha256']}
        record['completed'] = True
    except BaseException as exc: record['error']=repr(exc); raise
    finally:
        inference.InferenceSession = factory; manager = encoder = None; gc.collect()
        record['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat(); save()


if __name__ == '__main__': main()
