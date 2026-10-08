---
title: "Qwen2.5-7B-Instruct 部署指南"
sidebar_label: "Qwen2.5-7B-Instruct"
description: "Qwen2.5-7B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-7B-Instruct 部署指南

Qwen2.5-7B-Instruct 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 下载固定版本模型

在连接算力卡的 RK3576 终端执行。此固定版本包含一套 `qwen2.5-7b-ctx-int4-ax650` 权重，共 28 个文本层和一个输出层。完整文件约 5.62 GiB，下载分区建议至少预留 8 GiB。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b/97ccbbde2f22
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-7B-Instruct \
  --revision 97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb \
  --local-dir "$MODEL_DIR"
```

板载空间不足时，将 `MODEL_DIR` 指向已挂载的存储卡或 SSD。代理设置见[下载方式与文件校验](../../usage/download-models.md)。

下载[固定版本文件校验包](../../../static/examples/qwen25-7b-standard-20261003.tar.gz)，复制到 RK3576 的 `~/Downloads`，并命名为 `qwen25-7b-standard-20261003.tar.gz`。校验包不包含模型权重，使用 Python 3.9 或更高版本运行：

```bash
cd ~/Downloads
echo '93e334372ebac1fd15465faf702f4e237db5b2cc89464c6b347546a1ab42033d  qwen25-7b-standard-20261003.tar.gz' | sha256sum -c -
tar -xzf qwen25-7b-standard-20261003.tar.gz
python3 qwen25-7b-standard-20261003/verify_models.py "$MODEL_DIR"
```

校验包应显示 `OK`，脚本应输出 `Verified 49 model files`。文件缺失或校验不一致时，重新下载对应文件，通过后再运行。

## 准备分词环境与程序

继续在当前终端执行。分词服务使用 Python，模型推理由仓库中的 ARM64 AXCL 程序完成。

```bash
python3 -m venv ~/edgeaccel/qwen25-7b-uid-env
~/edgeaccel/qwen25-7b-uid-env/bin/python -m pip install \
  'transformers==4.51.3' 'tokenizers==0.21.4'
export PATH=/usr/bin/axcl:$PATH
axcl-smi
cd "$MODEL_DIR"
echo '1f9f1a1ca329b47f70840e8b6d104ce8248a82326aa2402bccb31144590a8fb2  main_axcl_aarch64' | sha256sum -c -
chmod +x main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序校验应显示 `OK`，依赖中不能出现 `not found`。帮助信息应包含 `--devices`、`--system_prompt` 和 `--url_tokenizer_model`。

## 启动官方分词服务

将当前终端作为终端 1，执行后保持服务运行：

```bash
cd "$MODEL_DIR"
USE_TORCH=0 USE_TF=0 USE_FLAX=0 TOKENIZERS_PARALLELISM=false \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/edgeaccel/qwen25-7b-uid-env/bin/python qwen2.5_tokenizer_uid.py \
  --host 127.0.0.1 --port 8519
```

这里只使用分词器，不需要安装 PyTorch。程序通过 UID 创建独立会话，须保留仓库配套的分词脚本及模板。

## 配置单卡并运行问答

另开终端 2，重新设置同一模型目录，创建独立运行目录。以下配置使用设备 0、`top_k=1` 和原版 Qwen 系统提示词。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b/97ccbbde2f22
WEIGHTS="$MODEL_DIR/qwen2.5-7b-ctx-int4-ax650"
RUN_DIR=~/edgeaccel/results/qwen2-5-7b
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
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 AXLLM_DEVICES=0 \
  "$MODEL_DIR/main_axcl_aarch64" \
  --devices 0 \
  --system_prompt 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.' \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:8519 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 152064 --tokens_embed_size 3584 \
  --use_mmap_load_embed 0 --live_print 1 2>&1 | tee answer.log
```

`--use_mmap_load_embed 0` 会将约 1.02 GiB 的 embedding 加载到主机内存，还需为操作系统和运行程序保留空间。等待出现输入提示后输入问题：

```text
What is 2 + 3? Reply with only the number.
```

回答结束后输入 `q` 退出。复现各条独立样例时，每次重新启动程序；同一进程中的连续对话需要另行验证。完成后执行 `axcl-smi` 确认模型资源已释放，并在终端 1 按 `Ctrl+C` 结束分词服务。




## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

在RK3576 + AX8850 16GB上完成算术、中文问答和结构化输出三条独立样例。算术和中文回答符合要求；结构化输出的字段、数值正确，但额外包含Markdown代码围栏。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

正确返回5，并满足只返回数字的要求。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 用于高速连接和传输计算机系统中各种扩展卡和设备之间的数据。
```

用一句中文说明PCIe用于扩展设备之间的高速数据传输。

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

apple=3、pear=2正确，但附带Markdown代码围栏，未满足只返回JSON对象的要求。

**使用时注意：**

- 仅验证固定版本Int4权重的三条独立短输入；不代表长上下文、连续对话、并发或长期稳定性已验证。
- 请求只返回JSON时，回复仍包含Markdown代码围栏；原始回复不能直接作为纯JSON解析。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | RK3576 ARM64，约4GB主机内存，Ubuntu 24.04，6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM15232MiB |
| 模型版本 | qwen2.5-7b-ctx-int4-ax650；仓库原版ARM64 CLI和UID分词服务 |
| 分词环境 | Python3.12.3 / Transformers4.51.3 / tokenizers0.21.4 |
| 运行配置 | 设备0，Qwen原版系统提示词，top_k=1，mmap_embed=0；每条样例新进程、独立会话 |
| 模型读取 | 只读网络模型文件；完整进程耗时包含加载，不代表本地磁盘加载速度或纯NPU性能 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例1完整进程 | 177.914 s | 包含模型加载、单次问答及退出；仅作本次操作耗时参考。 |
| 示例2完整进程 | 182.308 s | 包含模型加载、单次问答及退出；仅作本次操作耗时参考。 |
| 示例3完整进程 | 181.345 s | 包含模型加载、单次问答及退出；仅作本次操作耗时参考。 |

适用范围：

- 本次使用16GB算力卡，实际8GB卡容量与稳定性需要单独测试。
- 模型通过只读网络挂载读取，完整进程耗时包含模型加载；不代表本地磁盘或纯NPU性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_qwen2.5_7b_ctx_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/run_qwen2.5_7b_ctx_int4_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5-7b-ctx-int4-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_7b_ctx_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/run_qwen2.5_7b_ctx_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_7b_ctx_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/run_qwen2.5_7b_ctx_int4_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_7b_ctx_int4_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/run_qwen2.5_7b_ctx_int4_axcl_aarch64_api.sh) | 启动或构建脚本 |
| [`run_qwen2.5_7b_ctx_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/run_qwen2.5_7b_ctx_int4_axcl_x86.sh) | 启动或构建脚本 |

仓库提交：`97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/tree/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/tree/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/README.md)。
- [主要程序入口：qwen2.5_tokenizer_uid.py](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct/blob/97ccbbde2f2282a24ff00bb5df8e5c9eb34033fb/qwen2.5_tokenizer_uid.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-context)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-context)。

返回[完整模型目录](../catalog.mdx)。
