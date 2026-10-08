---
title: "YOLOv8-Seg 部署指南"
sidebar_label: "YOLOv8-Seg"
description: "YOLOv8-Seg 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# YOLOv8-Seg 部署指南

YOLOv8-Seg 用于图像分割。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `AX650/yolov8n-seg_640x640_npu3.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页包含 **RK3576 DshanPi A1 + AX8850 16GB M.2** 与 **RK3576 DshanPi A1 + AX8850 8GB M.2** 的样例。按效果展示中的权重和容量对应使用，不同环境的结果不能互相替代。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/YOLOv8-Seg` 的固定版本。下面下载本页选用的 12 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/yolov8-seg/c53ebcbf84d7
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/YOLOv8-Seg \
  "ax_infer.py" \
  "bus.jpg" \
  "AX650/yolov8l-seg_640x640_npu1.axmodel" \
  "AX650/yolov8l-seg_640x640_npu3.axmodel" \
  "AX650/yolov8m-seg_640x640_npu1.axmodel" \
  "AX650/yolov8m-seg_640x640_npu3.axmodel" \
  "AX650/yolov8n-seg_640x640_npu1.axmodel" \
  "AX650/yolov8s-seg_640x640_npu1.axmodel" \
  "AX650/yolov8s-seg_640x640_npu3.axmodel" \
  "AX650/yolov8x-seg_640x640_npu1.axmodel" \
  "AX650/yolov8x-seg_640x640_npu3.axmodel" \
  "AX650/yolov8n-seg_640x640_npu3.axmodel" \
  --revision c53ebcbf84d783488a878fa462d3b3f28f3b858d \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 配置 Python 后端

激活已安装 PyAXEngine 的主机虚拟环境。先检查可用 provider：

```bash
source ~/edgeaccel/python-env/bin/activate
python -c "import axengine; print(axengine.get_available_providers())"
```

必须包含 `AXCLRTExecutionProvider`。保留已安装的 PyAXEngine，按下面命令安装本例依赖。

在已激活的环境中安装该入口直接使用的依赖；以下依赖用于本页的命令行示例：

```bash
python -m pip install numpy==1.26.4 ml-dtypes==0.5.3 opencv-python-headless==4.11.0.86
```


该脚本支持 `--providers`，下面的命令已显式选择 AXCL。

## 运行模型

在模型根目录执行，输入与权重使用该提交的实际路径：

```bash
cd "$MODEL_DIR"
test -s AX650/yolov8n-seg_640x640_npu3.axmodel
test -s bus.jpg
set -o pipefail
python ax_infer.py --model-path AX650/yolov8n-seg_640x640_npu3.axmodel --test-img bus.jpg --providers AXCLRTExecutionProvider 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `result_yolov8_seg.jpg` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`ax_infer.py` 源码](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/blob/c53ebcbf84d783488a878fa462d3b3f28f3b858d/ax_infer.py)。

## 选择其他 AX650 权重

前面的下载命令包含本页实测的十个AX650权重。默认入口使用n规格NPU3；需要切换规模时，选择下表中的文件。仓库内其他芯片目录面向对应芯片，不用于本页AX8850算力卡。

| 权重（位于AX650目录） | 本组实测容量 |
| --- | --- |
| `yolov8l-seg_640x640_npu1.axmodel` | 16GB |
| `yolov8l-seg_640x640_npu3.axmodel` | 16GB |
| `yolov8m-seg_640x640_npu1.axmodel` | 16GB |
| `yolov8m-seg_640x640_npu3.axmodel` | 16GB |
| `yolov8n-seg_640x640_npu1.axmodel` | 16GB |
| `yolov8s-seg_640x640_npu1.axmodel` | 16GB |
| `yolov8s-seg_640x640_npu3.axmodel` | 16GB |
| `yolov8x-seg_640x640_npu1.axmodel` | 16GB |
| `yolov8x-seg_640x640_npu3.axmodel` | 16GB |

在同一模型目录执行，修改`WEIGHT`选择一个文件：

```bash
cd "$MODEL_DIR"
WEIGHT=AX650/yolov8l-seg_640x640_npu1.axmodel
OUT=~/edgeaccel/results/yolov8-seg
mkdir -p "$OUT"
python ax_infer.py --model-path "$WEIGHT" --test-img bus.jpg \
  --providers AXCLRTExecutionProvider \
  --img-save-path "$OUT/$(basename "$WEIGHT" .axmodel).jpg"
