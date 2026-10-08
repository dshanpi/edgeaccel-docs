---
title: "DeepSeek-R1-Distill-Qwen-1.5B 部署指南"
sidebar_label: "DeepSeek-R1-Distill-Qwen-1.5B"
description: "DeepSeek-R1-Distill-Qwen-1.5B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DeepSeek-R1-Distill-Qwen-1.5B 部署指南

DeepSeek-R1-Distill-Qwen-1.5B 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B` 的固定版本。下面下载本页选用的 72 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-1-5b/88000a3b3447
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B \
  "deepseek-r1-1.5b-int4-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l0_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l10_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l11_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l12_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l13_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l14_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l15_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l16_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l17_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l18_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l19_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l1_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l20_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l21_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l22_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l23_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l24_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l25_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l26_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l27_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l2_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l3_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l4_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l5_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l6_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l7_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l8_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_p128_l9_together.axmodel" \
  "deepseek-r1-1.5b-int4-ax650/qwen2_post.axmodel" \
  "deepseek-r1_tokenizer/LICENSE" \
  "deepseek-r1_tokenizer/README.md" \
  "deepseek-r1_tokenizer/config.json" \
  "deepseek-r1_tokenizer/figures/benchmark.jpg" \
  "deepseek-r1_tokenizer/generation_config.json" \
  "deepseek-r1_tokenizer/tokenizer.json" \
  "deepseek-r1_tokenizer/tokenizer_config.json" \
  "deepseek-r1_tokenizer_uid.py" \
  "main_axcl_aarch64" \
  "post_config.json" \
  "run_deepseek-r1_1.5b_int4_axcl_aarch64.sh" \
  "deepseek-r1-1.5b-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l0_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l10_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l11_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l12_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l13_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l14_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l15_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l16_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l17_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l18_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l19_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l1_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l20_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l21_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l22_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l23_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l24_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l25_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l26_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l27_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l2_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l3_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l4_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l5_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l6_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l7_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l8_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_p128_l9_together.axmodel" \
  "deepseek-r1-1.5b-ax650/qwen2_post.axmodel" \
  "run_deepseek-r1_1.5b_axcl_aarch64.sh" \
  --revision 88000a3b344735e9ee0b59f3e6f5f0e7168738e8 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词服务

本页使用该仓库的 AXCL 程序 `main_axcl_aarch64` 和 **UID 分词接口**。W8A16、W4A16 两组权重共用程序与词表；不要混用独立 `DeepSeek-R1-Distill-Qwen-1.5B-GPTQ-Int4` 仓库中的模型或分词脚本。

在 RK3576 主机执行：

```bash
python3 -m venv ~/edgeaccel/deepseek15-env
source ~/edgeaccel/deepseek15-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查应全部解析成功，不能出现 `not found`。本页固定版本的 `config.json` 不是运行配置，不要作为新版 AX-LLM 的 JSON 配置传入程序。

## 配置采样并启动服务

下方效果使用贪心采样：`top_k=1`，关闭 temperature、repetition penalty 和 top-p。这与仓库的默认随机采样不同。先备份配置，再设置相同参数：

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
python deepseek-r1_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持服务运行。它为每次运行分配独立会话，监听本机回环地址，不需要对外开放端口。

## 运行两组权重

在另一终端恢复模型目录，先选择 W8A16：

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-1-5b/88000a3b3447
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
WEIGHT_DIR=deepseek-r1-1.5b-ax650
MMAP=0
PROMPT='What is 2 + 3? Reply with only the number.'
printf '%s\nq\n' "$PROMPT" | ./main_axcl_aarch64 \
  --template_filename_axmodel "$WEIGHT_DIR/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHT_DIR/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHT_DIR/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed "$MMAP" --live_print 0 --devices 0 \
  --system_prompt 'You are deepseek, You are a helpful assistant.'
