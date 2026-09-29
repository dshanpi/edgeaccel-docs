---
title: "MobileSAM 部署指南"
sidebar_label: "MobileSAM"
description: "MobileSAM 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MobileSAM 部署指南

MobileSAM 用于图像分割。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MobileSAM` 的固定版本。下面下载本页选用的 9 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/mobilesam/36552af82921
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MobileSAM \
  "README.md" \
  "requirements.txt" \
  "python_ax/main.py" \
  "python_ax/sam_encoder.py" \
  "python_ax/sam_decoder.py" \
  "ax_model/mobile_sam_encoder_650.axmodel" \
  "ax_model/mobile_sam_decoder_650.axmodel" \
  "images/test.jpg" \
  "images/truck.jpg" \
  --revision 36552af82921ea8d253a4bf4e1893bff64544e08 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分割例程

在 RK3576 主机激活已安装 [PyAXEngine](../../usage/python.md) 的环境，安装图像处理依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86'
python -c "import axengine; print(axengine.get_available_providers())"
```

确认输出包含 `AXCLRTExecutionProvider`。下载 [MobileSAM 算力卡例程](../../../static/examples/mobilesam_card.py)，保存为 `~/edgeaccel/mobilesam_card.py`。

## 运行点提示和框提示

保持上文下载步骤中的 `MODEL_DIR`，指定一个尚不存在的结果目录：

```bash
python ~/edgeaccel/mobilesam_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/mobilesam
```

例程使用 `mobile_sam_encoder_650.axmodel` 和 `mobile_sam_decoder_650.axmodel`，显式选择 AXCL。编码器将图片按比例缩放、右侧与底部补边到 1024×1024；解码器接收提示坐标，输出四个候选掩码，并按模型预测分数选择一个。

本例沿用官方提示坐标：足球图片运行 3 个点提示、4 个框提示，车辆图片运行 1 个点提示、4 个框提示。坐标单位为原图像素；点格式为 `(x,y)`，框格式为 `(左上角 x,左上角 y,宽,高)`。

| 输出文件 | 内容 |
| --- | --- |
| `test-input.png`、`truck-input.png` | 实际输入图片 |
| `*-overlay.png` | 提示位置和绿色分割区域叠加图 |
| `*-mask.png` | 选中掩码，按官方步骤缩放回原图 |
| `*-raw.npz` | 解码器原始掩码和预测分数 |
| `deployment-result.json` | 提示坐标、选中掩码、重复运行核对和耗时 |

打开 `*-overlay.png` 查看效果。点选可能得到衣服、车窗等局部区域；需要完整目标时，对照框提示结果。模型给出的预测分数用于选择掩码，不等于用人工标注测得的 IoU。

本例每张图片编码两次，每组提示解码两次，并检查输出是否一致。掩码按官方顺序先以 `>0` 阈值处理，再用双线性插值放大、裁剪；边缘可能出现中间灰度，不能把灰度值当作模型置信度。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两张官方图片完成 4 组点提示和 8 组框提示，生成对应分割图；各输入重复输出一致。点提示可能选择上衣或车窗等局部区域，不能视为完整目标分割。

**test.jpg / 点提示 [910, 641]**

