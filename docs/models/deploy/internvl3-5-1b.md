---
title: "InternVL3_5-1B 部署指南"
sidebar_label: "InternVL3_5-1B"
description: "InternVL3_5-1B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# InternVL3_5-1B 部署指南

InternVL3_5-1B 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/InternVL3_5-1B` 的固定版本。下面下载本页选用的 56 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/internvl3-5-1b/ead75a3befa5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/InternVL3_5-1B \
  "README.md" \
  "examples/image_0.jpg" \
  "examples/image_1.jpg" \
  "examples/image_2.png" \
  "examples/image_3.png" \
  "infer_axmodel.py" \
  "internvl3-5_axmodel/model.embed_tokens.weight.npy" \
  "internvl3-5_axmodel/qwen3_p128_l0_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l10_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l11_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l12_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l13_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l14_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l15_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l16_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l17_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l18_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l19_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l1_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l20_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l21_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l22_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l23_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l24_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l25_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l26_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l27_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l2_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l3_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l4_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l5_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l6_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l7_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l8_together.axmodel" \
  "internvl3-5_axmodel/qwen3_p128_l9_together.axmodel" \
  "internvl3-5_axmodel/qwen3_post.axmodel" \
  "internvl3-5_tokenizer/README.md" \
  "internvl3-5_tokenizer/added_tokens.json" \
  "internvl3-5_tokenizer/chat_template.jinja" \
  "internvl3-5_tokenizer/config.json" \
  "internvl3-5_tokenizer/configuration_intern_vit.py" \
  "internvl3-5_tokenizer/configuration_internvl_chat.py" \
  "internvl3-5_tokenizer/conversation.py" \
  "internvl3-5_tokenizer/generation_config.json" \
  "internvl3-5_tokenizer/merges.txt" \
  "internvl3-5_tokenizer/modeling_intern_vit.py" \
  "internvl3-5_tokenizer/modeling_internvl_chat.py" \
  "internvl3-5_tokenizer/preprocessor_config.json" \
  "internvl3-5_tokenizer/processor_config.json" \
  "internvl3-5_tokenizer/special_tokens_map.json" \
  "internvl3-5_tokenizer/tokenizer.json" \
  "internvl3-5_tokenizer/tokenizer_config.json" \
  "internvl3-5_tokenizer/video_preprocessor_config.json" \
  "internvl3-5_tokenizer/vocab.json" \
  "utils/infer_func.py" \
  "vit-models/internvl_vit_model_1x3x448x448.axmodel" \
  --revision ead75a3befa5b9c17b97bc0093c34db1b72c1d99 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备图文推理环境

本例在 **RK3576 + AX8850 16GB M.2** 上运行 InternVL3.5-1B。视觉编码、28 层语言模型和输出层均通过 AXCL 执行；分词、图像处理和 KV 缓存由主机管理。

在已安装 PyAXEngine 的 AXCL Python 环境中准备依赖：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'ml-dtypes==0.5.3' 'Pillow==11.3.0' \
  'onnxruntime==1.20.1' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认提供者列表包含 `AXCLRTExecutionProvider`，设备 0 可用。本次使用 PyAXEngine `0.1.3.rc3`。此处版本对应本页的固定权重与运行示例，安装后保持同一 Python 环境运行。

下载 [InternVL3.5 算力卡运行示例](../../../static/examples/internvl35_card.py)，保存为 `~/edgeaccel/internvl35_card.py`。前面的固定版本下载约 1.78 GB，包含 Python 推理入口、分词器、图片、视觉模型、语言模型和 NumPy 格式的 Embedding。保留各目录结构，无需重复下载另外两份 `.bin` Embedding。

例程校验官方脚本版本，指定 AXCL 后端，保留官方图像处理、提示词模板、预填充与解码流程。Embedding 使用只读内存映射；每次问答清空 KV 缓存，默认最多生成 96 个 token。

## 运行图像描述与文本问答

沿用下载步骤中的 `MODEL_DIR`，指定一个尚不存在的结果目录：

```bash
python ~/edgeaccel/internvl35_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/internvl35-1b-01
```

程序依次运行小熊猫识别、大熊猫图片描述和 `2加3` 纯文本问答。每张图片按官方单块方式处理为 448 × 448 输入，使用 256 个视觉 token。语言模型加载一次，三个问题彼此独立。

使用自己的图片与问题：

```bash
python ~/edgeaccel/internvl35_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/edgeaccel/inputs/photo.jpg \
  --question '请用一句中文描述图片中看见的内容。' \
  --output ~/edgeaccel/results/internvl35-1b-custom-01
