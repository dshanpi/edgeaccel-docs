---
title: "rf-detr-large 部署指南"
sidebar_label: "rf-detr-large"
description: "rf-detr-large 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# rf-detr-large 部署指南

rf-detr-large 用于目标检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/rf-detr-large` 的固定版本。下面下载本页选用的 9 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/rf-detr-large/6a71d9f1f392
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/rf-detr-large \
  "README.md" \
  "models/preprocessor_config.json" \
  "models/rf-detr-large.axmodel" \
  "models/rf-detr-large_704_b2_post.onnx" \
  "pulsar2_config.json" \
  "src/infer/b2_infer_axmodel.py" \
  "datasets/coco2017val_5000/000000000139.jpg" \
  "datasets/coco2017val_5000/000000001268.jpg" \
  "datasets/coco2017val_5000/000000001503.jpg" \
  --revision 6a71d9f1f392415f214d573af99989da405610cc \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备推理例程

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境，再安装本例依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0' 'onnxruntime==1.20.1'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程显式选择 `AXCLRTExecutionProvider`，使用本页固定提交中的前后处理代码，并将本次结果写入独立目录。

## 执行图片检测

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task rf-detr-b2 --variant large \
  --output results/large
```

输出目录需要尚不存在；再次运行时换一个目录名。每张图片运行三次，保存原始输入、检测图以及 `deployment-result.json` 中的候选框和调用耗时。

输入为仓库内三张 COCO 样例，图像转为 RGB 并直接缩放到 704×704，使用 U8 NHWC 输入。归一化由编译模型完成。骨干网络和分类输出在算力卡上运行，配套 `b2_post.onnx` 边界框后处理在 RK3576 CPU 上运行；两部分耗时单独记录。阈值为 0.5，结果图以 `-output.png` 结尾。

打开结果图片，核对检测框是否落在目标上；再查看记录中的 `completed`、`repeatedDetectionsEqual` 和分数。重复结果一致仅说明本组输入可复现，不能代替漏检、误检和定位精度评估。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-27 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

官方样例已通过 AXCL 生成本次检测图；每张图片重复运行三次，保留相同的候选框。

**000000000139**

阈值 0.5，保留 11 个候选框。同一输入运行三次，框坐标、类别和分数一致。

<div className="model-effect-gallery">

<figure>

[![官方输入 · 000000000139](../../../static/validation/effects/rf-detr-large-20260927/000000000139-input.webp)](../../../static/validation/effects/rf-detr-large-20260927/000000000139-input.webp)

<figcaption>官方输入 · 000000000139</figcaption>
</figure>

<figure>

[![本次检测结果 · 000000000139](../../../static/validation/effects/rf-detr-large-20260927/000000000139-output.webp)](../../../static/validation/effects/rf-detr-large-20260927/000000000139-output.webp)

<figcaption>本次检测结果 · 000000000139</figcaption>
</figure>

</div>

| 类别 | 候选框数 |
| --- | --- |
| tv | 2 |
| person | 1 |
| chair | 3 |
| vase | 2 |
| dining table | 2 |
| clock | 1 |

**000000001268**

阈值 0.5，保留 6 个候选框。同一输入运行三次，框坐标、类别和分数一致。

<div className="model-effect-gallery">

<figure>

[![官方输入 · 000000001268](../../../static/validation/effects/rf-detr-large-20260927/000000001268-input.webp)](../../../static/validation/effects/rf-detr-large-20260927/000000001268-input.webp)

<figcaption>官方输入 · 000000001268</figcaption>
</figure>

<figure>

[![本次检测结果 · 000000001268](../../../static/validation/effects/rf-detr-large-20260927/000000001268-output.webp)](../../../static/validation/effects/rf-detr-large-20260927/000000001268-output.webp)

<figcaption>本次检测结果 · 000000001268</figcaption>
</figure>

</div>

| 类别 | 候选框数 |
| --- | --- |
| person | 4 |
| bird | 1 |
| handbag | 1 |

**000000001503**

阈值 0.5，保留 4 个候选框。同一输入运行三次，框坐标、类别和分数一致。

<div className="model-effect-gallery">

<figure>

[![官方输入 · 000000001503](../../../static/validation/effects/rf-detr-large-20260927/000000001503-input.webp)](../../../static/validation/effects/rf-detr-large-20260927/000000001503-input.webp)

<figcaption>官方输入 · 000000001503</figcaption>
</figure>

<figure>

[![本次检测结果 · 000000001503](../../../static/validation/effects/rf-detr-large-20260927/000000001503-output.webp)](../../../static/validation/effects/rf-detr-large-20260927/000000001503-output.webp)

<figcaption>本次检测结果 · 000000001503</figcaption>
</figure>

</div>

| 类别 | 候选框数 |
| --- | --- |
| keyboard | 1 |
| laptop | 1 |
| mouse | 1 |
| tv | 1 |

**使用时注意：**

- 只测试仓库内 3 张图片；重复运行一致性不等同于检测准确率，未计算 COCO mAP。
- 仅在 RK3576 + AX8850 16GB 上验证；未测试 8GB、实时视频或长期运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-27。模型版本：`6a71d9f1f392415f214d573af99989da405610cc`。

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
| rf-detr-large.axmodel | 40.599 ms（9 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载、图像前处理与后处理，未剔除首轮。 |
| RK3576 边界框后处理 | 4.619 ms（9 次平均） | 仅官方 ONNX bbox 后处理调用及输入准备，CPUExecutionProvider，2 个 intra-op 线程；不含画框。 |

适用范围：

- 只测试仓库内 3 张图片；重复运行一致性不等同于检测准确率，未计算 COCO mAP。
- 仅在 RK3576 + AX8850 16GB 上验证；未测试 8GB、实时视频或长期运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`src/infer/b2_infer_axmodel.py`](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/src/infer/b2_infer_axmodel.py) | Python 程序 / 前后处理 |
| [`src/tool/b2_cut.py`](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/src/tool/b2_cut.py) | Python 程序 / 前后处理 |
| [`models/rf-detr-large.axmodel`](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/models/rf-detr-large.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/config.json) | 运行配置 |
| [`models/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/models/preprocessor_config.json) | 运行配置 |
| [`pulsar2_config.json`](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/pulsar2_config.json) | 运行配置 |

仓库提交：`6a71d9f1f392415f214d573af99989da405610cc`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/rf-detr-large/tree/6a71d9f1f392415f214d573af99989da405610cc)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/rf-detr-large/tree/6a71d9f1f392415f214d573af99989da405610cc)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/README.md)。
- [主要程序入口：src/infer/b2_infer_axmodel.py](https://huggingface.co/AXERA-TECH/rf-detr-large/blob/6a71d9f1f392415f214d573af99989da405610cc/src/infer/b2_infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
