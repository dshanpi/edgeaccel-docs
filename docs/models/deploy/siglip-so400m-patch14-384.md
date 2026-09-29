---
title: "siglip-so400m-patch14-384 部署指南"
sidebar_label: "siglip-so400m-patch14-384"
description: "siglip-so400m-patch14-384 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# siglip-so400m-patch14-384 部署指南

siglip-so400m-patch14-384 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/siglip-so400m-patch14-384` 的固定版本。下面下载本页选用的 12 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/siglip-so400m-patch14-384/002659be687d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/siglip-so400m-patch14-384 \
  "000000039769.jpg" \
  "README.md" \
  "ax650/siglip_text_u16.axmodel" \
  "ax650/siglip_vision_u16_fcu8.axmodel" \
  "python/inference_axmodel.py" \
  "python/requirements.txt" \
  "tokenizer/config.json" \
  "tokenizer/preprocessor_config.json" \
  "tokenizer/special_tokens_map.json" \
  "tokenizer/spiece.model" \
  "tokenizer/tokenizer.json" \
  "tokenizer/tokenizer_config.json" \
  --revision 002659be687de26fead6d991b6307a0553d34c27 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备图文匹配环境

本例在 RK3576 + AX8850 16GB M.2 上运行 SigLIP SO400M，比较图片与六条英文描述的匹配程度。图像和文本编码器均使用 AXCL。在已安装 PyAXEngine 的 Python 环境执行：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'sentencepiece==0.2.1' 'Pillow==11.3.0'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认包含 `AXCLRTExecutionProvider`，设备 0 可用。模型下载清单中的两份 `ax650/*.axmodel` 和整个 `tokenizer` 目录须保留，本例使用随模型发布的本地图像处理器和分词器。

## 运行官方图片与六条描述

下载 [SigLIP 算力卡示例](../../../static/examples/siglip_card.py)，保存为 `~/edgeaccel/siglip_card.py`。保留前面下载步骤中的 `MODEL_DIR`，指定尚不存在的输出目录：

```bash
python ~/edgeaccel/siglip_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/siglip-01
```

程序读取官方 `000000039769.jpg`，使用 384 × 384 图像输入和 64 token 文本输入。每个编码器取官方示例使用的第二路 1152 维输出，进行 L2 归一化后计算余弦相似度。

| 输出 | 查看内容 |
| --- | --- |
| `input.png` | 实际输入图片 |
| `deployment-result.json` | `completed: true`、六条描述的分数与排序、两份权重的实际调用和耗时 |
| `embeddings.npz` | 原始向量、归一化向量、图像张量和 token，便于复算 |
| `imageRepeatExact` / `textRepeatExact` | 图片及首条描述的重复原始输出是否一致 |

本例只展示余弦分数。官方示例中的 sigmoid 缩放和偏置使用随机数，不能作为可信的匹配概率，因此本例不生成百分比概率。

## 替换图片和英文描述

每个 `--text` 对应一条候选描述。文本连同特殊 token 超过固定长度时，程序要求缩短输入：

```bash
python ~/edgeaccel/siglip_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/edgeaccel/inputs/photo.jpg \
  --text 'Two cats resting on a couch.' \
  --text 'Two dogs running in a park.' \
  --output ~/edgeaccel/results/siglip-custom-01
```

## 查看匹配分数

下方展示本次真实图片与全部候选描述的结果。分数适合比较候选之间的相对匹配程度，不能视作分类准确率，也不保证描述中的数量、位置和动作细节全部正确。

耗时按主机侧 `session.run` 计时，包含主机与算力卡的数据传输，不含模型加载、预处理、分词和结果保存。当前样例不替代完整图文检索数据集评测。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已完成官方图片的双编码器推理，以下展示六条英文描述的实际匹配结果及原始输入。

**两只猫：图片与英文描述匹配**

实际输入是两只猫躺在粉色沙发上的图片。“Two cats resting on a pink couch.” 排名第一，“a photo of 2 cats” 排名第二，两项均高于狗、汽车、海滩及蔬菜描述。这里展示归一化向量余弦分数，不使用随机缩放和偏置产生的百分比。

<div className="model-effect-gallery">

<figure>

[![实际输入：官方 000000039769.jpg](../../../static/validation/effects/siglip-so400m-patch14-384-20260928/input.png)](../../../static/validation/effects/siglip-so400m-patch14-384-20260928/input.png)

<figcaption>实际输入：官方 000000039769.jpg</figcaption>
</figure>

</div>

| 排名 | 候选描述 | 余弦分数 |
| --- | --- | --- |
| 1 | Two cats resting on a pink couch. | 0.186040 |
| 2 | a photo of 2 cats | 0.145750 |
| 3 | a photo of 2 dogs | 0.069122 |
| 4 | A sunset over the beach. | -0.002559 |
| 5 | A red car parked on a city street. | -0.042389 |
| 6 | A plate of fresh vegetables. | -0.051342 |

**使用时注意：**

- 本次为一张官方图片、六条英文描述的基本运行测试，未进行CPU参考或完整检索集评测。
- 同图两次输出及重复文本输出逐字节一致，不代表跨设备或长期稳定性。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`002659be687de26fead6d991b6307a0553d34c27`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 图像编码平均耗时 | 193.428 ms | 同图两次session.run平均；384 × 384输入，包含传输，不含加载和预处理。 |
| 文本编码平均耗时 | 26.666 ms / 条 | 六条描述和首条重复，共七次单条调用；64 token固定输入。 |
| 匹配向量 | 1152 维 | 两编码器的第二路输出按官方示例取值，经L2归一化计算余弦分数。 |

适用范围：

- 本次为一张官方图片、六条英文描述的基本运行测试，未进行CPU参考或完整检索集评测。
- 同图两次输出及重复文本输出逐字节一致，不代表跨设备或长期稳定性。
- 本次使用16GB卡，真实8GB容量仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/inference_axmodel.py`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/python/inference_axmodel.py) | Python 程序 / 前后处理 |
| [`ax650/siglip_text_u16.axmodel`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/ax650/siglip_text_u16.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax650/siglip_vision_u16_fcu8.axmodel`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/ax650/siglip_vision_u16_fcu8.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/python/requirements.txt) | Python 依赖清单 |
| [`tokenizer/config.json`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/tokenizer/config.json) | 运行配置 |
| [`tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/tokenizer/preprocessor_config.json) | 运行配置 |
| [`tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/tokenizer/tokenizer_config.json) | 运行配置 |

仓库提交：`002659be687de26fead6d991b6307a0553d34c27`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/tree/002659be687de26fead6d991b6307a0553d34c27)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/tree/002659be687de26fead6d991b6307a0553d34c27)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/README.md)。
- [主要程序入口：python/inference_axmodel.py](https://huggingface.co/AXERA-TECH/siglip-so400m-patch14-384/blob/002659be687de26fead6d991b6307a0553d34c27/python/inference_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
