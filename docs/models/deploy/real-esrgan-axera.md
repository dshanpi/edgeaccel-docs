---
title: "Real-ESRGAN.axera 部署指南"
sidebar_label: "Real-ESRGAN.axera"
description: "Real-ESRGAN.axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Real-ESRGAN.axera 部署指南

Real-ESRGAN.axera 用于图像超分辨率。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Real-ESRGAN.axera` 的固定版本。下面下载本页选用的 5 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/real-esrgan-axera/e56bfc5639dc
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Real-ESRGAN.axera \
  "README.md" \
  "run_axmodel.py" \
  "model/realesrgan-x2.axmodel" \
  "model/realesrgan-x4.axmodel" \
  "pics/0014.jpg" \
  --revision e56bfc5639dca3d6d36899aaa37345c13183d198 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 运行 2 倍与 4 倍超分辨率

在模型目录执行，两种倍率分别生成结果目录：

```bash
cd "$MODEL_DIR"
for scale in x2 x4; do
  python vision_card.py --model-dir . --task realesrgan --variant "$scale" \
    --output "results/$scale" || break
done
```

输入为 `pics/0014.jpg`。例程按 108 像素分块，两侧各补 10 像素，使用 128×128 模型输入；推理后裁除边缘并拼接。不要把 x2 权重与 x4 的输出倍率混用。

检查 `results/x2/output.png`、`results/x4/output.png`，输出宽高应分别为输入的 2 倍和 4 倍。结果目录已存在时换用新目录，避免混入旧图片。


## 查看部署效果

**固定样例已核对** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

x2 与 x4 在同一张插画上分别生成 358×358、716×716 输出，主要轮廓与颜色保留，未见明显分块接缝；已核对这两个固定样例。细线与重建纹理不代表真实细节恢复。

**Real-ESRGAN x2**

179×179 插画生成 358×358 输出。帽子、眼睛、胡须和手部轮廓保留，主要颜色相符；轮廓更平滑，原图中的细线和噪点也有保留。当前样例未见明显分块接缝。 无高分辨率真值，未报告 PSNR 或 SSIM。

<div className="model-effect-gallery">

<figure>

[![输入 · 179×179](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x2/input.webp)](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x2/input.webp)

<figcaption>输入 · 179×179</figcaption>
</figure>

<figure>

[![Real-ESRGAN x2 输出 · 358×358](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x2/output.webp)](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x2/output.webp)

<figcaption>Real-ESRGAN x2 输出 · 358×358</figcaption>
</figure>

</div>

**Real-ESRGAN x4**

179×179 插画生成 716×716 输出。主要构图与颜色保留，轮廓较平滑；胡须和衣服边缘存在重建纹理，不能当作真实细节恢复。当前样例未见明显分块接缝。 无高分辨率真值，未报告 PSNR 或 SSIM。

<div className="model-effect-gallery">

<figure>

[![输入 · 179×179](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x4/input.webp)](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x4/input.webp)

<figcaption>输入 · 179×179</figcaption>
</figure>

<figure>

[![Real-ESRGAN x4 输出 · 716×716](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x4/output.webp)](../../../static/validation/effects/real-esrgan-axera-20260924/realesrgan-x4/output.webp)

<figcaption>Real-ESRGAN x4 输出 · 716×716</figcaption>
</figure>

</div>

**使用时注意：**

- 只测试一张插画，未评估照片、人脸、细小文字或标准超分辨率数据集。
- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`e56bfc5639dca3d6d36899aaa37345c13183d198`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel；AXCLRTExecutionProvider |
| NumPy / OpenCV / Pillow | 1.26.4 / 4.11.0.86 / 11.3.0 |
| Torch / Torchvision | 2.5.1 / 0.20.1 |
| 图文前处理 | Transformers 4.51.3 / Tokenizers 0.21.4；ftfy 6.3.1 / regex 2025.9.18 |
| VAD SDK | silero-vad-axera 0.1.2，复用 SileroAx；权重来自页面固定仓库提交 |
| C++ 检测 | axcl-samples cbfa4c76891758983ca2b0c99c11d6621d59af39 / OpenCV 4.6.0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| realesrgan-x2 / realesrgan-x2.axmodel | 24.634 ms（4 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |
| realesrgan-x4 / realesrgan-x4.axmodel | 81.314 ms（4 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/gradio_demo.py) | Python 程序 / 前后处理 |
| [`run_axmodel.py`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/run_axmodel.py) | Python 程序 / 前后处理 |
| [`model/realesrgan-x2.axmodel`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/model/realesrgan-x2.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model/realesrgan-x4.axmodel`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/model/realesrgan-x4.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assert/gradio_demo.JPG`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/assert/gradio_demo.JPG) | 配套资源 |
| [`build_config.json`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/build_config.json) | 运行配置 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/requirements.txt) | Python 依赖清单 |

仓库提交：`e56bfc5639dca3d6d36899aaa37345c13183d198`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/tree/e56bfc5639dca3d6d36899aaa37345c13183d198)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/tree/e56bfc5639dca3d6d36899aaa37345c13183d198)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/README.md)。
- [主要程序入口：gradio_demo.py](https://huggingface.co/AXERA-TECH/Real-ESRGAN.axera/blob/e56bfc5639dca3d6d36899aaa37345c13183d198/gradio_demo.py)。

返回[完整模型目录](../catalog.mdx)。
