---
title: "MiniCPM-V-4.6-GPTQ 部署指南"
sidebar_label: "MiniCPM-V-4.6-GPTQ"
description: "MiniCPM-V-4.6-GPTQ 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM-V-4.6-GPTQ 部署指南

MiniCPM-V-4.6-GPTQ 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MiniCPM-V-4.6-GPTQ` 的固定版本。下面下载本页选用的 30 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/minicpm-v-4-6-gptq/7ee5a562b9b5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MiniCPM-V-4.6-GPTQ \
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
  --revision 7ee5a562b9b5ae6185f2fa05dc343a3416df14f8 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX650-C128-P1152-CTX2047-V7` |
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

**固定样例已核对** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

同一张图片的三组固定问答已核对：英文描述识别出三名白色宇航服人物与树林，人数为三人，中文简短描述与画面的大体内容相符。结论只覆盖这张图片和本页三次请求。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/minicpm-v-4-6-gptq/inputs/input.png)](../../../static/validation/effects/minicpm-v-4-6-gptq/inputs/input.png)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the image in one sentence.
```

**实际回复**

```text
The image depicts three astronauts in white spacesuits standing amidst a dense, stylized forest, with their visors reflecting a muted, eerie light.
```

**示例 2：输入**

```text
How many people are in the image?
```

**实际回复**

```text
There are three people in the image, all wearing astronaut suits. They appear to be standing in a forested or natural setting.
```

**示例 3：输入**

```text
请用一句简短的中文描述图片，不要推测人物的意图或表情。
```

**实际回复**

```text
三位宇航员在森林中，身着白色宇航服，姿态各异。
```

**使用时注意：**

- 这里只核对人数、服装与大体场景，未开展数据集精度或复杂视觉推理评测。
- 此版本只实测单张图片；上游视频演示不作为本机视频结果。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`7ee5a562b9b5ae6185f2fa05dc343a3416df14f8`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |
| 大模型测试方式 | 单卡串行运行，计划 3 次独立请求，实际完成数量见记录；temperature=0、enable_thinking=false、stream=false、max_tokens=128 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 完整生成请求 | 3 | 仅 /v1/chat/completions；另有 health 与模型列表两项接口检查 |
| 三次 HTTP 耗时 | 5.466 / 5.245 / 3.570 s | 按本页展示顺序；客户端从请求到完整回复，不包含服务启动 |
| 三次首 token 延迟 | 1038.125 / 1186.129 / 1085.219 ms | 运行时返回的 usage 字段；单 token 回复可能没有 decode_tps，不估算缺失值。TTFT 非客户端流式到达时间 |
| 三次生成速率 | 6.394 / 6.212 / 5.786 token/s | 运行时返回的 usage 字段；单 token 回复可能没有 decode_tps，不估算缺失值。TTFT 非客户端流式到达时间 |
| 服务就绪等待 | 30.61 s | 进程启动至 /health 返回成功，含模型加载与轮询等待 |

适用范围：

- 这里只核对人数、服装与大体场景，未开展数据集精度或复杂视觉推理评测。
- 此版本只实测单张图片；上游视频演示不作为本机视频结果。
- 仅执行本页列出的短请求，未测试长期稳定性、并发或最大上下文；上游板端性能不作为本机结果。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/config.json) | 运行配置 |
| [`qwen3_5_text_post.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/qwen3_5_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`minicpm_v46_tokenizer.txt`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/minicpm_v46_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`minicpmv4_6_vision_448.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/minicpmv4_6_vision_448.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/post_config.json) | 运行配置 |
| [`qwen3_5_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/qwen3_5_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/qwen3_5_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/qwen3_5_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/qwen3_5_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/openai_api_demo.png`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/assets/openai_api_demo.png) | 示例输入 |

仓库提交：`7ee5a562b9b5ae6185f2fa05dc343a3416df14f8`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/tree/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/tree/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ/blob/7ee5a562b9b5ae6185f2fa05dc343a3416df14f8/README.md)。

返回[完整模型目录](../catalog.mdx)。
