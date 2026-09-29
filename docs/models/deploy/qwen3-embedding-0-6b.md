---
title: "Qwen3-Embedding-0.6B 部署指南"
sidebar_label: "Qwen3-Embedding-0.6B"
description: "Qwen3-Embedding-0.6B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-Embedding-0.6B 部署指南

Qwen3-Embedding-0.6B 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-Embedding-0.6B` 的固定版本。下面下载本页选用的 32 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-embedding-0-6b/c899b296e820
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-Embedding-0.6B \
  "config.json" \
  "qwen3_p128_l0_together.axmodel" \
  "qwen3_p128_l1_together.axmodel" \
  "qwen3_p128_l2_together.axmodel" \
  "qwen3_p128_l3_together.axmodel" \
  "qwen3_p128_l4_together.axmodel" \
  "qwen3_p128_l5_together.axmodel" \
  "qwen3_p128_l6_together.axmodel" \
  "qwen3_p128_l7_together.axmodel" \
  "qwen3_p128_l8_together.axmodel" \
  "qwen3_p128_l9_together.axmodel" \
  "qwen3_p128_l10_together.axmodel" \
  "qwen3_p128_l11_together.axmodel" \
  "qwen3_p128_l12_together.axmodel" \
  "qwen3_p128_l13_together.axmodel" \
  "qwen3_p128_l14_together.axmodel" \
  "qwen3_p128_l15_together.axmodel" \
  "qwen3_p128_l16_together.axmodel" \
  "qwen3_p128_l17_together.axmodel" \
  "qwen3_p128_l18_together.axmodel" \
  "qwen3_p128_l19_together.axmodel" \
  "qwen3_p128_l20_together.axmodel" \
  "qwen3_p128_l21_together.axmodel" \
  "qwen3_p128_l22_together.axmodel" \
  "qwen3_p128_l23_together.axmodel" \
  "qwen3_p128_l24_together.axmodel" \
  "qwen3_p128_l25_together.axmodel" \
  "qwen3_p128_l26_together.axmodel" \
  "qwen3_p128_l27_together.axmodel" \
  "qwen3_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "tokenizer.txt" \
  --revision c899b296e820c98635190527cfb5730f214a1752 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-Embedding-0.6B` |
| 分词器类型（tokenizer_type） | `Qwen3` |
| 多模态类型（vlm_type） | 不启用 |
| Transformer 层数 | 28 |
| 分片命名模板 | `qwen3_p128_l%d_together.axmodel` |
| Embedding 模式 | 是，使用 /v1/embeddings |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `tokenizer.txt` | 已找到 |

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
files += [c[k] for k in ["filename_post_axmodel","filename_tokens_embed","url_tokenizer_model"] if c.get(k)]
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

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。

```bash
python3 - <<'PY'
import json, urllib.request
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

**固定样例已核对** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

每批 4 条英文短句得到 4 个 1024 维向量。相同文本的余弦相似度为 1，近义句的相似度高于无关句；两次请求的向量一致。

以第一条文本 `A cat is sitting on the mat.` 为查询，对比结果如下：

| 对比文本 | 余弦相似度 |
| --- | --- |
| A cat is sitting on the mat. | 1.000000 |
| There is a cat on the floor. | 0.768545 |
| The capital of France is Paris. | 0.164911 |

相似度用于比较本模型中的文本关系，不能直接解释为百分比准确率。

**使用时注意：**

- 只检查了 3 种短英文文本及其中一条重复输入，尚未评估中文、长文本或检索召回率。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`c899b296e820c98635190527cfb5730f214a1752`。

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
| 批量向量 API 请求数 | 2 | attempt-2/api.json 的 /v1/embeddings；每次 4 条文本，另有 health 和 models |
| 实际向量维度 | 1024 | 两批共 8 个响应向量；所有元素均有限，L2 模长约 1.0000006–1.0000010 |
| 重复文本余弦相似度 | 1 | 两批分别重新计算；A cat is sitting on the mat. 与同一句重复输入 |
| 相关文本余弦相似度 | 0.768545 | 两批一致；A cat is sitting on the mat. 与 There is a cat on the floor. |
| 无关文本余弦相似度 | 0.164911 | 两批一致；猫主题句与 The capital of France is Paris. |
| 两批向量数据是否完全一致 | true | 独立比较两次 response.data 的 index/向量数组，结果相等 |
| 2 次批量 HTTP 耗时 | 4.010 / 4.010 | 秒/批；每批 4 条输入，客户端端到端时间，不含服务启动 |
| 服务启动等待时间 | 33.64 | 秒；attempt-2/result.json startupWallSeconds，包含模型加载与就绪探测 |

适用范围：

- correctness 仅表示固定短文本的接口结构、数值完整性、重复一致性和样例相似关系核对通过；没有与原始模型浮点向量对齐，未计算检索基准或量化误差。
- 每批 4 条文本中含 1 条重复句，共 3 种不同文本；不能宣称覆盖 8 种文本或 8 个独立 API 请求。总 HTTP 记录为 4，其中 2 次是 health/models。
- attempt-1 因端口 8000 已占用在模型加载前退出，attempt-2 改为 8001 后完成。首次失败属于服务端口条件，不应隐去或解释为模型推理失败。
- 仅测试短英文文本，未验证中文、长文本截断、不同 batch 长度、并发请求或下游检索召回效果。
- 两批约 4.010 秒为每批 4 文本的端到端 HTTP 时间，不能当作单条文本延迟、纯 NPU 延迟或 tokens/s。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python_backup/infer_axmodel.py`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/python_backup/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`python_backup/utils/infer_func.py`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/python_backup/utils/infer_func.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/config.json) | 运行配置 |
| [`qwen3_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/qwen3_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`qwen3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/qwen3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/qwen3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/qwen3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/qwen3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/qwen3_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`python_backup/qwen3_embedding_0.6b_tokenizer/1_Pooling/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/python_backup/qwen3_embedding_0.6b_tokenizer/1_Pooling/config.json) | 运行配置 |
| [`python_backup/qwen3_embedding_0.6b_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/python_backup/qwen3_embedding_0.6b_tokenizer/config.json) | 运行配置 |
| [`python_backup/qwen3_embedding_0.6b_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/python_backup/qwen3_embedding_0.6b_tokenizer/generation_config.json) | 运行配置 |

仓库提交：`c899b296e820c98635190527cfb5730f214a1752`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/tree/c899b296e820c98635190527cfb5730f214a1752)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/tree/c899b296e820c98635190527cfb5730f214a1752)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/README.md)。
- [主要程序入口：python_backup/infer_axmodel.py](https://huggingface.co/AXERA-TECH/Qwen3-Embedding-0.6B/blob/c899b296e820c98635190527cfb5730f214a1752/python_backup/infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
