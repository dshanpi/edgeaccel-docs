---
title: "Qwen2.5-3B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen2.5-3B-Instruct-GPTQ-Int4"
description: "Qwen2.5-3B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-3B-Instruct-GPTQ-Int4 部署指南

Qwen2.5-3B-Instruct-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4` 的固定版本。下面下载本页选用的 87 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-3b-instruct-gptq-int4/f1994e9ff277
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4 \
  --include "README.md" "main_axcl_aarch64" "post_config.json" "qwen2.5-3b-gptq-int4-ax650/model.embed_tokens.weight.bfloat16.bin" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l14_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l15_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l16_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l17_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l18_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l19_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l1_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l20_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l21_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l22_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l23_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l24_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l25_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l26_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l27_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l28_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l29_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l2_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l30_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l31_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l32_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l33_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l34_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l35_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l3_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l4_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l5_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l6_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l7_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l8_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l9_together.axmodel" "qwen2.5-3b-gptq-int4-ax650/qwen2_post.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/model.embed_tokens.weight.bfloat16.bin" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l0_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l10_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l11_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l12_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l13_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l14_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l15_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l16_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l17_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l18_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l19_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l1_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l20_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l21_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l22_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l23_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l24_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l25_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l26_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l27_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l28_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l29_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l2_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l30_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l31_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l32_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l33_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l34_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l35_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l3_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l4_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l5_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l6_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l7_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l8_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_p128_l9_together.axmodel" "qwen2.5-3b-gptq-int4-ctx-ax650/qwen2_post.axmodel" "qwen2.5_tokenizer.py" "qwen2.5_tokenizer/merges.txt" "qwen2.5_tokenizer/tokenizer.json" "qwen2.5_tokenizer/tokenizer_config.json" "qwen2.5_tokenizer/vocab.json" "qwen2.5_tokenizer_uid.py" "run_qwen2.5_3b_gptq_int4_axcl_aarch64.sh" "run_qwen2.5_3b_gptq_int4_ctx_axcl_x86.sh" \
  --revision f1994e9ff277d8dfea28ead7878041e1a1f00cf0 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备程序与分词服务

以下命令在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`。本页实测使用主机内部存储；非 CTX 文件约 2.63GB，CTX 文件约 3.01GB，两套完整下载约 5.63GB，另外预留运行和日志空间。本节使用仓库自带的 ARM64 程序和非 CTX 权重；分词服务使用 `qwen2.5_tokenizer.py`。

```bash
python3 -m venv ~/edgeaccel/qwen25-gptq-env
source ~/edgeaccel/qwen25-gptq-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4' 'jinja2==3.1.6'
cd "$MODEL_DIR"
printf '%s  %s\n' \
  bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

程序校验须显示 `OK`，动态库检查不得出现 `not found`。设置固定采样参数，并保留上游配置副本：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('post_config.json')
backup = p.with_suffix('.json.upstream')
if not backup.exists():
    backup.write_bytes(p.read_bytes())
config = json.loads(p.read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
p.write_text(json.dumps(config, indent=2) + '\n')
PY
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
python qwen2.5_tokenizer.py --host 127.0.0.1 --port 12345
```

保持这个终端运行。Python 服务负责分词，文本生成由 AXCL 程序在算力卡上完成。

## 运行单轮问答

另开主机终端，设置同一内部存储中的模型目录。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-3b-instruct-gptq-int4/f1994e9ff277
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

PROMPT='What is 2 + 3? Reply with only the number.'
WEIGHTS=qwen2.5-3b-gptq-int4-ax650
./main_axcl_aarch64 \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 36 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:12345 \
  --bos 0 --eos 0 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 2048 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 --prompt "$PROMPT"
```

当前设置采用非 mmap 方式加载 embedding，在生成结束后显示完整回答并退出。复现其他单轮输入时，修改 `PROMPT` 后重新运行同一命令：

```text
请用一句中文说明 PCIe 的用途。
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

运行日志应完成 36 层和 post 模型初始化，随后输出回答并出现 `hit eos`。程序结束后运行 `axcl-smi`，确认推理进程已释放资源。模型加载耗时与首 token、生成速率分别记录。

## 准备 CTX 版本

