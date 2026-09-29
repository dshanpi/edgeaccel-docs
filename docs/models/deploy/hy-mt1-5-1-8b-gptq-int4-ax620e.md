---
title: "HY-MT1.5-1.8B_GPTQ_INT4-AX620E 部署指南"
sidebar_label: "HY-MT1.5-1.8B_GPTQ_INT4-AX620E"
description: "HY-MT1.5-1.8B_GPTQ_INT4-AX620E 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# HY-MT1.5-1.8B_GPTQ_INT4-AX620E 部署指南

HY-MT1.5-1.8B_GPTQ_INT4-AX620E 用于文本翻译。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。非本卡编译目标。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该仓库名称指定的芯片不是本指南的 AX650 / AX8850 系列卡目标。不能通过改文件名、换主机架构或调整 AXCL 参数使其变成当前卡的权重。

先选择 AX650 / AX8850 的独立编译版本；没有相应权重时，按[转换自有模型](../custom-model.md)准备原始模型、量化数据和目标芯片配置。

可继续核对的同系列条目：[HY-MT1.5-1.8B_GPTQ_INT4](hy-mt1-5-1-8b-gptq-int4.md)。具体上下文和任务是否等价，仍以各自页面为准。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 先测短问答，再测两轮上下文；翻译模型使用有参考译文的短句。
- 记录首 token 延迟、生成速率和实际上下文长度，确认没有乱码、持续重复或异常提前结束。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gradio_cpp_backend.py`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/gradio_cpp_backend.py) | Python 程序 / 前后处理 |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/gradio_demo.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/config.json) | 运行配置 |
| [`hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_post.axmodel`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`hymt1-5_1k_ax620e_axmodel/model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`hymt1-5-1.8b_tokenizer.txt`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5-1.8b_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/post_config.json) | 运行配置 |
| [`hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_1k_ax620e_axmodel/hunyuan_v1_dense_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`hymt1-5_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_tokenizer/config.json) | 运行配置 |
| [`hymt1-5_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/hymt1-5_tokenizer/generation_config.json) | 运行配置 |

仓库提交：`3f3c4b6fa107fefa4bac4b3eda75b340908de888`。仓库中的 33 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/tree/3f3c4b6fa107fefa4bac4b3eda75b340908de888)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/tree/3f3c4b6fa107fefa4bac4b3eda75b340908de888)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/README.md)。
- [主要程序入口：gradio_cpp_backend.py](https://huggingface.co/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4-AX620E/blob/3f3c4b6fa107fefa4bac4b3eda75b340908de888/gradio_cpp_backend.py)。
- [配套项目：AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4.axera](https://github.com/AXERA-TECH/HY-MT1.5-1.8B_GPTQ_INT4.axera/tree/main/model_convert)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-internvl)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-internvl)。

返回[完整模型目录](../catalog.mdx)。
