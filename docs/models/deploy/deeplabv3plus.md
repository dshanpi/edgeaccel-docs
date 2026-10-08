---
title: "DeepLabv3Plus 部署指南"
sidebar_label: "DeepLabv3Plus"
description: "DeepLabv3Plus 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DeepLabv3Plus 部署指南

DeepLabv3Plus 用于图像分割。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `models-ax650/deeplabv3plus_mobilenet_u16.axmodel`。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/DeepLabv3Plus` 的固定版本。下面下载本页选用的 7 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/deeplabv3plus/6d29643d003d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeepLabv3Plus \
  "infer.py" \
  "models-ax650/deeplabv3plus_mobilenet_u16.axmodel" \
  "samples/1_image.png" \
  "datasets/__init__.py" \
  "datasets/cityscapes.py" \
  "datasets/utils.py" \
  "datasets/voc.py" \
  --revision 6d29643d003d7e7d22f7c28a177980f292ec5fca \
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


按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 `.upstream` 备份；原表达式不匹配时停止，避免误改其他版本。本例还将 CPU 后处理的 Torch argmax 改为 NumPy argmax，并保留同版本 VOC 调色板，从而无需安装 Torch/TorchVision；权重不变。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
edits = [
    {"path": "infer.py", "old": """import torch
""", "new": ""},
    {"path": "infer.py", "old": "from datasets import VOCSegmentation, Cityscapes, cityscapes", "new": """def voc_cmap(N=256, normalized=False):
    def bitget(byteval, idx):
        return ((byteval & (1 << idx)) != 0)

    dtype = 'float32' if normalized else 'uint8'
    cmap = np.zeros((N, 3), dtype=dtype)
    for i in range(N):
        r = g = b = 0
        c = i
        for j in range(8):
            r = r | (bitget(c, 0) << 7-j)
            g = g | (bitget(c, 1) << 7-j)
            b = b | (bitget(c, 2) << 7-j)
            c = c >> 3

        cmap[i] = np.array([r, g, b])

    cmap = cmap/255 if normalized else cmap
    return cmap

VOC_CMAP = voc_cmap()"""},
    {"path": "infer.py", "old": """    pred = torch.from_numpy(pred)
    pred = pred.max(1)[1].cpu().numpy()[0] # HW""", "new": "    pred = np.argmax(pred, axis=1)[0] # HW; same first-index argmax for finite logits"},
    {"path": "infer.py", "old": "decode_fn = VOCSegmentation.decode_target", "new": "decode_fn = lambda mask: VOC_CMAP[mask]"},
    {"path": "infer.py", "old": "axe.InferenceSession(model)", "new": "axe.InferenceSession(model, providers=[\"AXCLRTExecutionProvider\"])"}
]
for edit in edits:
    path = Path(edit.get("path", "infer.py"))
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
test -s models-ax650/deeplabv3plus_mobilenet_u16.axmodel
test -s samples/1_image.png
set -o pipefail
python infer.py --model models-ax650/deeplabv3plus_mobilenet_u16.axmodel --img samples/1_image.png 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `output-ax.png` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`infer.py` 源码](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/blob/6d29643d003d7e7d22f7c28a177980f292ec5fca/infer.py)。

## 查看部署效果

**固定样例已核对** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定飞机图片的分割主体已核对：机身、机翼、尾翼和起落架的位置与输入一致。螺旋桨及细边缘较粗，局部存在漏分或外扩；下方叠加图用于检查这些边界。

**飞机前景与边界**

依次显示实际输入、原始分割掩码和叠加图。叠加图由保存的原图与原始掩码在主机上按50%颜色混合生成，背景不变，未修正掩码；不是新增推理输出。

<div className="model-effect-gallery">

<figure>

[![实际输入：513×513 飞机图](../../../static/validation/effects/deeplabv3plus/inputs/1_image.png)](../../../static/validation/effects/deeplabv3plus/inputs/1_image.png)

<figcaption>实际输入：513×513 飞机图</figcaption>
</figure>

<figure>

[![原始输出掩码](../../../static/validation/effects/deeplabv3plus/outputs/output-ax.png)](../../../static/validation/effects/deeplabv3plus/outputs/output-ax.png)

<figcaption>原始输出掩码</figcaption>
</figure>

<figure>

[![原图与掩码叠加（主机生成，未修正掩码）](../../../static/validation/effects/deeplabv3plus/outputs/input-mask-overlay.png)](../../../static/validation/effects/deeplabv3plus/outputs/input-mask-overlay.png)

<figcaption>原图与掩码叠加（主机生成，未修正掩码）</figcaption>
</figure>

</div>

**使用时注意：**

- 叠加图由保存的原图与原始掩码在主机上按50%颜色混合生成，背景不变，未修正掩码；不是新增推理输出。
- 仅人工核对 1 张 513×513 飞机图和输出掩码，未使用像素级真值，未计算 mIoU 或类别准确率。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`6d29643d003d7e7d22f7c28a177980f292ec5fca`。

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
| 输入与输出掩码尺寸 | 513×513 | 实际 PNG 文件头；输入与可视化输出一致 |
| 分割张量形状 | 1×21×513×513 | tensors.json 实际输出；全部 5526549 元素为有限数值 |
| 单次 session.run 时延 | 113.74 | 毫秒；主机墙钟，包含 AXCL 调用及数据复制，排除张量统计，不是纯 NPU 时延 |
| session.run：deeplabv3plus_mobilenet_u16.axmodel | 113.744 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 未审核全部 21 类；红色仅为可视化类别色，不代表已独立确认所有类别映射。
- 只记录一次 session.run，不是热身后的平均时延或稳定性测试。
- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer.py`](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/blob/6d29643d003d7e7d22f7c28a177980f292ec5fca/infer.py) | Python 程序 / 前后处理 |
| [`models-ax650/deeplabv3plus_mobilenet_u16.axmodel`](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/blob/6d29643d003d7e7d22f7c28a177980f292ec5fca/models-ax650/deeplabv3plus_mobilenet_u16.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`samples/1_image.png`](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/blob/6d29643d003d7e7d22f7c28a177980f292ec5fca/samples/1_image.png) | 示例输入 |

仓库提交：`6d29643d003d7e7d22f7c28a177980f292ec5fca`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/tree/6d29643d003d7e7d22f7c28a177980f292ec5fca)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 选择 models-ax650/deeplabv3plus_mobilenet_u16.axmodel，输入为 513×513。输出是 VOC 语义分割类别图，不是实例编号。
- 本次实测使用下方完整补丁：将 Torch 的通道维 max 改为 NumPy argmax(axis=1)，并直接使用同一 revision 的 datasets/voc.py 中 VOC 调色板函数。未更换权重、输入布局、预处理或类别映射。
- 应用补丁后不再导入 Torch、torchvision 或 datasets 包，运行文件只需本页列出的 infer.py、权重和样图；补丁中的所有替换必须一起应用。
- NumPy argmax 与原后处理按有限 logits 核对；实际输出已记录于实测张量日志。此补丁没有执行原 Torch 程序作逐像素对照，不将其写成两实现等价性测试通过。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/tree/6d29643d003d7e7d22f7c28a177980f292ec5fca)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/blob/6d29643d003d7e7d22f7c28a177980f292ec5fca/README.md)。
- [主要程序入口：infer.py](https://huggingface.co/AXERA-TECH/DeepLabv3Plus/blob/6d29643d003d7e7d22f7c28a177980f292ec5fca/infer.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/DeepLabv3Plus)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
