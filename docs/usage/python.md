---
title: "通过 Python 调用算力卡"
description: "使用固定版本 YOLOv8n 与公交车图片，完成 PyAXEngine 安装、推理、结果检查和资源释放。"
---

# 通过 Python 调用算力卡

使用 Python 加载 **YOLOv8n**，检测官方 `bus.jpg`，生成带检测框的图片。全部命令在连接算力卡的 Linux 主机执行。

| 项目 | 本页固定配置 |
| --- | --- |
| 主机 | RK3576 DShanPi-A1，Ubuntu 24.04，aarch64，Python 3.12.3 |
| 算力卡 | AX8850 16GB，AXCL / 固件 3.16.0 |
| 推理接口 | PyAXEngine 0.1.3.rc3 发布的 0.1.3 wheel，`AXCLRTExecutionProvider` |
| 模型 | `AXERA-TECH/YOLOv8`，`AX650/yolov8n_640x640_npu3.axmodel` |
| 输入与输出 | 官方公交车图片 → `result.jpg` |

## 准备设备与目录

先完成[安装 AXCL](../ax650n/quick-start/arm64.md)和[设备检查](device-check.md)，保持风扇运行，停止其他推理应用。本页需要约 300 MB 可用空间。

```bash
/usr/bin/axcl/axcl-smi
sudo apt-get install -y python3-venv curl
APP_ROOT=${EDGEACCEL_WORK:-$HOME/edgeaccel/application-guides}
mkdir -p "$APP_ROOT/python/AX650"
cd "$APP_ROOT/python"
```

设备列表应显示 AX8850，且没有其他推理进程。空间不足时，在执行上述命令前将 `EDGEACCEL_WORK` 设置为已挂载、当前用户可写的存储目录；后续新终端保持相同设置。

网络需要代理时，在当前终端设置自己的代理地址，再执行下载。例如本地代理位于 `192.168.1.38:7897`：

```bash
export http_proxy=http://192.168.1.38:7897
export https_proxy=http://192.168.1.38:7897
export no_proxy=localhost,127.0.0.1
```

## 安装已核对的 PyAXEngine 版本

```bash
curl -fL --retry 2 \
  https://github.com/AXERA-TECH/pyaxengine/releases/download/0.1.3.rc3/axengine-0.1.3-py3-none-any.whl \
  -o axengine-0.1.3-py3-none-any.whl
printf '%s  %s\n' \
  762d0284623947aac5e4ecd8253e7049be975e9a73a9a6bfa20ac504c362efac \
  axengine-0.1.3-py3-none-any.whl | sha256sum -c -
```

校验显示 `OK` 后安装。校验不符时停止，不继续加载文件。

```bash
python3 -m venv env
source env/bin/activate
python -m pip install --no-cache-dir \
  ./axengine-0.1.3-py3-none-any.whl \
  numpy==1.26.4 ml-dtypes==0.5.3 opencv-python-headless==4.11.0.86
python -m pip check
python -c 'import axengine; print(axengine.get_available_providers())'
```

应显示 `No broken requirements found.`，后端列表包含 `AXCLRTExecutionProvider`。该后端通过 PCIe 调用算力卡；`AxEngineExecutionProvider` 面向芯片板端。

本站其他模型页使用 `~/edgeaccel/python-env` 作为通用入口。首次安装且该位置不存在时，可为本环境建立链接；已有环境不覆盖：

```bash
mkdir -p ~/edgeaccel
if [ ! -e ~/edgeaccel/python-env ] && [ ! -L ~/edgeaccel/python-env ]; then
  ln -s "$APP_ROOT/python/env" ~/edgeaccel/python-env
fi
```

## 下载模型、输入与配套脚本

```bash
REV=65567714c2388b9c6b85bfb10b21535e7db0dee0
for FILE in ax_infer.py bus.jpg AX650/yolov8n_640x640_npu3.axmodel; do
  curl -fL --retry 2 \
    "https://huggingface.co/AXERA-TECH/YOLOv8/resolve/$REV/$FILE" \
    -o "$FILE" || break
done
sha256sum -c <<'SHA256'
66c8e8b8b9374c2ec49035986a341b63bbb3cbd69999306889633be7b2f94fb4  ax_infer.py
33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c  bus.jpg
e5563cc868a98e9ee051cb9941844be934c55cd5a37264d10bff534dd613e86b  AX650/yolov8n_640x640_npu3.axmodel
SHA256
```

三个文件均为 `OK` 后运行。脚本、图片与模型来自同一固定提交，不替换为其他芯片目录中的权重。

## 运行图片推理

```bash
set -o pipefail
python ax_infer.py \
  --model-path AX650/yolov8n_640x640_npu3.axmodel \
  --test-img bus.jpg --img-save-path result.jpg \
  --score-thres 0.25 --nms-thres 0.7 \
  --providers AXCLRTExecutionProvider 2>&1 | tee inference.log
```

日志应显示 `Using provider: AXCLRTExecutionProvider` 和 `Saved to result.jpg`。这条命令执行一次推理后退出，不启动后台服务。

脚本内部通过以下两步调用模型；图片缩放、填充与检测框解码仍使用同版本官方实现：

```python
session = axengine.InferenceSession(model_path, providers=["AXCLRTExecutionProvider"])
outputs = session.run(None, {session.get_inputs()[0].name: input_tensor})
```

这段用于说明接口，不是可独立运行的完整示例。更换模型时，应同步核对输入布局、数据类型和前后处理。

## 查看部署效果

下图为上述命令在本页 16GB 环境生成的实际结果。

![YOLOv8n 实际检测结果](../../static/examples/application-guides/python-result.jpg)

| 日志输出 | 本次结果 |
| --- | --- |
| 目标数 | 5 |
| 公交车 | 1 个，分数 0.88 |
| 行人 | 3 个，分数 0.84、0.84、0.80 |
| stop sign | 1 个，分数 0.34，位于图片左侧边缘，需人工复核 |
| 输出尺寸 | 810 × 1080 |

检测分数不是准确率。此处核对了固定图片的运行与可见结果，没有使用独立标注集评估模型精度。一次 `session.run` 耗时约 38.46 ms，不包含模型加载、前处理、后处理及写图，也不能直接换算成整套应用帧率。

在主机检查自己的输出文件：

```bash
python - <<'PY'
import cv2
original = cv2.imread('bus.jpg')
result = cv2.imread('result.jpg')
assert original is not None and result is not None
assert original.shape == result.shape and (original != result).any()
print('OUTPUT_OK', result.shape)
PY
```

文件检查通过后仍需打开图片核对检测框。可从主机桌面打开，或复制到自己的电脑查看。

## 结束运行并释放环境

前台运行需要提前结束时按 `Ctrl+C`。正常完成后不需要额外杀进程；执行以下命令退出虚拟环境并检查卡端资源：

```bash
deactivate
/usr/bin/axcl/axcl-smi
```

本次程序正常退出后进程列表为空，CMM 回到空闲基线 18 MiB。其他环境的基线可能不同，应与运行前比较。

后续再次运行时，重新设置 `APP_ROOT`，进入 `$APP_ROOT/python` 并执行 `source env/bin/activate`。视频处理继续阅读[处理视频与接入视频流](video.md)。需要设备管理、内存或视频底层接口时，使用配套 [pyAXCL SDK](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_pyaxcl.html)；它与本页的 PyAXEngine 接口不同。
