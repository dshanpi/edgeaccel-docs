---
title: "yolo26-pose 部署指南"
sidebar_label: "yolo26-pose"
description: "yolo26-pose 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# yolo26-pose 部署指南

yolo26-pose 用于人体姿态估计。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `ax650/yolo26n-pose_npu3.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页包含 **RK3576 DshanPi A1 + AX8850 16GB M.2** 与 **RK3576 DshanPi A1 + AX8850 8GB M.2** 的样例。按效果展示中的权重和容量对应使用，不同环境的结果不能互相替代。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/yolo26-pose` 的固定版本。下面下载本页选用的 12 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/yolo26-pose/48847027a8d7
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/yolo26-pose \
  "ax_infer.py" \
  "bus.jpg" \
  "ax650/yolo26l-pose_npu1.axmodel" \
  "ax650/yolo26l-pose_npu3.axmodel" \
  "ax650/yolo26m-pose_npu1.axmodel" \
  "ax650/yolo26m-pose_npu3.axmodel" \
  "ax650/yolo26n-pose_npu1.axmodel" \
  "ax650/yolo26s-pose_npu1.axmodel" \
  "ax650/yolo26s-pose_npu3.axmodel" \
  "ax650/yolo26x-pose_npu1.axmodel" \
  "ax650/yolo26x-pose_npu3.axmodel" \
  "ax650/yolo26n-pose_npu3.axmodel" \
  --revision 48847027a8d718f7586e2024a348555a89a79b80 \
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
test -s ax650/yolo26n-pose_npu3.axmodel
test -s bus.jpg
set -o pipefail
python ax_infer.py --model-path ax650/yolo26n-pose_npu3.axmodel --test-img bus.jpg --providers AXCLRTExecutionProvider 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `result_yolo26_pose.jpg` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`ax_infer.py` 源码](https://huggingface.co/AXERA-TECH/yolo26-pose/blob/48847027a8d718f7586e2024a348555a89a79b80/ax_infer.py)。

## 选择其他 AX650 权重

前面的下载命令包含本页实测的十个AX650权重。默认入口使用n规格NPU3；需要切换规模时，选择下表中的文件。`ax615/`、`ax630C/`、`ax637/`目录面向其他芯片，不用于本页AX8850算力卡。

| 权重（位于ax650目录） | 本组实测容量 |
| --- | --- |
| `yolo26l-pose_npu1.axmodel` | 16GB |
| `yolo26l-pose_npu3.axmodel` | 16GB |
| `yolo26m-pose_npu1.axmodel` | 16GB |
| `yolo26m-pose_npu3.axmodel` | 16GB |
| `yolo26n-pose_npu1.axmodel` | 16GB |
| `yolo26s-pose_npu1.axmodel` | 16GB |
| `yolo26s-pose_npu3.axmodel` | 16GB |
| `yolo26x-pose_npu1.axmodel` | 16GB |
| `yolo26x-pose_npu3.axmodel` | 16GB |

在同一模型目录执行，修改`WEIGHT`选择一个文件：

```bash
cd "$MODEL_DIR"
WEIGHT=ax650/yolo26l-pose_npu1.axmodel
OUT=~/edgeaccel/results/yolo26-pose
mkdir -p "$OUT"
python ax_infer.py --model-path "$WEIGHT" --test-img bus.jpg \
  --providers AXCLRTExecutionProvider \
  --img-save-path "$OUT/$(basename "$WEIGHT" .axmodel).jpg"
```

打开`OUT`目录中的输出图，与下方同规模、同NPU配置的实测结果对照。NPU1与NPU3是编译配置；不表示需要连接一张或三张算力卡。保持默认置信度阈值0.25和NMS阈值0.7，以便复现下方样例。


## 查看部署效果

### 其余9个AX650权重：16GB卡样例

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

9个AX650权重各独立运行两次，原始输出及效果图可重复。下方展示五种规模的姿态结果；同规模NPU1/NPU3输出图完全相同时合并展示。

**yolo26l · NPU1 / NPU3**

四个人物框覆盖画面中的行人，中央两人的骨架大体随四肢展开；左侧截断人物仅显示一个关键点，右侧人物骨架不完整。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![固定输入：bus.jpg](../../../static/validation/effects/yolo26-pose-variants-20261005/inputs/bus.jpg)](../../../static/validation/effects/yolo26-pose-variants-20261005/inputs/bus.jpg)

