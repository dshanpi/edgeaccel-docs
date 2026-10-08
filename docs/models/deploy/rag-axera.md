---
title: "RAG.axera 部署指南"
sidebar_label: "RAG.axera"
description: "RAG.axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# RAG.axera 部署指南

RAG.axera 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/RAG.axera` 的固定版本。下面下载本页选用的 81 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/rag-axera/1ed9a31a4ffb
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/RAG.axera \
  --include "models/*.axmodel" "models/*.npy" "tokenizer/*" "pdf_sample/*" \
  --revision 1ed9a31a4ffb70912a225e0247e4b14158a67a7b \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备问答程序

本例使用官方 RAG.axera 固定权重，在 RK3576 + AX8850 16GB M.2 算力卡上通过 `AXCLRTExecutionProvider` 执行文档嵌入和回答生成。配套程序提供 PDF/TXT 上传、流式回答、来源页码和问答记录。

模型文件约 4.67 GB，存储目录建议至少有 6 GB 可用空间。`MODEL_DIR` 应指向完整模型目录；也可指向已挂载并完成校验的只读目录。本次实测从主机通过只读网络目录读取模型，耗时包含该传输方式的影响。

下载[本页配套运行包](/examples/rag-axera-20261002.tar.gz)，保存到连接算力卡的 Linux 主机 `~/edgeaccel/`。保留前文的 `MODEL_DIR`，执行：

```bash
cd ~/edgeaccel
tar -xzf rag-axera-20261002.tar.gz
cd rag-card
source ~/edgeaccel/python-env/bin/activate
python -m pip install -r requirements.txt
export MODEL_DIR
python -c 'from pathlib import Path; from rag_package_candidate import verify_package; import os; print(verify_package(Path(os.environ["MODEL_DIR"]), Path("package-files.json"), "6fb78040940bb347ebe511b9079be8020a9f8df30bcb679c31ccf3b8c9fefd7a"))'
```

若 PyAXEngine 安装在其他虚拟环境，替换激活路径。校验结果应显示 `verifiedFiles: 81`，不一致时重新下载对应文件后再运行。

## 启动文档问答

在连接算力卡的 Linux 主机执行：

```bash
cd ~/edgeaccel/rag-card
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
python rag_app_candidate.py \
  --package-root "$MODEL_DIR" \
  --data-dir ~/edgeaccel/results/rag \
  --expected-boot-id "$(cat /proc/sys/kernel/random/boot_id)" \
  --host 127.0.0.1 --port 7860 --device 0
```

首次加载后终端显示 `http://127.0.0.1:7860`。保留此终端，在主机桌面浏览器打开该地址。若从另一台电脑访问，在该电脑建立 SSH 转发，将命令中的用户名和地址替换为实际值：

```bash
ssh -N -L 7860:127.0.0.1:7860 用户名@开发板IP
```

然后在该电脑打开 `http://127.0.0.1:7860`。

## 上传资料并提问

1. 选择下载目录中的 `pdf_sample/introduction.pdf`，上传并建立索引。本例为 4 页 PDF，生成 7 个片段、1024 维向量。
2. 输入“Pulsar2 的核心功能是把哪种文件编译成哪种文件？”，提交后观察流式回答。
3. 核对页面中的来源文件、页码和原文片段，再对照回答。生成模型可能省略正文引用编号，不能把检索相似度当作回答置信度。
4. 点击问答记录查看本次输出与结束状态；记录同时保存于 `~/edgeaccel/results/rag/records/`。

可继续提问“资料里的‘对分’指什么？”和“这份资料作者的手机号码是多少？”。后者在资料中没有答案，应明确说明无法确定。

也可通过 HTTP 接口执行同样的上传和提问：

```bash
curl --fail -H 'Content-Type: application/pdf' \
  -H 'X-Filename: introduction.pdf' \
  --data-binary "@$MODEL_DIR/pdf_sample/introduction.pdf" \
  http://127.0.0.1:7860/documents
curl --fail -N -H 'Content-Type: application/json' \
  --data '{"question":"资料里的‘对分’指什么？","max_tokens":128,"k":3,"stream":true}' \
  http://127.0.0.1:7860/ask
```

输出以 `finish_reason: eos` 结束表示模型自然结束；`length` 表示达到输出上限，需检查回答是否完整。上传新文件会替换当前检索索引。本例适用于可提取文字的 PDF 和 TXT，未接入扫描件 OCR；单文件上限 20 MiB。停止服务时在运行终端按 `Ctrl+C`。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 PDF 上传、向量建库、检索与三次文档问答。

**PDF 资料问答**

