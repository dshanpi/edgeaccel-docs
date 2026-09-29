---
title: "Depth-Anything-3 部署指南"
sidebar_label: "Depth-Anything-3"
description: "Depth-Anything-3 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Depth-Anything-3 部署指南

Depth-Anything-3 用于深度估计。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `models-ax650/da3-small.axmodel`。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Depth-Anything-3` 的固定版本。下面下载本页选用的 3 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/depth-anything-3/7bf36032e88d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Depth-Anything-3 \
  "python/infer.py" \
  "models-ax650/da3-small.axmodel" \
  "examples/demo01.jpg" \
  --revision 7bf36032e88d4cfba089a6ddb05fa99724742177 \
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
    {"path": "python/infer.py", "old": "axe.InferenceSession(model)", "new": "axe.InferenceSession(model, providers=[\"AXCLRTExecutionProvider\"])"}
]
for edit in edits:
    path = Path(edit.get("path", "python/infer.py"))
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
test -s models-ax650/da3-small.axmodel
test -s examples/demo01.jpg
set -o pipefail
python python/infer.py --model models-ax650/da3-small.axmodel --img examples/demo01.jpg 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `output-ax.png` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`python/infer.py` 源码](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/7bf36032e88d4cfba089a6ddb05fa99724742177/python/infer.py)。

## 查看部署效果

**固定样例已核对** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

da3-small 在 AXCL 上生成街景深度可视化；近处车辆和道路、远处建筑的层次与输入场景大致对应，输出张量均为有限数值。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/depth-anything-3/inputs/demo01.jpg)](../../../static/validation/effects/depth-anything-3/inputs/demo01.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/depth-anything-3/outputs/output-ax.png)](../../../static/validation/effects/depth-anything-3/outputs/output-ax.png)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 仅核对单张图片的相对层次，没有公制距离标定或深度真值。
- 该结果不证明 DA3 的多视角几何、相机估计或长视频功能；本次仅运行 python/infer.py 单图入口。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`7bf36032e88d4cfba089a6ddb05fa99724742177`。

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
| session.run：da3-small.axmodel | 39.254 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 仅核对单张图片的相对层次，没有公制距离标定或深度真值。
- 该结果不证明 DA3 的多视角几何、相机估计或长视频功能；本次仅运行 python/infer.py 单图入口。
- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/infer.py`](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/7bf36032e88d4cfba089a6ddb05fa99724742177/python/infer.py) | Python 程序 / 前后处理 |
| [`models-ax650/da3-small.axmodel`](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/7bf36032e88d4cfba089a6ddb05fa99724742177/models-ax650/da3-small.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`examples/demo01.jpg`](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/7bf36032e88d4cfba089a6ddb05fa99724742177/examples/demo01.jpg) | 示例输入 |

仓库提交：`7bf36032e88d4cfba089a6ddb05fa99724742177`。仓库中的 8 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Depth-Anything-3/tree/7bf36032e88d4cfba089a6ddb05fa99724742177)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 仓库有 small、base、mono 和 metric 权重。相对深度与公制深度的语义不同，选择后保留同一前后处理。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Depth-Anything-3/tree/7bf36032e88d4cfba089a6ddb05fa99724742177)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/7bf36032e88d4cfba089a6ddb05fa99724742177/README.md)。
- [主要程序入口：python/infer.py](https://huggingface.co/AXERA-TECH/Depth-Anything-3/blob/7bf36032e88d4cfba089a6ddb05fa99724742177/python/infer.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Depth-Anything-3)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
