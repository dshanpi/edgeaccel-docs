---
title: "Qwen3-VL-4B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen3-VL-4B-Instruct-GPTQ-Int4"
description: "Qwen3-VL-4B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-4B-Instruct-GPTQ-Int4 部署指南

Qwen3-VL-4B-Instruct-GPTQ-Int4 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4` 的固定版本。下面下载本页选用的 42 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-4b-instruct-gptq-int4/49e8c2a907b6
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4 \
  "config.json" \
  "qwen3_vl_text_p128_l0_together.axmodel" \
  "qwen3_vl_text_p128_l1_together.axmodel" \
  "qwen3_vl_text_p128_l2_together.axmodel" \
  "qwen3_vl_text_p128_l3_together.axmodel" \
  "qwen3_vl_text_p128_l4_together.axmodel" \
  "qwen3_vl_text_p128_l5_together.axmodel" \
  "qwen3_vl_text_p128_l6_together.axmodel" \
  "qwen3_vl_text_p128_l7_together.axmodel" \
  "qwen3_vl_text_p128_l8_together.axmodel" \
  "qwen3_vl_text_p128_l9_together.axmodel" \
  "qwen3_vl_text_p128_l10_together.axmodel" \
  "qwen3_vl_text_p128_l11_together.axmodel" \
  "qwen3_vl_text_p128_l12_together.axmodel" \
  "qwen3_vl_text_p128_l13_together.axmodel" \
  "qwen3_vl_text_p128_l14_together.axmodel" \
  "qwen3_vl_text_p128_l15_together.axmodel" \
  "qwen3_vl_text_p128_l16_together.axmodel" \
  "qwen3_vl_text_p128_l17_together.axmodel" \
  "qwen3_vl_text_p128_l18_together.axmodel" \
  "qwen3_vl_text_p128_l19_together.axmodel" \
  "qwen3_vl_text_p128_l20_together.axmodel" \
  "qwen3_vl_text_p128_l21_together.axmodel" \
  "qwen3_vl_text_p128_l22_together.axmodel" \
  "qwen3_vl_text_p128_l23_together.axmodel" \
  "qwen3_vl_text_p128_l24_together.axmodel" \
  "qwen3_vl_text_p128_l25_together.axmodel" \
  "qwen3_vl_text_p128_l26_together.axmodel" \
  "qwen3_vl_text_p128_l27_together.axmodel" \
  "qwen3_vl_text_p128_l28_together.axmodel" \
  "qwen3_vl_text_p128_l29_together.axmodel" \
  "qwen3_vl_text_p128_l30_together.axmodel" \
  "qwen3_vl_text_p128_l31_together.axmodel" \
  "qwen3_vl_text_p128_l32_together.axmodel" \
  "qwen3_vl_text_p128_l33_together.axmodel" \
  "qwen3_vl_text_p128_l34_together.axmodel" \
  "qwen3_vl_text_p128_l35_together.axmodel" \
  "qwen3_vl_text_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "qwen3_tokenizer.txt" \
  "Qwen3-VL-4B-Instruct_vision.axmodel" \
  "post_config.json" \
  --revision 49e8c2a907b6355a365e5bb62ed6298d9596574b \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4` |
| 分词器类型（tokenizer_type） | `Qwen3VL` |
| 多模态类型（vlm_type） | `Qwen3VL` |
| Transformer 层数 | 36 |
| 分片命名模板 | `qwen3_vl_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_vl_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen3_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `Qwen3-VL-4B-Instruct_vision.axmodel` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 36 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

## 检查完整模型包

在模型根目录执行文件检查：

```bash
cd "$MODEL_DIR"
python3 - <<'PY'
import json
from pathlib import Path
p = Path(".")
c = json.loads((p / "config.json").read_text())
files = [c["template_filename_axmodel"] % i for i in range(c["axmodel_num"])]
files += [c[k] for k in ["filename_post_axmodel","filename_tokens_embed","url_tokenizer_model","filename_image_encoder_axmodel","post_config_path"] if c.get(k)]
missing = [str(p / f) for f in files if not (p / f).is_file()]
assert not missing, missing
print("模型配套文件齐全")
PY
```

此包按新 `axllm` 配置接口核对。使用[本站编译的 AXCL 程序](../llm-runtime.md)，包内 `bin/axllm` 可能是 AX650 板端程序，不能仅因同为 ARM64 就直接使用。

## 启动单卡服务

终端 1 执行，保持服务前台运行：

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
"$AXLLM" version
AXLLM_DEVICES=0 "$AXLLM" serve "$MODEL_DIR" --port 8000
```

