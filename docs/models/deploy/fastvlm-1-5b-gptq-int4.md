---
title: "FastVLM-1.5B-GPTQ-Int4 部署指南"
sidebar_label: "FastVLM-1.5B-GPTQ-Int4"
description: "FastVLM-1.5B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# FastVLM-1.5B-GPTQ-Int4 部署指南

FastVLM-1.5B-GPTQ-Int4 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/FastVLM-1.5B-GPTQ-Int4` 的固定版本。下面下载本页选用的 35 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/fastvlm-1-5b-gptq-int4/0cdae3c2711c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/FastVLM-1.5B-GPTQ-Int4 \
  "config.json" \
  "llava_qwen2_p128_l0_together.axmodel" \
  "llava_qwen2_p128_l1_together.axmodel" \
  "llava_qwen2_p128_l2_together.axmodel" \
  "llava_qwen2_p128_l3_together.axmodel" \
  "llava_qwen2_p128_l4_together.axmodel" \
  "llava_qwen2_p128_l5_together.axmodel" \
  "llava_qwen2_p128_l6_together.axmodel" \
  "llava_qwen2_p128_l7_together.axmodel" \
  "llava_qwen2_p128_l8_together.axmodel" \
  "llava_qwen2_p128_l9_together.axmodel" \
  "llava_qwen2_p128_l10_together.axmodel" \
  "llava_qwen2_p128_l11_together.axmodel" \
  "llava_qwen2_p128_l12_together.axmodel" \
  "llava_qwen2_p128_l13_together.axmodel" \
  "llava_qwen2_p128_l14_together.axmodel" \
  "llava_qwen2_p128_l15_together.axmodel" \
  "llava_qwen2_p128_l16_together.axmodel" \
  "llava_qwen2_p128_l17_together.axmodel" \
  "llava_qwen2_p128_l18_together.axmodel" \
  "llava_qwen2_p128_l19_together.axmodel" \
  "llava_qwen2_p128_l20_together.axmodel" \
  "llava_qwen2_p128_l21_together.axmodel" \
  "llava_qwen2_p128_l22_together.axmodel" \
  "llava_qwen2_p128_l23_together.axmodel" \
  "llava_qwen2_p128_l24_together.axmodel" \
  "llava_qwen2_p128_l25_together.axmodel" \
  "llava_qwen2_p128_l26_together.axmodel" \
  "llava_qwen2_p128_l27_together.axmodel" \
  "llava_qwen2_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "FastVLM_tokenizer.txt" \
  "image_encoder_1024x1024.axmodel" \
  "post_config.json" \
  "image.png" \
  --revision 0cdae3c2711cc457708b9bb5b4dee77839755d7a \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/FastVLM-1.5B-GPTQ-Int4` |
| 分词器类型（tokenizer_type） | `FastVLM` |
| 多模态类型（vlm_type） | `FastVLM` |
| Transformer 层数 | 28 |
| 分片命名模板 | `llava_qwen2_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `llava_qwen2_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `FastVLM_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `image_encoder_1024x1024.axmodel` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 28 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

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

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。本例使用下载包内的 `image.png`。

```bash
python3 - <<'PY'
import json, urllib.request, base64
from pathlib import Path
base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/v1/models", timeout=30) as r:
    model = json.load(r)["data"][0]["id"]
image = Path("~/edgeaccel/models/fastvlm-1-5b-gptq-int4/0cdae3c2711c/image.png").expanduser()
mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
encoded = base64.b64encode(image.read_bytes()).decode()
payload = {"model": model, "messages": [{"role": "user", "content": [
    {"type": "text", "text": "Describe the image in one sentence."},
    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
]}], "max_tokens": 128, "temperature": 0}
endpoint = "/v1/chat/completions"
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

