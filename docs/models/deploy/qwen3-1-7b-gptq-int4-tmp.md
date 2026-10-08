---
title: "Qwen3-1.7B-GPTQ-Int4-tmp 部署指南"
sidebar_label: "Qwen3-1.7B-GPTQ-Int4-tmp"
description: "Qwen3-1.7B-GPTQ-Int4-tmp 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-1.7B-GPTQ-Int4-tmp 部署指南

Qwen3-1.7B-GPTQ-Int4-tmp 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 选择规格并下载模型

本页分别验证以下规格。一次选择一组，下载对应权重与共用文件；切换规格前先停止模型服务。

| VARIANT | 所选文件数 |
| --- | --- |
| `context-2500-prefill-2k` | 31 |
| `context-2k-prefill-1500` | 31 |
| `context-2k-prefill-1k` | 31 |

以下默认选择第一组。执行前修改 `VARIANT`，并确认主机内部模型目录所在分区至少有 3.5 GiB 可用空间。空间不足时，先备份结果并清理已完成测试的权重目录，再下载下一组。

```bash
set -e
MODEL_DIR=~/edgeaccel/models/qwen3-1-7b-gptq-int4-tmp/f93afe51b24b
VARIANT=context-2500-prefill-2k
case "$VARIANT" in
  context-2500-prefill-2k) WEIGHTS="Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k" ;;
  context-2k-prefill-1500) WEIGHTS="Qwen3-1.7B-GPTQ-Int4-context-2k-prefill-1500" ;;
  context-2k-prefill-1k) WEIGHTS="Qwen3-1.7B-GPTQ-Int4-context-2k-prefill-1k" ;;
  *) echo "未知模型规格" >&2; exit 1 ;;
esac
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
python3 - "$MODEL_DIR" <<'PY'
import shutil, sys
free = shutil.disk_usage(sys.argv[1]).free / 1024**3
assert free >= 3.5, f"当前仅有 {free:.2f} GiB 可用，请先释放空间"
PY
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp \
  --include "$WEIGHTS/*" "README.md" "model.embed_tokens.weight.bfloat16.bin" \
  --revision f93afe51b24b084020f6fd32c666b2e7fd4c7d31 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留同一终端的 `MODEL_DIR`、`VARIANT` 变量，后续配置沿用所选目录与规格。下载受阻时见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配置与分词器

本仓库包含三组模型权重和共用 embedding，没有提供运行配置与分词器。本例使用 [Qwen3-1.7B-GPTQ-Int4 固定版本](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4/tree/6bbc2ec7f7cff174d06058de4aed85112df6261b)的配套文件，并使用[固定版本 AXCL 运行时](../llm-runtime.md)。

每组权重及共用 embedding 约 1.95–2.08GB，以下配置沿用前文选定的规格。配套配置与分词文件约 1.63MB。

在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`：

```bash
RUNTIME_DIR=~/edgeaccel/runtime/qwen3-17b/6bbc2ec7f7cf
mkdir -p "$RUNTIME_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-1.7B-GPTQ-Int4 \
  --include 'README.md' 'config.json' 'post_config.json' 'qwen3_tokenizer.txt' \
  --revision 6bbc2ec7f7cff174d06058de4aed85112df6261b \
  --local-dir "$RUNTIME_DIR"
```

`VARIANT` 可选 `context-2500-prefill-2k`、`context-2k-prefill-1500` 或 `context-2k-prefill-1k`。先停止已有模型服务，再为所选规格生成配置：

```bash
export MODEL_DIR RUNTIME_DIR VARIANT
python3 - <<'PY'
import json, os, shutil
from pathlib import Path
root = Path(os.environ['MODEL_DIR']).expanduser()
support = Path(os.environ['RUNTIME_DIR']).expanduser()
variant = os.environ['VARIANT']
assert variant in ['context-2500-prefill-2k', 'context-2k-prefill-1500', 'context-2k-prefill-1k']
folder = 'Qwen3-1.7B-GPTQ-Int4-' + variant
config = json.loads((support / 'config.json').read_text())
assert config['axmodel_num'] == 28
assert config['devices'] == [0]
assert config['tokens_embed_num'] == 151936 and config['tokens_embed_size'] == 2048
config.update(model_name='AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp',
              template_filename_axmodel=folder + '/qwen3_p128_l%d_together.axmodel',
              filename_post_axmodel=folder + '/qwen3_post.axmodel')
files = [config['template_filename_axmodel'] % i for i in range(28)]
files += [config['filename_post_axmodel'], config['filename_tokens_embed']]
missing = [f for f in files if not (root / f).is_file()]
assert not missing, missing
for name in ['post_config.json', 'qwen3_tokenizer.txt']:
    shutil.copy2(support / name, root / name)
(root / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
print('模型文件齐全，已生成配置：', folder)
PY
```

只修改配置中的模型名称和两项权重路径，保留原配置的层数、embedding 维度、mmap 加载方式及设备编号。不要混入同系列其他量化版本的权重。

