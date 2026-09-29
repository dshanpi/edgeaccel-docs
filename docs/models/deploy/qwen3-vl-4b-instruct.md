---
title: "Qwen3-VL-4B-Instruct 部署指南"
sidebar_label: "Qwen3-VL-4B-Instruct"
description: "Qwen3-VL-4B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-4B-Instruct 部署指南

Qwen3-VL-4B-Instruct 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL 部署步骤。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-4B-Instruct` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-4b-instruct/052d3999478f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-4B-Instruct \
  --revision 052d3999478f8974b736f8663072e9a72aaabbf5 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `Qwen3-VL-4B-Instruct-AX650-c128_p1152` |
| 分词器类型（tokenizer_type） | `Qwen3VL` |
| 多模态类型（vlm_type） | `Qwen3VL` |
| Transformer 层数 | 36 |
| 分片命名模板 | `qwen3_vl_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_vl_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `tokenizer.txt` | 已找到 |
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

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。本例使用下载包内的 `01.jpg`。

```bash
python3 - <<'PY'
import json, urllib.request, base64
from pathlib import Path
base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/v1/models", timeout=30) as r:
    model = json.load(r)["data"][0]["id"]
image = Path("~/edgeaccel/models/qwen3-vl-4b-instruct/052d3999478f/01.jpg").expanduser()
mime = "image/png" if image.suffix.lower() == ".png" else "image/jpeg"
encoded = base64.b64encode(image.read_bytes()).decode()
payload = {"model": model, "messages": [{"role": "user", "content": [
    {"type": "text", "text": "描述图片中的主要对象。"},
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

**本机尚未实测。** 部署后请按以下项目检查输出。

- 使用已知内容的单张图片提问，回答应包含可核对的图像细节。
- 再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-4B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/Qwen3-VL-4B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/post_config.json) | 运行配置 |
| [`qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`052d3999478f8974b736f8663072e9a72aaabbf5`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/tree/052d3999478f8974b736f8663072e9a72aaabbf5)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/tree/052d3999478f8974b736f8663072e9a72aaabbf5)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/README.md)。

返回[完整模型目录](../catalog.mdx)。
