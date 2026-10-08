---
title: "RT-DETR 部署指南"
sidebar_label: "RT-DETR"
description: "RT-DETR 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# RT-DETR 部署指南

RT-DETR 用于目标检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `rtdetr_msda.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/RT-DETR` 的固定版本。下面下载本页选用的 3 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/rt-detr/38efdf670e0a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/RT-DETR \
  "axmodel_inference.py" \
  "rtdetr_msda.axmodel" \
  "ssd_horse.jpg" \
  --revision 38efdf670e0a4c78d3d8e4f67d76058221bbfd0a \
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
python -m pip install numpy==1.26.4 ml-dtypes==0.5.3 opencv-python-headless==4.11.0.86 Pillow
```


按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 `.upstream` 备份；原表达式不匹配时停止，避免误改其他版本。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
edits = [
    {"path": "axmodel_inference.py", "old": "axe.InferenceSession(model_path)", "new": "axe.InferenceSession(model_path, providers=[\"AXCLRTExecutionProvider\"])"}
]
for edit in edits:
    path = Path(edit.get("path", "axmodel_inference.py"))
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
test -s rtdetr_msda.axmodel
test -s ssd_horse.jpg
set -o pipefail
python axmodel_inference.py  2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `output.jpg` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`axmodel_inference.py` 源码](https://huggingface.co/AXERA-TECH/RT-DETR/blob/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a/axmodel_inference.py)。

## 查看部署效果

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

本次 8GB 样例输出马、两名人物、货车和 bench 共 5 个框。前景犬只没有检测框，远处 bench 类别未独立确认；本次效果核对未通过，保留实际图片与原始结果。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/rt-detr/inputs/ssd_horse.jpg)](../../../static/validation/effects/rt-detr/inputs/ssd_horse.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/rt-detr/outputs/output.jpg)](../../../static/validation/effects/rt-detr/outputs/output.jpg)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 存在可见犬只漏检，未完成全类别正确性核对。
- 只有一张输入、一次 session.run；没有 mAP、完整召回率或稳定性结果。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`38efdf670e0a4c78d3d8e4f67d76058221bbfd0a`。

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
| session.run：rtdetr_msda.axmodel | 21.703 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`axmodel_inference.py`](https://huggingface.co/AXERA-TECH/RT-DETR/blob/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a/axmodel_inference.py) | Python 程序 / 前后处理 |
| [`rtdetr_msda.axmodel`](https://huggingface.co/AXERA-TECH/RT-DETR/blob/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a/rtdetr_msda.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ssd_horse.jpg`](https://huggingface.co/AXERA-TECH/RT-DETR/blob/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a/ssd_horse.jpg) | 示例输入 |

仓库提交：`38efdf670e0a4c78d3d8e4f67d76058221bbfd0a`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/RT-DETR/tree/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/RT-DETR/tree/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/RT-DETR/blob/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a/README.md)。
- [主要程序入口：axmodel_inference.py](https://huggingface.co/AXERA-TECH/RT-DETR/blob/38efdf670e0a4c78d3d8e4f67d76058221bbfd0a/axmodel_inference.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/RT-DETR)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
