---
title: "Gesture-axera 部署指南"
sidebar_label: "Gesture-axera"
description: "Gesture-axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Gesture-axera 部署指南

Gesture-axera 用于目标检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `AX650/ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel`。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页包含 **RK3576 DshanPi A1 + AX8850 16GB M.2** 与 **RK3576 DshanPi A1 + AX8850 8GB M.2** 的样例。按效果展示中的权重和容量对应使用，不同环境的结果不能互相替代。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Gesture-axera` 的固定版本。下面下载本页选用的 3 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/gesture-axera/6c0782a0a413
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Gesture-axera \
  "ax_ges_infer.py" \
  "AX650/ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel" \
  "ges_1280_720.jpg" \
  --revision 6c0782a0a413cd55bdca21e83801f3b8abce9264 \
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


按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 `.upstream` 备份；原表达式不匹配时停止，避免误改其他版本。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
edits = [
    {"path": "ax_ges_infer.py", "old": "ort.InferenceSession(opt.model)", "new": "ort.InferenceSession(opt.model, providers=[\"AXCLRTExecutionProvider\"])"}
]
for edit in edits:
    path = Path(edit.get("path", "ax_ges_infer.py"))
    source = path.read_text(encoding="utf-8")
    if edit["old"] not in source:
        assert edit["new"] in source, f"补丁目标不匹配：{path}"
        continue
    backup = path.with_name(path.name + ".upstream")
    if not backup.exists():
        backup.write_text(source, encoding="utf-8")
    path.write_text(source.replace(edit["old"], edit["new"]), encoding="utf-8")
    print(f"已修改 {path}")
PY
```

重新下载原始源码后，需要再次执行此修改。

## 运行模型

在模型根目录执行，输入与权重使用该提交的实际路径：

```bash
cd "$MODEL_DIR"
test -s AX650/ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel
test -s ges_1280_720.jpg
set -o pipefail
python ax_ges_infer.py --model AX650/ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel --img ges_1280_720.jpg 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `out.jpg` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`ax_ges_infer.py` 源码](https://huggingface.co/AXERA-TECH/Gesture-axera/blob/6c0782a0a413cd55bdca21e83801f3b8abce9264/ax_ges_infer.py)。

## 运行 NHWC 变体（可选）

默认步骤使用NCHW权重。下列NHWC变体需要配套的输入布局处理，不能只替换模型文件名。

### 准备例程

在RK3576主机激活前文安装的PyAXEngine环境。下载[NHWC视觉运行包](../../../static/examples/vision-nhwc-deployment-20261005.zip)，保存到 `~/edgeaccel`，然后解压：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m zipfile -e ~/edgeaccel/vision-nhwc-deployment-20261005.zip ~/edgeaccel
```

### 下载对应权重和样例

```bash
NHWC_MODELS=~/edgeaccel/models-nhwc
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Gesture-axera \
  --revision 6c0782a0a413cd55bdca21e83801f3b8abce9264 \
  --include "ax_ges_infer.py" "ges_1280_720.jpg" "AX650/ax_ax650_gesture_algo_ok_like_stop_rgb_nhwc_V1.0.0.axmodel" \
  --local-dir "$NHWC_MODELS/Gesture-axera"
```

### 运行并查看输出

```bash
python ~/edgeaccel/vision-nhwc/vision_nhwc.py \
  --models-root "$NHWC_MODELS" --case gesture \
  --output ~/edgeaccel/results/gesture-nhwc
```

每次使用尚不存在的结果目录。程序应显示 `AXCLRTExecutionProvider`；输出图或终端识别文字应与下方NHWC效果一致。运行包保留固定版本原始前后处理，实际使用的输入布局为NHWC。


## 查看部署效果

### NHWC：配套运行包

**固定样例已核对** · RK3576 DshanPi A1 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

1 个 NHWC 权重完成固定样例测试，每个权重独立运行三次，原始输出与效果图一致。下方展示本次输入、输出及样例范围。

**gesture · ax_ax650_gesture_algo_ok_like_stop_rgb_nhwc_V1.0.0.axmodel**

拼图中三个手势分别输出ok 0.936、like 0.910、stop 0.929，位置与手势一致。

<div className="model-effect-gallery">

<figure>