<figcaption>固定输入：bus.jpg</figcaption>
</figure>

<figure>

[![实际骨架输出：yolo26l](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26l.jpg)](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26l.jpg)

<figcaption>实际骨架输出：yolo26l</figcaption>
</figure>

</div>

| 权重 | 程序输出人物框数 | 从左到右各人物显示关键点数（最多17） |
| --- | --- | --- |
| yolo26l-pose_npu1.axmodel | 4 | 1 / 16 / 16 / 9 |
| yolo26l-pose_npu3.axmodel | 4 | 1 / 16 / 16 / 9 |

**yolo26m · NPU1 / NPU3**

四个人物框覆盖行人，中央两人的骨架大体对齐身体；最左侧截断人物未显示置信度超过0.5的关键点，右侧骨架不完整。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![实际骨架输出：yolo26m](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26m.jpg)](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26m.jpg)

<figcaption>实际骨架输出：yolo26m</figcaption>
</figure>

</div>

| 权重 | 程序输出人物框数 | 从左到右各人物显示关键点数（最多17） |
| --- | --- | --- |
| yolo26m-pose_npu1.axmodel | 4 | 0 / 16 / 16 / 9 |
| yolo26m-pose_npu3.axmodel | 4 | 0 / 16 / 16 / 9 |

**yolo26n · NPU1**

四个人物框均有输出，中央两人显示躯干与四肢关键点；左右边缘人物被画面截断，左侧仅显示少量关键点，右侧骨架不完整。

<div className="model-effect-gallery">

<figure>

[![实际骨架输出：yolo26n](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26n.jpg)](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26n.jpg)

<figcaption>实际骨架输出：yolo26n</figcaption>
</figure>

</div>

| 权重 | 程序输出人物框数 | 从左到右各人物显示关键点数（最多17） |
| --- | --- | --- |
| yolo26n-pose_npu1.axmodel | 4 | 1 / 16 / 16 / 6 |

**yolo26s · NPU1 / NPU3**

四个人物框均有输出，中央两人的面部与肢体关键点可见；左侧截断人物只有少量关键点，右侧人物只显示部分骨架。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![实际骨架输出：yolo26s](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26s.jpg)](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26s.jpg)

<figcaption>实际骨架输出：yolo26s</figcaption>
</figure>

</div>

| 权重 | 程序输出人物框数 | 从左到右各人物显示关键点数（最多17） |
| --- | --- | --- |
| yolo26s-pose_npu1.axmodel | 4 | 1 / 16 / 16 / 9 |
| yolo26s-pose_npu3.axmodel | 4 | 1 / 16 / 16 / 9 |

**yolo26x · NPU1 / NPU3**

中央两人的骨架大体随身体展开；左右边缘人物仍只有部分关键点。最左侧人物框明显向下延伸到路面，不能把较高置信度当作定位准确的证明。 NPU1与NPU3输出图的文件内容相同，因此合并展示。

<div className="model-effect-gallery">

<figure>

[![实际骨架输出：yolo26x](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26x.jpg)](../../../static/validation/effects/yolo26-pose-variants-20261005/outputs/yolo26x.jpg)

<figcaption>实际骨架输出：yolo26x</figcaption>
</figure>

</div>

| 权重 | 程序输出人物框数 | 从左到右各人物显示关键点数（最多17） |
| --- | --- | --- |
| yolo26x-pose_npu1.axmodel | 4 | 2 / 16 / 16 / 7 |
| yolo26x-pose_npu3.axmodel | 4 | 2 / 16 / 16 / 7 |

**使用时注意：**

- 固定单张街景图，左侧被截断人物的关键点很少或未显示，右侧被截断人物的骨架不完整；未用人工关键点标注计算OKS或姿态AP。
- 关键点置信度超过0.5时才绘制，显示点数不等于正确点数。本组使用16GB卡，不替代这些权重的8GB容量回归；AX615、AX630C与AX637目录面向其他芯片，不在本组AX8850验证范围。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### n · NPU3：8GB卡样例

