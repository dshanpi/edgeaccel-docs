---
title: "MiniCPM-V-4.6-GPTQ-AX637 部署指南"
sidebar_label: "MiniCPM-V-4.6-GPTQ-AX637"
description: "MiniCPM-V-4.6-GPTQ-AX637 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM-V-4.6-GPTQ-AX637 部署指南

MiniCPM-V-4.6-GPTQ-AX637 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。非本卡编译目标。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该仓库名称指定的芯片不是本指南的 AX650 / AX8850 系列卡目标。不能通过改文件名、换主机架构或调整 AXCL 参数使其变成当前卡的权重。

先选择 AX650 / AX8850 的独立编译版本；没有相应权重时，按[转换自有模型](../custom-model.md)准备原始模型、量化数据和目标芯片配置。

可继续核对的同系列条目：[MiniCPM-V-4.6-GPTQ](minicpm-v-4-6-gptq.md)、[MiniCPM-V-4.6-GPTQ-INT4-C256-P6K-CTX8K](minicpm-v-4-6-gptq-int4-c256-p6k-ctx8k.md)。具体上下文和任务是否等价，仍以各自页面为准。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 使用已知内容的单张图片提问，回答应包含可核对的图像细节。
- 再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/config.json) | 运行配置 |
| [`qwen3_5_text_post.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/qwen3_5_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`minicpm_v46_tokenizer.txt`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/minicpm_v46_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`minicpmv4_6_vision_448.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/minicpmv4_6_vision_448.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/post_config.json) | 运行配置 |
| [`qwen3_5_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/qwen3_5_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/qwen3_5_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/qwen3_5_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/qwen3_5_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/openai_api_demo.png`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/assets/openai_api_demo.png) | 示例输入 |

仓库提交：`d52aef1aabcf08e7554ee259b36f90876726f993`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/tree/d52aef1aabcf08e7554ee259b36f90876726f993)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/tree/d52aef1aabcf08e7554ee259b36f90876726f993)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM-V-4.6-GPTQ-AX637/blob/d52aef1aabcf08e7554ee259b36f90876726f993/README.md)。
- [配套项目：AXERA-TECH/MiniCPM-V-4.6.axera](https://github.com/AXERA-TECH/MiniCPM-V-4.6.axera)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。
- [配套项目：AXERA-TECH/ax-llm.git](https://github.com/AXERA-TECH/ax-llm.git)。

返回[完整模型目录](../catalog.mdx)。
