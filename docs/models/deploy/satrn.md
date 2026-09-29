---
title: "satrn 部署指南"
sidebar_label: "satrn"
description: "satrn 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# satrn 部署指南

satrn 用于英文文字识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/satrn` 的固定版本。下面下载本页选用的 7 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/satrn/5566540345a8
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/satrn \
  "README.md" \
  "axmodel/backbone_encoder.axmodel" \
  "axmodel/decoder.axmodel" \
  "run_axmodel.py" \
  "onboard_run_axmodel.py" \
  "run_model.py" \
  "demo_text_recog.jpg" \
  --revision 5566540345a83859cff8972526e154d3cbdc844b \
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

## 识别单张文字裁剪图

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task satrn --variant word \
  --output results/word
```

输入为 `demo_text_recog.jpg`。例程将文字图缩放到 100×32，先运行 backbone/encoder，再逐字符运行 decoder，遇到结束标记停止，最多生成 25 个字符。

查看 `results/word/deployment-result.json` 中的 `text`，并与 `input.png` 核对。本页只运行文字识别；整张文档还需要文字检测、裁剪和阅读顺序处理。

字典和前处理依据：[MMOCR v1.0.1 SATRN 配置](https://github.com/open-mmlab/mmocr/blob/v1.0.1/configs/textrecog/satrn/_base_satrn_shallow.py)、[90 字符字典](https://github.com/open-mmlab/mmocr/blob/v1.0.1/dicts/english_digits_symbols.txt)。该字典不包含中文。


## 查看部署效果

**固定样例已核对** · 2026-09-24 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

官方文字图片识别结果为 STAR，与图片中的四个字母一致。

**英文文字识别**

图片中的文字为 STAR，模型实际返回 STAR；随后输出结束标记。编码器运行 1 次，解码器运行 5 次。

<div className="model-effect-gallery">

<figure>

[![输入文字裁剪图](../../../static/validation/effects/satrn-20260924/satrn-word/input.webp)](../../../static/validation/effects/satrn-20260924/satrn-word/input.webp)

<figcaption>输入文字裁剪图</figcaption>
</figure>

</div>

| 图片文字 | 实际输出 | 字符核对 |
| --- | --- | --- |
| STAR | STAR | 4 / 4 一致 |

**使用时注意：**

- 只核对一个英文裁剪词；不包含整页文字检测、中文、多行或完整 OCR 数据集评测。
- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-24。模型版本：`5566540345a83859cff8972526e154d3cbdc844b`。

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
| satrn-word / backbone_encoder.axmodel | 16.305 ms（1 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |
| satrn-word / decoder.axmodel | 9.776 ms（5 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |

适用范围：

- 只核对一个英文裁剪词；不包含整页文字检测、中文、多行或完整 OCR 数据集评测。
- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`axmodel/backbone_encoder.axmodel`](https://huggingface.co/AXERA-TECH/satrn/blob/5566540345a83859cff8972526e154d3cbdc844b/axmodel/backbone_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodel/decoder.axmodel`](https://huggingface.co/AXERA-TECH/satrn/blob/5566540345a83859cff8972526e154d3cbdc844b/axmodel/decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/satrn/blob/5566540345a83859cff8972526e154d3cbdc844b/config.json) | 运行配置 |

仓库提交：`5566540345a83859cff8972526e154d3cbdc844b`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/satrn/tree/5566540345a83859cff8972526e154d3cbdc844b)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/satrn/tree/5566540345a83859cff8972526e154d3cbdc844b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/satrn/blob/5566540345a83859cff8972526e154d3cbdc844b/README.md)。

返回[完整模型目录](../catalog.mdx)。
