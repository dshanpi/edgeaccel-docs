---
title: "Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 部署指南"
sidebar_label: "Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407"
description: "Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 部署指南

Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL 部署步骤。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407/97ecf827ecfc
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 \
  --revision 97ecf827ecfc3b07d35b74b852981d3415d14a1a \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-VL-Embedding-2B` |
| 分词器类型（tokenizer_type） | `Qwen3VL` |
| 多模态类型（vlm_type） | `Qwen3VL` |
| Transformer 层数 | 28 |
| 分片命名模板 | `qwen3_vl_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 是，使用 /v1/embeddings |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_vl_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen3_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `Qwen3-VL-Embedding-2B_vision_384x384.axmodel` | 已找到 |

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
files += [c[k] for k in ["filename_post_axmodel","filename_tokens_embed","url_tokenizer_model","filename_image_encoder_axmodel"] if c.get(k)]
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

## 发送向量提取请求

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。先把一张内容已知的图片保存到 `~/edgeaccel/inputs/test.jpg`，再运行客户端。

```bash
python3 - <<'PY'
import json, urllib.request, base64
from pathlib import Path
base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/v1/models", timeout=30) as r:
    model = json.load(r)["data"][0]["id"]
payload = {"model": model, "input": ["A cat is sitting on the mat.", "A cat is sitting on the mat.", "There is a cat on the floor.", "The capital of France is Paris."], "encoding_format": "float"}
endpoint = "/v1/embeddings"
request = urllib.request.Request(base + endpoint,
    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as r:
    result = json.load(r)
vectors = [item["embedding"] for item in result["data"]]
print("向量数量：", len(vectors))
print("各向量维度：", [len(vector) for vector in vectors])
PY
```

检查 data 中向量数量与输入条数一致、维度固定，并且数值有限。Embedding 模型不使用交互式 run 或聊天接口。

运行时依据：[固定源码版本](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)、[配置接口](https://github.com/AXERA-TECH/ax-llm/blob/8501c22b940f8c5804cb35044c5ffc136918b8f1/docs/configuration.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 检查向量维度、有限数值及是否需要归一化；文本与图片使用配套编码器。
- 用匹配对、不匹配对比较相似度排序，再建立小型索引；更换模型后重建索引。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-Embedding-2B_vision_384x384.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/Qwen3-VL-Embedding-2B_vision_384x384.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`97ecf827ecfc3b07d35b74b852981d3415d14a1a`。仓库中的 30 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/tree/97ecf827ecfc3b07d35b74b852981d3415d14a1a)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。
- 此提交没有 README.md。已核对文件清单；运行参数和验收数据不能仅根据仓库名称补写。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/tree/97ecf827ecfc3b07d35b74b852981d3415d14a1a)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
