---
title: "Real-ESRGAN 部署指南"
sidebar_label: "Real-ESRGAN"
description: "Real-ESRGAN 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Real-ESRGAN 部署指南

Real-ESRGAN 用于图像增强与修复。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `ax650/realesrgan-x4-256.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Real-ESRGAN` 的固定版本。下面下载本页选用的 3 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/real-esrgan/45767e2bceb3
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Real-ESRGAN \
  "main.py" \
  "ax650/realesrgan-x4-256.axmodel" \
  "test_256.jpeg" \
  --revision 45767e2bceb3e624477af4922d31418a7a044bc5 \
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
    {"path": "main.py", "old": "ort.InferenceSession(model_path)", "new": "ort.InferenceSession(model_path, providers=[\"AXCLRTExecutionProvider\"])"}
]
for edit in edits:
    path = Path(edit.get("path", "main.py"))
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
test -s ax650/realesrgan-x4-256.axmodel
test -s test_256.jpeg
set -o pipefail
python main.py --model ax650/realesrgan-x4-256.axmodel --input test_256.jpeg --output output_test_256.jpg 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `output_test_256.jpg` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`main.py` 源码](https://huggingface.co/AXERA-TECH/Real-ESRGAN/blob/45767e2bceb3e624477af4922d31418a7a044bc5/main.py)。

## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

动漫人物样图成功生成 1024×1024 输出。人工对照可见人物、持剑姿态、背景和颜色关系保留，脸部与头发轮廓完整，没有明显通道错乱或大片破损。原图实际为 243×243，程序先调整到 256×256，再由模型放大 4 倍。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/real-esrgan/inputs/test_256.jpeg)](../../../static/validation/effects/real-esrgan/inputs/test_256.jpeg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/real-esrgan/outputs/output_test_256.jpg)](../../../static/validation/effects/real-esrgan/outputs/output_test_256.jpg)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 没有配套高分辨率真值，未计算 PSNR、SSIM 或其它客观图像质量指标。
- 输出中的平滑边缘与重建纹理不能证明恢复了真实细节，也不能仅凭观感宣称质量提升幅度。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`45767e2bceb3e624477af4922d31418a7a044bc5`。

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
| 原始图片尺寸 | 243×243 | 实际 test_256.jpeg 文件头，文件名不代表实际尺寸 |
| 网络输入尺寸 | 256×256 | tensors.json 输入 [1,256,256,3]，uint8 |
| 实际输出尺寸 | 1024×1024 | output_test_256.jpg 文件头；相对网络输入为 4 倍，不是相对原图精确 4 倍 |
| 单次 session.run 时延 | 883.16 | 毫秒；主机墙钟，包含 AXCL 调用及复制，排除张量统计，不是纯 NPU 时延 |
| session.run：realesrgan-x4-256.axmodel | 883.164 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 没有配套高分辨率真值，未计算 PSNR、SSIM 或其它客观图像质量指标。
- 输出中的平滑边缘与重建纹理不能证明恢复了真实细节，也不能仅凭观感宣称质量提升幅度。
- 只测试 1 张动漫图；未覆盖真实照片、文字图、任意输入尺寸或分块拼接边缘。
- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`main.py`](https://huggingface.co/AXERA-TECH/Real-ESRGAN/blob/45767e2bceb3e624477af4922d31418a7a044bc5/main.py) | Python 程序 / 前后处理 |
| [`ax650/realesrgan-x4-256.axmodel`](https://huggingface.co/AXERA-TECH/Real-ESRGAN/blob/45767e2bceb3e624477af4922d31418a7a044bc5/ax650/realesrgan-x4-256.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`test_256.jpeg`](https://huggingface.co/AXERA-TECH/Real-ESRGAN/blob/45767e2bceb3e624477af4922d31418a7a044bc5/test_256.jpeg) | 示例输入 |

仓库提交：`45767e2bceb3e624477af4922d31418a7a044bc5`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Real-ESRGAN/tree/45767e2bceb3e624477af4922d31418a7a044bc5)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页选择 x4-256 编译模型，固定样图为 test_256.jpeg；检查输出长宽与四倍超分辨率任务一致，再评估边缘细节。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Real-ESRGAN/tree/45767e2bceb3e624477af4922d31418a7a044bc5)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Real-ESRGAN/blob/45767e2bceb3e624477af4922d31418a7a044bc5/README.md)。
- [主要程序入口：main.py](https://huggingface.co/AXERA-TECH/Real-ESRGAN/blob/45767e2bceb3e624477af4922d31418a7a044bc5/main.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Real-ESRGAN)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
