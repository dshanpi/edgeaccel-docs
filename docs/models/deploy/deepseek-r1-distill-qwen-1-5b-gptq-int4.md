---
title: "DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4 部署指南"
sidebar_label: "DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4"
description: "DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4 部署指南

DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4` 的固定版本。下面下载本页选用的 38 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-1-5b-gptq-int4/496f830bba4e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4 \
  "README.md" \
  "config.json" \
  "deepseek-r1-1.5b-gptq-int4-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l14_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l15_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l16_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l17_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l18_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l19_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l1_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l20_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l21_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l22_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l23_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l24_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l25_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l26_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l27_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l2_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l3_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l4_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l5_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l6_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l7_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l8_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l9_together.axmodel" \
  "deepseek-r1-1.5b-gptq-int4-ax650/qwen2_post.axmodel" \
  "deepseek-r1_tokenizer.py" \
  "deepseek-r1_tokenizer/tokenizer.json" \
  "deepseek-r1_tokenizer/tokenizer_config.json" \
  "main_axcl_aarch64" \
  "post_config.json" \
  "run_deepseek-r1_1.5b_gptq_int4_axcl_aarch64.sh" \
  --revision 496f830bba4e2310ccd17aa7d243ead4d59df12d \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词服务

本例使用仓库的 ARM64 AXCL 程序和 `deepseek-r1_tokenizer.py`。在 RK3576 主机安装已测试的分词依赖：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。仓库中的空 `config.json` 不作为新版 AX-LLM 服务配置；使用下方已测试的旧版命令行参数。

## 运行单轮问答

先设置本页使用的贪心采样，再启动分词服务。该服务使用非 UID 接口，不能替换为 Qwen 的 UID 服务。

```bash
cd "$MODEL_DIR"
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
python deepseek-r1_tokenizer.py --host 127.0.0.1 --port 12345
```

保持分词服务运行。在另一终端执行下方命令，替换 `PROMPT` 的内容即可测试其他问题。`--continue 0` 表示完成一题后退出，`--live_print 0` 表示生成结束后输出完整回复。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-1-5b-gptq-int4/496f830bba4e
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
PROMPT='What is 2 + 3? Reply with only the number.'
./main_axcl_aarch64 \
  --template_filename_axmodel 'deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l%d_together.axmodel' \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:12345 \
  --bos 0 --eos 0 \
  --filename_post_axmodel deepseek-r1-1.5b-gptq-int4-ax650/qwen2_post.axmodel \
  --filename_tokens_embed deepseek-r1-1.5b-gptq-int4-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 --prompt "$PROMPT"
```

等待模型加载和生成结束。原始回复可能包含 `<think>` 思考文本、最终回答以及 Markdown 格式，不能直接当作 JSON 或单个数字传给其他程序。结束使用后，在分词服务终端按 `Ctrl+C`。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但算术回复含解释；JSON 回复含代码围栏或额外文字，不能直接解析为指定对象；本次格式要求未通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复的最终回答部分**

```text
The result of 2 + 3 is 5.

**Answer:** 5
```

最终数值为 5，但原始回复包含思考文本、说明和 Markdown，没有遵循只输出数字的要求。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
<think>
Okay, so I need to figure out what 2 plus 3 is. Hmm, I remember from school that when you add numbers, you combine them. So, 2 and 3 together. Let me think, 2 plus 3. If I have two apples and then get three more, how many apples do I have in total? That would be five. Yeah, that makes sense. So, 2 plus 3 equals 5. I think that's the right answer. I don't think I'm missing anything here. It's a simple addition problem, and I can visualize it with objects to make sure. So, I'm confident that the answer is 5.
</think>

The result of 2 + 3 is 5.

**Answer:** 5
```

</details>

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复的最终回答部分**

```text
PCIe是高性能计算芯片的扩展，支持多种计算模式和架构，广泛应用于人工智能、图像处理和数据科学等领域。
```

该句未正确说明 PCIe 的含义，不能用作技术说明。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
<think>
好的，我现在需要帮用户用一句中文说明PCIe的用途。首先，用户已经提供了一个例子，是“PCIe是高性能计算芯片的扩展，支持多种计算模式和架构，广泛应用于人工智能、图像处理和数据科学等领域。”看起来用户希望得到一个简洁明了的解释，可能用于学习或快速了解PCIe的基本信息。

我应该先确认PCIe是什么，然后说明它的主要功能和应用场景。可能需要提到它在AI、图像处理和数据科学中的应用，这样用户能更清楚PCIe的用途。同时，要保持语言简洁，避免过于复杂的术语，让用户容易理解。

另外，考虑到用户可能是在学习相关技术，所以解释时应该简明扼要，重点突出PCIe的优势和适用场景。可能还需要提到PCIe的扩展性，因为它支持多种架构，这样用户能理解它在不同场景中的应用。

最后，检查一下用词是否准确，比如“扩展”是否正确，是否需要更专业的术语？不过用户给的例子已经用词准确，所以保持一致。确保句子流畅，没有语法错误，这样用户读起来会更顺畅。
</think>

PCIe是高性能计算芯片的扩展，支持多种计算模式和架构，广泛应用于人工智能、图像处理和数据科学等领域。
```

