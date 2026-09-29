---
title: "siglip2-base-patch16-224 部署指南"
sidebar_label: "siglip2-base-patch16-224"
description: "siglip2-base-patch16-224 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# siglip2-base-patch16-224 部署指南

siglip2-base-patch16-224 用于图文相似度比较。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/siglip2-base-patch16-224` 的固定版本。下面下载本页选用的 10 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/siglip2-base-patch16-224/ad55e40ba57d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/siglip2-base-patch16-224 \
  "README.md" \
  "python/axmodel_infer.py" \
  "000000039769.jpg" \
  "ax650/siglip2-base-patch16-224_text.axmodel" \
  "ax650/siglip2-base-patch16-224_vision.axmodel" \
  "tokenizer/config.json" \
  "tokenizer/preprocessor_config.json" \
  "tokenizer/special_tokens_map.json" \
  "tokenizer/tokenizer.json" \
  "tokenizer/tokenizer_config.json" \
  --revision ad55e40ba57d930573b75d294d4b5aa452fa6a00 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

本例还需要以下前处理依赖：

```bash
python -m pip install 'torch==2.5.1' 'torchvision==0.20.1'
```

```bash
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4' 'sentencepiece==0.2.1' 'protobuf==4.25.8'
```

## 对比图片与两条描述

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task siglip2 --variant base224 \
  --output results/cats
```

输入为仓库自带的 `000000039769.jpg`，描述为 `a photo of 2 cats` 和 `a photo of 2 dogs`。例程从本地 `tokenizer/` 加载配套前处理文件，使用 `tokenizer.json` 对应的 fast tokenizer，将文本补齐或截断为编译模型要求的 64 token，不额外下载分词模型。

查看 `results/cats/deployment-result.json` 中的余弦相似度与 `sigmoidScore`。SigLIP 使用独立 sigmoid 匹配分数，两条描述的分数不要求相加等于 1，也不能当作已标定的识别准确率。


## 查看部署效果

**固定样例已核对** · 2026-09-24 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

配套图像与文本编码器均取得输出，对官方双猫图片比较 cats 与 dogs 两条描述。

**SigLIP2 base / patch16 / 224**

以下数值为真实图片与候选描述的匹配分数；不是准确率。 两项分数与同版本模型卡公布的 AX650 样例结果相差小于 1×10⁻⁸。cats 的绝对分数仅约 0.106，需根据业务数据确定阈值。

<div className="model-effect-gallery">

<figure>

[![官方图文匹配输入](../../../static/validation/effects/siglip2-base-patch16-224-20260924/siglip2-base224-fixed64/input.jpg)](../../../static/validation/effects/siglip2-base-patch16-224-20260924/siglip2-base224-fixed64/input.jpg)

<figcaption>官方图文匹配输入</figcaption>
</figure>

</div>

| 候选文本 | 余弦相似度 | 独立 sigmoid 分数 |
| --- | --- | --- |
| a photo of 2 cats | 0.129930 | 0.105968 |
| a photo of 2 dogs | 0.052817 | 0.000020 |

**使用时注意：**

- 只测试一张图片与两条英文描述；匹配分数不代表经过标定的分类准确率。
- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-24。模型版本：`ad55e40ba57d930573b75d294d4b5aa452fa6a00`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel；AXCLRTExecutionProvider |
| NumPy / OpenCV / Pillow | 1.26.4 / 4.11.0.86 / 11.3.0 |
| Torch / Torchvision | 2.5.1 / 0.20.1 |
| 图文前处理 | Transformers 4.51.3 / Tokenizers 0.21.4；ftfy 6.3.1 / regex 2025.9.18 |
| VAD SDK | silero-vad-axera 0.1.2，复用 SileroAx；权重来自页面固定仓库提交 |
| C++ 检测 | axcl-samples cbfa4c76891758983ca2b0c99c11d6621d59af39 / OpenCV 4.6.0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| siglip2-base224-fixed64 / siglip2-base-patch16-224_vision.axmodel | 20.092 ms（1 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |
| siglip2-base224-fixed64 / siglip2-base-patch16-224_text.axmodel | 6.913 ms（2 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |

适用范围：

- 只测试一张图片与两条英文描述；匹配分数不代表经过标定的分类准确率。
- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/axmodel_infer.py`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/python/axmodel_infer.py) | Python 程序 / 前后处理 |
| [`ax650/siglip2-base-patch16-224_text.axmodel`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/ax650/siglip2-base-patch16-224_text.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax650/siglip2-base-patch16-224_vision.axmodel`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/ax650/siglip2-base-patch16-224_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/config.json) | 运行配置 |
| [`python/onnx_infer.py`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/python/onnx_infer.py) | Python 程序 / 前后处理 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/python/requirements.txt) | Python 依赖清单 |
| [`tokenizer/config.json`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/tokenizer/config.json) | 运行配置 |
| [`tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/tokenizer/preprocessor_config.json) | 运行配置 |
| [`tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/tokenizer/tokenizer_config.json) | 运行配置 |

仓库提交：`ad55e40ba57d930573b75d294d4b5aa452fa6a00`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/tree/ad55e40ba57d930573b75d294d4b5aa452fa6a00)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/tree/ad55e40ba57d930573b75d294d4b5aa452fa6a00)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/README.md)。
- [主要程序入口：python/axmodel_infer.py](https://huggingface.co/AXERA-TECH/siglip2-base-patch16-224/blob/ad55e40ba57d930573b75d294d4b5aa452fa6a00/python/axmodel_infer.py)。

返回[完整模型目录](../catalog.mdx)。
