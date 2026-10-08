---
title: "DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 部署指南"
sidebar_label: "DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4"
description: "DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 部署指南

DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 下载固定版本模型

在连接算力卡的 RK3576 终端执行。模型包约 5.13 GiB，下载分区建议至少有 8 GiB 可用空间；板载空间不足时，将 `MODEL_DIR` 改为已挂载的 SSD 或存储卡目录。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-7b-int4/9b903307e1ea
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 \
  --revision 9b903307e1ea3b216330e88f8e6fe39b6627bb74 \
  --local-dir "$MODEL_DIR"
```

保留完整目录中的 28 个文本层、输出层、embedding、分词器、ARM64 程序和配置文件。代理设置见[下载方式与文件校验](../../usage/download-models.md)。标准 7B 版与本 Int4 版的分词服务接口不同，不能互换脚本。

下载[固定版本文件校验包](../../../static/examples/deepseek7b-int4-verify-20261003.tar.gz)，复制到 RK3576 的 `~/Downloads`，并将下载文件命名为 `deepseek7b-int4-verify-20261003.tar.gz`。使用 Python 3.9 或更高版本校验全部 43 个文件：

```bash
cd ~/Downloads
echo '45846cf74f7d20ed094f67f75e23111a847669223ee32aafc601f8dc2e0d00f1  deepseek7b-int4-verify-20261003.tar.gz' | sha256sum -c -
tar -xzf deepseek7b-int4-verify-20261003.tar.gz
python3 deepseek7b-int4-verify-20261003/verify_models.py "$MODEL_DIR"
```

校验包应显示 `OK`，脚本应输出 `Verified 43 model files`。文件缺失或 SHA256 不一致时，重新下载对应文件并再次校验，通过后再启动模型。

## 准备分词环境与运行程序

本页使用仓库中的 `main_axcl_aarch64`，适用于 Linux ARM64 主机上的 AXCL 算力卡。先确认 AXCL 驱动和设备可用，再安装分词依赖：

```bash
python3 -m venv ~/edgeaccel/deepseek7b-tokenizer-env
~/edgeaccel/deepseek7b-tokenizer-env/bin/python -m pip install \
  'transformers==4.51.3' 'tokenizers==0.21.4'
export PATH=/usr/bin/axcl:$PATH
axcl-smi
cd "$MODEL_DIR"
echo 'bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec  main_axcl_aarch64' | sha256sum -c -
chmod +x main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序校验应显示 `OK`，依赖中不能出现 `not found`。帮助信息应包含 `--filename_tokenizer_model`、`--tokenizer_type` 和 `--use_mmap_load_embed`。本程序通过 PATH 调用 `axcl-smi`，因此两个终端都要包含 `/usr/bin/axcl`。

## 启动官方分词服务

继续使用当前终端作为终端 1。进入模型根目录后执行，保持进程运行：

```bash
cd "$MODEL_DIR"
USE_TORCH=0 USE_TF=0 USE_FLAX=0 TOKENIZERS_PARALLELISM=false \
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ~/edgeaccel/deepseek7b-tokenizer-env/bin/python deepseek-r1_tokenizer.py \
  --host 127.0.0.1 --port 8519
```

这里仅运行分词器，不需要安装 PyTorch。使用原始脚本和模板；本仓库模板会保留两个起始 token，不能自行删掉其中一个。

## 配置采样并运行问答

终端 2 重新设置模型目录，创建单独的运行目录。以下配置使用 `top_k=1`，关闭温度、重复惩罚和 top-p 采样，便于复现短输入；原始模型配置保持不变。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-7b-int4/9b903307e1ea
RUN_DIR=~/edgeaccel/results/deepseek-r1-7b-int4
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
curl --fail http://127.0.0.1:8519/eos_id
cd "$RUN_DIR"
WEIGHTS="$MODEL_DIR/deepseek-r1-7b-gptq-int4-ax650"
set -o pipefail
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 AXLLM_DEVICES=0 \
  "$MODEL_DIR/main_axcl_aarch64" \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:8519 --bos 0 --eos 0 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 152064 --tokens_embed_size 3584 \
  --use_mmap_load_embed 0 --live_print 1 --continue 0 \
  --prompt 'What is 2 + 3? Reply with only the number.' 2>&1 | tee answer.log
```

`/eos_id` 应返回包含 `"eos_id": 151643` 的 JSON。`--use_mmap_load_embed 0` 沿用官方示例的 embedding 读取方式，会将约 1.02 GiB 的 embedding 文件加载到主机内存，`--continue 0` 表示每次只运行一个独立问题。更换 `--prompt` 可复现下方其他输入。

完整进程计时包含模型加载和退出，不能等同于纯推理耗时。运行结束后执行 `axcl-smi`，确认模型资源已释放；不再使用分词服务时，在终端 1 按 `Ctrl+C` 退出。




## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

在 16GB M.2 算力卡上完成算术、中文说明和 JSON 三条独立问答。算术最终结果为 5，中文回复可读，JSON 代码块内的键值正确；三条均包含思考文本，严格输出格式尚未通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复的最终回答部分**

```text
5
```

最终数值为 5，与预检结果一致；完整回复包含思考文本，没有满足“只返回数字”的格式要求。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
Okay, so I need to figure out what 2 plus 3 is. Hmm, let's see. I remember from when I was a kid that addition is like combining things. So if I have 2 apples and someone gives me 3 more apples, how many apples do I have in total? That should be 2 plus 3. 

Wait, but I'm not sure if I'm thinking about this correctly. Maybe I should count them out. Let me try. Starting with 2, if I add 1, that's 3, then 4, then 5. So 2 plus 3 equals 5. Yeah, that makes sense. I think I got it right. So the answer should be 5.
</think>

5
```