版本输出必须显示 AXCL 后端。保留内存预检；若提示 CMM 不足，先缩小模型或使用较短上下文的独立编译包，不关闭内存预检强制运行。

## 发送图片问答请求

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。先下载与下方效果展示相同的样例图，再发送请求。

```bash
mkdir -p ~/edgeaccel/inputs/three-astronauts
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/FastVLM-1.5B-GPTQ-Int4 image.png \
  --revision 0cdae3c2711cc457708b9bb5b4dee77839755d7a \
  --local-dir ~/edgeaccel/inputs/three-astronauts
printf '%s  %s\n' '622ae2d01ff4467fa69a7888728d776650117a0f4887e96ba0fb9a8a6d77b3c3' ~/edgeaccel/inputs/three-astronauts/image.png | sha256sum -c -
```

该图是下方问答实际使用的输入；校验输出应为 OK。

```bash
python3 - <<'PY'
import json, urllib.request, base64
from pathlib import Path
base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/v1/models", timeout=30) as r:
    model = json.load(r)["data"][0]["id"]
image = Path("~/edgeaccel/inputs/three-astronauts/image.png").expanduser()
mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
encoded = base64.b64encode(image.read_bytes()).decode()
payload = {"model": model, "messages": [{"role": "user", "content": [
    {"type": "text", "text": "Describe the image in one sentence."},
    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
]}], "max_tokens": 128, "temperature": 0}
endpoint = "/v1/chat/completions"
payload.update(enable_thinking=False, stream=False)
request = urllib.request.Request(base + endpoint,
    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as r:
    result = json.load(r)
print(result["choices"][0]["message"]["content"])
PY
```

检查 choices 中的回复是否完整且与输入相关。替换 messages 中的提问文字，可复现下方其他问题；保持其余输入和生成参数一致。回复达到 max_tokens 上限时可能被截断，可先要求简短回答。HTTP 请求成功只说明接口可用，仍需按下节核对效果。

运行时依据：[固定源码版本](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)、[配置接口](https://github.com/AXERA-TECH/ax-llm/blob/8501c22b940f8c5804cb35044c5ffc136918b8f1/docs/configuration.md)。

## 查看部署效果

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

三次单图请求返回文本。人数回答正确，但英文描述带有特殊标记，中文仅返回 <|im_start|><|im_start|>，没有有效描述；本次中文问答质量未通过。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-4b-instruct-gptq-int4/inputs/input.png)](../../../static/validation/effects/qwen3-vl-4b-instruct-gptq-int4/inputs/input.png)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the image in one sentence.
```

**实际回复**

```text
<|im_start|><|im_start|>
Three astronauts in white spacesuits stand amidst a dense, monochrome forest, their helmets reflecting the eerie, leafy surroundings as they appear to be exploring or encountering an alien environment.
```

**示例 2：输入**

```text
How many people are in the image?
```

**实际回复**

```text
The image shows three people. They are all wearing white astronaut suits and are positioned in a forest-like setting with tall, thin trees and leafy ground cover. The central figure is raising their arms, while the other two are positioned to their left and right, respectively. All three are clearly visible and appear to be the same type of person — astronauts — in the same environment.

✅ **Answer: 3**
```

**示例 3：输入**

```text
请用一句简短的中文描述图片，不要推测人物的意图或表情。
```

**实际回复**

```text
<|im_start|><|im_start|>
```

**使用时注意：**

- 本样例的中文回复仅含 <|im_start|> 特殊标记；英文也存在不可靠细节，未通过回答正确性检查。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`49e8c2a907b6355a365e5bb62ed6298d9596574b`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 返回响应的图文请求 | 3 | 接口返回三次响应；特殊标记、重复或截断回复不计为有效完整回答。 |
| 服务启动等待 | 78.541 s | 启动进程至健康检查成功 |
| 各次 HTTP 耗时 | 21.174 / 40.728 / 5.005 s | 从发送请求到完整回复，不包含模型启动 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-4B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/Qwen3-VL-4B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/post_config.json) | 运行配置 |
| [`Qwen3-VL-4B-Instruct_vision_u8.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/Qwen3-VL-4B-Instruct_vision_u8.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/images/demo.jpg) | 示例输入 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/requirements.txt) | Python 依赖清单 |

仓库提交：`49e8c2a907b6355a365e5bb62ed6298d9596574b`。仓库中的 39 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/tree/49e8c2a907b6355a365e5bb62ed6298d9596574b)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/tree/49e8c2a907b6355a365e5bb62ed6298d9596574b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-GPTQ-Int4/blob/49e8c2a907b6355a365e5bb62ed6298d9596574b/README.md)。

返回[完整模型目录](../catalog.mdx)。
