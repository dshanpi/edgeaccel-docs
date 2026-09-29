---
title: "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448 部署指南"
sidebar_label: "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448"
description: "Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448 部署指南

Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。非本卡编译目标。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该仓库名称指定的芯片不是本指南的 AX650 / AX8850 系列卡目标。不能通过改文件名、换主机架构或调整 AXCL 参数使其变成当前卡的权重。

先选择 AX650 / AX8850 的独立编译版本；没有相应权重时，按[转换自有模型](../custom-model.md)准备原始模型、量化数据和目标芯片配置。

可继续核对的同系列条目：[Qwen3-VL-2B-Instruct-GPTQ-Int4](qwen3-vl-2b-instruct-gptq-int4.md)、[Qwen3-VL-2B-Instruct-GPTQ-Int4-C256-P3584-CTX4095](qwen3-vl-2b-instruct-gptq-int4-c256-p3584-ctx4095.md)、[Qwen3-VL-2B-Instruct-GPTQ-Int4-C512-P3584-CTX4095](qwen3-vl-2b-instruct-gptq-int4-c512-p3584-ctx4095.md)、[Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047](qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047.md)。具体上下文和任务是否等价，仍以各自页面为准。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 使用已知内容的单张图片提问，回答应包含可核对的图像细节。
- 再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/gradio_demo.py) | Python 程序 / 前后处理 |
| [`qwen3_tokenizer.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3_tokenizer.py) | 旧版分词服务入口 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-2B-Instruct_vision_u8_320_ax630c.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/Qwen3-VL-2B-Instruct_vision_u8_320_ax630c.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/post_config.json) | 运行配置 |
| [`Qwen3-VL-2B-Instruct_vision_u8_384_ax630c.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/Qwen3-VL-2B-Instruct_vision_u8_384_ax630c.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p64_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3_vl_text_p64_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p64_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3_vl_text_p64_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p64_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3_vl_text_p64_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/images/demo.jpg) | 示例输入 |
| [`qwen3-vl-tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/qwen3-vl-tokenizer/config.json) | 运行配置 |

仓库提交：`c06b111eda89157875cdde1f42ed35bf3e917331`。仓库中的 31 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/tree/c06b111eda89157875cdde1f42ed35bf3e917331)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/tree/c06b111eda89157875cdde1f42ed35bf3e917331)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/README.md)。
- [主要程序入口：gradio_demo.py](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-AX630C-P320-CTX448/blob/c06b111eda89157875cdde1f42ed35bf3e917331/gradio_demo.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。
- [配套项目：AXERA-TECH/ax-llm.git](https://github.com/AXERA-TECH/ax-llm.git)。

返回[完整模型目录](../catalog.mdx)。