官方 introduction.pdf 实际上传、向量建库、检索及回答生成；以下为模型原始回答。

| 项目 | 实测结果 |
| --- | --- |
| 问题 | Pulsar2 的核心功能是把哪种文件编译成哪种文件？ |
| 实际回答 | Pulsar2的核心功能是把.onnx模型编译成.axmodel模型。 |
| 检索来源 | 第 1 页、第 4 页、第 2 页 |
| 完成方式 | eos |
| 问答耗时 | 32.447 s |

| 项目 | 实测结果 |
| --- | --- |
| 问题 | 资料里的“对分”指什么？ |
| 实际回答 | 所谓 对分, 即对⽐⼯具链编译前后的同⼀个模型不同版本 (⽂件类型) 推理结果之间的误差。 |
| 检索来源 | 第 4 页、第 2 页、第 3 页 |
| 完成方式 | eos |
| 问答耗时 | 31.008 s |

| 项目 | 实测结果 |
| --- | --- |
| 问题 | 这份资料作者的手机号码是多少？ |
| 实际回答 | 无法从资料中获取这份资料的作者手机号码的信息。 |
| 检索来源 | 第 4 页、第 2 页、第 3 页 |
| 完成方式 | eos |
| 问答耗时 | 13.885 s |

**使用时注意：**

- 本次为 RK3576 + AX8850 16GB、AXCL 3.16 的基础部署，8GB 卡与长期连续运行尚未验证。
- 三次回答均自然结束；生成正文未附引用编号，应结合页面列出的页码和原文片段核对。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`1ed9a31a4ffb70912a225e0247e4b14158a67a7b`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12 / PyAXEngine 0.1.3 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 索引 | 4 页 / 7 个片段 / 1024 维 | 官方 introduction.pdf，单份可提取文字的 PDF。 |
| 资料问题 | 2 / 2 回答符合原文 | 人工智能助手逐项对照原始 PDF；非通用准确率评测。 |
| 无答案问题 | 明确说明无法确定 | 资料不含作者手机号，未生成号码。 |
| 算力卡执行 | 57 个 AXModel / 2784 次调用 | 向量模型取末层隐藏状态，词表输出头仅加载未调用。 |

适用范围：

- 无答案问题仍能检索到相似片段；相似度不是回答置信度，不能据此认定资料中存在答案。
- 本次模型由只读网络挂载读取，耗时含文件访问、CPU 处理及逐次输出校验，不作为本地磁盘或服务吞吐基准。
- 本次验证独立 AXCL 配套程序的真实 HTTP 流程；未据此认定上游 Gradio/FastAPI 原程序已适配。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gui.py`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/gui.py) | Python 程序 / 前后处理 |
| [`llm_api.py`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/llm_api.py) | Python 程序 / 前后处理 |
| [`models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/models/Qwen2.5-1.5B-Instruct_axmodel/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/demo.png`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/assets/demo.png) | 示例输入 |
| [`tokenizer/Qwen2.5-1.5B-Instruct/config.json`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/tokenizer/Qwen2.5-1.5B-Instruct/config.json) | 运行配置 |
| [`tokenizer/Qwen2.5-1.5B-Instruct/generation_config.json`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/tokenizer/Qwen2.5-1.5B-Instruct/generation_config.json) | 运行配置 |
| [`tokenizer/Qwen2.5-1.5B-Instruct/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/tokenizer/Qwen2.5-1.5B-Instruct/tokenizer_config.json) | 运行配置 |
| [`tokenizer/Qwen3-Embedding-0.6B/1_Pooling/config.json`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/tokenizer/Qwen3-Embedding-0.6B/1_Pooling/config.json) | 运行配置 |
| [`tokenizer/Qwen3-Embedding-0.6B/config.json`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/tokenizer/Qwen3-Embedding-0.6B/config.json) | 运行配置 |
| [`tokenizer/Qwen3-Embedding-0.6B/generation_config.json`](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/tokenizer/Qwen3-Embedding-0.6B/generation_config.json) | 运行配置 |

仓库提交：`1ed9a31a4ffb70912a225e0247e4b14158a67a7b`。仓库中的 58 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/RAG.axera/tree/1ed9a31a4ffb70912a225e0247e4b14158a67a7b)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/RAG.axera/tree/1ed9a31a4ffb70912a225e0247e4b14158a67a7b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/README.md)。
- [主要程序入口：gui.py](https://huggingface.co/AXERA-TECH/RAG.axera/blob/1ed9a31a4ffb70912a225e0247e4b14158a67a7b/gui.py)。

返回[完整模型目录](../catalog.mdx)。
