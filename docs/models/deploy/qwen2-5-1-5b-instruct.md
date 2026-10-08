---
title: "Qwen2.5-1.5B-Instruct 部署指南"
sidebar_label: "Qwen2.5-1.5B-Instruct"
description: "Qwen2.5-1.5B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-1.5B-Instruct 部署指南

Qwen2.5-1.5B-Instruct 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-1.5B-Instruct` 的固定版本。下面下载本页选用的 70 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct/eaa03390b75f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-1.5B-Instruct \
  --include "README.md" "main_axcl_aarch64" "post_config.json" "qwen2.5_tokenizer_uid.py" "qwen2.5_tokenizer/*" "run_qwen2.5_1.5b_ctx_axcl_aarch64.sh" "run_qwen2.5_1.5b_ctx_int4_axcl_aarch64.sh" "qwen2.5-1.5b-ctx-int4-ax650/*" "qwen2.5-1.5b-ctx-ax650/*" \
  --revision eaa03390b75ff42286b46ad492d007ce536b303d \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备程序与分词服务

本页使用同一仓库中的 ARM64 AXCL 程序、UID 分词服务和两套 CTX 权重。完整下载约 4.25GB。以下命令在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`。

```bash
python3 -m venv ~/edgeaccel/qwen25-ctx-env
source ~/edgeaccel/qwen25-ctx-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
printf '%s  %s\n' \
  1f9f1a1ca329b47f70840e8b6d104ce8248a82326aa2402bccb31144590a8fb2 \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

程序校验须显示 `OK`，动态库检查不得出现 `not found`。Python 服务负责分词，文本生成由 AXCL 程序在算力卡上完成。

设置与下方效果一致的采样参数：

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
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持这个终端运行。分词服务与 AXCL 程序使用同一个模型目录。

## 选择精度并运行

另开主机终端，设置同一路径并选择权重目录。若下载到外接存储，将 `MODEL_DIR` 改为实际目录。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct/eaa03390b75f
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

# INT4；测试 INT8 时改为 qwen2.5-1.5b-ctx-ax650
WEIGHTS=qwen2.5-1.5b-ctx-int4-ax650

./main_axcl_aarch64 \
  --system_prompt 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.' \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0
```

本页采用非 mmap 方式加载 embedding，保持 `--use_mmap_load_embed 0`。两套权重均使用 28 层、同一分词服务和相同采样参数。确认模型初始化完成并出现 `prompt >>`，再输入问题；当前设置在生成结束后显示完整回答。

## 输入单轮问题与连续对话

先输入一条问题，例如：

```text
What is 2 + 3? Reply with only the number.
```

等待回复后输入 `q` 退出。复现下方各条单轮样例时，分别重新启动程序，避免上一题的上下文影响下一题。

连续对话使用同一个程序进程。重新启动后，依次输入以下两行，每次等待模型回答后再输入下一行：

```text
Remember code 4729. Reply only OK.
What code did I ask you to remember? Reply with only the digits.
```

第二轮未重复给出数字，用于检查模型能否利用前一轮上下文。完成后输入 `q`，更换 `WEIGHTS` 再测试另一种精度；不要同时启动两个推理进程。

全部测试结束后，在分词服务终端按 `Ctrl+C` 退出，再运行 `axcl-smi` 确认推理进程已经释放资源。下方保留实际回答，内容与格式问题不会人工改写成正确结果。


## 查看部署效果

### INT4：单轮问答与连续对话

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但JSON 回复含代码围栏或额外文字，不能直接解析为指定对象；本次格式要求未通过。 两轮短对话能原样回忆 4729；该结果不代表长上下文通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

精确返回5，数值和只输出数字的要求均符合。

程序内部首 token 耗时：485.44 ms；含模型加载的完整进程：55.383 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速的计算机总线标准，用于连接计算机的外部设备，如硬盘、内存、显卡等。PCIe提高了数据传输速度，使得计算机能够更快地处理数据，提供更好的性能和更高的效率。
```

实际回答包含两句话，未满足一句话要求；内存设备的举例缺少适用条件，不作为严谨的PCIe技术说明。

程序内部首 token 耗时：573.81 ms；含模型加载的完整进程：91.694 s。内部计时不等同于客户端端到端首字延迟。

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

字段和数值正确，但增加了Markdown围栏，不满足只返回可直接解析JSON的要求。

程序内部首 token 耗时：480.39 ms；含模型加载的完整进程：69.174 s。内部计时不等同于客户端端到端首字延迟。

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

按要求仅回复OK。

本轮程序内部首 token 耗时：489.25 ms。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply with only the digits.
```

**实际回复**

```text
4729
```

准确返回前一轮提供的4729，第二轮输入未重复该数字；本次短对话记忆检查通过。

本轮程序内部首 token 耗时：485.84 ms。

整个对话进程：33.239 s，包含一次模型加载、全部轮次和退出；不代表单轮推理耗时。内部首 token 计时不含模型加载。

**使用时注意：**

- 基本运行已完成，但未通过全部内容和格式检查；不据此宣称通用回答质量通过。
- 仅实测16GB卡的三条单轮输入和两轮短对话；未验证实际8GB容量、长上下文、并发及持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### INT8：单轮问答与连续对话

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但JSON 回复含代码围栏或额外文字，不能直接解析为指定对象；本次格式要求未通过。 两轮短对话能原样回忆 4729；该结果不代表长上下文通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