三次英文图文请求均正常结束，人数回答为三人；长回复把图片称为黑白图，并加入无法确认的漂浮描述，细节质量未通过。尚未测试中文视觉问题。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/fastvlm-1-5b-gptq-int4/inputs/input.png)](../../../static/validation/effects/fastvlm-1-5b-gptq-int4/inputs/input.png)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the image in one sentence.
```

**实际回复**

```text
Three astronauts in white spacesuits are standing in a forest.
```

**示例 2：输入**

```text
How many people are in the image?
```

**实际回复**

```text
The image depicts three astronauts in a forest setting. The image is in black and white, giving it a surreal and otherworldly appearance. The astronauts are wearing full space suits with helmets, and they appear to be floating or standing on the ground, which is unusual for an outdoor setting. The background shows a dense forest with tall trees and some undergrowth. The overall scene creates a striking contrast between the futuristic space suits and the natural environment of the forest.
```

**使用时注意：**

- 这是一张图片的 3 次请求、2 种问题；第三次重复第一问且回复相同，下方合并展示。尚未测试多图、视频、OCR 或中文视觉问答。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`0cdae3c2711cc457708b9bb5b4dee77839755d7a`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| C++ 视觉示例提交 | cbfa4c76891758983ca2b0c99c11d6621d59af39 |
| Python 后端 | Python 3.12.3；PyAXEngine 0.1.3.rc3 发布的 0.1.3 wheel；NumPy 1.26.4 / ml-dtypes 0.5.3 |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 图文生成请求数 | 3 | api.json 中 /v1/chat/completions；同一图片，另含 health 与 models 共 5 条 HTTP 记录 |
| 实际测试图片尺寸 | 512×512 | input.png 文件头；SHA256 622ae2d01ff4467fa69a7888728d776650117a0f4887e96ba0fb9a8a6d77b3c3 与 api.json 输入记录一致 |
| 图像编码器输入尺寸 | 1024×1024 | config-tested.json 与 server.log 的模型真实输入解析，区别于原始图片尺寸 |
| 服务启动等待时间 | 37.82 | 秒；result.json startupWallSeconds，包含加载与就绪探测 |
| 3 次图文 HTTP 耗时 | 5.120 / 23.473 / 4.206 | 秒；客户端端到端，不含服务启动；第 2 次输出 92 tokens，另两次均 12 tokens |
| 3 次运行时 TTFT | 1812.36 / 2017.84 / 1782.90 | 毫秒；response.usage.ttft_ms，与 server.log 一致，不是客户端流式首字测量 |
| 3 次运行时 decode 速率 | 3.361 / 4.253 / 4.745 | token/s；response.usage.decode_tps，不由 HTTP 总耗时推算 |

适用范围：

- 只测试同一张图片的 3 次请求、2 种问题；不能当作 3 张独立图片或通用视觉理解精度验证。总 HTTP 记录为 5，另含 health/models。
- 第二问只询问人数，回复却扩展为 92 tokens 的长段落；人数正确不代表附加细节正确。实际输入可见低饱和绿色及头盔暖色反光，不能严格称为黑白图，画面也不能确认人物漂浮。
- 3 次请求均为 temperature=0、stream=false、max_tokens=128；未测试视频、多图、OCR、中文视觉问题、流式输出或长上下文。
- server.log 每次都记录新的 vision cache store，没有显示缓存命中；不能将第三次较短耗时解释为已证实的视觉缓存命中加速。后两次均重置 KV。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/config.json) | 运行配置 |
| [`llava_qwen2_post.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/llava_qwen2_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`FastVLM_tokenizer.txt`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/FastVLM_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`image_encoder_1024x1024.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/image_encoder_1024x1024.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/post_config.json) | 运行配置 |
| [`image_encoder_512x512.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/image_encoder_512x512.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llava_qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/llava_qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llava_qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/llava_qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llava_qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/llava_qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`0cdae3c2711cc457708b9bb5b4dee77839755d7a`。仓库中的 31 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/tree/0cdae3c2711cc457708b9bb5b4dee77839755d7a)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/tree/0cdae3c2711cc457708b9bb5b4dee77839755d7a)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4/blob/0cdae3c2711cc457708b9bb5b4dee77839755d7a/README.md)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/FastVLM-1.5B-GPTQ-Int4)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
