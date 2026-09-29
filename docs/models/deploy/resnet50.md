---
title: "resnet50 部署指南"
sidebar_label: "resnet50"
description: "resnet50 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# resnet50 部署指南

resnet50 用于图像分类。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/resnet50` 的固定版本。下面下载本页选用的 7 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/resnet50/e36200659c15
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/resnet50 \
  "models/model.axmodel" \
  "models/model_meta.json" \
  "python/example.py" \
  "python/resnet50_sdk/__init__.py" \
  "python/resnet50_sdk/inference.py" \
  "python/resnet50_sdk/postprocess.py" \
  "python/resnet50_sdk/preprocess.py" \
  --revision e36200659c15f6c22adb5f1d1720c73459c58e20 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装分类依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'pillow==11.3.0'
python -m pip check
```

## 指定算力卡后端

在前一节下载的模型目录执行。只修改推理后端，图片缩放、归一化和分类后处理继续使用同版本官方 SDK。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path('python/resnet50_sdk/inference.py')
s = p.read_text()
old = 'axengine.InferenceSession(model_path)'
new = 'axengine.InferenceSession(model_path, providers=["AXCLRTExecutionProvider"])'
if old in s:
    backup = p.with_suffix('.py.upstream')
    if not backup.exists():
        backup.write_text(s)
    p.write_text(s.replace(old, new))
else:
    assert new in s, '源码与固定版本不匹配'
PY
```

## 准备公交车图片

下载下方效果展示使用的[输入图片](../../../static/validation/effects/resnet50/input.jpg)，复制到主机的 `$MODEL_DIR/input.jpg`。在主机检查文件：

```bash
cd "$MODEL_DIR"
printf '%s  %s\n' \
  '33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c' \
  input.jpg | sha256sum -c -
```

## 输出 Top-5 分类

```bash
cd "$MODEL_DIR"
PYTHONPATH="$MODEL_DIR/python" python - <<'PY'
import json
from resnet50_sdk import ResNet50Classifier
model = ResNet50Classifier('models/model.axmodel')
for i in range(3):
    result = model.classify('input.jpg', top_k=5)
    print(json.dumps({'round': i + 1, 'top5': result}, ensure_ascii=False))
PY
```

日志应显示 `AXCLRTExecutionProvider`，每次输出 5 个类别编号及分数。本版本 SDK 只内置部分标签，因此部分结果显示为 `class_654` 等名称；下方展示按完整 ImageNet 类别表映射的英文标签。

本例使用 RGB、224×224 缩放及 SDK 自带的 ImageNet 均值和标准差，输入为 NCHW / float32。替换图片时保留这套前处理；三次同图重复只检查输出一致性。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

公交车图片的 Top-1 为 ImageNet 类别 654（minibus），Softmax 分数约 0.7184；同图三次输出一致。该样例未核对细分车型标签，不代表完整分类精度。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/resnet50/input.jpg)](../../../static/validation/effects/resnet50/input.jpg)

<figcaption>输入图片</figcaption>
</figure>

</div>

下面按原始类别编号展示 Top-5。英文标签按 [Torchvision v0.23.0 的 ImageNet 类别表](https://raw.githubusercontent.com/pytorch/vision/v0.23.0/torchvision/models/_meta.py) 映射；Softmax 分数不是分类准确率。

**官方 SDK 前处理**

| 类别编号 | ImageNet 标签 | Softmax 分数 |
| --- | --- | --- |
| 654 | minibus | 0.718376 |
| 734 | police van | 0.037748 |
| 829 | streetcar | 0.019127 |
| 874 | trolleybus | 0.015955 |
| 779 | school bus | 0.011618 |

同一输入连续运行 3 次，上表类别和分数一致。

**使用时注意：**

- 仅使用一张公交车图片；没有独立细分车型标注或 ImageNet 验证集评估。
- 官方 SDK 标签表不完整，下方按 Torchvision 的 ImageNet 类别表补充显示名称，原始类别编号不变。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-23。模型版本：`e36200659c15f6c22adb5f1d1720c73459c58e20`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel（包版本 0.1.3）；AXCLRTExecutionProvider |
| NumPy / Pillow | 1.26.4 / 11.3.0 |
| ml-dtypes / OpenCV | 0.5.3 / opencv-python-headless 4.11.0.86 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 三次 Python 调用耗时 | 0.107063 / 0.060877 / 0.060231 s | 按展示顺序；包含 SDK 调用的前后处理，标点模型第一次包含延迟加载；不作为纯 NPU 延迟 |

适用范围：

- 仅使用一张公交车图片；没有独立细分车型标注或 ImageNet 验证集评估。
- 官方 SDK 标签表不完整，下方按 Torchvision 的 ImageNet 类别表补充显示名称，原始类别编号不变。
- 本页使用 AX8850 16GB M.2 卡；未验证 8GB 容量、并发或长期连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/example.py`](https://huggingface.co/AXERA-TECH/resnet50/blob/e36200659c15f6c22adb5f1d1720c73459c58e20/python/example.py) | Python 程序 / 前后处理 |
| [`models/model.axmodel`](https://huggingface.co/AXERA-TECH/resnet50/blob/e36200659c15f6c22adb5f1d1720c73459c58e20/models/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/resnet50/blob/e36200659c15f6c22adb5f1d1720c73459c58e20/python/requirements.txt) | Python 依赖清单 |

仓库提交：`e36200659c15f6c22adb5f1d1720c73459c58e20`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/resnet50/tree/e36200659c15f6c22adb5f1d1720c73459c58e20)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/resnet50/tree/e36200659c15f6c22adb5f1d1720c73459c58e20)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/resnet50/blob/e36200659c15f6c22adb5f1d1720c73459c58e20/README.md)。
- [主要程序入口：python/example.py](https://huggingface.co/AXERA-TECH/resnet50/blob/e36200659c15f6c22adb5f1d1720c73459c58e20/python/example.py)。

返回[完整模型目录](../catalog.mdx)。