**固定样例已核对** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

AXCL 后端完成 bus.jpg 姿态推理，输出 4 个人员框及关键点。中间两名完整可见行人的头部、肩部、躯干和下肢关键点落在相应人体部位，骨架随站姿和屈腿方向连接；两侧被画面截断的行人只显示部分关键点，未出现整图坐标偏移。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/yolo26-pose/inputs/bus.jpg)](../../../static/validation/effects/yolo26-pose/inputs/bus.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/yolo26-pose/outputs/result_yolo26_pose.jpg)](../../../static/validation/effects/yolo26-pose/outputs/result_yolo26_pose.jpg)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 仅作单图关键点位置与骨架连线的目视核对，未逐点标注或计算 OKS、PCK、左右关节误差。
- 两侧行人被截断，不能据此确认遮挡关节坐标正确；未覆盖动态动作和连续视频。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**其余9个AX650权重：16GB卡样例**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 16GB M.2。模型版本：`48847027a8d718f7586e2024a348555a89a79b80`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 / 内核 | Ubuntu 24.04 / Armbian；aarch64；6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；总量15232 MiB，空闲占用18 MiB |
| Python后端 | AXCLRTExecutionProvider；NumPy 1.26.4；OpenCV 4.11.0 |
| 前后处理 | 固定版本原始ax_infer.py，RGB uint8输入，置信度阈值0.25、NMS阈值0.7，640×640 NHWC输入，关键点绘制阈值0.5 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| yolo26l-pose_npu1.axmodel | 60.207 / 58.990 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26l-pose_npu3.axmodel | 37.466 / 36.991 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26m-pose_npu1.axmodel | 51.833 / 52.456 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26m-pose_npu3.axmodel | 34.324 / 34.228 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26n-pose_npu1.axmodel | 28.141 / 28.659 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26s-pose_npu1.axmodel | 31.659 / 35.152 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26s-pose_npu3.axmodel | 28.587 / 27.798 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26x-pose_npu1.axmodel | 100.896 / 99.363 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |
| yolo26x-pose_npu3.axmodel | 53.674 / 49.785 ms | 两个独立进程各一次session.run墙钟；含传输，不含加载、输出存盘和后处理，无预热，不代表持续吞吐。 |

</details>

**n · NPU3：8GB卡样例**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`48847027a8d718f7586e2024a348555a89a79b80`。

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
| 输出人员数 | 4 人 | 本次 bus.jpg 日志计数；重点对照中间两名完整可见行人的姿态 |
| session.run：yolo26n-pose_npu3.axmodel | 26.086 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_infer.py`](https://huggingface.co/AXERA-TECH/yolo26-pose/blob/48847027a8d718f7586e2024a348555a89a79b80/ax_infer.py) | Python 程序 / 前后处理 |
| [`ax650/yolo26n-pose_npu3.axmodel`](https://huggingface.co/AXERA-TECH/yolo26-pose/blob/48847027a8d718f7586e2024a348555a89a79b80/ax650/yolo26n-pose_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`bus.jpg`](https://huggingface.co/AXERA-TECH/yolo26-pose/blob/48847027a8d718f7586e2024a348555a89a79b80/bus.jpg) | 示例输入 |

仓库提交：`48847027a8d718f7586e2024a348555a89a79b80`。仓库中的 20 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/yolo26-pose/tree/48847027a8d718f7586e2024a348555a89a79b80)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 模型卡的 ax_infer_pose.py 与此提交实际文件名不同；文件表和源码入口是 ax_infer.py，本页使用实际文件名。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/yolo26-pose/tree/48847027a8d718f7586e2024a348555a89a79b80)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/yolo26-pose/blob/48847027a8d718f7586e2024a348555a89a79b80/README.md)。
- [主要程序入口：ax_infer.py](https://huggingface.co/AXERA-TECH/yolo26-pose/blob/48847027a8d718f7586e2024a348555a89a79b80/ax_infer.py)。

返回[完整模型目录](../catalog.mdx)。