精确返回5，数值和只输出数字的要求均符合。

程序内部首 token 耗时：686.02 ms；含模型加载的完整进程：179.306 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速扩展插槽标准，用于连接计算机的外部设备，如显卡、声卡、网卡等，提供高速的数据传输和并行处理能力，提高了计算机的性能和灵活性。
```

实际回答为一句话，满足长度要求；技术说明仍需专门核对，本例不作为完整的事实准确性验收。

程序内部首 token 耗时：672.53 ms；含模型加载的完整进程：201.328 s。内部计时不等同于客户端端到端首字延迟。

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

字段和数值正确，但增加了Markdown围栏，不满足只返回可直接解析JSON的要求。

程序内部首 token 耗时：547.42 ms；含模型加载的完整进程：199.678 s。内部计时不等同于客户端端到端首字延迟。

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

按要求仅回复OK。

本轮程序内部首 token 耗时：553.24 ms。

**第 2 轮：输入**

```text
What code did I ask you to remember? Reply with only the digits.
```

**实际回复**

```text
4729
```

准确返回前一轮提供的4729，第二轮输入未重复该数字；本次短对话记忆检查通过。

本轮程序内部首 token 耗时：609.92 ms。

整个对话进程：156.448 s，包含一次模型加载、全部轮次和退出；不代表单轮推理耗时。内部首 token 计时不含模型加载。

**使用时注意：**

- 基本运行已完成，但严格JSON格式未满足；中文事实和更广泛回答质量仍需专项核对。
- 仅实测16GB卡的三条单轮输入和两轮短对话；未验证实际8GB容量、长上下文、并发及持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**INT4：单轮问答与连续对话**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`eaa03390b75ff42286b46ad492d007ce536b303d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 程序与分词服务 | 本仓库官方 main_axcl_aarch64；Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 |
| 加载与存储 | 外接ext4存储卡；use_mmap_load_embed=0，AXCL设备0 |
| 采样 | top_k=1；关闭temperature、repetition_penalty、top_p；live_print=0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1首token | 485.44 ms | 程序内部计时，不含模型加载，不等同于客户端端到端首字延迟。 |
| 单轮示例2首token | 573.81 ms | 程序内部计时，不含模型加载，不等同于客户端端到端首字延迟。 |
| 单轮示例3首token | 480.39 ms | 程序内部计时，不含模型加载，不等同于客户端端到端首字延迟。 |
| 连续对话完整进程 | 33.239 s | 一次模型加载、两轮生成与退出的总耗时，不是单轮推理耗时。 |

适用范围：

- 两种精度采用同一输入和采样设置；少量样例不足以比较整体精度或稳定性。

</details>

**INT8：单轮问答与连续对话**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`eaa03390b75ff42286b46ad492d007ce536b303d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 程序与分词服务 | 本仓库官方 main_axcl_aarch64；Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 |
| 加载与存储 | 外接ext4存储卡；use_mmap_load_embed=0，AXCL设备0 |
| 采样 | top_k=1；关闭temperature、repetition_penalty、top_p；live_print=0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1首token | 686.02 ms | 程序内部计时，不含模型加载，不等同于客户端端到端首字延迟。 |
| 单轮示例2首token | 672.53 ms | 程序内部计时，不含模型加载，不等同于客户端端到端首字延迟。 |
| 单轮示例3首token | 547.42 ms | 程序内部计时，不含模型加载，不等同于客户端端到端首字延迟。 |
| 连续对话完整进程 | 156.448 s | 一次模型加载、两轮生成与退出的总耗时，不是单轮推理耗时。 |

适用范围：

- 两种精度采用同一输入和采样设置；少量样例不足以比较整体精度或稳定性。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_qwen2.5_1.5b_ctx_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/run_qwen2.5_1.5b_ctx_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`qwen2.5-1.5b-ctx-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5-1.5b-ctx-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-ctx-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5-1.5b-ctx-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-ctx-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5-1.5b-ctx-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-ctx-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5-1.5b-ctx-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-ctx-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5-1.5b-ctx-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_1.5b_ctx_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/run_qwen2.5_1.5b_ctx_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_1.5b_ctx_ax650_api.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/run_qwen2.5_1.5b_ctx_ax650_api.sh) | 启动或构建脚本 |
| [`run_qwen2.5_1.5b_ctx_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/run_qwen2.5_1.5b_ctx_axcl_x86.sh) | 启动或构建脚本 |
| [`run_qwen2.5_1.5b_ctx_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh) | 启动或构建脚本 |

仓库提交：`eaa03390b75ff42286b46ad492d007ce536b303d`。仓库中的 58 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/tree/eaa03390b75ff42286b46ad492d007ce536b303d)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/tree/eaa03390b75ff42286b46ad492d007ce536b303d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/README.md)。
- [主要程序入口：qwen2.5_tokenizer_uid.py](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct/blob/eaa03390b75ff42286b46ad492d007ce536b303d/qwen2.5_tokenizer_uid.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-context)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-context)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen2.5-1.5B-Instruct)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