```

程序完成一题后读取 `q` 并退出。`--live_print 0` 在生成结束后显示完整回复；总耗时包含模型加载、分词通信、生成和释放。

运行 W4A16 时，将变量改为以下值，再执行同一条 `printf … | ./main_axcl_aarch64 …` 命令：

```bash
WEIGHT_DIR=deepseek-r1-1.5b-int4-ax650
MMAP=1
```

两组均使用各自目录中的 28 层模型、post 模型与 embedding。测试其他内容时修改 `PROMPT`；本页另外使用了“一句中文说明 PCIe 用途”和“只返回指定 JSON”两道固定问题。

## 检查实际回复

程序应正常生成文本并退出，运行结束后用 `axcl-smi` 确认模型进程已释放。下方分别保留两组权重的原始回复和逐题观察。

内容与格式需分别判断：算术结果是否为 5、PCIe 说明是否准确、JSON 是否可直接解析。输出可能含有思考过程、Markdown 或额外说明，不能直接当作数字或 JSON 交给业务程序。短题运行通过不代表长上下文、多轮或完整能力评测通过。

结束使用后，在分词服务终端按 `Ctrl+C`。需要恢复默认采样时，将 `post_config.json.upstream` 复制回 `post_config.json`。


## 查看部署效果

### W4A16：Int4 AX650 权重

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但算术回复含解释；JSON 回复含代码围栏或额外文字，不能直接解析为指定对象；本次格式要求未通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复的最终回答部分**

```text
Sure! Let's solve the problem step by step.

**Problem:**  
What is 2 + 3?

**Solution:**

To find the sum of 2 and 3, we perform the following addition:

\[
2 + 3 = 5
\]

**Answer:**  
\boxed{5}
```

最终数值为 5，但包含多段解释与公式，没有满足“只返回数字”的要求。

程序内部首 token 耗时：512.86 ms；含模型加载的完整进程：57.882 s。内部计时不等同于客户端端到端首字延迟。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
I need to determine the sum of 2 and 3.

First, I'll add the two numbers together.

2 plus 3 equals 5.

Finally, I'll present the result clearly.
</think>

Sure! Let's solve the problem step by step.

**Problem:**  
What is 2 + 3?

**Solution:**

To find the sum of 2 and 3, we perform the following addition:

\[
2 + 3 = 5
\]

**Answer:**  
\boxed{5}
```

</details>

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复的最终回答部分**

```text
PCIe是高性能计算平台，支持并行计算和加速算法开发，广泛应用于科学计算、机器学习和人工智能等领域，帮助加速复杂算法的执行。
```

回答把 PCIe 说成高性能计算平台，概念错误；思考部分还虚构了用户已经给出示例。这条回答未通过内容核对。

程序内部首 token 耗时：518.15 ms；含模型加载的完整进程：83.781 s。内部计时不等同于客户端端到端首字延迟。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
好的，我现在需要帮用户用一句中文说明PCIe的用途。首先，用户已经提供了一个例子，是“PCIe是高性能计算平台，支持并行计算和加速算法开发。”这已经很清晰了，但用户可能希望更详细或者更简洁的表达。

我应该考虑用户可能的使用场景。他们可能是在学习计算机科学，特别是高性能计算相关领域，或者是在开发相关软件，需要了解PCIe的作用。因此，我需要确保解释准确，同时用词专业但易懂。

用户可能希望了解PCIe的主要功能，比如并行计算、加速算法，以及它在科学计算中的应用。所以，我应该涵盖这些点，同时保持简洁，避免冗长的句子。

另外，用户可能希望看到PCIe在实际应用中的例子，比如超级计算机的使用，这样能更直观地理解其用途。所以，我应该提到这些例子，让解释更全面。

最后，我要确保用词准确，比如“高性能计算平台”和“加速算法开发”是正确的术语，同时保持句子的流畅和自然。
</think>