[![输入：ges_1280_720.jpg](../../../static/validation/effects/gesture-axera-nhwc-20261005/inputs/gesture.jpg)](../../../static/validation/effects/gesture-axera-nhwc-20261005/inputs/gesture.jpg)

<figcaption>输入：ges_1280_720.jpg</figcaption>
</figure>

<figure>

[![NHWC实际输出：gesture](../../../static/validation/effects/gesture-axera-nhwc-20261005/outputs/gesture.jpg)](../../../static/validation/effects/gesture-axera-nhwc-20261005/outputs/gesture.jpg)

<figcaption>NHWC实际输出：gesture</figcaption>
</figure>

</div>

**使用时注意：**

- 固定官方样例，未覆盖独立数据集精度、视频连续运行或长期稳定性。
- 本次使用16GB算力卡；不替代该NHWC权重在8GB卡上的实测。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### NCHW：原部署入口

**固定样例已核对** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

AXCL 后端完成三幅手势拼接图推理。输出 ok、like、stop 各 1 个框，置信度分别为 0.936、0.910、0.929；逐图对照可见的 OK 手势、竖拇指和张开手掌，标签及框位置一致。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/gesture-axera/inputs/ges_1280_720.jpg)](../../../static/validation/effects/gesture-axera/inputs/ges_1280_720.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/gesture-axera/outputs/out.jpg)](../../../static/validation/effects/gesture-axera/outputs/out.jpg)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 只核对仓库提供的一张三手势拼接图，未覆盖手掌旋转、遮挡、小目标或其他手势。
- 未计算分类准确率、漏检率或视频稳定性；三次置信度不作为性能或精度结论。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**NHWC：配套运行包**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 16GB M.2。模型版本：`6c0782a0a413cd55bdca21e83801f3b8abce9264`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 / 内核 | Ubuntu 24.04 / Armbian；aarch64；6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；总量 15232 MiB，空闲占用 18 MiB |
| Python 后端 | AXCLRTExecutionProvider；NumPy 1.26.4；OpenCV 4.11.0 |
| 输入与后处理 | 固定仓库原始样例；保留原始色序和后处理，按模型元数据转换 NHWC 布局 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| ax_ax650_gesture_algo_ok_like_stop_rgb_nhwc_V1.0.0.axmodel | 8.234 / 8.478 / 8.170 ms | 三次独立进程各一次session.run墙钟，含传输，不含加载和后处理；非预热平均性能。 |

适用范围：

- 仅三种固定手势的一张拼图，未测光照、运动与遮挡。

</details>

**NCHW：原部署入口**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`6c0782a0a413cd55bdca21e83801f3b8abce9264`。

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
| 输出目标数 | 3 个：ok、like、stop 各 1 个 | 本次 ges_1280_720.jpg 拼接图的类别与位置人工对照 |
| session.run：ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel | 9.596 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_ges_infer.py`](https://huggingface.co/AXERA-TECH/Gesture-axera/blob/6c0782a0a413cd55bdca21e83801f3b8abce9264/ax_ges_infer.py) | Python 程序 / 前后处理 |
| [`AX650/ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel`](https://huggingface.co/AXERA-TECH/Gesture-axera/blob/6c0782a0a413cd55bdca21e83801f3b8abce9264/AX650/ax_ax650_gesture_algo_ok_like_stop_V1.0.0.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ges_1280_720.jpg`](https://huggingface.co/AXERA-TECH/Gesture-axera/blob/6c0782a0a413cd55bdca21e83801f3b8abce9264/ges_1280_720.jpg) | 示例输入 |

仓库提交：`6c0782a0a413cd55bdca21e83801f3b8abce9264`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Gesture-axera/tree/6c0782a0a413cd55bdca21e83801f3b8abce9264)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 识别 ok、like、stop 三种手势；使用 256×448 输入及配套 anchors，不沿用普通 COCO 检测参数。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Gesture-axera/tree/6c0782a0a413cd55bdca21e83801f3b8abce9264)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Gesture-axera/blob/6c0782a0a413cd55bdca21e83801f3b8abce9264/README.md)。
- [主要程序入口：ax_ges_infer.py](https://huggingface.co/AXERA-TECH/Gesture-axera/blob/6c0782a0a413cd55bdca21e83801f3b8abce9264/ax_ges_infer.py)。

返回[完整模型目录](../catalog.mdx)。
