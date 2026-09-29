"""Resident AXCL worker. Upstream encoding and postprocessing stay unchanged."""
import contextlib, hashlib, json, os, sys, time, types
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
root = Path(sys.argv[1]).resolve()
lock = json.loads(Path(__file__).with_name('model-lock.json').read_text())
for name, expected in lock['files'].items():
    path = root / name
    if hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() != expected:
        raise RuntimeError('模型文件校验失败: ' + name)
source = (root / 'python/ax650/infer.py').read_text()
old = 'provider = "AxEngineExecutionProvider"'
assert source.count(old) == 1
module = types.ModuleType('laya_upstream')
exec(compile(source.replace(old, 'provider = "AXCLRTExecutionProvider"'), 'laya_upstream', 'exec'), module.__dict__)
with contextlib.redirect_stdout(sys.stderr):
    model = module.LayaAx650(root / 'multilingual')
print(json.dumps({'event': 'ready'}), flush=True)
for line in sys.stdin:
    try:
        request = json.loads(line)
        for question in request['questions'].values():
            head, _ = module.build_sequence(model.tokenizer, '', module.internal_question(question), model.seq_len, model.head_max_len)
            count = len(model.tokenizer(request['state'].replace(model.tokenizer.mask_token, ' '), add_special_tokens=False)['input_ids'])
            if count + len(head) > model.seq_len:
                raise ValueError('观察描述过长，请缩短后重试，避免截断输入。')
        start = time.perf_counter()
        with contextlib.redirect_stdout(sys.stderr):
            result = model.predict(request)
        result.update(wallMilliseconds=(time.perf_counter()-start)*1000, revision=lock['revision'], provider='AXCLRTExecutionProvider', request=request)
        print(json.dumps({'event': 'result', 'result': result}, ensure_ascii=False, allow_nan=False), flush=True)
    except ValueError as error:
        print(json.dumps({'event': 'invalid', 'error': str(error)}, ensure_ascii=False), flush=True)
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'event': 'error', 'error': '推理失败。请检查设备和服务日志后重新启动。'}, ensure_ascii=False), flush=True)
        break