PCIe是高性能计算平台，支持并行计算和加速算法开发，广泛应用于科学计算、机器学习和人工智能等领域，帮助加速复杂算法的执行。
```

</details>

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复的最终回答部分**

````text
The JSON object with "apple" equal to 3 and "pear" equal to 2 is as follows:

```json
{
  "apple": 3,
  "pear": 2
}
```
````

代码块内的对象为 apple=3、pear=2；最终回答仍有说明和 Markdown，完整回复还含思考文本，不能直接作为 JSON 解析。

程序内部首 token 耗时：496.25 ms；含模型加载的完整进程：133.193 s。内部计时不等同于客户端端到端首字延迟。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

````text
Okay, so I need to figure out how to return a JSON object where "apple" is equal to 3 and "pear" is equal to 2. Let me think about how to approach this.

First, I know that JSON is a data format that's easy for humans to read and easy for machines to parse and generate. It's usually used in web applications and web services. So, I need to create a dictionary in JSON format where the keys are "apple" and "pear", and their corresponding values are 3 and 2 respectively.

I should start by recalling the syntax for JSON. It's a key-value pair structure, with keys and values separated by commas. The entire structure is enclosed in curly braces {}. So, the basic structure would be { "apple": 3, "pear": 2 }.

Wait, but in JSON, the keys are usually strings, so I don't need quotes around them. So, it should be { "apple": 3, "pear": 2 }.

I should also make sure that the JSON is properly formatted. Each key-value pair is on a new line, and the entire object is enclosed in curly braces. So, the JSON string would look like this:

{
  "apple": 3,
  "pear": 2
}

I should check if there are any syntax errors here. The keys are in double quotes, which is correct. The values are numbers, which is fine. The commas between the key-value pairs are correct. The entire structure is enclosed in curly braces.

Is there anything else I need to consider? Maybe the order of the keys? In JSON, the order doesn't matter, so it doesn't matter if "apple" comes before "pear" or vice versa. So, the order in the JSON doesn't affect its validity.

I should also make sure that the JSON is valid and can be parsed correctly. If I were to write this in a programming language like JavaScript or Python, it would be straightforward. But since the question is about a JSON object, I don't need to worry about that.

Wait, but the user said "equal to 3 and 2." Does that mean I need to represent it as a JSON object with those values? Yes, that's what I'm doing.

I think that's all. So, the JSON object is straightforward. I just need to write it correctly with the keys and values as specified.
</think>

The JSON object with "apple" equal to 3 and "pear" equal to 2 is as follows:

```json
{
  "apple": 3,
  "pear": 2
}
```
````

</details>

**使用时注意：**

- 贪心采样下仅确认基本生成流程；事实准确性和严格格式未全部通过，不能据此判断量化精度或定位差异原因。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### W8A16：默认 AX650 权重

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但算术回复含解释；JSON 回复含代码围栏或额外文字，不能直接解析为指定对象；本次格式要求未通过。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复的最终回答部分**

```text
The sum of 2 and 3 is:

\[
2 + 3 = \boxed{5}
\]
```

最终数值为 5，算术内容正确；仍有解释与公式，没有满足“只返回数字”的要求。

程序内部首 token 耗时：544.66 ms；含模型加载的完整进程：71.707 s。内部计时不等同于客户端端到端首字延迟。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
I need to determine the sum of 2 and 3.

First, I'll add the two numbers together.

2 plus 3 equals 5.

So, the final answer is 5.
</think>

The sum of 2 and 3 is:

\[
2 + 3 = \boxed{5}
\]
```

</details>

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复的最终回答部分**

```text
PCIe（PCIe）是高性能插槽，主要用于连接高性能处理器、显卡和其他高性能设备，提供高速数据传输。
```

最终句子提到设备连接和高速传输，但把 PCIe 简单等同于插槽，术语不够准确；完整回复还包含额外思考文本。

程序内部首 token 耗时：569.58 ms；含模型加载的完整进程：80.811 s。内部计时不等同于客户端端到端首字延迟。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
好的，我现在需要帮用户用一句中文说明 PCIe 的用途。首先，我得弄清楚 PCIe是什么。 PCIe是高性能插槽，主要用于连接高性能处理器和显卡，提供高速数据传输。用户可能是在写技术文档或者需要解释这个术语给其他人。我应该用简洁明了的句子，直接点出 PCIe的作用，比如连接高性能设备，提供高速数据传输。这样用户就能清楚 PCIe的作用了。
</think>

PCIe（PCIe）是高性能插槽，主要用于连接高性能处理器、显卡和其他高性能设备，提供高速数据传输。
```

</details>

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复的最终回答部分**

```text
{"apple": 3, "pear": 2}
```

最终回答部分可解析为 apple=3、pear=2 的 JSON；完整回复前面含长段思考，不能将整个响应直接作为 JSON 解析。

程序内部首 token 耗时：621.37 ms；含模型加载的完整进程：169.048 s。内部计时不等同于客户端端到端首字延迟。

模型还返回了思考文本；下方显示最终回答，完整回复可展开核对。

<details>
<summary>查看模型原始完整回复</summary>

```text
Okay, so I need to figure out how to create a JSON object where "apple" is equal to 3 and "pear" is equal to 2. Let me think about how to approach this.