```

打开`OUT`目录中的输出图，与下方同规模、同NPU配置的实测结果对照。NPU1与NPU3是编译配置；不表示需要连接一张或三张算力卡。保持默认置信度阈值0.25和NMS阈值0.7，以便复现下方样例。


## 查看部署效果

### 其余9个AX650权重：16GB卡样例

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

9个AX650权重各独立运行两次，原始输出及效果图可重复。下方展示五种规模的实例分割结果；同规模NPU1/NPU3输出图完全相同时合并展示。

**yolov8l · NPU1 / NPU3**

公交车和人物区域均有掩码输出，左侧截断人物出现两个重叠实例，其中一个框延伸到路面；边界有偏差，未做像素标注精度评估。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![固定输入：bus.jpg](../../../static/validation/effects/yolov8-seg-variants-20261005/inputs/bus.jpg)](../../../static/validation/effects/yolov8-seg-variants-20261005/inputs/bus.jpg)

<figcaption>固定输入：bus.jpg</figcaption>
</figure>

<figure>

[![实际实例分割输出：yolov8l](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8l.jpg)](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8l.jpg)

<figcaption>实际实例分割输出：yolov8l</figcaption>
</figure>

</div>

| 权重 | 程序输出实例总数 | 各类别实例数 |
| --- | --- | --- |
| yolov8l-seg_640x640_npu1.axmodel | 6 | person: 5；bus: 1 |
| yolov8l-seg_640x640_npu3.axmodel | 6 | person: 5；bus: 1 |

**yolov8m · NPU1 / NPU3**

公交车及四个人物有掩码输出；中央左侧人物领口附近额外标出tie，原图不能确认存在领带，应视为疑似误检，不能按实例总数推断准确率。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![实际实例分割输出：yolov8m](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8m.jpg)](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8m.jpg)

<figcaption>实际实例分割输出：yolov8m</figcaption>
</figure>

</div>

| 权重 | 程序输出实例总数 | 各类别实例数 |
| --- | --- | --- |
| yolov8m-seg_640x640_npu1.axmodel | 6 | person: 4；bus: 1；tie: 1 |
| yolov8m-seg_640x640_npu3.axmodel | 6 | person: 4；bus: 1；tie: 1 |

**yolov8n · NPU1**

公交车与四个人物均有实例掩码；人物与车身交界和轮胎附近仍有边界偏差，单张图片未验证分割精度。

<div className="model-effect-gallery">

<figure>

[![实际实例分割输出：yolov8n](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8n.jpg)](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8n.jpg)

<figcaption>实际实例分割输出：yolov8n</figcaption>
</figure>

</div>

| 权重 | 程序输出实例总数 | 各类别实例数 |
| --- | --- | --- |
| yolov8n-seg_640x640_npu1.axmodel | 5 | person: 4；bus: 1 |

**yolov8s · NPU1 / NPU3**

公交车与四个人物有掩码输出；中央右侧人物领口额外标出tie，原图不能确认存在领带，保留为疑似误检；掩码边界也有偏差。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![实际实例分割输出：yolov8s](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8s.jpg)](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8s.jpg)

<figcaption>实际实例分割输出：yolov8s</figcaption>
</figure>

</div>

| 权重 | 程序输出实例总数 | 各类别实例数 |
| --- | --- | --- |
| yolov8s-seg_640x640_npu1.axmodel | 6 | person: 4；bus: 1；tie: 1 |
| yolov8s-seg_640x640_npu3.axmodel | 6 | person: 4；bus: 1；tie: 1 |

**yolov8x · NPU1 / NPU3**

公交车与人物掩码均可见；左侧截断人物出现两个重叠实例和延伸至路面的框，中央左侧人物领口另有疑似领带误检。未做人工像素标注精度评估。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![实际实例分割输出：yolov8x](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8x.jpg)](../../../static/validation/effects/yolov8-seg-variants-20261005/outputs/yolov8x.jpg)

<figcaption>实际实例分割输出：yolov8x</figcaption>
</figure>

</div>

| 权重 | 程序输出实例总数 | 各类别实例数 |
| --- | --- | --- |
| yolov8x-seg_640x640_npu1.axmodel | 7 | person: 5；bus: 1；tie: 1 |
| yolov8x-seg_640x640_npu3.axmodel | 7 | person: 5；bus: 1；tie: 1 |

**使用时注意：**

- 固定单张街景图，部分规模在左侧截断人物处输出重复实例，个别框延伸到路面；m/s/x规格在领口附近有疑似领带误检，掩码边界仍有偏差，未用人工像素标注计算IoU或掩码AP。
- 程序输出实例数不等于真实目标数。本组使用16GB卡，不替代这些权重的8GB容量回归；仓库内其他芯片目录面向对应芯片，不在本组AX8850验证范围。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### n · NPU3：8GB卡样例

**固定样例已核对** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

bus.jpg 输出 1 个公交车与 4 个人物实例；公交车与主要行人的掩码覆盖对应物体区域，完成单样本实例分割核对。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/yolov8-seg/inputs/bus.jpg)](../../../static/validation/effects/yolov8-seg/inputs/bus.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/yolov8-seg/outputs/result_yolov8_seg.jpg)](../../../static/validation/effects/yolov8-seg/outputs/result_yolov8_seg.jpg)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 局部人物边缘、遮挡和公交车与行人重叠区域只能定性核对；没有像素真值，不能报告 IoU 或 mAP。
- 仅一个样例、一次程序启动；没有独立数据集精度评测或长时间稳定性测试。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**其余9个AX650权重：16GB卡样例**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 16GB M.2。模型版本：`c53ebcbf84d783488a878fa462d3b3f28f3b858d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 / 内核 | Ubuntu 24.04 / Armbian；aarch64；6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；总量15232 MiB，空闲占用18 MiB |
| Python后端 | AXCLRTExecutionProvider；NumPy 1.26.4；OpenCV 4.11.0 |
| 前后处理 | 固定版本原始ax_infer.py，RGB uint8输入，置信度阈值0.25、NMS阈值0.7，640×640 NHWC输入，原始process_mask阈值0.5 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| yolov8l-seg_640x640_npu1.axmodel | 119.943 / 126.452 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8l-seg_640x640_npu3.axmodel | 77.266 / 83.615 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8m-seg_640x640_npu1.axmodel | 89.827 / 94.830 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8m-seg_640x640_npu3.axmodel | 71.571 / 72.093 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8n-seg_640x640_npu1.axmodel | 60.299 / 65.243 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8s-seg_640x640_npu1.axmodel | 71.551 / 74.497 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8s-seg_640x640_npu3.axmodel | 65.004 / 59.539 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8x-seg_640x640_npu1.axmodel | 170.611 / 168.345 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolov8x-seg_640x640_npu3.axmodel | 91.133 / 91.496 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |

