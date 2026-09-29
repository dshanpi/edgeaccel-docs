---
title: "jina-clip-v2 部署指南"
sidebar_label: "jina-clip-v2"
description: "jina-clip-v2 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# jina-clip-v2 部署指南

jina-clip-v2 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/jina-clip-v2` 的固定版本。下面下载本页选用的 13 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/jina-clip-v2/00914adf025a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/jina-clip-v2 \
  "README.md" \
  "beach1.jpg" \
  "image_encoder.axmodel" \
  "image_encoder_224x224.axmodel" \
  "jina-clip-v2/config.json" \
  "jina-clip-v2/config_sentence_transformers.json" \
  "jina-clip-v2/modules.json" \
  "jina-clip-v2/preprocessor_config.json" \
  "jina-clip-v2/special_tokens_map.json" \
  "jina-clip-v2/tokenizer.json" \
  "jina-clip-v2/tokenizer_config.json" \
  "run_axmodel.py" \
  "text_encoder.axmodel" \
  --revision 00914adf025ae2b9fa62ead49bd1f1c401a37502 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备图文检索环境

本例在 RK3576 + AX8850 16GB M.2 上运行 Jina-CLIP-v2，用同一张海滩图片比较六条中英文描述。文本编码器、512 × 512 图像编码器和 224 × 224 图像编码器均通过 AXCL 调用。

在已安装 PyAXEngine 的 Python 环境执行：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'sentencepiece==0.2.1' 'Pillow==11.3.0'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认列表包含 `AXCLRTExecutionProvider`，设备 0 可用。本例沿用官方示例的前 512 维特征截取和 L2 归一化，比较图像与文本向量的余弦相似度。

## 下载固定版本图像处理器

模型文件中的处理器配置引用了独立源码仓库。下载下面两个固定版本文件，避免运行时自动获取变化中的代码：

```bash
PROCESSOR_DIR=~/edgeaccel/processors/jina-clip-39e6a55a
mkdir -p "$PROCESSOR_DIR"
~/edgeaccel/hf-env/bin/hf download jinaai/jina-clip-implementation \
  processing_clip.py transform.py \
  --revision 39e6a55ae971b59bea6e44675d237c99762e7ee2 \
  --local-dir "$PROCESSOR_DIR"
```

下载 [Jina-CLIP-v2 算力卡示例](../../../static/examples/jina_clip_card.py)，保存为 `~/edgeaccel/jina_clip_card.py`。例程检查官方推理函数和这两个处理器文件的校验值，使用本地分词器和图像处理器，不在推理过程中下载依赖。

## 运行两个图像编码规格

保持前面下载步骤中的 `MODEL_DIR`、`PROCESSOR_DIR`，指定一个尚不存在的输出目录：

```bash
python ~/edgeaccel/jina_clip_card.py \
  --model-dir "$MODEL_DIR" --processor-dir "$PROCESSOR_DIR" \
  --output ~/edgeaccel/results/jina-clip-01
```

程序读取官方 `beach1.jpg`，逐条编码六条描述，然后分别运行两份图像权重。每个图像规格重复推理两次，首条文本也重复一次，结果保存在 `deployment-result.json` 和 `embeddings.npz`。

| 检查项 | 预期结果 |
| --- | --- |
| `completed` | 两份图像模型及全部文本正常完成后为 `true` |
| `sessions` | 包含三个 `.axmodel` 的实际调用和耗时 |
| `variants` | 分别包含 512、224 两种输入尺寸的分数与排序 |
| `textRepeatExact` / `repeatExact` | 记录相同输入的重复原始输出是否一致 |
| `input.png` | 本次实际输入图像 |

512 和 224 使用各自的编译权重。改变图片缩放尺寸不能代替切换对应权重，程序会核对输入形状和数据类型。

## 替换图片和候选描述

将图片路径与候选描述替换为业务输入；每个 `--text` 对应一条候选：

```bash
python ~/edgeaccel/jina_clip_card.py \
  --model-dir "$MODEL_DIR" --processor-dir "$PROCESSOR_DIR" \
  --image ~/edgeaccel/inputs/photo.jpg \
  --text 'A sunset over the beach.' \
  --text '一辆红色汽车停在路边。' \
  --output ~/edgeaccel/results/jina-clip-custom-01