First, I know that JSON is a data interchange format that's used to exchange data between a data structure and a programming language or a web application. It's known for its use in creating web applications because of its ability to handle complex data structures.

So, the user wants a JSON object. That means I need to structure the data in a way that's recognized by JSON. I remember that in JSON, key-value pairs are separated by commas, and each key-value pair is enclosed in double quotes. The entire object is enclosed in curly braces.

The user specified that "apple" should be 3 and "pear" should be 2. So, I need to create an object where "apple" is the key and 3 is the value, and "pear" is the other key with 2 as the value.

Let me start by writing the structure. I'll open with a curly brace, then add the key-value pairs separated by commas. So, it would look like:

{
  "apple": 3,
  "pear": 2
}

Wait, but I should make sure that the syntax is correct. Each key is enclosed in double quotes, and the value is either a number or a string. In this case, both values are numbers, so that's fine.

I should also check if there are any trailing commas or missing braces. In this case, there are no trailing commas, and the braces are properly opened and closed. So, that should be correct.

Is there any other way to represent this? Maybe using an object literal, but I think the way I have it is sufficient. I don't think I need to include any additional information or explanations because the user just wants the JSON object.

I should also consider if there are any edge cases. For example, what if the user wants different data types? But in this case, both values are numbers, so it's straightforward.

Another thing to think about is whether the JSON is valid. I can test it by pasting it into a JSON validator. But since I'm just thinking through it, I can assume that the syntax is correct.

So, putting it all together, the JSON object should be:

{
  "apple": 3,
  "pear": 2
}

I think that's it. It meets the user's requirements and is properly formatted in JSON.
</think>

{"apple": 3, "pear": 2}
```

</details>

**使用时注意：**

- 贪心采样下仅确认基本生成流程；内容与严格格式未全部通过，没有据此判断完整模型精度。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**W4A16：Int4 AX650 权重**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`88000a3b344735e9ee0b59f3e6f5f0e7168738e8`。

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
| 示例 1 进程耗时 | 57.882 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 83.781 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 133.193 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

**W8A16：默认 AX650 权重**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`88000a3b344735e9ee0b59f3e6f5f0e7168738e8`。

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
| 示例 1 进程耗时 | 71.707 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 80.811 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 169.048 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_deepseek-r1_1.5b_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/run_deepseek-r1_1.5b_axcl_aarch64.sh) | 启动或构建脚本 |
| [`deepseek-r1_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1_tokenizer_uid.py) | 旧版分词服务入口 |
| [`deepseek-r1-1.5b-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1-1.5b-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1-1.5b-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1-1.5b-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1-1.5b-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-1.5b-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1-1.5b-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/config.json) | 运行配置 |
| [`deepseek-r1_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1_tokenizer/config.json) | 运行配置 |
| [`deepseek-r1_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1_tokenizer/generation_config.json) | 运行配置 |
| [`deepseek-r1_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/post_config.json) | 运行配置 |
| [`run_deepseek-r1_1.5b_ax650.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/run_deepseek-r1_1.5b_ax650.sh) | 启动或构建脚本 |
| [`run_deepseek-r1_1.5b_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/run_deepseek-r1_1.5b_axcl_x86.sh) | 启动或构建脚本 |

仓库提交：`88000a3b344735e9ee0b59f3e6f5f0e7168738e8`。仓库中的 87 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/tree/88000a3b344735e9ee0b59f3e6f5f0e7168738e8)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/tree/88000a3b344735e9ee0b59f3e6f5f0e7168738e8)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/README.md)。
- [主要程序入口：deepseek-r1_tokenizer_uid.py](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B/blob/88000a3b344735e9ee0b59f3e6f5f0e7168738e8/deepseek-r1_tokenizer_uid.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-context)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-context)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/DeepSeek-R1-Distill-Qwen-1.5B)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