</details>

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复的最终回答部分**

```text
PCIe（PCI Express）是一种高性能的总线技术，主要用于在计算机内部连接和传输数据，提升设备之间的性能和扩展性。
```

最终回答用一句中文概括了 PCIe 的连接和数据传输用途；完整回复还包含思考过程。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
好的，用户让我用一句中文说明PCIe的用途。首先，我得明确PCIe是什么。PCIe是PCIExpress的缩写，是一种用于传输数据的专用总线，对吧？它主要用在计算机内部，帮助不同组件之间传输数据，比如CPU、GPU、内存控制器等。

那PCIe的用途是什么呢？它主要用来提高计算机内部的性能，因为总线带宽高，传输速度快，这样系统整体运行会更流畅。另外，PCIe还支持扩展性，可以增加更多的设备，比如更多的GPU或存储设备，这样系统功能更丰富，性能也更强。

所以，总结一下，PCIe的用途就是作为高性能的总线，用于连接和传输数据，提升计算机内部的性能和扩展性。这样用户就能明白PCIe在现代计算机中的重要性了。
</think>

PCIe（PCI Express）是一种高性能的总线技术，主要用于在计算机内部连接和传输数据，提升设备之间的性能和扩展性。
```

</details>

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复的最终回答部分**

````text
```json
{"apple": 3, "pear": 2}
```
````

代码块内的对象包含 apple=3、pear=2；最终回答保留 Markdown 代码块，完整回复还含思考文本，不能直接作为纯 JSON 解析。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

````text
Alright, so I just received a query from a user. Let me try to understand what they're asking for. The user wrote, "You are DeepSeek-R1, You are a helpful assistant. Return only a JSON object with apple equal to 3 and pear equal to 2." Hmm, okay, so they're telling me that they're DeepSeek-R1, an AI assistant, and they want me to return a JSON object with specific values: apple set to 3 and pear set to 2.

First, I need to parse the user's request correctly. They mention that I'm DeepSeek-R1, so I should acknowledge that. Then, they want a JSON object. JSON objects are key-value pairs, so I need to structure it correctly. The keys should be "apple" and "pear", with the corresponding values 3 and 2.

I should make sure that the JSON syntax is correct. That means proper use of quotation marks, colons, and commas. Also, the JSON should be valid so that it can be parsed without errors. So, I'll structure it as {"apple": 3, "pear": 2}.

Now, I need to respond to the user. They might be testing my ability to generate specific JSON outputs or perhaps they're using this for some application that requires exact data. It's also possible they're checking if I can follow instructions precisely. Either way, the response needs to be clear and concise.

I should also consider if there's any additional context I might need. The user didn't mention anything else, so I can assume they just want the JSON object as specified. No extra information or formatting is needed.

I should make sure to return only the JSON object without any extra text. The user emphasized "Return only a JSON object," so I need to stick to that. No explanations, no extra sentences—just the JSON.

Putting it all together, I'll start with a friendly greeting, mention that I'm DeepSeek-R1, and then provide the JSON object as specified. I'll make sure the JSON is correctly formatted so that it's valid and can be used wherever it's needed.

I don't see any hidden requirements here, so I can proceed without overcomplicating things. The user's request seems straightforward, so I'll execute it as such.
</think>

```json
{"apple": 3, "pear": 2}
```
````

</details>

**使用时注意：**

- 本次使用单卡、top_k=1 和独立短问题；未覆盖长上下文、多轮对话、并发或持续负载。
- 模型会输出思考文本，JSON 回答还带 Markdown 代码块；接入结构化接口前需处理格式并校验结果。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`9b903307e1ea3b216330e88f8e6fe39b6627bb74`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | RK3576 ARM64，约 4GB 主机内存，Ubuntu 24.04，6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件 V3.16.0，CMM 15232 MiB |
| 运行程序 | 仓库原版 main_axcl_aarch64，SHA256 bb111fc0…；原版无状态 HTTP 分词服务 |
| 分词环境 | Python 3.12.3 / Transformers 4.51.3 / tokenizers 0.21.4；关闭可选 Torch、TF、Flax 导入 |
| 运行配置 | 单卡独立短问答；top_k=1，mmap_embed=0，continue=0 |
| 模型读取 | 只读网络模型文件；完整进程耗时包含模型加载，不代表本地磁盘或纯 NPU 性能 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例 1 完整进程 | 204.875 s | 包含模型加载、问答及退出；仅作本次操作耗时参考。 |
| 示例 2 完整进程 | 220.120 s | 包含模型加载、问答及退出；仅作本次操作耗时参考。 |
| 示例 3 完整进程 | 314.536 s | 包含模型加载、问答及退出；仅作本次操作耗时参考。 |

适用范围：

- 仅验证当前 16GB 卡；实际 8GB 卡的容量和兼容性需要单独测试。
- 三次程序均报告 hit eos，输入与生成长度未达到 1024 的上下文容量；未独立采集 EOS token ID，不据此宣称所有终止路径均已覆盖。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |
| [`deepseek-r1_tokenizer.py`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1_tokenizer.py) | 旧版分词服务入口 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/config.json) | 运行配置 |
| [`deepseek-r1_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/post_config.json) | 运行配置 |
| [`run_deepseek-r1_7b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_deepseek-r1_7b_gptq_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_axcl_x86.sh) | 启动或构建脚本 |

仓库提交：`9b903307e1ea3b216330e88f8e6fe39b6627bb74`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/tree/9b903307e1ea3b216330e88f8e6fe39b6627bb74)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/tree/9b903307e1ea3b216330e88f8e6fe39b6627bb74)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/README.md)。
- [主要程序入口：deepseek-r1_tokenizer.py](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1_tokenizer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