```

本版文本模型使用 50 个 token 的固定输入，包括特殊 token。文本不足时补齐，超过时程序要求缩短描述，不静默截断。

## 查看排序与耗时

下方保留本次输入和两种图像规格的实际分数。**余弦相似度用于比较候选描述，不是识别准确率或百分比概率**；更高分数也不证明描述中的每一处细节都正确。

表中推理耗时为 `session.run` 的主机侧计时，包含主机与卡的数据传输，不包含模型加载、分词、图像预处理和保存。单张图片和少量描述不能替代完整检索数据集评估。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已完成文本编码器及两种尺寸图像编码器的图文匹配，以下展示实际输入和全部六条候选描述的分数。

**海边日落：中英文图文匹配**

实际输入包含落日、海面、浪花与沙滩。两种图像尺寸下，中英文日落描述均排在前两位，完整排序一致。相似度是归一化向量的余弦分数，不是分类概率。

<div className="model-effect-gallery">

<figure>

[![实际输入：官方 beach1.jpg](../../../static/validation/effects/jina-clip-v2-20260928/input.png)](../../../static/validation/effects/jina-clip-v2-20260928/input.png)

<figcaption>实际输入：官方 beach1.jpg</figcaption>
</figure>

</div>

| 候选描述 | 512 × 512 分数 | 224 × 224 分数 |
| --- | --- | --- |
| beautiful sunset over the beach | 0.314032 | 0.313744 |
| 蓝蓝的天空和海面，在夕阳的照射下，显得非常美丽 | 0.322470 | 0.327772 |
| 一群人在沙滩上散步 | 0.095253 | 0.099843 |
| A red car parked on a city street. | -0.057583 | -0.054729 |
| 一只猫坐在书桌上。 | -0.028126 | -0.023218 |
| Snow-covered mountains under a cloudy sky. | 0.061315 | 0.081488 |

**使用时注意：**

- 本次为一张图片、六条短文本的基本运行验证，未进行完整检索数据集评测或 CPU 浮点参考对照。
- 按官方示例截取前512维后重新归一化；原始输出为1024维。两次图片输出和重复文本输出逐字节一致。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`00914adf025ae2b9fa62ead49bd1f1c401a37502`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 512 图像编码 | 604.805 ms | 两次 session.run 平均值，包含传输，不含加载、图像预处理及文本编码。 |
| 224 图像编码 | 63.056 ms | 同一图片两次 session.run 平均值；不能据此推断其他场景的精度。 |
| 文本编码 | 19.547 ms / 条 | 六条描述及第一条的重复输入，共七次单条调用；固定长度50 token。 |

适用范围：

- 本次为一张图片、六条短文本的基本运行验证，未进行完整检索数据集评测或 CPU 浮点参考对照。
- 按官方示例截取前512维后重新归一化；原始输出为1024维。两次图片输出和重复文本输出逐字节一致。
- 本次使用16GB卡，真实8GB容量及长时间连续运行仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axmodel.py`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/run_axmodel.py) | Python 程序 / 前后处理 |
| [`image_encoder.axmodel`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/image_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`image_encoder_224x224.axmodel`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/image_encoder_224x224.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`text_encoder.axmodel`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/text_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/config.json) | 运行配置 |
| [`jina-clip-v2/config.json`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/jina-clip-v2/config.json) | 运行配置 |
| [`jina-clip-v2/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/jina-clip-v2/preprocessor_config.json) | 运行配置 |
| [`jina-clip-v2/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/jina-clip-v2/tokenizer_config.json) | 运行配置 |

仓库提交：`00914adf025ae2b9fa62ead49bd1f1c401a37502`。仓库中的 3 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/jina-clip-v2/tree/00914adf025ae2b9fa62ead49bd1f1c401a37502)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/jina-clip-v2/tree/00914adf025ae2b9fa62ead49bd1f1c401a37502)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/README.md)。
- [主要程序入口：run_axmodel.py](https://huggingface.co/AXERA-TECH/jina-clip-v2/blob/00914adf025ae2b9fa62ead49bd1f1c401a37502/run_axmodel.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/jina-clip-v2)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
