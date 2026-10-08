---
title: "Qwen2.5-7B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen2.5-7B-Instruct-GPTQ-Int4"
description: "Qwen2.5-7B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-7B-Instruct-GPTQ-Int4 部署指南

Qwen2.5-7B-Instruct-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。




## 下载固定版本模型

在连接算力卡的 RK3576 终端执行。本页使用仓库原版 ARM64 AXCL 程序，配套 28 个文本层、一个输出层和非 UID 分词服务。37 个文件约 5.12 GiB，下载分区建议至少预留 8 GiB。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4 \
  --include 'README.md' 'main_axcl_aarch64' 'post_config.json' \
  'qwen2.5_tokenizer.py' 'qwen2.5_tokenizer/*' \
  'model.embed_tokens.weight.bfloat16.bin' \
  'qwen2_p128_l*_together.axmodel' 'qwen2_post.axmodel' \
  'run_qwen2.5_7b_gptq_int4_axcl_aarch64.sh' \
  --revision 5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c \
  --local-dir "$MODEL_DIR"
```

板载空间不足时，将 `MODEL_DIR` 指向已挂载的存储卡、SSD 或只读模型目录。代理及离线复制方法见[下载方式与文件校验](../../usage/download-models.md)。本次实测从主机的只读网络目录加载权重，完整进程耗时包含网络读取。

下载[37 个模型文件的 SHA256 校验清单](/examples/qwen25-7b-gptq-model-files-20261004.sha256)，将文件重命名为 `qwen25-7b-gptq-model-files-20261004.sha256` 并复制到 `MODEL_DIR`，再执行：

```bash
cd "$MODEL_DIR"
sha256sum -c qwen25-7b-gptq-model-files-20261004.sha256
```

全部文件应显示 `OK`。出现缺失或不匹配时，重新下载对应文件后再运行。

## 准备分词环境与程序

在 RK3576 上执行。Python 负责分词，模型推理由 AXCL 程序完成。

```bash
python3 -m venv ~/edgeaccel/qwen25-7b-gptq-env
~/edgeaccel/qwen25-7b-gptq-env/bin/python -m pip install \
  'transformers==4.51.3' 'tokenizers==0.21.4'
export PATH=/usr/bin/axcl:$PATH
axcl-smi
cd "$MODEL_DIR"
echo 'bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec  main_axcl_aarch64' | sha256sum -c -
chmod +x main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序校验应显示 `OK`，依赖中不能出现 `not found`。帮助信息应包含 `--tokenizer_type`、`--filename_tokenizer_model`、`--prompt` 和 `--continue`。以下步骤用于设备列表中只有一张卡、编号为 0 的环境。

## 启动官方分词服务

终端 1 执行，保持服务运行：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
cd "$MODEL_DIR"
USE_TORCH=0 USE_TF=0 USE_FLAX=0 TOKENIZERS_PARALLELISM=false \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/edgeaccel/qwen25-7b-gptq-env/bin/python qwen2.5_tokenizer.py \
  --host 127.0.0.1 --port 8521
```

保留 `qwen2.5_tokenizer.py` 及同目录的 `qwen2.5_tokenizer` 文件夹。服务内置 Qwen 原版系统提示词；启动输出应包含 `eos_id` 对应的 `151645`。分词服务无需安装 PyTorch。

## 运行单次问答

另开终端 2，设置同一模型目录并创建独立运行目录。以下配置使用 `top_k=1`，每次提问启动一个新进程。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
RUN_DIR=~/edgeaccel/results/qwen25-7b-gptq
export PATH=/usr/bin/axcl:$PATH
mkdir -p "$RUN_DIR"
python3 - "$MODEL_DIR/post_config.json" "$RUN_DIR/post_config.json" <<'PY'
import json, sys
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
Path(sys.argv[2]).write_text(json.dumps(config, indent=2) + '\n')
PY
cd "$RUN_DIR"
set -o pipefail
PROMPT='What is 2 + 3? Reply with only the number.'
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 AXLLM_DEVICES=0 \
  "$MODEL_DIR/main_axcl_aarch64" \
  --template_filename_axmodel "$MODEL_DIR/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:8521 \
  --bos 0 --eos 0 \
  --filename_post_axmodel "$MODEL_DIR/qwen2_post.axmodel" \
  --filename_tokens_embed "$MODEL_DIR/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 152064 --tokens_embed_size 3584 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 \
  --prompt "$PROMPT" 2>&1 | tee answer.log
```

`--use_mmap_load_embed 0` 会将约 1.02 GiB 的 embedding 加载到主机内存，须为操作系统和运行程序保留空间。`--live_print 0` 在生成结束后输出完整回答；等待期间可看到进度。上述算术问题应返回 `5`，日志应出现 `hit eos`，程序随后退出。

复现下方中文和 JSON 样例时，分别替换 `PROMPT` 并重新执行问答命令。测试结束后运行 `axcl-smi` 确认模型资源已释放，在终端 1 按 `Ctrl+C` 结束分词服务。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

在16GB M.2算力卡上完成三条独立短问答。算术和中文回答符合要求；结构化输出的字段和值正确，但附加代码围栏和无依据说明，严格JSON格式项未通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

正确返回5，满足只返回数字的要求。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 用于高速连接和通信，实现计算机组件之间的快速数据传输。
```

用一句中文说明PCIe用于计算机组件之间的高速数据传输。

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

Note: The value for "pear" seems to be missing a digit. I assume it should be `2` (two), but if you meant something else, please let me know.
````

apple=3、pear=2正确，但附带Markdown代码围栏及无依据的“pear缺少数字”说明，未满足只返回JSON对象的要求。

**使用时注意：**

- 本页验证固定版本的三条独立短输入；长上下文、连续对话、并发和长期稳定性仍需单独验证。
- 结构化样例含代码围栏及无依据说明，不能将原始回复直接作为纯JSON解析；业务使用前须检查生成内容。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | RK3576 ARM64，约4GB主机内存，Ubuntu 24.04，6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM15232MiB |
| 运行程序 | 仓库原版main_axcl_aarch64；非UID分词服务qwen2.5_tokenizer.py |
| 分词环境 | Python3.12.3 / Transformers4.51.3 / tokenizers0.21.4 |
| 运行配置 | 设备0，原版Qwen系统提示词，top_k=1、mmap_embed=0、live_print=0、continue=0；每条样例新进程 |
| 模型读取 | 主机只读网络文件；耗时包含模型加载、问答和退出 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例1完整进程 | 162.468 s | 包含网络模型加载、单次问答及退出；用于本次操作耗时参考。 |
| 示例2完整进程 | 163.760 s | 包含网络模型加载、单次问答及退出；用于本次操作耗时参考。 |
| 示例3完整进程 | 184.171 s | 包含网络模型加载、单次问答及退出；用于本次操作耗时参考。 |

适用范围：

- 本次从主机只读网络目录加载权重，完整进程耗时包含加载和退出，不代表本地存储或纯NPU性能。
- 本次使用AX8850 16GB算力卡；实际8GB卡仍需独立回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`qwen2.5_tokenizer.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2.5_tokenizer.py) | 旧版分词服务入口 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/config.json) | 运行配置 |
| [`qwen2_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen2_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/post_config.json) | 运行配置 |
| [`qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_7b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/run_qwen2.5_7b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_7b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/run_qwen2.5_7b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |

仓库提交：`5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/tree/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/tree/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/README.md)。
- [主要程序入口：qwen2.5_tokenizer.py](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2.5_tokenizer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。
- [配套项目：AXERA-TECH/ax-llm.git](https://github.com/AXERA-TECH/ax-llm.git)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