```

将 `photo.jpg` 替换为实际图片。纯文本问答省略 `--image`；需要先检查单张样例时使用 `--first-only`。提示词最多 1023 个 token，图片 token 也计入其中；超过范围时缩短问题。本版本官方预填充实现要求最后一块非空，输入 token 数恰为 128 的整数倍时，例程会提示调整问题后再运行。

## 查看回答与输入图片

| 文件或字段 | 判断方法 |
| --- | --- |
| `input-1.jpg`、`input-2.jpg` | 与两个图文问题对应的实际输入 |
| `deployment-result.json` 的 `samples` | 每个问题的原文、回答、token、停止原因和耗时 |
| `sessions` | 30 个 AXCL 模型的实际调用、形状组与有限值检查 |
| `completed` | 所有样例均正常结束时为 `true` |

每个回答的 `stopReason` 应为 `eos`，表示模型生成结束标记。`length` 表示达到输出上限，`context` 表示上下文耗尽；这两种情况会保留已有回答并以非零状态退出，不计作完整回答。可在范围内调整 `--max-new-tokens` 后用新的输出目录重试。

下方展示本次输入图片和回答原文。生成耗时包含预处理、主机与卡之间的数据传输、模型推理及示例记录开销，不含模型加载；首 token 时间表示示例内部拿到首个 token 的时间，不是网页首字延迟。模型加载时间在 JSON 中单独记录。

本页先核对少量图文和文本样例；它们不能代替完整数据集精度、长上下文、多图、多轮对话或真实 8GB 卡回归。使用业务图片时继续检查动物类别、颜色、位置和数量等细节。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已完成小熊猫识别、大熊猫图片描述和纯文本算术问答。下面保留本次实际输入、回答与耗时。

**单图理解与文本问答**

模型复用同一组已加载权重，每个问题清空 KV 缓存。下面展示两张实际输入图片、三个问题和完整回答；三次回答均到达 EOS。

**示例 1：输入**

[![示例 1 实际输入图片](../../../static/validation/effects/internvl3-5-1b-20260928/input-1.jpg)](../../../static/validation/effects/internvl3-5-1b-20260928/input-1.jpg)

```text
图中是什么动物？只用一个词回答。
```

**实际回复**

```text
红熊猫
```

回答“红熊猫”，与输入中的小熊猫相符，且遵循单词回答要求。

**示例 2：输入**

[![示例 2 实际输入图片](../../../static/validation/effects/internvl3-5-1b-20260928/input-2.jpg)](../../../static/validation/effects/internvl3-5-1b-20260928/input-2.jpg)

```text
请用一句中文描述图片中看见的内容。
```

**实际回复**

```text
这张图片展示了一只大熊猫正在竹林中休息，似乎在吃一些绿色植物。
```

识别出大熊猫和竹子场景；“休息”是模型对状态的解释，静态图片不能单独确认。这里保留完整原文。

**示例 3：输入**

```text
2加3等于多少？只回答数字。
```

**实际回复**

```text
5
```

输出为“5”，数值与只回答数字的格式均符合本题要求。

| 样例 | 生成耗时 | 内部首 token | 结束状态 |
| --- | --- | --- | --- |
| 1 | 5.624 s | 2.684 s | EOS |
| 2 | 29.214 s | 2.619 s | EOS |
| 3 | 2.027 s | 0.509 s | EOS |

**使用时注意：**

- 少量样例的类别及算术结果可对照，仍需独立数据集评估描述细节、数量、OCR和中文理解；不能把单帧中的状态解释视为已确认事实。
- 每次单图448×448、256视觉token，测试只覆盖decoder形状组0、1、2、3；未覆盖更长上下文、多图或多轮对话。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`ead75a3befa5b9c17b97bc0093c34db1b72c1d99`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际执行模型 | 30 个 AXMODEL | 28层语言模型、输出层及视觉编码器均通过 AXCL 调用，输出数值有限。 |
| 生成耗时 | 2.027–29.214 s | 模型已加载；包含预处理、主机与卡数据传输和推理，不是纯NPU耗时。 |
| 内部首 token | 0.509–2.684 s | 从样例预处理开始到取得首个token，不含模型加载，不等于网页首字延迟。 |

适用范围：

- 少量样例的类别及算术结果可对照，仍需独立数据集评估描述细节、数量、OCR和中文理解；不能把单帧中的状态解释视为已确认事实。
- 每次单图448×448、256视觉token，测试只覆盖decoder形状组0、1、2、3；未覆盖更长上下文、多图或多轮对话。
- 本次环境为16GB卡，真实8GB容量和长期连续运行仍待回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/gradio_demo.py) | Python 程序 / 前后处理 |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`internvl3-5_axmodel/qwen3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_axmodel/qwen3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3-5_axmodel/qwen3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_axmodel/qwen3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3-5_axmodel/qwen3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_axmodel/qwen3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3-5_axmodel/qwen3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_axmodel/qwen3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3-5_axmodel/qwen3_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_axmodel/qwen3_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/config.json) | 运行配置 |
| [`internvl3-5_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_tokenizer/config.json) | 运行配置 |
| [`internvl3-5_tokenizer/configuration_intern_vit.py`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_tokenizer/configuration_intern_vit.py) | 旧版分词服务入口 |
| [`internvl3-5_tokenizer/configuration_internvl_chat.py`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_tokenizer/configuration_internvl_chat.py) | 旧版分词服务入口 |
| [`internvl3-5_tokenizer/conversation.py`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_tokenizer/conversation.py) | 旧版分词服务入口 |
| [`internvl3-5_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_tokenizer/generation_config.json) | 运行配置 |
| [`internvl3-5_tokenizer/modeling_intern_vit.py`](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/internvl3-5_tokenizer/modeling_intern_vit.py) | 旧版分词服务入口 |

仓库提交：`ead75a3befa5b9c17b97bc0093c34db1b72c1d99`。仓库中的 30 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/tree/ead75a3befa5b9c17b97bc0093c34db1b72c1d99)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/tree/ead75a3befa5b9c17b97bc0093c34db1b72c1d99)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/README.md)。
- [主要程序入口：infer_axmodel.py](https://huggingface.co/AXERA-TECH/InternVL3_5-1B/blob/ead75a3befa5b9c17b97bc0093c34db1b72c1d99/infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