## 启动单卡服务

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
"$AXLLM" version
"$AXLLM" serve "$MODEL_DIR" --port 8000
```

版本输出应显示 AXCL 后端。保持此终端运行，等待 28 层及 post 模型加载完成。初始化失败时先停止测试并检查文件与设备状态，不关闭内存预检强制启动。

## 发送问答与两轮对话

另开主机终端执行。以下请求设置 `temperature=0`、`enable_thinking=false`、`max_tokens=128`，服务启动耗时不计入请求耗时。

```bash
python3 - <<'PY'
import json, time, urllib.request
base = 'http://127.0.0.1:8000'
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with http.open(base + '/health', timeout=5) as response:
    assert json.load(response)['status'] == 'healthy'
with http.open(base + '/v1/models', timeout=5) as response:
    model = json.load(response)['data'][0]['id']
assert model == 'AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp'

def ask(messages):
    payload = dict(model=model, messages=messages, max_tokens=128,
                   temperature=0, enable_thinking=False, stream=False)
    request = urllib.request.Request(base + '/v1/chat/completions',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    with http.open(request, timeout=180) as response:
        result = json.load(response)
    choice = result['choices'][0]
    print('输入：', messages[-1]['content'])
    print('回复：', choice['message']['content'])
    print('请求耗时：', round(time.monotonic() - started, 3), 's')
    print('usage：', result.get('usage'))
    assert choice['finish_reason'] == 'stop', '输出未正常结束，请检查返回的 finish_reason'
    return choice['message']['content']

for prompt in ['What is 2 + 3? Answer with only the number.',
               '请用一句中文说明 PCIe 的用途。',
               'Return only a JSON object with apple equal to 3 and pear equal to 2.']:
    ask([{'role': 'user', 'content': prompt}])
messages = [{'role': 'user', 'content': 'Remember this code: 4729. Reply only OK.'}]
reply = ask(messages)
messages += [{'role': 'assistant', 'content': reply},
             {'role': 'user', 'content': 'What code did I ask you to remember? Reply only with the digits.'}]
ask(messages)
PY
```

第二轮请求明确携带第一轮问题和模型的实际回复；客户端负责保存并传回对话历史。示例只检查短对话，不代表最大上下文或长期稳定性已经验证。完成后在服务终端按 `Ctrl+C`，再用 `axcl-smi` 确认推理进程退出。


## 查看部署效果

### context-2k-prefill-1k

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但短对话回复附加句点，未遵守仅输出 OK 或数字的要求；本次格式要求未通过。

**示例 1：输入**

```text
What is 2 + 3? Answer with only the number.
```

**实际回复**

```text
5
```

正确输出数字5。

程序内部首 token 耗时：1079.24 ms；完整 API 请求耗时：1.347 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 是一种用于计算机内部设备之间高速数据传输的串行计算机扩展总线标准。
```

用一句中文说明了PCIe用于计算机内部设备间高速数据传输，符合本条输入要求。

程序内部首 token 耗时：936.21 ms；完整 API 请求耗时：4.798 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

字段、数值和纯JSON格式均符合本条输入要求。

程序内部首 token 耗时：1200.06 ms；完整 API 请求耗时：3.228 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

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

回复为OK.，多了句号，未严格遵循只输出OK的格式要求。

程序内部首 token 耗时：939.47 ms；完整 API 请求耗时：1.288 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply only with the digits.
```

**实际回复**

```text
4729
```

请求携带第一轮问题和实际回复后，返回了正确的4729，且只包含数字。

程序内部首 token 耗时：1063.60 ms；完整 API 请求耗时：1.748 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**使用时注意：**

- 只覆盖所列短输入，首次确认回复OK.含额外句号；不代表完整题集质量、长上下文或持续运行已通过。
- 本次使用16GB卡，实际8GB容量需单独回归。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### context-2k-prefill-1500

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但短对话回复附加句点，未遵守仅输出 OK 或数字的要求；本次格式要求未通过。

**示例 1：输入**

```text
What is 2 + 3? Answer with only the number.
```

**实际回复**

```text
5
```

正确输出数字5。

程序内部首 token 耗时：1315.69 ms；完整 API 请求耗时：1.537 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 是一种用于计算机内部设备之间高速数据传输的串行计算机扩展总线标准。
```

用一句中文说明了PCIe用于计算机内部设备间高速数据传输，符合本条输入要求。

程序内部首 token 耗时：1288.64 ms；完整 API 请求耗时：5.570 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

字段、数值和纯JSON格式均符合本条输入要求。

程序内部首 token 耗时：1369.83 ms；完整 API 请求耗时：3.608 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

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

回复为OK.，多了句号，未严格遵循只输出OK的格式要求。

程序内部首 token 耗时：1287.16 ms；完整 API 请求耗时：1.733 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply only with the digits.
```

**实际回复**

```text
4729
```

请求携带第一轮问题和实际回复后，返回了正确的4729，且只包含数字。

程序内部首 token 耗时：1336.74 ms；完整 API 请求耗时：2.180 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**使用时注意：**

- 只覆盖所列短输入，首次确认回复OK.含额外句号；不代表完整题集质量、长上下文或持续运行已通过。
- 本次使用16GB卡，实际8GB容量需单独回归。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### context-2500-prefill-2k

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但短对话回复附加句点，未遵守仅输出 OK 或数字的要求；本次格式要求未通过。

**示例 1：输入**

```text
What is 2 + 3? Answer with only the number.
```

**实际回复**

```text
5
```

正确输出数字5。

程序内部首 token 耗时：1747.37 ms；完整 API 请求耗时：1.921 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 是一种用于计算机内部设备之间高速数据传输的串行计算机扩展总线标准。
```

用一句中文说明了PCIe用于计算机内部设备间高速数据传输，符合本条输入要求。

程序内部首 token 耗时：1754.31 ms；完整 API 请求耗时：5.542 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

字段、数值和纯JSON格式均符合本条输入要求。

程序内部首 token 耗时：2268.18 ms；完整 API 请求耗时：4.361 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

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

回复为OK.，多了句号，未严格遵循只输出OK的格式要求。

程序内部首 token 耗时：1629.23 ms；完整 API 请求耗时：2.073 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply only with the digits.
```

**实际回复**

```text
4729
```

请求携带第一轮问题和实际回复后，返回了正确的4729，且只包含数字。

程序内部首 token 耗时：1754.42 ms；完整 API 请求耗时：2.605 s。请求在模型加载完成后发出，包含响应传输，不含模型加载。

**使用时注意：**

- 只覆盖所列短输入，首次确认回复OK.含额外句号；不代表完整题集质量、长上下文或持续运行已通过。
- 本次使用16GB卡，实际8GB容量需单独回归。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**context-2k-prefill-1k**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`f93afe51b24b084020f6fd32c666b2e7fd4c7d31`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行时 | AX-LLM 8501c22b940f8c5804cb35044c5ffc136918b8f1，未修改源码，编译AXCL后端 |
| 配置与分词器 | 官方Qwen3-1.7B-GPTQ-Int4固定版本；配置只修改模型名称及两项tmp权重路径 |
| 加载与采样 | 主机内部ext4存储；设备0，embedding与层模型启用mmap；temperature=0、max_tokens=128、enable_thinking=false、stream=false |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 服务加载就绪 | 54.055 s | 启动程序至健康检查成功，包含模型加载和轮询等待，不是生成耗时。 |

适用范围：

- 目录名称表示上游编译规格，本次未测最大可用上下文、并发或长期运行。

</details>

**context-2k-prefill-1500**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`f93afe51b24b084020f6fd32c666b2e7fd4c7d31`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行时 | AX-LLM 8501c22b940f8c5804cb35044c5ffc136918b8f1，未修改源码，编译AXCL后端 |
| 配置与分词器 | 官方Qwen3-1.7B-GPTQ-Int4固定版本；配置只修改模型名称及两项tmp权重路径 |
| 加载与采样 | 主机内部ext4存储；设备0，embedding与层模型启用mmap；temperature=0、max_tokens=128、enable_thinking=false、stream=false |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 服务加载就绪 | 56.076 s | 启动程序至健康检查成功，包含模型加载和轮询等待，不是生成耗时。 |

适用范围：

- 目录名称表示上游编译规格，本次未测最大可用上下文、并发或长期运行。

</details>

**context-2500-prefill-2k**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`f93afe51b24b084020f6fd32c666b2e7fd4c7d31`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行时 | AX-LLM 8501c22b940f8c5804cb35044c5ffc136918b8f1，未修改源码，编译AXCL后端 |
| 配置与分词器 | 官方Qwen3-1.7B-GPTQ-Int4固定版本；配置只修改模型名称及两项tmp权重路径 |
| 加载与采样 | 主机内部ext4存储；设备0，embedding与层模型启用mmap；temperature=0、max_tokens=128、enable_thinking=false、stream=false |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 服务加载就绪 | 62.080 s | 启动程序至健康检查成功，包含模型加载和轮询等待，不是生成耗时。 |

适用范围：

- 目录名称表示上游编译规格，本次未测最大可用上下文、并发或长期运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/blob/f93afe51b24b084020f6fd32c666b2e7fd4c7d31/Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/blob/f93afe51b24b084020f6fd32c666b2e7fd4c7d31/Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/blob/f93afe51b24b084020f6fd32c666b2e7fd4c7d31/Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/blob/f93afe51b24b084020f6fd32c666b2e7fd4c7d31/Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/blob/f93afe51b24b084020f6fd32c666b2e7fd4c7d31/Qwen3-1.7B-GPTQ-Int4-context-2500-prefill-2k/qwen3_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`f93afe51b24b084020f6fd32c666b2e7fd4c7d31`。仓库中的 87 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/tree/f93afe51b24b084020f6fd32c666b2e7fd4c7d31)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。
- 这是带 tmp 标识的版本，固定本页提交使用，并与非 tmp 仓库分别保存。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/tree/f93afe51b24b084020f6fd32c666b2e7fd4c7d31)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-1.7B-GPTQ-Int4-tmp/blob/f93afe51b24b084020f6fd32c666b2e7fd4c7d31/README.md)。

返回[完整模型目录](../catalog.mdx)。
