---
title: "bge-m3 部署指南"
sidebar_label: "bge-m3"
description: "bge-m3 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# bge-m3 部署指南

bge-m3 用于文本向量检索。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/bge-m3` 的固定版本。下面下载本页选用的 5 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/bge-m3/46734ad9f85c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/bge-m3 \
  "README.md" \
  "model/bge-m3_u16_npu3.axmodel" \
  "python/axmodel_infer.py" \
  "python/compare_bge_m3_onnx_axmodel.py" \
  "python/onnx_infer.py" \
  --revision 46734ad9f85c79a243364ba51f5ffa64a628079a \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词器与运行环境

本例在 **RK3576 + AX8850 16GB M.2** 上运行 BGE-M3，完成中英文文本检索。算力卡一次输出三种表示：1024 维语义向量、稀疏关键词权重，以及用于 ColBERT 匹配的 token 向量。主机按官方方法计算匹配分数并排序。

在已安装 PyAXEngine 的 Python 环境中执行：

```bash
python -m pip install 'numpy==1.26.4' 'transformers==4.51.3'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认提供者列表包含 `AXCLRTExecutionProvider`。本例使用 PyAXEngine `0.1.3.rc3`，固定 AXMODEL 约 860 MB。

官方例程使用 BAAI 分词器，单独下载以下固定版本：

```bash
TOKENIZER_DIR=~/edgeaccel/tokenizers/bge-m3/5617a9f61b02
~/edgeaccel/hf-env/bin/hf download BAAI/bge-m3 \
  config.json special_tokens_map.json tokenizer.json tokenizer_config.json sentencepiece.bpe.model \
  --revision 5617a9f61b028005a4858fdac845db406aefb181 \
  --local-dir "$TOKENIZER_DIR"
```

这一步仅下载约 22 MB 分词器文件，无需下载 BAAI 的模型权重。保持当前终端中的 `MODEL_DIR` 与 `TOKENIZER_DIR`。

## 运行中英文检索

下载 [BGE-M3 算力卡示例](../../../static/examples/bge_m3_card.py)，保存为 `~/edgeaccel/bge_m3_card.py`。指定尚不存在的输出目录：

```bash
python ~/edgeaccel/bge_m3_card.py \
  --model-dir "$MODEL_DIR" \
  --tokenizer-dir "$TOKENIZER_DIR" \
  --output ~/edgeaccel/results/bge-m3-01
```

例程校验并调用官方 `python/axmodel_infer.py`，将会话后端明确指定为 AXCL。分词、有效 token 截取、稀疏权重去重和 ColBERT 分数计算沿用官方实现。每条文本补齐至 512 个 token；超过该范围应先分段。

程序依次编码 10 条文本：四个问题和六段候选说明。英文问题涉及 BGE-M3 与 BM25，中文问题涉及设备检查和代理下载，候选还包括植物养护及音乐内容。随后重复运行一条英文和一条中文问题，检查三种表示是否一致。

融合分数采用官方对照示例的权重：

```text
融合分数 = 0.4 × dense + 0.2 × sparse + 0.4 × ColBERT
```

各分量的尺度不同，分数不是概率。更换权重会改变排序，应按自己的检索数据评估。当前示例的 `TEXTS` 与查询、候选索引固定对应；替换文本时同步调整这些索引。

## 查看三种匹配分数

| 文件或字段 | 内容 |
| --- | --- |
| `deployment-result.json` 的 `results` | 四个查询的六项候选分数及融合排序 |
| `lexicalWeights` | 每条文本实际生成的稀疏 token 权重 |
| `repeatChecks` | 中英文重复输入的三种表示是否相同 |
| `sessions` | AXCL 实际调用次数、耗时、输出形状及数值检查 |
| `embeddings.npz` | 语义向量、有效 ColBERT 向量与输入 token，供进一步复核 |

下方保留本次实际候选和分数。调用耗时包含 AXCL 数据传输，不含模型加载、分词与检索后处理。当前结果不含 CPU 浮点参考，不能据此量化模型转换造成的误差；完整检索数据集和真实 8GB 卡需另行评估。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已完成10条中英文文本编码与四个查询的六候选检索，三种输出均实际生成。下面展示真实候选、三种分数和融合排序。

**中英文混合检索**

四个问题各检索同一组六段候选文本，融合分数最高的结果均对应相关说明。下表按融合分数从高到低列出全部候选；权重为dense 0.4、sparse 0.2、ColBERT 0.4。

| What is BGE M3? | dense | sparse | ColBERT | 融合 |
| --- | --- | --- | --- | --- |
| BGE M3 is an embedding model supporting dense retrieval, lexical matching and multi-vector interaction. | 0.606571 | 0.181214 | 0.765336 | 0.585006 |
| BM25 is a bag-of-words retrieval function that ranks a set of documents based on the query terms appearing in each document. | 0.314308 | 0.009913 | 0.435255 | 0.301808 |
| 运行 axcl-smi，检查算力卡是否被枚举以及设备状态。 | 0.240349 | 0.000000 | 0.355042 | 0.238157 |
| The pianist played a quiet melody at the concert. | 0.190102 | 0.000000 | 0.308271 | 0.199349 |
| 下载模型前设置 http_proxy 和 https_proxy，填写可用的代理地址。 | 0.230056 | 0.000000 | 0.256257 | 0.194525 |
| 番茄需要定期浇水和充足的阳光。 | 0.124595 | 0.000000 | 0.298802 | 0.169359 |

