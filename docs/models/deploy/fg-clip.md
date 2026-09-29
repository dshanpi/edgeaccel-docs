---
title: "FG-CLIP 部署指南"
sidebar_label: "FG-CLIP"
description: "FG-CLIP 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# FG-CLIP 部署指南

FG-CLIP 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/FG-CLIP` 的固定版本。下面下载本页选用的 12 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/fg-clip/1681903f53b5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/FG-CLIP \
  "README.md" \
  "bedroom.jpg" \
  "fg-clip2-base/config.json" \
  "fg-clip2-base/configuration_fgclip2.py" \
  "fg-clip2-base/modeling_fgclip2.py" \
  "fg-clip2-base/preprocessor_config.json" \
  "fg-clip2-base/special_tokens_map.json" \
  "fg-clip2-base/tokenizer.json" \
  "fg-clip2-base/tokenizer_config.json" \
  "image_encoder.axmodel" \
  "run_axmodel.py" \
  "text_encoder.axmodel" \
  --revision 1681903f53b528b37d0220e8d5f52291aace19f9 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备细粒度图文匹配环境

本例在 RK3576 + AX8850 16GB M.2 上运行官方 FG-CLIP2，比较卧室图片与四条中文描述，区分衣物颜色、鞋子和植物等细节。

在已安装 PyAXEngine 的 Python 环境执行：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'sentencepiece==0.2.1' 'Pillow==11.3.0'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认包含 `AXCLRTExecutionProvider`，设备 0 可用。保留模型目录中的 `fg-clip2-base` 文件夹，本例使用其 `Siglip2ImageProcessorFast` 和 `GemmaTokenizerFast`，不加载训练用模型。

## 运行官方卧室图片

下载 [FG-CLIP 算力卡示例](../../../static/examples/fgclip_card.py)，保存为 `~/edgeaccel/fgclip_card.py`。保留前面下载步骤设置的 `MODEL_DIR`，使用尚不存在的输出目录：

```bash
python ~/edgeaccel/fgclip_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/fgclip-01
```

程序读取 `bedroom.jpg` 和官方四条中文描述，显式调用两份 AXCL 编码器。图像重复运行两次，四条文本逐条运行，再重复第一条文本。

| 输出 | 检查内容 |
| --- | --- |
| `input.png` | 实际输入图片 |
| `deployment-result.json` | `completed: true`、两编码器实际调用、分数与排序 |
| `imageRepeatExact` / `textRepeatExact` | 重复输入的原始向量是否一致 |
| `embeddings.npz` | 图像与文本原始向量、图像张量、mask 和 token |

## 替换图片和候选描述

使用 `--image` 指定图片，每个 `--text` 指定一条中文或英文候选描述，输出目录须不同于已有结果。

本次固定权重的图像输入为 `1 × 1024 × 768`，mask 为 `1 × 1024`，文本输入为 `1 × 196`。例程沿用官方按图片尺寸确定 patch 数量的规则；官方 720 × 640 图片对应 1024 个 patch。其他尺寸若得到不同数量，程序会在推理前报告形状不匹配，需要匹配编译规格，不能直接改张量形状。

文本连同特殊 token 不得超过 196；超长时缩短描述，程序不静默截断。模型分数用于比较描述整体与图片的关系，不保证每一处细节都正确。

## 查看描述排序

下方展示原始图片、四条完整候选描述、向量点积和候选内 softmax 分数。后处理沿用官方 `dot × exp(4.75) - 16.75`，再对当前候选做 softmax；更换候选会改变分布，不能将该数值视为识别准确率或校准概率。

推理耗时按 `session.run` 的主机侧计时，包含数据传输，不含加载、分词、图像处理和保存。当前只完成官方单图基本运行，完整检索精度与其他输入规格仍需单独评估。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已完成官方卧室图片与四条中文描述的细粒度匹配，以下展示真实输入和全部候选分数。

**卧室图片：细节描述对照**

实际图片包含浅色衣物、两双鞋、绿植及床的一角。第一条描述排名最高；改为红蓝衣物、黑色高跟鞋或仙人掌的描述得分较低，街头市场描述最低。分数仅表示当前四条候选的相对匹配。

<div className="model-effect-gallery">

<figure>

[![实际输入：官方 bedroom.jpg，720 × 640](../../../static/validation/effects/fg-clip-20260928/input.png)](../../../static/validation/effects/fg-clip-20260928/input.png)

<figcaption>实际输入：官方 bedroom.jpg，720 × 640</figcaption>
</figure>

</div>

| 候选描述 | 向量点积 | 候选内 softmax |
| --- | --- | --- |
| 一个简约风格的卧室角落，黑色金属衣架上挂着多件米色和白色的衣物，下方架子放着两双浅色鞋子，旁边是一盆绿植，左侧可见一张铺有白色床单和灰色枕头的床。 | 0.196933 | 0.987573 |
| 一个简约风格的卧室角落，黑色金属衣架上挂着多件红色和蓝色的衣物，下方架子放着两双黑色高跟鞋，旁边是一盆绿植，左侧可见一张铺有白色床单和灰色枕头的床。 | 0.150804 | 0.00477548 |
| 一个简约风格的卧室角落，黑色金属衣架上挂着多件米色和白色的衣物，下方架子放着两双运动鞋，旁边是一盆仙人掌，左侧可见一张铺有白色床单和灰色枕头的床。 | 0.154882 | 0.00765103 |
| 一个繁忙的街头市场，摊位上摆满水果，背景是高楼大厦，人们在喧闹中购物。 | -0.079271 | 1.34837e-14 |

**使用时注意：**

- 官方单图与四条候选只证明基本运行，没有完整检索数据集或CPU参考。
- 候选内softmax不是准确率；向量点积沿用官方输出，没有额外强制归一化。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`1681903f53b528b37d0220e8d5f52291aace19f9`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 图像编码平均耗时 | 142.097 ms | 相同图片两次session.run，包含传输，不含加载和预处理。 |
| 文本编码平均耗时 | 12.615 ms / 条 | 四条描述和首条重复，共五次单条调用，196 token固定输入。 |
| 图像输入 / 输出 | 1024 patch / 768维向量 | 本次只验证该输入规格；点积和softmax均由保存的原始向量复算。 |

适用范围：

- 官方单图与四条候选只证明基本运行，没有完整检索数据集或CPU参考。
- 候选内softmax不是准确率；向量点积沿用官方输出，没有额外强制归一化。
- 本次为16GB卡；其他输入规格、长期连续运行和真实8GB容量仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axmodel.py`](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/run_axmodel.py) | Python 程序 / 前后处理 |
| [`image_encoder.axmodel`](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/image_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`text_encoder.axmodel`](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/text_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fg-clip2-base/config.json`](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/fg-clip2-base/config.json) | 运行配置 |
| [`fg-clip2-base/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/fg-clip2-base/preprocessor_config.json) | 运行配置 |
| [`fg-clip2-base/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/fg-clip2-base/tokenizer_config.json) | 运行配置 |

仓库提交：`1681903f53b528b37d0220e8d5f52291aace19f9`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/FG-CLIP/tree/1681903f53b528b37d0220e8d5f52291aace19f9)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/FG-CLIP/tree/1681903f53b528b37d0220e8d5f52291aace19f9)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/README.md)。
- [主要程序入口：run_axmodel.py](https://huggingface.co/AXERA-TECH/FG-CLIP/blob/1681903f53b528b37d0220e8d5f52291aace19f9/run_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
