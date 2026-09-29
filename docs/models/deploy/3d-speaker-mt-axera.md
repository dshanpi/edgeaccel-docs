---
title: "3D-Speaker-MT.Axera 部署指南"
sidebar_label: "3D-Speaker-MT.Axera"
description: "3D-Speaker-MT.Axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# 3D-Speaker-MT.Axera 部署指南

3D-Speaker-MT.Axera 用于音频理解与记录。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL Python 线索。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

模型卡含 Python / AXCL 相关信息，但可用 provider 列表不等于本示例实际使用 AXCL。先核对下列入口与会话创建方式，再形成可执行的部署组合。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`ax_meeting/utils/infer_func.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_func.py) | 仅文件清单已确认，调用方式待核对 |
| [`ax_meeting/utils/infer_utils.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_utils.py) | 仅文件清单已确认，调用方式待核对 |
| [`ax_meeting_transc_demo.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting_transc_demo.py) | 仅文件清单已确认，调用方式待核对 |
| [`build/lib/ax_meeting/utils/infer_func.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/build/lib/ax_meeting/utils/infer_func.py) | 仅文件清单已确认，调用方式待核对 |
| [`build/lib/ax_meeting/utils/infer_utils.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/build/lib/ax_meeting/utils/infer_utils.py) | 仅文件清单已确认，调用方式待核对 |
| [`examples/diar_asr_offline.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/examples/diar_asr_offline.py) | 仅文件清单已确认，调用方式待核对 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`assert/meeting_demo.png`、`assert/meeting_ui.jpg`、`ax_meeting/_upload_1566a625-52a6-4663-a62b-7570dac7b7dd_20200327_2P.wav`、`ax_meeting/_upload_1676128a-2d16-45b0-a3d5-faa94dea89bd_20200327_2P.wav`、`ax_meeting/_upload_176e329f-da53-4e64-85ca-4ba3f7ac76a3_20200327_2P.wav`、`ax_meeting/_upload_911af462-37e5-4314-911b-78fd3024cb7f_20200327_2P.wav`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。分别完成各子模型后，才能连接完整应用。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/3D-Speaker-MT.Axera` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/3d-speaker-mt-axera/3592794622a5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/3D-Speaker-MT.Axera \
  --revision 3592794622a5627aca47c81fdc2569e632ffc910 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 分别验证每个模型阶段的真实输入、输出和后端，再启动完整应用。
- 检查服务地址、错误传播、超时与资源释放；某个子模型运行不代表整条链路完成。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_meeting/utils/infer_func.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_func.py) | Python 程序 / 前后处理 |
| [`ax_meeting/utils/infer_utils.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_utils.py) | Python 程序 / 前后处理 |
| [`ax_meeting/ax_model/campplus.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/ax_model/campplus.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_meeting/ax_model/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/ax_model/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_meeting/ax_model/vad.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/ax_model/vad.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/campplus.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_model/campplus.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_model/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assert/gradio_demo.JPG`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/assert/gradio_demo.JPG) | 配套资源 |
| [`assert/meeting_demo.png`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/assert/meeting_demo.png) | 示例输入 |
| [`ax_meeting/utils/sentencepiece_tokenizer.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/sentencepiece_tokenizer.py) | 旧版分词服务入口 |
| [`build/lib/ax_meeting/utils/sentencepiece_tokenizer.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/build/lib/ax_meeting/utils/sentencepiece_tokenizer.py) | 旧版分词服务入口 |
| [`config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/requirements.txt) | Python 依赖清单 |
| [`utils/sentencepiece_tokenizer.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/utils/sentencepiece_tokenizer.py) | 旧版分词服务入口 |

仓库提交：`3592794622a5627aca47c81fdc2569e632ffc910`。仓库中的 9 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/tree/3592794622a5627aca47c81fdc2569e632ffc910)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/tree/3592794622a5627aca47c81fdc2569e632ffc910)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/README.md)。
- [主要程序入口：ax_meeting/utils/infer_func.py](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_func.py)。
- [配套项目：AXERA-TECH/3D-Speaker-MT.axera](https://github.com/AXERA-TECH/3D-Speaker-MT.axera)。
- [配套项目：AXERA-TECH/3D-Speaker-MT.axera](https://github.com/AXERA-TECH/3D-Speaker-MT.axera/tree/main/model_convert)。
- [配套项目：AXERA-TECH/3D-Speaker.axera](https://github.com/AXERA-TECH/3D-Speaker.axera/tree/master)。

返回[完整模型目录](../catalog.mdx)。