</details>

**n · NPU3：8GB卡样例**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`c53ebcbf84d783488a878fa462d3b3f28f3b858d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| C++ 视觉示例提交 | cbfa4c76891758983ca2b0c99c11d6621d59af39 |
| Python 后端 | Python 3.12.3；PyAXEngine 0.1.3.rc3 发布的 0.1.3 wheel；NumPy 1.26.4 / ml-dtypes 0.5.3 |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| session.run：yolov8n-seg_640x640_npu3.axmodel | 57.666 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 只采集到 1 次 session.run 调用，不能视为预热后的平均性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_infer.py`](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/blob/c53ebcbf84d783488a878fa462d3b3f28f3b858d/ax_infer.py) | Python 程序 / 前后处理 |
| [`AX650/yolov8n-seg_640x640_npu3.axmodel`](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/blob/c53ebcbf84d783488a878fa462d3b3f28f3b858d/AX650/yolov8n-seg_640x640_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`bus.jpg`](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/blob/c53ebcbf84d783488a878fa462d3b3f28f3b858d/bus.jpg) | 示例输入 |

仓库提交：`c53ebcbf84d783488a878fa462d3b3f28f3b858d`。仓库中的 31 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/tree/c53ebcbf84d783488a878fa462d3b3f28f3b858d)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/tree/c53ebcbf84d783488a878fa462d3b3f28f3b858d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/blob/c53ebcbf84d783488a878fa462d3b3f28f3b858d/README.md)。
- [主要程序入口：ax_infer.py](https://huggingface.co/AXERA-TECH/YOLOv8-Seg/blob/c53ebcbf84d783488a878fa462d3b3f28f3b858d/ax_infer.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/YOLOv8-Seg)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
