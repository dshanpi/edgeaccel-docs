---
title: "MiniCPM5-2B-GPTQ-Int4 部署指南"
sidebar_label: "MiniCPM5-2B-GPTQ-Int4"
description: "MiniCPM5-2B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM5-2B-GPTQ-Int4 部署指南

MiniCPM5-2B-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/MiniCPM5-2B-GPTQ-Int4` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/minicpm5-2b-gptq-int4/eb062da85bfa
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MiniCPM5-2B-GPTQ-Int4 \
  --revision eb062da85bfa5c839905da40911967263988dd6d \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 先测短问答，再测两轮上下文；翻译模型使用有参考译文的短句。
- 记录首 token 延迟、生成速率和实际上下文长度，确认没有乱码、持续重复或异常提前结束。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/blob/eb062da85bfa5c839905da40911967263988dd6d/config.json) | 运行配置 |
| [`generation_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/blob/eb062da85bfa5c839905da40911967263988dd6d/generation_config.json) | 运行配置 |
| [`quantize_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/blob/eb062da85bfa5c839905da40911967263988dd6d/quantize_config.json) | 运行配置 |
| [`tokenizer_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/blob/eb062da85bfa5c839905da40911967263988dd6d/tokenizer_config.json) | 运行配置 |

仓库提交：`eb062da85bfa5c839905da40911967263988dd6d`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/tree/eb062da85bfa5c839905da40911967263988dd6d)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是模型变体集合入口。优先选择明确标注 AX650 与上下文规格的子版本部署，避免将汇总配置当成运行配置。
- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 该提交未直接列出 .axmodel 文件；先核对模型卡指向的实际权重或程序仓库，不能将该目录直接交给 axcl_run_model。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/tree/eb062da85bfa5c839905da40911967263988dd6d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/blob/eb062da85bfa5c839905da40911967263988dd6d/README.md)。

返回[完整模型目录](../catalog.mdx)。
