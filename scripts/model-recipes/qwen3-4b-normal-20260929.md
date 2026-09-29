## 检查模型与程序

完整模型约 5.67GB。主机存储不足时，可将前文的 `MODEL_DIR` 设置为已挂载的外接存储目录。保持全部 36 个层文件、post 模型、embedding 和分词文件来自同一提交。

下载本页的[固定文件校验表](/validation/effects/qwen3-4b-20260929/download-manifest.json)，保存为 `$MODEL_DIR/download-manifest.json`。在 RK3576 主机终端执行：

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
"$AXLLM" version
ldd "$AXLLM"
cd "$MODEL_DIR"
python3 - <<'PY'
import hashlib
import json
from pathlib import Path
p = Path('.')
c = json.loads((p / 'config.json').read_text())
assert c['model_name'] == 'AXERA-TECH/Qwen3-4B'
assert c['axmodel_num'] == 36 and c['devices'] == [0]
files = [c['template_filename_axmodel'] % i for i in range(36)]
files += [c[k] for k in ['filename_post_axmodel', 'filename_tokens_embed',
                         'url_tokenizer_model', 'post_config_path']]
missing = [f for f in files if not (p / f).is_file()]
assert not missing, missing
manifest = json.loads((p / 'download-manifest.json').read_text())
assert manifest['modelId'] == 'Qwen3-4B'
assert manifest['revision'] == 'd3bf9ef4c74ffa2c3c3d1232908265b500fa7731'
for item in manifest['files']:
    h = hashlib.sha256()
    with (p / item['path']).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    assert h.hexdigest() == item['verifiedHashes']['sha256'], item['path']
print('全部模型文件校验通过')
PY
```

版本输出中的后端应为 `AXCL`，动态库不得出现 `not found`。校验会读取全部模型文件，完成后显示“全部模型文件校验通过”；不一致时停止运行，核对下载文件和存储设备。

运行时使用前文编译的固定源码提交 `8501c22b940f8c5804cb35044c5ffc136918b8f1`。保留官方 `config.json` 和 `post_config.json`，无需单独启动 Python 分词服务。

## 启动单卡服务

继续在当前终端执行：

```bash
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
AXLLM_DEVICES=0 "$AXLLM" serve "$MODEL_DIR" --port 8000
```

等待全部层、post 模型和 embedding 初始化完成，并出现服务启动信息。加载时间与主机和存储有关，服务就绪后再发送请求。保持该终端运行。

## 发送问题并保留对话历史

在同一主机另开终端。以下脚本先发送三条独立问题，再进行两轮对话；请求参数与下方效果展示一致。

```bash
python3 - <<'PY'
import json
import urllib.request

base = 'http://127.0.0.1:8000'
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with http.open(base + '/health', timeout=10) as r:
    assert json.load(r)['status'] == 'healthy'
with http.open(base + '/v1/models', timeout=10) as r:
    model = json.load(r)['data'][0]['id']
assert model == 'AXERA-TECH/Qwen3-4B'

def chat(messages):
    payload = dict(model=model, messages=messages, max_tokens=128,
                   temperature=0, enable_thinking=False, stream=False)
    req = urllib.request.Request(base + '/v1/chat/completions',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    with http.open(req, timeout=180) as r:
        result = json.load(r)
    choice = result['choices'][0]
    print('输入：', messages[-1]['content'])
    print('回复：', choice['message']['content'])
    print('结束原因：', choice['finish_reason'])
    print('用量与内部计时：', json.dumps(result.get('usage', {}), ensure_ascii=False))
    assert choice['finish_reason'] == 'stop', '输出未正常结束'
    return choice['message']['content']

for prompt in [
    'What is 2 + 3? Answer with only the number.',
    '请用一句中文说明 PCIe 的用途。',
    'Return only a JSON object with apple equal to 3 and pear equal to 2.'
]:
    chat([{'role': 'user', 'content': prompt}])

messages = [{'role': 'user', 'content': 'Remember this code: 4729. Reply only OK.'}]
answer = chat(messages)
messages += [{'role': 'assistant', 'content': answer},
             {'role': 'user', 'content': 'What code did I ask you to remember? Reply only with the digits.'}]
chat(messages)
PY
```

每个单轮请求只携带当前问题。第二轮对话同时携带第一轮问题和模型的实际回复；接入应用时也按此方式管理 `messages`，不能仅再次发送一个孤立问题。

本页关闭思考模式，使用非流式响应，最多生成 128 个 token。对照下方原始回复检查内容和格式；要求 JSON 的应用还需对返回文本执行 JSON 解析。

## 停止服务

在服务终端按 `Ctrl+C`，退出后执行 `axcl-smi`，确认推理进程已结束、设备内存已释放，再加载其他模型。
