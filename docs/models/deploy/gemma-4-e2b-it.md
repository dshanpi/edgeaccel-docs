---
title: "gemma-4-E2B-it 部署指南"
sidebar_label: "gemma-4-E2B-it"
description: "gemma-4-E2B-it 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# gemma-4-E2B-it 部署指南

gemma-4-E2B-it 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 尚未通过本机部署验证。已知 AXCL 限制。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

上游 AX-LLM 已记录 Gemma-4 在 AXCL 后端的输出异常。本页保留版本、文件与验证条件，当前不提供面向业务使用的启动步骤。

缺陷依据：[AX-LLM AXCL 相关问题](https://github.com/AXERA-TECH/ax-llm/issues/39)。升级运行时后需固定新提交，用相同输入检查输出内容，再更新此页状态。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/gemma-4-E2B-it` |
| 分词器类型（tokenizer_type） | `Gemma4VL` |
| 多模态类型（vlm_type） | `Gemma4VL` |
| Transformer 层数 | 35 |
| 分片命名模板 | `gemma4_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `gemma4_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `gemma4_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `gemma4_vision_h336_w480_t70.axmodel` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 35 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gradio_demo.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/infer_axmodel.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`assets/gemma4_audio_test_5s.wav`、`assets/gemma4_audio_test_chunk0_30s.wav`、`assets/gemma4_audio_test_chunk1_30s.wav`、`assets/gemma4_axera_banner.jpg`、`assets/gemma4_axera_banner.png`、`assets/openai_api_demo.png`。结合模型卡选择输入，结果图片不作为原始输入。

## 查看部署效果

**当前尚无通过验证的 AXCL 算力卡部署组合。** 上游仍记录了 Gemma 4 在 AXCL 后端的输出异常，需等待兼容运行组合并完成本机复测。状态见[官方问题记录](https://github.com/AXERA-TECH/ax-llm/issues/39)。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gradio_demo.py) | Python 程序 / 前后处理 |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/config.json) | 运行配置 |
| [`gemma4_text_post.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`gemma4_tokenizer.txt`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`gemma4_vision_h336_w480_t70.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_vision_h336_w480_t70.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/post_config.json) | 运行配置 |
| [`gemma4_audio_30s.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_audio_30s.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`gemma4_audio_5s.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_audio_5s.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`gemma4_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`gemma4_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`gemma4_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gemma4_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/openai_api_demo.png`](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/assets/openai_api_demo.png) | 示例输入 |

仓库提交：`452478de7867c162165b46f53e709f5d3d4bc3ad`。仓库中的 41 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/tree/452478de7867c162165b46f53e709f5d3d4bc3ad)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/tree/452478de7867c162165b46f53e709f5d3d4bc3ad)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/README.md)。
- [主要程序入口：gradio_demo.py](https://huggingface.co/AXERA-TECH/gemma-4-E2B-it/blob/452478de7867c162165b46f53e709f5d3d4bc3ad/gradio_demo.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。
- [配套项目：AXERA-TECH/ax-llm.git](https://github.com/AXERA-TECH/ax-llm.git)。
- [配套项目：AXERA-TECH/gemma-4-E2B-it.axera](https://github.com/AXERA-TECH/gemma-4-E2B-it.axera)。

返回[完整模型目录](../catalog.mdx)。
