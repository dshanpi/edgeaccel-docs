---
title: "DEIMv2 部署指南"
sidebar_label: "DEIMv2"
description: "DEIMv2 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DEIMv2 部署指南

DEIMv2 用于目标检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/DEIMv2` 的固定版本。下面下载本页选用的 4 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/deimv2/3aac1231f17c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DEIMv2 \
  "README.md" \
  "axmodel_inf.py" \
  "deimv2_dinov3_s_coco.axmodel" \
  "people.jpg" \
  --revision 3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备推理例程

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境，再安装本例依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0' 'torch==2.5.1' 'torchvision==0.20.1'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程显式选择 `AXCLRTExecutionProvider`，使用本页固定提交中的前后处理代码，并将本次结果写入独立目录。

## 执行图片检测

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task deimv2 --variant official \
  --output results/official
```

输出目录需要尚不存在；再次运行时换一个目录名。每张图片运行三次，保存原始输入、检测图以及 `deployment-result.json` 中的候选框和调用耗时。

输入为 `people.jpg`，输出为 `input.png` 与 `output.png`。按固定版本模型卡的 `-ms n` 设置保持长宽比缩放、居中补黑边，再将 RGB 转为 0–1 浮点张量，不使用均值和标准差归一化。阈值为 0.4；图上显示官方后处理输出的类别编号。

打开结果图片，核对检测框是否落在目标上；再查看记录中的 `completed`、`repeatedDetectionsEqual` 和分数。重复结果一致仅说明本组输入可复现，不能代替漏检、误检和定位精度评估。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

画面可见 5 人，官方 -ms n 配置输出 7 个类别 0 候选框和 2 个类别 29 框；中央人物有重复框，另有大框覆盖多人区域。本次检测质量未通过，三次输出一致不能消除这些问题。

**people**

阈值 0.4，三次得到相同的 9 个候选框。图中可见 5 人；中央人物的两个框重叠 IoU 为 0.782，另有一个框横跨大部分人物区域。两个类别 29 框覆盖白色圆盘。这里只保留官方输出的类别编号，未计算有标注数据集的精度。

<div className="model-effect-gallery">

<figure>

[![官方输入 · people](../../../static/validation/effects/deimv2-20260927/input.webp)](../../../static/validation/effects/deimv2-20260927/input.webp)

<figcaption>官方输入 · people</figcaption>
</figure>

<figure>

[![本次检测结果 · people](../../../static/validation/effects/deimv2-20260927/output.webp)](../../../static/validation/effects/deimv2-20260927/output.webp)

<figcaption>本次检测结果 · people</figcaption>
</figure>

</div>

| 类别编号 | 候选框数 |
| --- | --- |
| 0 | 7 |
| 29 | 2 |

**使用时注意：**

- 只测试仓库内 1 张图片；重复运行一致性不等同于检测准确率，未计算 COCO mAP。 按官方 -ms n 步骤生成的结果包含重复与过大候选框，质量尚需复核。
- 仅在 RK3576 + AX8850 16GB 上验证；未测试 8GB、实时视频或长期运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel；AXCLRTExecutionProvider |
| NumPy / OpenCV / Pillow | 1.26.4 / 4.11.0.86 / 11.3.0 |
| Torch / Torchvision | 2.5.1 / 0.20.1 |
| RF-DETR bbox 后处理 | ONNX Runtime 1.20.1 / CPUExecutionProvider / intra-op 2、inter-op 1 |
| C++ 分割示例 | axcl-samples cbfa4c76891758983ca2b0c99c11d6621d59af39 / OpenCV 4.6.0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| deimv2_dinov3_s_coco.axmodel | 65.191 ms（3 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载、图像前处理与后处理，未剔除首轮。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`axmodel_inf.py`](https://huggingface.co/AXERA-TECH/DEIMv2/blob/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70/axmodel_inf.py) | Python 程序 / 前后处理 |
| [`deimv2_dinov3_s_coco.axmodel`](https://huggingface.co/AXERA-TECH/DEIMv2/blob/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70/deimv2_dinov3_s_coco.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/DEIMv2/blob/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70/config.json) | 运行配置 |

仓库提交：`3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DEIMv2/tree/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DEIMv2/tree/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DEIMv2/blob/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70/README.md)。
- [主要程序入口：axmodel_inf.py](https://huggingface.co/AXERA-TECH/DEIMv2/blob/3aac1231f17c1c8a61903ecf3f63e4c3ae6a9f70/axmodel_inf.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/DEIMv2)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
