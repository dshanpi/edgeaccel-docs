---
title: "Qwen2.5-7B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen2.5-7B-Instruct-GPTQ-Int4"
description: "Qwen2.5-7B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-7B-Instruct-GPTQ-Int4 部署指南

Qwen2.5-7B-Instruct-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 实测未完成。[查看部署效果](#查看部署效果)。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4` 的固定版本。下面下载本页选用的 33 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-gptq-int4/5b09894da95a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4 \
  "config.json" \
  "qwen2_p128_l0_together.axmodel" \
  "qwen2_p128_l1_together.axmodel" \
  "qwen2_p128_l2_together.axmodel" \
  "qwen2_p128_l3_together.axmodel" \
  "qwen2_p128_l4_together.axmodel" \
  "qwen2_p128_l5_together.axmodel" \
  "qwen2_p128_l6_together.axmodel" \
  "qwen2_p128_l7_together.axmodel" \
  "qwen2_p128_l8_together.axmodel" \
  "qwen2_p128_l9_together.axmodel" \
  "qwen2_p128_l10_together.axmodel" \
  "qwen2_p128_l11_together.axmodel" \
  "qwen2_p128_l12_together.axmodel" \
  "qwen2_p128_l13_together.axmodel" \
  "qwen2_p128_l14_together.axmodel" \
  "qwen2_p128_l15_together.axmodel" \
  "qwen2_p128_l16_together.axmodel" \
  "qwen2_p128_l17_together.axmodel" \
  "qwen2_p128_l18_together.axmodel" \
  "qwen2_p128_l19_together.axmodel" \
  "qwen2_p128_l20_together.axmodel" \
  "qwen2_p128_l21_together.axmodel" \
  "qwen2_p128_l22_together.axmodel" \
  "qwen2_p128_l23_together.axmodel" \
  "qwen2_p128_l24_together.axmodel" \
  "qwen2_p128_l25_together.axmodel" \
  "qwen2_p128_l26_together.axmodel" \
  "qwen2_p128_l27_together.axmodel" \
  "qwen2_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "qwen2_tokenizer.txt" \
  "post_config.json" \
  --revision 5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4` |
| 分词器类型（tokenizer_type） | `Qwen2_5` |
| 多模态类型（vlm_type） | 不启用 |
| Transformer 层数 | 28 |
| 分片命名模板 | `qwen2_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen2_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen2_tokenizer.txt` | 已找到 |
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
files += [c[k] for k in ["filename_post_axmodel","filename_tokens_embed","url_tokenizer_model","post_config_path"] if c.get(k)]
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

## 发送文本请求

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。

```bash
python3 - <<'PY'
import json, urllib.request
base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/v1/models", timeout=30) as r:
    model = json.load(r)["data"][0]["id"]
payload = {"model": model, "messages": [{"role": "user", "content": "请用一句话说明 PCIe 的用途。"}], "max_tokens": 128, "temperature": 0}
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

**部署效果待验证**

此固定版本尚未完成有效推理，部署效果待验证。

当前没有可展示的成功运行结果。

- 先测短问答，再测两轮上下文；翻译模型使用有参考译文的短句。
- 记录首 token 延迟、生成速率和实际上下文长度，确认没有乱码、持续重复或异常提前结束。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`qwen2.5_tokenizer.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2.5_tokenizer.py) | 旧版分词服务入口 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/config.json) | 运行配置 |
| [`qwen2_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen2_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/post_config.json) | 运行配置 |
| [`qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_7b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/run_qwen2.5_7b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_7b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/run_qwen2.5_7b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |

仓库提交：`5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/tree/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/tree/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/README.md)。
- [主要程序入口：qwen2.5_tokenizer.py](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4/blob/5b09894da95a2cdfb3cfd542441b8c0cd8c92d7c/qwen2.5_tokenizer.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen2.5-7B-Instruct-GPTQ-Int4)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
