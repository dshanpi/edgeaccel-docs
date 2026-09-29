---
title: "mobilenetv3-small 部署指南"
sidebar_label: "mobilenetv3-small"
description: "mobilenetv3-small 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# mobilenetv3-small 部署指南

mobilenetv3-small 用于图像分类。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/mobilenetv3-small` 的固定版本。下面下载本页选用的 4 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/mobilenetv3-small/22236ff870c9
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/mobilenetv3-small \
  "models/model.axmodel" \
  "models/model_meta.json" \
  "python/example.py" \
  "python/inference.py" \
  --revision 22236ff870c903cdefa0dcb9767db3a09903620e \
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

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path('python/inference.py')
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

下载[实测输入图片](../../../static/validation/effects/mobilenetv3-small/input.jpg)，复制到主机的 `$MODEL_DIR/input.jpg`，然后校验：

```bash
cd "$MODEL_DIR"
printf '%s  %s\n' \
  '33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c' \
  input.jpg | sha256sum -c -
```

## 运行分类

本版本官方 Python 示例按 RGB 读取图片，模型元数据写的是 BGR。下面先复现 Python 示例的 RGB 输入，再单独运行 BGR 对照；两种输入的实测结果均未正确识别公交车，当前仅确认模型能够执行。

```bash
cd "$MODEL_DIR"
CHANNEL_ORDER=RGB PYTHONPATH="$MODEL_DIR/python" python - <<'PY'
import json, os
import numpy as np
from PIL import Image
from inference import MobileNetV3Classifier
data = np.array(Image.open('input.jpg').resize((224, 224)), dtype=np.float32)
data = data.transpose(2, 0, 1)[None] / 255.0
order = os.environ['CHANNEL_ORDER']
assert order in ['RGB', 'BGR']
if order == 'BGR':
    data = np.ascontiguousarray(data[:, ::-1, :, :])
model = MobileNetV3Classifier('models/model.axmodel')
for i in range(3):
    logits = model.classify(data)[0]
    assert np.isfinite(logits).all()
    probs = np.exp(logits - logits.max())
    probs /= probs.sum()
    top5 = [{'class_id': int(j), 'confidence': float(probs[j])}
            for j in np.argsort(-logits)[:5]]
    print(json.dumps({'round': i + 1, 'order': order, 'top5': top5}))
PY
```

日志应显示 `AXCLRTExecutionProvider`，输出张量含 1000 个分类分值。将上面命令中的 `CHANNEL_ORDER=RGB` 改为 `CHANNEL_ORDER=BGR` 后重新执行，即可复现下方 BGR 对照。没有证据表明仅交换通道即可恢复本版本的分类效果。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

官方 RGB 示例和按模型元数据设置的 BGR 输入均完成三次推理，但 Top-5 未识别出图中的公交车。当前仅确认基本运行，分类效果未通过核对。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/mobilenetv3-small/input.jpg)](../../../static/validation/effects/mobilenetv3-small/input.jpg)

<figcaption>输入图片</figcaption>
</figure>

</div>

下面按原始类别编号展示 Top-5。英文标签按 [Torchvision v0.23.0 的 ImageNet 类别表](https://raw.githubusercontent.com/pytorch/vision/v0.23.0/torchvision/models/_meta.py) 映射；Softmax 分数不是分类准确率。

**RGB：官方 Python 示例**

| 类别编号 | ImageNet 标签 | Softmax 分数 |
| --- | --- | --- |
| 789 | shoji | 0.037458 |
| 619 | lampshade | 0.037458 |
| 647 | measuring cup | 0.037458 |
| 624 | library | 0.032510 |
| 453 | bookcase | 0.031602 |

同一输入连续运行 3 次，上表类别和分数一致。

**BGR：按模型元数据交换通道**

| 类别编号 | ImageNet 标签 | Softmax 分数 |
| --- | --- | --- |
| 789 | shoji | 0.033196 |
| 624 | library | 0.033196 |
| 619 | lampshade | 0.033196 |
| 720 | pill bottle | 0.033196 |
| 647 | measuring cup | 0.033196 |

同一输入连续运行 3 次，上表类别和分数一致。

**使用时注意：**

- 同一张公交车图的 RGB、BGR 两组输入均未得到正确分类；不能据此宣称模型适用于业务分类。
- 前处理依据本仓库固定版本；仍需配套浮点模型及验证集核查转换和前处理的一致性。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-23。模型版本：`22236ff870c903cdefa0dcb9767db3a09903620e`。

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
| 三次 Python 调用耗时 | 0.012477 / 0.009024 / 0.008942 s | 按展示顺序；包含 SDK 调用的前后处理，标点模型第一次包含延迟加载；不作为纯 NPU 延迟 |

适用范围：

- 同一张公交车图的 RGB、BGR 两组输入均未得到正确分类；不能据此宣称模型适用于业务分类。
- 前处理依据本仓库固定版本；仍需配套浮点模型及验证集核查转换和前处理的一致性。
- 本页使用 AX8850 16GB M.2 卡；未验证 8GB 容量、并发或长期连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/example.py`](https://huggingface.co/AXERA-TECH/mobilenetv3-small/blob/22236ff870c903cdefa0dcb9767db3a09903620e/python/example.py) | Python 程序 / 前后处理 |
| [`python/inference.py`](https://huggingface.co/AXERA-TECH/mobilenetv3-small/blob/22236ff870c903cdefa0dcb9767db3a09903620e/python/inference.py) | Python 程序 / 前后处理 |
| [`models/model.axmodel`](https://huggingface.co/AXERA-TECH/mobilenetv3-small/blob/22236ff870c903cdefa0dcb9767db3a09903620e/models/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/mobilenetv3-small/blob/22236ff870c903cdefa0dcb9767db3a09903620e/python/requirements.txt) | Python 依赖清单 |

仓库提交：`22236ff870c903cdefa0dcb9767db3a09903620e`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/mobilenetv3-small/tree/22236ff870c903cdefa0dcb9767db3a09903620e)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/mobilenetv3-small/tree/22236ff870c903cdefa0dcb9767db3a09903620e)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/mobilenetv3-small/blob/22236ff870c903cdefa0dcb9767db3a09903620e/README.md)。
- [主要程序入口：python/example.py](https://huggingface.co/AXERA-TECH/mobilenetv3-small/blob/22236ff870c903cdefa0dcb9767db3a09903620e/python/example.py)。

返回[完整模型目录](../catalog.mdx)。