</details>

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复的最终回答部分**

````text
The JSON object with 'apple' set to 3 and 'pear' set to 2 is as follows:

```json
{
  "apple": 3,
  "pear": 2
}
```
````

最终代码块内的 apple=3、pear=2 符合要求；整段原始回复还含思考文本、说明和围栏，不能直接作为 JSON 解析。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

````text
<think>
Okay, so I need to figure out how to solve this problem where I have to return a JSON object with 'apple' equal to 3 and 'pear' equal to 2. Let me think about how to approach this.

First, I know that JSON is a data interchange format that's used to represent data structures in a readable and easy-to-understand format. It's commonly used in web applications, APIs, and other systems that need to exchange data with other systems.

The user has specified that the output should be a JSON object. So, I need to make sure that the structure I return is correct. In JSON, objects are defined with curly braces, and each key-value pair is separated by a comma. The keys are in double quotes, and the values can be numbers, strings, or other objects.

So, the keys here are 'apple' and 'pear'. The values are 3 and 2, respectively. I need to make sure that the keys are in double quotes and the values are in double quotes as well. So, the structure should look like this:

{
  "apple": 3,
  "pear": 2
}

I should also check if there are any other requirements. The user didn't specify any additional features, so I think this is straightforward.

Wait, maybe I should consider if the values are numbers or strings. In this case, they are numbers, so using numbers in the JSON is appropriate. If the values were strings, I might need to enclose them in quotes, but since they are numbers, it's fine.

Another thing to consider is the syntax. The JSON should be properly formatted with each key-value pair separated by a comma, and the entire object should be enclosed in curly braces. Also, the keys should be in double quotes, and the entire JSON should be in double quotes as well.

I should also make sure that the JSON is valid and can be parsed correctly by any application that needs it. So, no special characters or syntax errors should be present.

Let me think if there's anything else. The user wants the output to be a JSON object, so I don't need to add any additional fields or methods. Just the object with the specified keys and values.

I think that's all. So, the final JSON should be as I wrote earlier.
</think>

The JSON object with 'apple' set to 3 and 'pear' set to 2 is as follows:

```json
{
  "apple": 3,
  "pear": 2
}
```
````

</details>

**使用时注意：**

- 本次基本运行通过，中文事实性和严格输出格式未通过核对。页面折叠保存原始完整回复，未将最终回答片段冒充全部输出。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`496f830bba4e2310ccd17aa7d243ead4d59df12d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | aarch64 / RK3576，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 推理程序 | 官方固定提交的 main_axcl_aarch64，AXCL 设备 0；跨仓库复用时另列程序来源与校验值。 |
| 分词服务 | 官方配套 tokenizer；Python 3.12 / Transformers 4.51.3 / Tokenizers 0.21.4 |
| 采样 | top_k=1；关闭 temperature、repetition_penalty、top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例 1 进程耗时 | 51.304 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 66.242 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 102.434 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_deepseek-r1_1.5b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/run_deepseek-r1_1.5b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |
| [`deepseek-r1_tokenizer.py`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1_tokenizer.py) | 旧版分词服务入口 |
| [`deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1-1.5b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/config.json) | 运行配置 |
| [`deepseek-r1_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/post_config.json) | 运行配置 |
| [`run_deepseek-r1_1.5b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/run_deepseek-r1_1.5b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_deepseek-r1_1.5b_gptq_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/run_deepseek-r1_1.5b_gptq_int4_axcl_x86.sh) | 启动或构建脚本 |

仓库提交：`496f830bba4e2310ccd17aa7d243ead4d59df12d`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/tree/496f830bba4e2310ccd17aa7d243ead4d59df12d)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/tree/496f830bba4e2310ccd17aa7d243ead4d59df12d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/README.md)。
- [主要程序入口：deepseek-r1_tokenizer.py](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4/blob/496f830bba4e2310ccd17aa7d243ead4d59df12d/deepseek-r1_tokenizer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
