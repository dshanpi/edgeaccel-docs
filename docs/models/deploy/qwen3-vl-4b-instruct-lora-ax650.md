---
title: "Qwen3-VL-4B-Instruct-LoRA-AX650 部署指南"
sidebar_label: "Qwen3-VL-4B-Instruct-LoRA-AX650"
description: "Qwen3-VL-4B-Instruct-LoRA-AX650 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-4B-Instruct-LoRA-AX650 部署指南

Qwen3-VL-4B-Instruct-LoRA-AX650 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 尚未通过本机部署验证。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-VLM-AX650-P1536-C2048-Chunk128` |
| 分词器类型（tokenizer_type） | `Qwen3VL` |
| 多模态类型（vlm_type） | `Qwen3VL` |
| Transformer 层数 | 36 |
| 分片命名模板 | `qwen3_vl_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_vl_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen3_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `Qwen3-VL-4B-Instruct_vision.axmodel` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 36 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 准备本模型的输入

本提交可核对的样本：`assets/chartqa_00.png`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-4b-instruct-lora-ax650/e68e2e360d6d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650 \
  --revision e68e2e360d6ddcd3de7c8c9dde6040f6d1885679 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**暂未提供可复现的 M.2 算力卡部署效果。** 官方包提供 ChartQA 和 Design 两组 LoRA，面向文本聊天与单张图片请求。待配套 AXCL 运行时验证通过后，本页再补充操作命令和实际输出。图片问答可先参考已验证的 [Qwen3-VL-4B 基础版](./qwen3-vl-4b-instruct.md)。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-4B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/Qwen3-VL-4B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/post_config.json) | 运行配置 |
| [`Qwen3-VL-4B-Instruct_vision_u8.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/Qwen3-VL-4B-Instruct_vision_u8.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`lora/qwen3-vl-lora-chartqa/source_adapter_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/lora/qwen3-vl-lora-chartqa/source_adapter_config.json) | 运行配置 |
| [`lora/qwen3-vl-lora-design/source_adapter_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/lora/qwen3-vl-lora-design/source_adapter_config.json) | 运行配置 |

仓库提交：`e68e2e360d6ddcd3de7c8c9dde6040f6d1885679`。仓库中的 39 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/tree/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 包内服务器是 AX650 aarch64 板端程序。除基础模型外还有两组 LoRA；AXCL 部署还需确认对应运行时具备相同 LoRA 加载能力，不能用本站普通 VLM 命令替代。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/tree/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct-LoRA-AX650/blob/e68e2e360d6ddcd3de7c8c9dde6040f6d1885679/README.md)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
