---
title: "DeOldify 部署指南"
sidebar_label: "DeOldify"
description: "DeOldify 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DeOldify 部署指南

DeOldify 用于图像增强与修复。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/DeOldify` 的固定版本。下面下载本页选用的 4 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/deoldify/9f8a5b53053a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeOldify \
  "python/run_axmodel.py" \
  "image/1850Geography.jpg" \
  "model/colorize_stable.axmodel" \
  "model/colorize_artistic.axmodel" \
  --revision 9f8a5b53053a224ad6da0974b069c72b87a26837 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装图像处理依赖

在 RK3576 主机激活已安装 PyAXEngine 的环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
python -m pip check
```

下载 [enhancement_card.py](../../../static/examples/enhancement_card.py) 和 [image-enhancement-cases.json](../../../static/examples/image-enhancement-cases.json)，保存到 `$MODEL_DIR`。运行脚本复用固定版本官方前后处理，指定 `AXCLRTExecutionProvider`，并把输入、模型和输出目录替换为本页路径。

## 运行配套样例

以下命令按顺序运行本仓库全部已选变体。使用新的结果目录；同名目录已存在时脚本停止，避免混入旧图。

```bash
cd "$MODEL_DIR"
for name in deoldify-stable deoldify-artistic; do
  python enhancement_card.py --model-dir . \
    --cases image-enhancement-cases.json --case "$name" \
    --output "results/$name" || break
done
```

确认日志使用 `AXCLRTExecutionProvider`，退出码为 0，并在 `results/变体名称/outputs/` 中生成图片。`enhancement-result.json` 记录实际执行的权重、输入校验值、输出尺寸和耗时。只运行一种算法时，将循环中的名称改为对应名称。

输出用于观察本次处理效果；是否符合业务要求，还需用自己的图片检查颜色、细节和伪影。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

Stable 与 Artistic 两个上色权重处理同一张官方老照片，分别生成 572×694 的彩色图片。

以下图片由本次运行生成，点击可查看原尺寸。各算法的输入、模型分辨率和后处理不同，不能直接根据这些样例比较算法优劣。

**Stable**

输入为黑白老照片；下方展示 Stable 权重的实际上色结果。

<div className="model-effect-gallery">

<figure>

[![原始输入](../../../static/validation/effects/deoldify/inputs/deoldify-stable.jpg)](../../../static/validation/effects/deoldify/inputs/deoldify-stable.jpg)

<figcaption>原始输入</figcaption>
</figure>

<figure>

[![本次运行输出](../../../static/validation/effects/deoldify/outputs/deoldify-stable.jpg)](../../../static/validation/effects/deoldify/outputs/deoldify-stable.jpg)

<figcaption>本次运行输出</figcaption>
</figure>

</div>

**Artistic**

使用同一输入；下方展示 Artistic 权重的实际上色结果。

<div className="model-effect-gallery">

<figure>

[![原始输入](../../../static/validation/effects/deoldify/inputs/deoldify-artistic.jpg)](../../../static/validation/effects/deoldify/inputs/deoldify-artistic.jpg)

<figcaption>原始输入</figcaption>
</figure>

<figure>

[![本次运行输出](../../../static/validation/effects/deoldify/outputs/deoldify-artistic.jpg)](../../../static/validation/effects/deoldify/outputs/deoldify-artistic.jpg)

<figcaption>本次运行输出</figcaption>
</figure>

</div>

**使用时注意：**

- 上色结果是模型推测的颜色，不能作为历史原始色彩的依据。
- 只测试单张照片，未评估视频上色、色彩一致性或完整数据集。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-23。模型版本：`9f8a5b53053a224ad6da0974b069c72b87a26837`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel；AXCLRTExecutionProvider |
| NumPy / OpenCV / Pillow | 1.26.4 / 4.11.0.86 / 11.3.0 |
| Torch / Torchvision | 2.5.1 / 0.20.1 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| Stable 样例总耗时 | 5.697679 s | Python 示例主体，包括模型加载、前后处理、推理和保存图片；不单独作为 NPU 性能 |
| Artistic 样例总耗时 | 2.951496 s | Python 示例主体，包括模型加载、前后处理、推理和保存图片；不单独作为 NPU 性能 |

适用范围：

- 上色结果是模型推测的颜色，不能作为历史原始色彩的依据。
- 只测试单张照片，未评估视频上色、色彩一致性或完整数据集。
- 使用 16GB 算力卡，未验证 8GB 容量、并发或长期连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/gradio_demo.py`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/python/gradio_demo.py) | Python 程序 / 前后处理 |
| [`python/run_axmodel.py`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/python/run_axmodel.py) | Python 程序 / 前后处理 |
| [`model/colorize_artistic.axmodel`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/model/colorize_artistic.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model/colorize_stable.axmodel`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/model/colorize_stable.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assert/gradio_demo.JPG`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/assert/gradio_demo.JPG) | 配套资源 |
| [`config.json`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/python/requirements.txt) | Python 依赖清单 |

仓库提交：`9f8a5b53053a224ad6da0974b069c72b87a26837`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DeOldify/tree/9f8a5b53053a224ad6da0974b069c72b87a26837)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DeOldify/tree/9f8a5b53053a224ad6da0974b069c72b87a26837)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/README.md)。
- [主要程序入口：python/gradio_demo.py](https://huggingface.co/AXERA-TECH/DeOldify/blob/9f8a5b53053a224ad6da0974b069c72b87a26837/python/gradio_demo.py)。

返回[完整模型目录](../catalog.mdx)。