点选中央人物，选中其主体区域，未做逐像素边界评测。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![点提示 \[910, 641\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-point-0-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-point-0-overlay.webp)

<figcaption>点提示 [910, 641] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 3 |
| 掩码非零面积占比 | 6.23% |
| 重复输出 | 编码与解码均逐项一致 |

**test.jpg / 点提示 [1488, 607]**

点选右侧人物，选中其主体区域。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![点提示 \[1488, 607\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-point-1-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-point-1-overlay.webp)

<figcaption>点提示 [1488, 607] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 3 |
| 掩码非零面积占比 | 3.99% |
| 重复输出 | 编码与解码均逐项一致 |

**test.jpg / 点提示 [579, 704]**

点选远处蓝衣人物，主要选中上衣，未包含完整双腿。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![点提示 \[579, 704\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-point-2-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-point-2-overlay.webp)

<figcaption>点提示 [579, 704] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 1 |
| 掩码非零面积占比 | 1.10% |
| 重复输出 | 编码与解码均逐项一致 |

**test.jpg / 框提示 [750, 211, 380, 940]**

框选中央人物，选中主体区域。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![框提示 \[750, 211, 380, 940\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-box-0-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-box-0-overlay.webp)

<figcaption>框提示 [750, 211, 380, 940] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 2 |
| 掩码非零面积占比 | 6.23% |
| 重复输出 | 编码与解码均逐项一致 |

**test.jpg / 框提示 [479, 482, 191, 518]**

框选远处蓝衣人物，结果比点提示覆盖更完整，包含腿部。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![框提示 \[479, 482, 191, 518\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-box-1-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-box-1-overlay.webp)

<figcaption>框提示 [479, 482, 191, 518] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 3 |
| 掩码非零面积占比 | 2.23% |
| 重复输出 | 编码与解码均逐项一致 |

**test.jpg / 框提示 [1345, 333, 289, 701]**

框选右侧人物，选中主体区域。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![框提示 \[1345, 333, 289, 701\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-box-2-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-box-2-overlay.webp)

<figcaption>框提示 [1345, 333, 289, 701] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 0 |
| 掩码非零面积占比 | 3.90% |
| 重复输出 | 编码与解码均逐项一致 |

**test.jpg / 框提示 [1, 357, 311, 751]**

框选左侧人物，边缘与附近重叠人体需进一步核对。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · test.jpg](../../../static/validation/effects/mobilesam-20260928/test-input.webp)](../../../static/validation/effects/mobilesam-20260928/test-input.webp)

<figcaption>实际输入 · test.jpg</figcaption>
</figure>

<figure>

[![框提示 \[1, 357, 311, 751\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/test-box-3-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/test-box-3-overlay.webp)

<figcaption>框提示 [1, 357, 311, 751] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 3 |
| 掩码非零面积占比 | 6.09% |
| 重复输出 | 编码与解码均逐项一致 |

**truck.jpg / 点提示 [500, 375]**

点选车窗，主要选中局部窗玻璃，并非整辆车。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · truck.jpg](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)

<figcaption>实际输入 · truck.jpg</figcaption>
</figure>

<figure>

[![点提示 \[500, 375\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/truck-point-0-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/truck-point-0-overlay.webp)

<figcaption>点提示 [500, 375] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 1 |
| 掩码非零面积占比 | 1.19% |
| 重复输出 | 编码与解码均逐项一致 |

**truck.jpg / 框提示 [1375, 550, 275, 250]**

框选右侧车轮，选中车轮及附近局部。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · truck.jpg](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)

<figcaption>实际输入 · truck.jpg</figcaption>
</figure>

<figure>

[![框提示 \[1375, 550, 275, 250\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/truck-box-0-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/truck-box-0-overlay.webp)

<figcaption>框提示 [1375, 550, 275, 250] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 2 |
| 掩码非零面积占比 | 2.01% |
| 重复输出 | 编码与解码均逐项一致 |

**truck.jpg / 框提示 [75, 275, 1650, 575]**

框选整车，结果覆盖车辆主体。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · truck.jpg](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)

<figcaption>实际输入 · truck.jpg</figcaption>
</figure>

<figure>

[![框提示 \[75, 275, 1650, 575\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/truck-box-1-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/truck-box-1-overlay.webp)

<figcaption>框提示 [75, 275, 1650, 575] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 2 |
| 掩码非零面积占比 | 29.59% |
| 重复输出 | 编码与解码均逐项一致 |

**truck.jpg / 框提示 [425, 600, 275, 275]**

框选左侧车轮，选中车轮及附近轮拱局部。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · truck.jpg](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)

<figcaption>实际输入 · truck.jpg</figcaption>
</figure>

<figure>

[![框提示 \[425, 600, 275, 275\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/truck-box-2-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/truck-box-2-overlay.webp)

<figcaption>框提示 [425, 600, 275, 275] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 3 |
| 掩码非零面积占比 | 2.32% |
| 重复输出 | 编码与解码均逐项一致 |

**truck.jpg / 框提示 [1240, 675, 160, 75]**

框选车身底部，选中局部踏板区域。 绿色为所选掩码，提示标记也用绿色显示。

<div className="model-effect-gallery">

<figure>

[![实际输入 · truck.jpg](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)](../../../static/validation/effects/mobilesam-20260928/truck-input.webp)

<figcaption>实际输入 · truck.jpg</figcaption>
</figure>

<figure>

[![框提示 \[1240, 675, 160, 75\] · 本次分割](../../../static/validation/effects/mobilesam-20260928/truck-box-3-overlay.webp)](../../../static/validation/effects/mobilesam-20260928/truck-box-3-overlay.webp)

<figcaption>框提示 [1240, 675, 160, 75] · 本次分割</figcaption>
</figure>

</div>

| 项目 | 结果 |
| --- | --- |
| 选中掩码编号（从 0 开始） | 3 |
| 掩码非零面积占比 | 0.45% |
| 重复输出 | 编码与解码均逐项一致 |

**使用时注意：**

- 仅核对两张图片的点与框提示；未测试负点提示、输入掩码修正、多轮交互或视频。
- 掩码边缘和重叠目标未用像素标注评测；预测分数不代表实测 IoU。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`36552af82921ea8d253a4bf4e1893bff64544e08`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / OpenCV 4.11.0 |
| 输入 | AX650 编码器：uint8 [1,1024,1024,3]；解码器：float32 图像特征、提示与空掩码 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| mobile_sam_encoder_650.axmodel | 83.407 ms（4 次平均） | AXCL session.run 墙钟，包含输入输出传输；不含加载、前后处理和保存，未剔除首轮。 |
| mobile_sam_decoder_650.axmodel | 35.742 ms（24 次平均） | AXCL session.run 墙钟，包含输入输出传输；不含加载、前后处理和保存，未剔除首轮。 |

适用范围：

- 仅核对两张图片的点与框提示；未测试负点提示、输入掩码修正、多轮交互或视频。
- 掩码边缘和重叠目标未用像素标注评测；预测分数不代表实测 IoU。
- 仅验证 AX650 两个权重；620E 文件不用于本页算力卡部署。
- 仅在 16GB 卡验证，真实 8GB 回归待完成。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python_ax/main.py`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/python_ax/main.py) | Python 程序 / 前后处理 |
| [`ax_model/mobile_sam_decoder_620E.axmodel`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/ax_model/mobile_sam_decoder_620E.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/mobile_sam_decoder_650.axmodel`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/ax_model/mobile_sam_decoder_650.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/mobile_sam_encoder_620E.axmodel`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/ax_model/mobile_sam_encoder_620E.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/mobile_sam_encoder_650.axmodel`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/ax_model/mobile_sam_encoder_650.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/config.json) | 运行配置 |
| [`images/test.jpg`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/images/test.jpg) | 示例输入 |
| [`python_onnx/main.py`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/python_onnx/main.py) | Python 程序 / 前后处理 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/requirements.txt) | Python 依赖清单 |

仓库提交：`36552af82921ea8d253a4bf4e1893bff64544e08`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MobileSAM/tree/36552af82921ea8d253a4bf4e1893bff64544e08)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 使用图像编码与提示解码两个阶段。点击坐标、原图尺寸和模型缩放映射必须一致。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MobileSAM/tree/36552af82921ea8d253a4bf4e1893bff64544e08)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/README.md)。
- [主要程序入口：python_ax/main.py](https://huggingface.co/AXERA-TECH/MobileSAM/blob/36552af82921ea8d253a4bf4e1893bff64544e08/python_ax/main.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/MobileSAM)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
