---
title: "Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047 部署指南"
sidebar_label: "Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047"
description: "Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047 部署指南

Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047` 的固定版本。下面下载本页选用的 31 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047/14aafe22f5b2
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047 \
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
  "qwen3_5_tokenizer.txt" \
  "qwen3_5_vision.axmodel" \
  "post_config.json" \
  "image.png" \
  --revision 14aafe22f5b269c200fe3affd6f5d031a5ef93a6 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3.5-2B` |
| 分词器类型（tokenizer_type） | `Qwen3_5VL` |
| 多模态类型（vlm_type） | `Qwen3VL` |
| Transformer 层数 | 24 |
| 分片命名模板 | `qwen3_5_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_5_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen3_5_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `qwen3_5_vision.axmodel` | 已找到 |
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

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

三次单图请求均返回文本。中文误述左侧双手交叉胸前及惊讶表情，并在128 token处未完整结束；细节和完整回复未通过。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047/inputs/input.png)](../../../static/validation/effects/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047/inputs/input.png)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the image in one sentence.
```

**实际回复**

```text
Three astronauts in white spacesuits stand amidst a surreal, monochromatic forest of bamboo-like stalks, with one astronaut raising their hands in a gesture of surprise or triumph.
```

**示例 2：输入**

```text
How many people are in the image?
```

**实际回复**

```text
There are **three** people in the image.

All three individuals are wearing white space suits (astronauts) and appear to be standing in a forest or jungle-like environment. The central figure is raising both arms, while the two on the sides are looking downward or to the side. Their helmets and visors reflect light, suggesting they are in a low-light or shaded area.

✅ Final Answer: **3**
```

**示例 3：输入**

```text
请用中文描述图片中的人物和环境。
```

**实际回复**

本次输出已达到设置的 128 token 上限，下面保留原始回复；不能仅凭接口的 finish_reason 判定句子已完整结束。

```text
这张图片描绘了一个充满奇幻和科幻色彩的场景：

- **人物**：画面中有三位身穿白色宇航服的人物，他们站在一片茂密的丛林中。中间的宇航员正举起双手，似乎在欢呼或庆祝；左边的宇航员双手交叉于胸前，表情略显惊讶；右边的宇航员则微微弯腰，似乎在观察地面或周围植物。他们的头盔面罩反射着环境光，呈现出金属光泽。

- **环境**：他们身处一片幽深的森林中，背景是模糊的树木轮廓，营造出一种神秘而深邃的氛围。前景中可见低矮的草本植物，部分叶片呈半透明
```

**使用时注意：**

- 人物表情、动机和部分动作细节无法从本图确认，不能只按人数正确判定整段描述正确。
- 中文回复达到 max_tokens=128，句子未写完；测试范围仅为单图三次请求。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`14aafe22f5b269c200fe3affd6f5d031a5ef93a6`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |
| 大模型测试方式 | 单卡串行运行，3 次独立请求；temperature=0、enable_thinking=false、stream=false、max_tokens=128 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 返回文本的图文请求 | 3 | 三次接口响应；中文达到128 token上限而未完整结束，不以stop标志代替完整回答。 |
| 三次 HTTP 耗时 | 10.413 / 21.702 / 33.237 s | 按本页展示顺序；客户端从请求到完整回复，不包含服务启动 |
| 三次首 token 延迟 | 1915.332 / 1621.695 / 1758.450 ms | 运行时返回的 usage 字段；单 token 回复可能没有 decode_tps，不估算缺失值。TTFT 非客户端流式到达时间 |
| 三次生成速率 | 4.023 / 4.241 / 4.044 token/s | 运行时返回的 usage 字段；单 token 回复可能没有 decode_tps，不估算缺失值。TTFT 非客户端流式到达时间 |
| 服务就绪等待 | 53.03 s | 进程启动至 /health 返回成功，含模型加载与轮询等待 |

适用范围：

- 仅执行本页列出的短请求，未测试长期稳定性、并发或最大上下文；上游板端性能不作为本机结果。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/config.json) | 运行配置 |
| [`qwen3_5_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_5_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`qwen3_5_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/post_config.json) | 运行配置 |
| [`qwen3_5_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/qwen3_5_text_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`14aafe22f5b269c200fe3affd6f5d031a5ef93a6`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/tree/14aafe22f5b269c200fe3affd6f5d031a5ef93a6)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/tree/14aafe22f5b269c200fe3affd6f5d031a5ef93a6)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047/blob/14aafe22f5b269c200fe3affd6f5d031a5ef93a6/README.md)。

返回[完整模型目录](../catalog.mdx)。
