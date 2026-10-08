---
title: "MiniCPM-V-4.6 部署指南"
sidebar_label: "MiniCPM-V-4.6"
description: "MiniCPM-V-4.6 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM-V-4.6 部署指南

MiniCPM-V-4.6 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MiniCPM-V-4.6` 的固定版本。下面下载本页选用的 30 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/minicpm-v-4-6/35470c6072a7
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MiniCPM-V-4.6 \
  "config.json" \
  "qwen3_5_text_p128_l0_together.axmodel" \
  "qwen3_5_text_p128_l1_together.axmodel" \
  "qwen3_5_text_p128_l2_together.axmodel" \
  "qwen3_5_text_p128_l3_together.axmodel" \
  "qwen3_5_text_p128_l4_together.axmodel" \
  "qwen3_5_text_p128_l5_together.axmodel" \
  "qwen3_5_text_p128_l6_together.axmodel" \
  "qwen3_5_text_p128_l7_together.axmodel" \
  "qwen3_5_text_p128_l8_together.axmodel" \
  "qwen3_5_text_p128_l9_together.axmodel" \
  "qwen3_5_text_p128_l10_together.axmodel" \
  "qwen3_5_text_p128_l11_together.axmodel" \
  "qwen3_5_text_p128_l12_together.axmodel" \
  "qwen3_5_text_p128_l13_together.axmodel" \
  "qwen3_5_text_p128_l14_together.axmodel" \
  "qwen3_5_text_p128_l15_together.axmodel" \
  "qwen3_5_text_p128_l16_together.axmodel" \
  "qwen3_5_text_p128_l17_together.axmodel" \
  "qwen3_5_text_p128_l18_together.axmodel" \
  "qwen3_5_text_p128_l19_together.axmodel" \
  "qwen3_5_text_p128_l20_together.axmodel" \
  "qwen3_5_text_p128_l21_together.axmodel" \
  "qwen3_5_text_p128_l22_together.axmodel" \
  "qwen3_5_text_p128_l23_together.axmodel" \
  "qwen3_5_text_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "minicpm_v46_tokenizer.txt" \
  "minicpmv4_6_vision_448.axmodel" \
  "post_config.json" \
  --revision 35470c6072a771607bf89f9742d84046e86f1563 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/MiniCPM-V-4.6-AX650-C128-P1152-CTX2047` |
| 分词器类型（tokenizer_type） | `MiniCPMV46VL` |
| 多模态类型（vlm_type） | `MiniCPMV46VL` |
| Transformer 层数 | 24 |
| 分片命名模板 | `qwen3_5_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_5_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `minicpm_v46_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `minicpmv4_6_vision_448.axmodel` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 24 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

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

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

16GB 卡的三次单图请求均返回文本，中文识别出树林中的三名宇航服人物。英文描述未遵守一句话要求并加入意图推测；人数回复含思考标记且在 128 token 处截断，完整回复与格式质量未通过。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/minicpm-v-4-6/input.png)](../../../static/validation/effects/minicpm-v-4-6/input.png)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the image in one sentence.
```

**实际回复**

```text
The image depicts three astronauts in white spacesuits, standing in a forested area with tall trees. The central astronaut has his arms raised, as if in a gesture of celebration or excitement. The other two astronauts are standing beside him, one slightly behind and to the left, and the other to the right, both also in a relaxed posture. The scene is set in a serene, natural environment, with the astronauts appearing to be in a state of camaraderie and adventure. The lighting suggests it is daytime, and the overall atmosphere is one of exploration and teamwork.
```

**示例 2：输入**

```text
How many people are in the image?
```

**实际回复**

本次输出已达到设置的 128 token 上限，下面保留原始回复；不能仅凭接口的 finish_reason 判定句子已完整结束。

```text
Okay, let's think about how to count the number of people in the image. The image shows three individuals, all wearing astronaut suits. I need to count each of them to make sure I don't miss any. Looking at the image, there's one in the front center, another to the left, and a third on the right. Each of these is a distinct person. So, I should simply count these figures. Let me verify: yes, there are three distinct people, each in a space suit. Therefore, the number of people in the image is three.
</think>

Looking at the image, I can see three
```

**示例 3：输入**

```text
请用一句简短的中文描述图片，不要推测人物的意图或表情。
```

**实际回复**

```text
这张图片展示了一个科幻场景，有三位穿着宇航服的宇航员站在森林中。
```

**使用时注意：**

- 英文描述没有遵守一句话要求，并加入庆祝、兴奋等意图推测；人数回复包含思考文本和 `</think>` 标记，达到 128 token 上限后句子未完整结束。
- 本次设置 enable_thinking=false，仍出现思考文本。接入应用前应确认所用模型、分词模板与运行程序能满足回复格式要求。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`35470c6072a771607bf89f9742d84046e86f1563`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；原版 Release / AXCL / Linux aarch64 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 返回文本的图文请求 | 3 | 三次接口响应；人数回复达到128 token上限且未完整结束，不把stop标志当作完整回答。 |
| 三次请求耗时 | 18.167 / 18.177 / 3.749 s | 按展示顺序；HTTP 请求至完整响应的墙钟耗时，不含模型加载 |
| 服务就绪等待 | 52.09 s | 启动进程至健康检查成功，包含模型加载和轮询等待 |
| 三次首 token 延迟 | 893.59 / 1041.31 / 1011.57 ms | 运行程序返回的 usage.ttft_ms，不是客户端流式到达时间 |

适用范围：

- 本页结果来自 16GB 卡，不作为 8GB 卡的容量验证。temperature=0、enable_thinking=false、stream=false、max_tokens=128。
- 仅测试本页短请求，未覆盖完整数据集、最大上下文、多轮对话、并发或长期连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/infer_axmodel.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/python/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`python/infer_torch.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/python/infer_torch.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/config.json) | 运行配置 |
| [`qwen3_5_text_post.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/qwen3_5_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`minicpm_v46_tokenizer.txt`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/minicpm_v46_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`minicpmv4_6_vision_448.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/minicpmv4_6_vision_448.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/post_config.json) | 运行配置 |
| [`qwen3_5_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/qwen3_5_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/qwen3_5_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/qwen3_5_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/qwen3_5_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/openai_api_demo.png`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/assets/openai_api_demo.png) | 示例输入 |
| [`python/minicpm_v46_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/python/minicpm_v46_tokenizer/config.json) | 运行配置 |

仓库提交：`35470c6072a771607bf89f9742d84046e86f1563`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/tree/35470c6072a771607bf89f9742d84046e86f1563)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/tree/35470c6072a771607bf89f9742d84046e86f1563)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/README.md)。
- [主要程序入口：python/infer_axmodel.py](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6/blob/35470c6072a771607bf89f9742d84046e86f1563/python/infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
