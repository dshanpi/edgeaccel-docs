---
title: "Qwen3-4B 部署指南"
sidebar_label: "Qwen3-4B"
description: "Qwen3-4B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-4B 部署指南

Qwen3-4B 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-4B` 的固定版本。下面下载本页选用的 42 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-4b/d3bf9ef4c74f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-4B \
  "README.md" \
  "config.json" \
  "qwen3_p128_l0_together.axmodel" \
  "qwen3_p128_l1_together.axmodel" \
  "qwen3_p128_l2_together.axmodel" \
  "qwen3_p128_l3_together.axmodel" \
  "qwen3_p128_l4_together.axmodel" \
  "qwen3_p128_l5_together.axmodel" \
  "qwen3_p128_l6_together.axmodel" \
  "qwen3_p128_l7_together.axmodel" \
  "qwen3_p128_l8_together.axmodel" \
  "qwen3_p128_l9_together.axmodel" \
  "qwen3_p128_l10_together.axmodel" \
  "qwen3_p128_l11_together.axmodel" \
  "qwen3_p128_l12_together.axmodel" \
  "qwen3_p128_l13_together.axmodel" \
  "qwen3_p128_l14_together.axmodel" \
  "qwen3_p128_l15_together.axmodel" \
  "qwen3_p128_l16_together.axmodel" \
  "qwen3_p128_l17_together.axmodel" \
  "qwen3_p128_l18_together.axmodel" \
  "qwen3_p128_l19_together.axmodel" \
  "qwen3_p128_l20_together.axmodel" \
  "qwen3_p128_l21_together.axmodel" \
  "qwen3_p128_l22_together.axmodel" \
  "qwen3_p128_l23_together.axmodel" \
  "qwen3_p128_l24_together.axmodel" \
  "qwen3_p128_l25_together.axmodel" \
  "qwen3_p128_l26_together.axmodel" \
  "qwen3_p128_l27_together.axmodel" \
  "qwen3_p128_l28_together.axmodel" \
  "qwen3_p128_l29_together.axmodel" \
  "qwen3_p128_l30_together.axmodel" \
  "qwen3_p128_l31_together.axmodel" \
  "qwen3_p128_l32_together.axmodel" \
  "qwen3_p128_l33_together.axmodel" \
  "qwen3_p128_l34_together.axmodel" \
  "qwen3_p128_l35_together.axmodel" \
  "qwen3_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "qwen3_tokenizer.txt" \
  "post_config.json" \
  --revision d3bf9ef4c74ffa2c3c3d1232908265b500fa7731 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

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


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-29 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

三条单轮请求完成算术、中文说明和JSON输出；两轮对话能够返回前文数字，但确认和追问回复均附带句号。下方保留原始输出。

**示例 1：输入**

```text
What is 2 + 3? Answer with only the number.
```

**实际回复**

```text
5
```

数值正确，且只输出数字。

程序内部首 token 耗时：1636.83 ms；完整 API 请求耗时：2.029 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速串行计算机总线标准，用于连接计算机内部的硬件设备，如显卡、固态硬盘等，实现高速数据传输。
```

用一句中文说明了PCIe连接设备和传输数据的用途，内容与问题相符。

程序内部首 token 耗时：1531.82 ms；完整 API 请求耗时：17.290 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

可直接解析为JSON，apple为3、pear为2，没有代码围栏或额外解释。

程序内部首 token 耗时：1628.56 ms；完整 API 请求耗时：6.354 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**连续对话 1**

两轮请求使用同一个服务进程；第二轮明确携带第一轮问题和模型的实际回复。

**第 1 轮：输入**

```text
Remember this code: 4729. Reply only OK.
```

**实际回复**

```text
OK.
```

实际返回“OK.”，末尾有句号，未严格满足“只回复OK”的格式要求。

程序内部首 token 耗时：1520.33 ms；完整 API 请求耗时：2.287 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply only with the digits.
```

**实际回复**

```text
4729.
```

返回数字4729，与前文一致；末尾附带句号，未严格满足“只输出数字”的要求。

程序内部首 token 耗时：1443.63 ms；完整 API 请求耗时：3.391 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**使用时注意：**

- 记忆确认返回“OK.”，数字追问返回“4729.”；数值一致，但纯文本格式约束未完全满足。业务使用前应检查输出格式。
- 仅在16GB算力卡上测试三条独立短请求与两轮短对话；未验证实际8GB容量、长上下文、并发或长期连续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-29。模型版本：`d3bf9ef4c74ffa2c3c3d1232908265b500fa7731`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行时 | AX-LLM固定提交8501c22b940f8c5804cb35044c5ffc136918b8f1，编译AXCL后端 |
| 加载与存储 | 外接ext4存储卡；原config.json和post_config.json，AXCL设备0 |
| 生成参数 | max_tokens=128、temperature=0、enable_thinking=false、stream=false |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 服务加载就绪 | 392.265 s | 启动程序至健康检查成功；受主机和外接存储影响，不是生成耗时。 |

适用范围：

- 记忆确认返回“OK.”，数字追问返回“4729.”；数值一致，但纯文本格式约束未完全满足。业务使用前应检查输出格式。
- 仅在16GB算力卡上测试三条独立短请求与两轮短对话；未验证实际8GB容量、长上下文、并发或长期连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/config.json) | 运行配置 |
| [`qwen3_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/post_config.json) | 运行配置 |
| [`qwen3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/qwen3_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`d3bf9ef4c74ffa2c3c3d1232908265b500fa7731`。仓库中的 37 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-4B/tree/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-4B/tree/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-4B/blob/d3bf9ef4c74ffa2c3c3d1232908265b500fa7731/README.md)。

返回[完整模型目录](../catalog.mdx)。