| Definition of BM25 | dense | sparse | ColBERT | 融合 |
| --- | --- | --- | --- | --- |
| BM25 is a bag-of-words retrieval function that ranks a set of documents based on the query terms appearing in each document. | 0.629127 | 0.186147 | 0.782360 | 0.601824 |
| BGE M3 is an embedding model supporting dense retrieval, lexical matching and multi-vector interaction. | 0.321465 | 0.000000 | 0.449926 | 0.308556 |
| 运行 axcl-smi，检查算力卡是否被枚举以及设备状态。 | 0.230503 | 0.000000 | 0.369542 | 0.240018 |
| 番茄需要定期浇水和充足的阳光。 | 0.166311 | 0.000000 | 0.335301 | 0.200645 |
| The pianist played a quiet melody at the concert. | 0.162586 | 0.000000 | 0.329098 | 0.196674 |
| 下载模型前设置 http_proxy 和 https_proxy，填写可用的代理地址。 | 0.208285 | 0.000000 | 0.259427 | 0.187085 |

| 如何确认算力卡被主机识别？ | dense | sparse | ColBERT | 融合 |
| --- | --- | --- | --- | --- |
| 运行 axcl-smi，检查算力卡是否被枚举以及设备状态。 | 0.750773 | 0.152129 | 0.713452 | 0.616116 |
| 下载模型前设置 http_proxy 和 https_proxy，填写可用的代理地址。 | 0.486139 | 0.006176 | 0.416441 | 0.362267 |
| BGE M3 is an embedding model supporting dense retrieval, lexical matching and multi-vector interaction. | 0.392339 | 0.000000 | 0.363000 | 0.302136 |
| BM25 is a bag-of-words retrieval function that ranks a set of documents based on the query terms appearing in each document. | 0.375839 | 0.000000 | 0.361888 | 0.295091 |
| The pianist played a quiet melody at the concert. | 0.343115 | 0.000000 | 0.367572 | 0.284275 |
| 番茄需要定期浇水和充足的阳光。 | 0.300683 | 0.010481 | 0.331629 | 0.255021 |

| 怎样通过代理下载模型？ | dense | sparse | ColBERT | 融合 |
| --- | --- | --- | --- | --- |
| 下载模型前设置 http_proxy 和 https_proxy，填写可用的代理地址。 | 0.785357 | 0.263797 | 0.799417 | 0.686669 |
| 运行 axcl-smi，检查算力卡是否被枚举以及设备状态。 | 0.432489 | 0.001912 | 0.420168 | 0.341445 |
| BGE M3 is an embedding model supporting dense retrieval, lexical matching and multi-vector interaction. | 0.407481 | 0.000000 | 0.363017 | 0.308199 |
| BM25 is a bag-of-words retrieval function that ranks a set of documents based on the query terms appearing in each document. | 0.342654 | 0.000000 | 0.346981 | 0.275854 |
| 番茄需要定期浇水和充足的阳光。 | 0.305400 | 0.006073 | 0.322258 | 0.252278 |
| The pianist played a quiet melody at the concert. | 0.257108 | 0.000000 | 0.301850 | 0.223583 |

| 实际调用 | 平均调用耗时 | 中英文重复检查 |
| --- | --- | --- |
| 12 | 200.173 ms | 各1条，三种原始输出逐字节一致 |

**使用时注意：**

- 当前只核对四个查询与六段候选，不能代替完整检索数据集的召回率、MRR或多语言精度。
- 没有运行CPU浮点参考，尚不能量化转换误差；关键词、语义与ColBERT分数尺度不同，融合权重须按业务验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`46734ad9f85c79a243364ba51f5ffa64a628079a`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际调用 | 12次 | 10条独立文本，加1条英文和1条中文重复；每次batch 1、512 token。 |
| 平均调用耗时 | 200.173 ms | 全部12次session.run墙钟，包含AXCL传输；不含加载、分词与后处理。 |
| 重复一致性 | 2/2 | 重复文本的dense、sparse与ColBERT原始输出hash均与首次相同。 |

适用范围：

- 当前只核对四个查询与六段候选，不能代替完整检索数据集的召回率、MRR或多语言精度。
- 没有运行CPU浮点参考，尚不能量化转换误差；关键词、语义与ColBERT分数尺度不同，融合权重须按业务验证。
- 每条输入最多512 token，未覆盖长文档分段、批处理、多用户和真实8GB卡回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/axmodel_infer.py`](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/python/axmodel_infer.py) | Python 程序 / 前后处理 |
| [`model/bge-m3_u16_npu3.axmodel`](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/model/bge-m3_u16_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/config.json) | 运行配置 |
| [`python/onnx_infer.py`](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/python/onnx_infer.py) | Python 程序 / 前后处理 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/requirements.txt) | Python 依赖清单 |

仓库提交：`46734ad9f85c79a243364ba51f5ffa64a628079a`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/bge-m3/tree/46734ad9f85c79a243364ba51f5ffa64a628079a)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 检查输出是 dense、sparse 还是多向量，并使用对应的相似度计算；不要混用不同模型生成的索引。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/bge-m3/tree/46734ad9f85c79a243364ba51f5ffa64a628079a)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/README.md)。
- [主要程序入口：python/axmodel_infer.py](https://huggingface.co/AXERA-TECH/bge-m3/blob/46734ad9f85c79a243364ba51f5ffa64a628079a/python/axmodel_infer.py)。

返回[完整模型目录](../catalog.mdx)。
