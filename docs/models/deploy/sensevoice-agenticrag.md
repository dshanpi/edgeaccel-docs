---
title: "SenseVoice_AgenticRAG 部署指南"
sidebar_label: "SenseVoice_AgenticRAG"
description: "SenseVoice_AgenticRAG 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SenseVoice_AgenticRAG 部署指南

SenseVoice_AgenticRAG 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`python/gradio_demo.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/gradio_demo.py) | 需要继续核对后端与依赖 |
| [`python/main.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/main.py) | 需要继续核对后端与依赖 |
| [`python/test_wer.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/test_wer.py) | 需要继续核对后端与依赖 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`example/en.mp3`、`example/ja.mp3`、`example/ko.mp3`、`example/yue.mp3`、`example/zh.mp3`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。本页列出的目标路径包括 `sensevoice_ax650/sensevoice.axmodel`、`sensevoice_ax650/sensevoice/sensevoice.axmodel`。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。分别完成各子模型后，才能连接完整应用。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/SenseVoice_AgenticRAG` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/sensevoice-agenticrag/748b06f6b0e4
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SenseVoice_AgenticRAG \
  --revision 748b06f6b0e43660f2092dbcf158189f543ab88c \
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
| [`python/gradio_demo.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/gradio_demo.py) | Python 程序 / 前后处理 |
| [`python/main.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/main.py) | Python 程序 / 前后处理 |
| [`sensevoice_ax650/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/sensevoice/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/sensevoice/streaming_sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice/streaming_sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/streaming_sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/streaming_sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/requirements.txt) | Python 依赖清单 |
| [`sensevoice_ax630c/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax630c/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax650/sensevoice/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax650/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/tokens.txt) | 分词器 / 字典，必须配套 |

仓库提交：`748b06f6b0e43660f2092dbcf158189f543ab88c`。仓库中的 6 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/tree/748b06f6b0e43660f2092dbcf158189f543ab88c)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/tree/748b06f6b0e43660f2092dbcf158189f543ab88c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/README.md)。
- [主要程序入口：python/gradio_demo.py](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/gradio_demo.py)。
- [配套项目：AXERA-TECH/ax_asr_api](https://github.com/AXERA-TECH/ax_asr_api)。
- [配套项目：AXERA-TECH/pyaxengine](https://github.com/AXERA-TECH/pyaxengine)。
- [配套项目：FunAudioLLM/SenseVoice](https://github.com/FunAudioLLM/SenseVoice)。

返回[完整模型目录](../catalog.mdx)。
