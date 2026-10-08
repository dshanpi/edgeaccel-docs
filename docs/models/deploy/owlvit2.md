---
title: "OWLViT2 部署指南"
sidebar_label: "OWLViT2"
description: "OWLViT2 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# OWLViT2 部署指南

OWLViT2 用于开放词汇检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/OWLViT2` 的固定版本。下面下载本页选用的 14 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/owlvit2/c8eab07c1762
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/OWLViT2 \
  "4cls_labels.json" \
  "HOW_TO_USE.md" \
  "README.md" \
  "axmodel/owlv2_image_4cls_640.axmodel" \
  "axmodel/owlv2_post_4cls_640.axmodel" \
  "axmodel/owlv2_text_4cls_640.axmodel" \
  "run_split_owlv2_full_demo.py" \
  "run_split_owlv2_full_demo_ax.py" \
  "split_4cls/owlv2_image_4cls.onnx" \
  "split_4cls/owlv2_post_4cls.onnx" \
  "split_4cls/owlv2_text_4cls.onnx" \
  "test_img/000000039769.jpg" \
  "test_img/ssd_horse.jpg" \
  "test_img/test.jpg" \
  --revision c8eab07c17622318cbd1f6234bb261c4eace2c51 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备开放词汇检测环境

本例在 RK3576 + AX8850 16GB M.2 上运行 OWLViT2 的图像编码、文本编码和匹配头，使用官方三张图片查询“人、车、猫、狗”。主机同时运行配套 CPU ONNX 参考，便于对照输出框和分数。

在已安装 PyAXEngine 的 Python 环境执行：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'Pillow==11.3.0' 'onnxruntime==1.20.1'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认包含 `AXCLRTExecutionProvider`，设备 0 可用。前面下载清单中的 `axmodel` 是算力卡权重，`split_4cls` 是主机参考权重；本例会使用两者。

## 下载固定版本处理器

保留前面下载步骤中的 `MODEL_DIR`。从上游模型仓库下载图像处理与分词配置：

```bash
PROCESSOR_DIR=~/edgeaccel/processors/owlv2-d69b086b
mkdir -p "$PROCESSOR_DIR"
~/edgeaccel/hf-env/bin/hf download google/owlv2-base-patch16-finetuned \
  config.json merges.txt preprocessor_config.json special_tokens_map.json \
  tokenizer_config.json vocab.json \
  --revision d69b086b07123308a4e198343ab2824e1af7774a \
  --local-dir "$PROCESSOR_DIR"
```

下载 [OWLViT2 算力卡示例](../../../static/examples/owlvit2_card.py)，保存为 `~/edgeaccel/owlvit2_card.py`。程序使用本地处理器，检查官方推理源码的版本，并明确区分 AXCL 与 CPU 后端。

## 运行三张官方图片

```bash
python ~/edgeaccel/owlvit2_card.py \
  --model-dir "$MODEL_DIR" --processor-dir "$PROCESSOR_DIR" \
  --output ~/edgeaccel/results/owlvit2-01
```

输出目录须尚不存在。程序按 `4cls_labels.json` 中的四条英文查询运行三段模型，每张图片重复两次算力卡推理，并运行一次 CPU 参考。

| 输出 | 查看内容 |
| --- | --- |
| `deployment-result.json` | `completed: true`、检测框、类别、分数、重复一致性、参考差值与耗时 |
| `sampleN-input.png` | 第 N 张实际输入 |
| `sampleN-card.png` / `sampleN-cpu.png` | 算力卡与 CPU 参考的完整结果图 |
| `sampleN-raw.npz` | 前处理输入、原始框、分数、objectness 和重复输出 |
| `text-vectors.npz` | 四条查询的文本向量及 token |

图像输入为 640 × 640。前处理、阈值 0.1、类别内 NMS 阈值 0.45、每类最多 20 个框均沿用官方示例；不额外乘 objectness，也不隐藏低分框。

## 替换输入图片

通过 `--image` 指定图片，可重复该参数处理多张图片。示例仍同时生成算力卡与 CPU 结果：

```bash
python ~/edgeaccel/owlvit2_card.py \
  --model-dir "$MODEL_DIR" --processor-dir "$PROCESSOR_DIR" \
  --image ~/edgeaccel/inputs/photo.jpg \
  --output ~/edgeaccel/results/owlvit2-custom-01
