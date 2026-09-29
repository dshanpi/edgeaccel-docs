---
title: "lcm-lora-sdv1-5-ax620e 部署指南"
sidebar_label: "lcm-lora-sdv1-5-ax620e"
description: "lcm-lora-sdv1-5-ax620e 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# lcm-lora-sdv1-5-ax620e 部署指南

lcm-lora-sdv1-5-ax620e 用于图像生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。非本卡编译目标。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该仓库名称指定的芯片不是本指南的 AX650 / AX8850 系列卡目标。不能通过改文件名、换主机架构或调整 AXCL 参数使其变成当前卡的权重。

先选择 AX650 / AX8850 的独立编译版本；没有相应权重时，按[转换自有模型](../custom-model.md)准备原始模型、量化数据和目标芯片配置。

可继续核对的同系列条目：[lcm-lora-sdv1-5](lcm-lora-sdv1-5.md)。具体上下文和任务是否等价，仍以各自页面为准。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 固定提示词、随机种子、步数和分辨率，检查图像内容和明显伪影。
- 分别记录首图耗时、后续耗时与峰值内存，验证各阶段输出接口一致。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`launcher.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/launcher.py) | Python 程序 / 前后处理 |
| [`models/text_encoder/sd15_text_encoder_sim.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models/text_encoder/sd15_text_encoder_sim.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/unet.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models/unet.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/vae_decoder.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models/vae_decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/vae_encoder.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models/vae_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models_320x320/text_encoder/sd15_text_encoder_sim.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models_320x320/text_encoder/sd15_text_encoder_sim.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/gradio_demo.png`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/assets/gradio_demo.png) | 示例输入 |
| [`config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/config.json) | 运行配置 |
| [`models/text_encoder/config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models/text_encoder/config.json) | 运行配置 |
| [`models/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models/tokenizer/tokenizer_config.json) | 运行配置 |
| [`models_320x320/text_encoder/config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models_320x320/text_encoder/config.json) | 运行配置 |
| [`models_320x320/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/models_320x320/tokenizer/tokenizer_config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/requirements.txt) | Python 依赖清单 |
| [`run_img2img_axe_infer.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/run_img2img_axe_infer.py) | Python 程序 / 前后处理 |

仓库提交：`11989dcb8c92684e38fc8c86a86721e93b64a7c3`。仓库中的 8 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/tree/11989dcb8c92684e38fc8c86a86721e93b64a7c3)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/tree/11989dcb8c92684e38fc8c86a86721e93b64a7c3)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/README.md)。
- [主要程序入口：launcher.py](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5-ax620e/blob/11989dcb8c92684e38fc8c86a86721e93b64a7c3/launcher.py)。

返回[完整模型目录](../catalog.mdx)。