CTX 权重使用 UID 分词接口。本模型仓库自带的 ARM64 程序用于前面的非 CTX 版本；CTX 运行程序单独下载到 `ctx-runtime`，保留两个程序及各自的启动命令。

先在原分词服务终端按 `Ctrl+C` 停止 `qwen2.5_tokenizer.py`，确认推理程序已经退出。在模型目录下载固定版本的 ARM64 UID 程序：

```bash
cd "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-3B-Instruct \
  main_axcl_aarch64 \
  --revision ad62e7be39deda430ce48469961d7ed4701f5405 \
  --local-dir "$MODEL_DIR/ctx-runtime"
printf '%s  %s\n' \
  a587bcc25917e4c66277fba689a0e2718f50103e0fd249729e0cfb2f9b1d7c83 \
  ctx-runtime/main_axcl_aarch64 | sha256sum -c -
chmod +x ctx-runtime/main_axcl_aarch64
ldd ctx-runtime/main_axcl_aarch64
source ~/edgeaccel/qwen25-gptq-env/bin/activate
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

程序来自 `Qwen2.5-3B-Instruct` 的上述固定提交。模型权重和分词资源仍使用本页 `Qwen2.5-3B-Instruct-GPTQ-Int4` 仓库中的 CTX 文件，不能替换为其他量化版本的权重。程序校验须显示 `OK`，动态库检查不得出现 `not found`。

## 运行 CTX 问答与连续对话

在另一个终端设置同一模型目录，运行以下命令。采样配置沿用前文的 `top_k=1` 设置。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-3b-instruct-gptq-int4/f1994e9ff277
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
WEIGHTS=qwen2.5-3b-gptq-int4-ctx-ax650
./ctx-runtime/main_axcl_aarch64 \
  --system_prompt 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.' \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 36 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 2048 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0
```

初始化完成并出现 `prompt >>` 后，输入前文的一条单轮问题。等待回复后输入 `q` 退出；每条单轮样例分别启动程序，避免上下文互相影响。

检查连续对话时，重新启动程序，在同一进程内依次输入下面两行。每次等待回复后再输入下一行：

```text
Remember code 4729. Reply only OK.
What code did I ask you to remember? Reply with only the digits.
```

第二轮没有再次给出数字，用于观察模型对上一轮信息的利用。结束后输入 `q` 退出，停止分词服务，并用 `axcl-smi` 确认推理资源释放。


## 查看部署效果

### CTX：单轮问答与连续对话

**已运行，效果仍需评估** · 2026-09-29 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

CTX版本完成三条单轮输入与同一进程内的两轮对话，第二轮正确返回第一轮给出的数字。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

输出为5，与题目结果一致。

程序内部首 token 耗时：899.39 ms；含模型加载的完整进程：53.114 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）的主要用途是提供高速、低延迟的数据传输通道，用于连接和加速计算机系统中的高速设备。
```

使用一句中文说明PCIe的高速传输与设备连接用途。

程序内部首 token 耗时：988.59 ms；含模型加载的完整进程：60.256 s。内部计时不等同于客户端端到端首字延迟。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

````text
```json
{
  "apple": 3,
  "pear": 2
}
```
````

对象中的apple为3、pear为2；回复包含Markdown代码围栏，未满足只返回JSON对象的格式要求。

程序内部首 token 耗时：915.64 ms；含模型加载的完整进程：58.903 s。内部计时不等同于客户端端到端首字延迟。

**连续对话 1**

以下各轮使用同一个进程和会话，保留上一轮上下文。

**第 1 轮：输入**

```text
Remember code 4729. Reply only OK.
```

**实际回复**

```text
OK
```

第一轮按要求回复OK。

本轮程序内部首 token 耗时：928.72 ms。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply with only the digits.
```

**实际回复**

```text
4729
```

第二轮准确返回上一轮给出的4729，且仅包含数字。

本轮程序内部首 token 耗时：936.11 ms。

整个对话进程：54.945 s，包含一次模型加载、全部轮次和退出；不代表单轮推理耗时。内部首 token 计时不含模型加载。

**使用时注意：**

- JSON回复带代码围栏，不能直接作为裸JSON解析；短输入基础运行不代表长上下文、持续运行或完整质量验收。
- 仅实测16GB卡上的所列短输入；实际8GB容量、长上下文、并发及持续运行仍需单独验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### 非 CTX：单轮问答