```

当前权重固定为四条文本查询，本次只验证官方“人、车、猫、狗”组合。更换词汇需要保持数量、分词长度及模型输入规格，并重新核对效果；图片中的物体若不在查询集合中，不以未返回该类别判定漏检。

## 对照实际检测结果

下方保留全部三组输入及两种后端的结果。当前低阈值下存在重复框、局部框和背景候选，图中的框数不是物体数量。算力卡与 CPU 参考的数值接近，也不能代替有标注数据集的 mAP 评估。

原始分数不裁剪，CPU 浮点运算可能出现接近零的微小负值。检测筛选仍按固定阈值执行。分阶段耗时仅统计对应 `session.run`，包含传输，不含模型加载、前后处理、文件保存，也不把 CPU 参考时间算作算力卡推理时间。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

三张图均完成 AXCL 与 CPU ONNX 对照。猫图按 COCO 标注核对：两只猫对应 4 个猫框和 1 个狗框；IoU≥0.5 时两种后端均为 2 个匹配、3 个误检，当前固定样例的类别与框质量检查未通过。

**三组检测结果统计**

查询固定为人、车、猫、狗。每图算力卡重复两次，图像输出和匹配分数逐字节一致；CPU参考每图一次。分数差以全部原始位置与类别计算，框差以归一化坐标计算。

| 输入图片 | 算力卡 / CPU 框数 | 分数平均绝对差 | 分数最大绝对差 | 归一化框平均绝对差 |
| --- | --- | --- | --- | --- |
| 000000039769.jpg | 5 / 5 | 0.000304 | 0.057090 | 0.013702 |
| ssd_horse.jpg | 24 / 24 | 0.000225 | 0.054061 | 0.009822 |
| test.jpg | 18 / 17 | 0.000243 | 0.083819 | 0.012605 |

**000000039769.jpg：输入与检测框**

原图与 COCO val2017 的 000000039769.jpg 文件及像素一致，查询类别范围内有两只猫的标注。两种后端均返回 4 个猫框和 1 个狗框；部分猫框覆盖身体局部，狗框与一个猫框重合。保留阈值 0.1、类别内 NMS 0.45 的全部输出。按分数从高到低做同类一对一匹配，IoU≥0.5 时均有 2 个匹配、3 个误检；IoU≥0.75 时均无匹配。这里是单图检查，不是 mAP 或完整数据集精度。 仅统计本次查询的人、车、猫、狗；图中遥控器等未查询类别不计为漏检。标注来源为 [COCO 官方下载页](https://cocodataset.org/#download) 的 val2017 实例标注。

<div className="model-effect-gallery">

<figure>

[![000000039769.jpg · 实际输入](../../../static/validation/effects/owlvit2-20260928/sample1-input.png)](../../../static/validation/effects/owlvit2-20260928/sample1-input.png)

<figcaption>000000039769.jpg · 实际输入</figcaption>
</figure>

<figure>

[![000000039769.jpg · 算力卡完整输出](../../../static/validation/effects/owlvit2-20260928/sample1-card.png)](../../../static/validation/effects/owlvit2-20260928/sample1-card.png)

<figcaption>000000039769.jpg · 算力卡完整输出</figcaption>
</figure>

<figure>

[![000000039769.jpg · CPU ONNX 完整参考](../../../static/validation/effects/owlvit2-20260928/sample1-cpu.png)](../../../static/validation/effects/owlvit2-20260928/sample1-cpu.png)

<figcaption>000000039769.jpg · CPU ONNX 完整参考</figcaption>
</figure>

<figure>

[![COCO 两个猫标注与本次完整检测结果对照](../../../static/validation/effects/owlvit2-20260928/owlvit2-coco-comparison.png)](../../../static/validation/effects/owlvit2-20260928/owlvit2-coco-comparison.png)

<figcaption>COCO 两个猫标注与本次完整检测结果对照</figcaption>
</figure>

</div>

| 后端 | 匹配 IoU | 匹配 TP | 误检 FP | 未匹配标注 FN |
| --- | --- | --- | --- | --- |
| AXCL | 0.5 | 2 | 3 | 0 |
| AXCL | 0.75 | 0 | 5 | 2 |
| CPU ONNX | 0.5 | 2 | 3 | 0 |
| CPU ONNX | 0.75 | 0 | 5 | 2 |

| AXCL 框类别 | 分数 | 与同类标注的最大 IoU |
| --- | --- | --- |
| 猫 | 0.577765 | 0.504460 |
| 猫 | 0.511989 | 0.644351 |
| 猫 | 0.358931 | 0.195834 |
| 猫 | 0.175782 | 0.272218 |
| 狗 | 0.114711 | 无狗类标注 |

**ssd_horse.jpg：输入与检测框**

人、车辆及狗的位置有对应候选，右侧背景仍存在密集低分人类框。马不在本次四类查询中。 阈值0.1、类别内NMS 0.45，保留全部输出框。

<div className="model-effect-gallery">

<figure>

[![ssd_horse.jpg · 实际输入](../../../static/validation/effects/owlvit2-20260928/sample2-input.png)](../../../static/validation/effects/owlvit2-20260928/sample2-input.png)

<figcaption>ssd_horse.jpg · 实际输入</figcaption>
</figure>

<figure>

[![ssd_horse.jpg · 算力卡完整输出](../../../static/validation/effects/owlvit2-20260928/sample2-card.png)](../../../static/validation/effects/owlvit2-20260928/sample2-card.png)

<figcaption>ssd_horse.jpg · 算力卡完整输出</figcaption>
</figure>

<figure>

[![ssd_horse.jpg · CPU ONNX 完整参考](../../../static/validation/effects/owlvit2-20260928/sample2-cpu.png)](../../../static/validation/effects/owlvit2-20260928/sample2-cpu.png)

<figcaption>ssd_horse.jpg · CPU ONNX 完整参考</figcaption>
</figure>

</div>

**test.jpg：输入与检测框**

人物区域返回多个重叠或局部框；算力卡18框、CPU参考17框，边界与筛选结果存在差异。 阈值0.1、类别内NMS 0.45，保留全部输出框。

<div className="model-effect-gallery">

<figure>

[![test.jpg · 实际输入](../../../static/validation/effects/owlvit2-20260928/sample3-input.png)](../../../static/validation/effects/owlvit2-20260928/sample3-input.png)

<figcaption>test.jpg · 实际输入</figcaption>
</figure>

<figure>

[![test.jpg · 算力卡完整输出](../../../static/validation/effects/owlvit2-20260928/sample3-card.png)](../../../static/validation/effects/owlvit2-20260928/sample3-card.png)

<figcaption>test.jpg · 算力卡完整输出</figcaption>
</figure>

<figure>

[![test.jpg · CPU ONNX 完整参考](../../../static/validation/effects/owlvit2-20260928/sample3-cpu.png)](../../../static/validation/effects/owlvit2-20260928/sample3-cpu.png)

<figcaption>test.jpg · CPU ONNX 完整参考</figcaption>
</figure>

</div>

**使用时注意：**

- 低阈值下存在局部框、重复框和背景候选；只证明基本运行，未判定检测精度通过。
- CPU参考最低分约-5.96e-8，原始值完整保留；算力卡分数在0～1内，没有通过裁剪隐藏差异。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`c8eab07c17622318cbd1f6234bb261c4eace2c51`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 图像编码平均耗时 | 239.175 ms | 共6次session.run，包含传输，不含加载、前后处理、保存和CPU参考。 |
| 文本编码平均耗时 | 6.183 ms | 共2次session.run，包含传输，不含加载、前后处理、保存和CPU参考。 |
| 匹配头平均耗时 | 54.524 ms | 共6次session.run，包含传输，不含加载、前后处理、保存和CPU参考。 |

适用范围：

- 只测试固定四类和静态图片；真实8GB容量、其他词汇、视频及长期运行仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_split_owlv2_full_demo.py`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/run_split_owlv2_full_demo.py) | Python 程序 / 前后处理 |
| [`run_split_owlv2_full_demo_ax.py`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/run_split_owlv2_full_demo_ax.py) | Python 程序 / 前后处理 |
| [`axmodel/owlv2_image_4cls_640.axmodel`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/axmodel/owlv2_image_4cls_640.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodel/owlv2_post_4cls_640.axmodel`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/axmodel/owlv2_post_4cls_640.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodel/owlv2_text_4cls_640.axmodel`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/axmodel/owlv2_text_4cls_640.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`4cls_labels.json`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/4cls_labels.json) | 配套资源 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/requirements.txt) | Python 依赖清单 |
| [`test_img/test.jpg`](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/test_img/test.jpg) | 示例输入 |

仓库提交：`c8eab07c17622318cbd1f6234bb261c4eace2c51`。仓库中的 3 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/OWLViT2/tree/c8eab07c17622318cbd1f6234bb261c4eace2c51)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/OWLViT2/tree/c8eab07c17622318cbd1f6234bb261c4eace2c51)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/README.md)。
- [主要程序入口：run_split_owlv2_full_demo.py](https://huggingface.co/AXERA-TECH/OWLViT2/blob/c8eab07c17622318cbd1f6234bb261c4eace2c51/run_split_owlv2_full_demo.py)。

返回[完整模型目录](../catalog.mdx)。
