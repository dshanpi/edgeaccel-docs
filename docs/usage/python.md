---
title: "通过 Python 调用算力卡"
---

# 通过 Python 调用算力卡

Linux 主机先完成 AXCL 安装和设备识别。Python 环境在主机运行，必须选择算力卡后端。

## 选择接口

| 接口 | 用途 | 导入名 |
|---|---|---|
| pyAXCL | AXCL 设备、内存、NPU、视频等接口 | `axcl` |
| PyAXEngine | 较简洁的模型推理接口，便于原型验证 | `axengine` |

两个包的接口不同，不能互换。需要完整 AXCL 功能时优先使用官方 pyAXCL；仅做模型原型时可采用 PyAXEngine。

## 安装 pyAXCL

使用与安装版本配套的 SDK 中 `axcl/out/python/pyAXCL-版本-py3-none-any.whl`。Python 需符合 SDK 要求，官方文档要求 3.9 或更高。将实际 wheel 放入 `~/axcl-setup`，用其真实文件名替换下面占位符。

```bash
python3 -m venv ~/edgeaccel/python-env
source ~/edgeaccel/python-env/bin/activate
python -m pip install ~/axcl-setup/实际的pyAXCL文件名.whl
python -c 'import axcl; print(axcl.__file__)'
```

导入成功只证明 Python 可找到包。继续按 SDK 自带设备和 NPU 示例检查设备初始化、内存分配、模型执行及资源释放，不把导入结果作为推理通过。

## 安装已核对的 PyAXEngine 版本

2026-09-23 已在 RK3576 主机的 Python 3.12 虚拟环境中导入 PyAXEngine，并确认可用后端包含 `AXCLRTExecutionProvider`。本节固定使用官方 [0.1.3.rc3 发布版](https://github.com/AXERA-TECH/pyaxengine/releases/tag/0.1.3.rc3)，wheel 内的包版本仍显示为 `0.1.3`，因此同时保留发布标签和文件校验值。

从[官方发布文件](https://github.com/AXERA-TECH/pyaxengine/releases/download/0.1.3.rc3/axengine-0.1.3-py3-none-any.whl)下载 `axengine-0.1.3-py3-none-any.whl`，保存到 `~/axcl-setup`。在 RK3576 主机校验文件：

```bash
cd ~/axcl-setup
printf '%s  %s\n' \
  '762d0284623947aac5e4ecd8253e7049be975e9a73a9a6bfa20ac504c362efac' \
  'axengine-0.1.3-py3-none-any.whl' | sha256sum -c -
```

输出应为 `axengine-0.1.3-py3-none-any.whl: OK`。校验不符时停止安装。使用独立环境，将 wheel 与固定版本的 NumPy、ml-dtypes 和 OpenCV 在同一次安装中提交给依赖解析器：

```bash
python3 -m venv ~/edgeaccel/python-env
source ~/edgeaccel/python-env/bin/activate
python -m pip install \
  ~/axcl-setup/axengine-0.1.3-py3-none-any.whl \
  'numpy==1.26.4' 'ml-dtypes==0.5.3' \
  'opencv-python-headless==4.11.0.86'
python -m pip check
python -c 'import axengine; print(axengine.get_available_providers())'
```

不要先装固定 NumPy，再单独安装未约束依赖版本的 axengine；后一条命令可能重新选择 NumPy 版本。后续安装模型依赖时同样保留上述版本约束，依赖冲突时为该模型建立独立环境，不直接升级共用环境。

`pip check` 应无依赖冲突，可用后端列表必须包含 `AXCLRTExecutionProvider`。导入和后端发现不等于某个模型已经运行，模型执行结果以[独立部署页面](../models/catalog.mdx)中的实测记录为准。

## 运行配套 Python 示例

获取同版本示例源码，避免 wheel 和示例 API 不一致。在官方 `examples/classification.py` 所在目录执行。`model.axmodel`、`input.jpg` 必须是该分类示例要求的配套模型与图片。

```bash
python classification.py \
  -m /实际模型目录/model.axmodel \
  -i /实际输入目录/input.jpg \
  -p AXCLRTExecutionProvider
```

显式使用 `AXCLRTExecutionProvider`。`AxEngineExecutionProvider` 面向芯片板端，不能用于 RK3576 主机上的 M.2 卡推理。

## 补齐 Whisper 音频依赖

本次 Whisper 示例使用 `librosa==0.9.1`。在 Python 3.12 环境中同时安装 `setuptools==75.8.0`，为该依赖组合提供 `pkg_resources`：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install \
  'numpy==1.26.4' 'ml-dtypes==0.5.3' \
  'librosa==0.9.1' 'setuptools==75.8.0'
python -c 'import librosa, pkg_resources; print(librosa.__version__)'
python -m pip check
```

导入失败时先解决 Python 依赖，再加载模型。此处只记录已使用的依赖组合，Whisper 的音频输入、模型文件与运行结果见[Whisper 部署指南](../models/deploy/whisper.md)。

## 检查输入输出与资源

按模型元数据核对张量名称、形状、布局与 dtype。分类示例的图片处理不能直接套用 YOLO、OCR 或语音模型。确认 AXCL provider 实际加载，检查设备内存变化、输出类别与参考结果，再循环运行并观察资源是否释放。

依据：[pyAXCL 官方说明](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_pyaxcl.html)、[PyAXEngine 0.1.3.rc3](https://github.com/AXERA-TECH/pyaxengine/releases/tag/0.1.3.rc3)。本次仅对上述 PyAXEngine 环境记录实测状态，不将其扩展为 pyAXCL 全部接口或所有模型的验证结论。
