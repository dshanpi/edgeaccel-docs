---
title: "Bird-Species-Classification 部署指南"
sidebar_label: "Bird-Species-Classification"
description: "Bird-Species-Classification 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Bird-Species-Classification 部署指南

Bird-Species-Classification 用于图像分类。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `model/bird-s/AX650/bird_650_npu3.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Bird-Species-Classification` 的固定版本。下面下载本页选用的 4 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/bird-species-classification/b81b4cb3be06
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Bird-Species-Classification \
  "axmodel_infer.py" \
  "model/bird-s/AX650/bird_650_npu3.axmodel" \
  "class_name.txt" \
  "test_images/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg" \
  --revision b81b4cb3be067a85ba730c5b2a67c566d3d9af68 \
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
python -m pip install numpy==1.26.4 ml-dtypes==0.5.3 opencv-python-headless==4.11.0.86 matplotlib Pillow
```


按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 `.upstream` 备份；原表达式不匹配时停止，避免误改其他版本。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
edits = [
    {"path": "axmodel_infer.py", "old": "providers = ['AxEngineExecutionProvider']", "new": "providers = ['AXCLRTExecutionProvider']"}
]
for edit in edits:
    path = Path(edit.get("path", "axmodel_infer.py"))
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
test -s model/bird-s/AX650/bird_650_npu3.axmodel
test -s test_images/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg
set -o pipefail
python axmodel_infer.py --model_file model/bird-s/AX650/bird_650_npu3.axmodel --class_map_file class_name.txt --image test_images/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg --image_size 224 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `prediction_result_top5.png` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`axmodel_infer.py` 源码](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/axmodel_infer.py)。

## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

使用 bird-s 权重并显式传入 --image_size 224 后完成推理，生成 Top-5 图片。Top-1 为 Ciccaba_virgata，分数 0.0727；只能确认分类程序运行，物种识别效果未通过独立核对。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/bird-species-classification/inputs/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg)](../../../static/validation/effects/bird-species-classification/inputs/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/bird-species-classification/outputs/prediction_result_top5.png)](../../../static/validation/effects/bird-species-classification/outputs/prediction_result_top5.png)

<figcaption>实际输出</figcaption>
</figure>

</div>

**使用时注意：**

- 初次沿用脚本默认 384×384，模型要求 224×224，出现 shape 错误；脚本捕获异常后仍返回 0，不能只看退出码。
- 修正输入尺寸后分数仍低，文件名编号 03111 未出现在本次 Top-5 编号中；需进一步核对类别映射、前处理与该样本标注。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`b81b4cb3be067a85ba730c5b2a67c566d3d9af68`。

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
| Top-1 分数 | 0.0727 | 单个固定样本的 Softmax 分数，非准确率 |
| session.run：bird_650_npu3.axmodel | 8.519 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 初次沿用脚本默认 384×384，模型要求 224×224，出现 shape 错误；脚本捕获异常后仍返回 0，不能只看退出码。
- 修正输入尺寸后分数仍低，文件名编号 03111 未出现在本次 Top-5 编号中；需进一步核对类别映射、前处理与该样本标注。
- 本次不作为鸟种分类精度验证，不推荐仅按 Top-1 结果直接做业务判断。
- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`axmodel_infer.py`](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/axmodel_infer.py) | Python 程序 / 前后处理 |
| [`model/bird-s/AX650/bird_650_npu3.axmodel`](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/model/bird-s/AX650/bird_650_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`class_name.txt`](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/class_name.txt) | 配套资源 |
| [`test_images/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg`](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/test_images/03111_2c0dfa5a-c4a0-47f8-ac89-6a289208050f.jpg) | 示例输入 |

仓库提交：`b81b4cb3be067a85ba730c5b2a67c566d3d9af68`。仓库中的 20 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/tree/b81b4cb3be067a85ba730c5b2a67c566d3d9af68)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 仓库包含 bird-s、bird-m、bird-l 和 bird-end2end。端到端方案分检测与识别两段，不能只加载其中一段就视为分类链路完成。
- 上游主函数捕获推理异常并打印 Inference failed 后可能退出码仍为 0，必须检查输出文件与 Top-5 文本。
- 选择 bird-s 直接分类路径，未验证两阶段 bird-end2end。
- bird-s 这份 AX650 权重的输入为 224×224，必须显式传入 --image_size 224。上游脚本默认 384×384 与此文件不匹配；首次实测因此未生成结果，修正尺寸后完成推理。
- 修正尺寸后的本次 Top-1 分数仅 0.0727。必须检查 Top-5 文本和新生成的 prediction_result_top5.png；退出码 0、完成推理或低置信度 Top-1 都不能单独证明鸟种识别正确。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/tree/b81b4cb3be067a85ba730c5b2a67c566d3d9af68)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/README.md)。
- [主要程序入口：axmodel_infer.py](https://huggingface.co/AXERA-TECH/Bird-Species-Classification/blob/b81b4cb3be067a85ba730c5b2a67c566d3d9af68/axmodel_infer.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Bird-Species-Classification)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