**已运行，效果仍需评估** · 2026-09-29 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

非CTX版本完成算术、中文用途说明和结构化输出三条输入；保留原始回复与完整进程耗时。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

输出为5，与题目结果一致。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）的主要用途是提供高速、低延迟的数据传输通道，用于连接和加速计算机系统中的各种高速外设和系统组件。
```

使用一句中文说明PCIe提供高速数据传输并连接外设的用途。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

````text
```json
{
  "apple": 3,
  "pear": 2
}
```
````

对象中的apple为3、pear为2；回复包含Markdown代码围栏，未满足只返回JSON对象的格式要求。

**使用时注意：**

- JSON回复带代码围栏，不能直接作为裸JSON解析；短输入基础运行不代表长上下文、持续运行或完整质量验收。
- 仅实测16GB卡上的所列短输入；实际8GB容量、长上下文、并发及持续运行仍需单独验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**CTX：单轮问答与连续对话**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-29。模型版本：`f1994e9ff277d8dfea28ead7878041e1a1f00cf0`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 非 CTX 程序 | 本模型仓库固定版本的 main_axcl_aarch64 与非 UID 分词服务 |
| CTX 程序 | Qwen2.5-3B-Instruct 固定版本的 ARM64 UID 程序；本模型仓库的 CTX 权重与 UID 分词服务 |
| 分词依赖 | Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 / Jinja2 3.1.6 |
| 加载与采样 | 主机内部ext4存储；use_mmap_load_embed=0，live_print=0，top_k=1；关闭temperature、repetition_penalty和top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1完整进程 | 53.114 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 单轮示例2完整进程 | 60.256 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 单轮示例3完整进程 | 58.903 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |

适用范围：

- JSON回复带代码围栏，不能直接作为裸JSON解析；短输入基础运行不代表长上下文、持续运行或完整质量验收。
- 仅实测16GB卡上的所列短输入；实际8GB容量、长上下文、并发及持续运行仍需单独验证。

</details>

**非 CTX：单轮问答**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-29。模型版本：`f1994e9ff277d8dfea28ead7878041e1a1f00cf0`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 非 CTX 程序 | 本模型仓库固定版本的 main_axcl_aarch64 与非 UID 分词服务 |
| CTX 程序 | Qwen2.5-3B-Instruct 固定版本的 ARM64 UID 程序；本模型仓库的 CTX 权重与 UID 分词服务 |
| 分词依赖 | Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 / Jinja2 3.1.6 |
| 加载与采样 | 主机内部ext4存储；use_mmap_load_embed=0，live_print=0，top_k=1；关闭temperature、repetition_penalty和top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1完整进程 | 51.415 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 单轮示例2完整进程 | 58.018 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 单轮示例3完整进程 | 54.983 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |

适用范围：

- JSON回复带代码围栏，不能直接作为裸JSON解析；短输入基础运行不代表长上下文、持续运行或完整质量验收。
- 仅实测16GB卡上的所列短输入；实际8GB容量、长上下文、并发及持续运行仍需单独验证。
- 该版本程序未输出首token耗时；保留原生生成速率和含模型加载的完整进程耗时。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_qwen2.5_3b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/run_qwen2.5_3b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen2.5_tokenizer.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5_tokenizer.py) | 旧版分词服务入口 |
| [`qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5-3b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`run_qwen2.5_3b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/run_qwen2.5_3b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_3b_gptq_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/run_qwen2.5_3b_gptq_int4_axcl_x86.sh) | 启动或构建脚本 |
| [`run_qwen2.5_3b_gptq_int4_ctx_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/run_qwen2.5_3b_gptq_int4_ctx_ax650.sh) | 启动或构建脚本 |

仓库提交：`f1994e9ff277d8dfea28ead7878041e1a1f00cf0`。仓库中的 74 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/tree/f1994e9ff277d8dfea28ead7878041e1a1f00cf0)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/tree/f1994e9ff277d8dfea28ead7878041e1a1f00cf0)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/README.md)。
- [主要程序入口：qwen2.5_tokenizer.py](https://huggingface.co/AXERA-TECH/Qwen2.5-3B-Instruct-GPTQ-Int4/blob/f1994e9ff277d8dfea28ead7878041e1a1f00cf0/qwen2.5_tokenizer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
