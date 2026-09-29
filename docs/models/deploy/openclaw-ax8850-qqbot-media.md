---
title: "openclaw-ax8850-qqbot-media 部署指南"
sidebar_label: "openclaw-ax8850-qqbot-media"
description: "openclaw-ax8850-qqbot-media 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# openclaw-ax8850-qqbot-media 部署指南

openclaw-ax8850-qqbot-media 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。
## 核对运行配置

配置文件：`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-VL-2B-Instruct` |
| 分词器类型（tokenizer_type） | `Qwen3VL` |
| 多模态类型（vlm_type） | `Qwen3VL` |
| Transformer 层数 | 28 |
| 分片命名模板 | `qwen3_vl_text_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_vl_text_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/Qwen3-VL-2B-Instruct_vision.axmodel` | 已找到 |
| `post_config_path` | `vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/post_config.json` | 已找到 |

逐层核对 28 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 准备本模型的输入

本提交可核对的样本：`SenseVoiceSmall-axmodel/test_wavs/en.wav`、`SenseVoiceSmall-axmodel/test_wavs/ja.wav`、`SenseVoiceSmall-axmodel/test_wavs/ko.wav`、`SenseVoiceSmall-axmodel/test_wavs/yue.wav`、`SenseVoiceSmall-axmodel/test_wavs/zh.wav`、`kokoro/kokoro-1.1-sid-1-en.wav`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。本页列出的目标路径包括 `SenseVoiceSmall-axmodel/ax650/model-10-seconds.axmodel`。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。分别完成各子模型后，才能连接完整应用。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/openclaw-ax8850-qqbot-media` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/openclaw-ax8850-qqbot-media/45cbc485b03f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/openclaw-ax8850-qqbot-media \
  --revision 45cbc485b03f48064e67c47839022c448f0391e1 \
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
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/config.json`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/config.json) | 运行配置 |
| [`SenseVoiceSmall-axmodel/ax650/model-10-seconds.axmodel`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/SenseVoiceSmall-axmodel/ax650/model-10-seconds.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/Qwen3-VL-2B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/Qwen3-VL-2B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/post_config.json`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/post_config.json) | 运行配置 |
| [`SenseVoiceSmall-axmodel/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/SenseVoiceSmall-axmodel/tokens.txt) | 分词器 / 字典，必须配套 |
| [`config.json`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/config.json) | 运行配置 |
| [`kokoro/kokoro-multi-lang-v1_0-axmodel/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/kokoro/kokoro-multi-lang-v1_0-axmodel/tokens.txt) | 分词器 / 字典，必须配套 |
| [`kokoro/kokoro-multi-lang-v1_1-axmodel/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/kokoro/kokoro-multi-lang-v1_1-axmodel/tokens.txt) | 分词器 / 字典，必须配套 |
| [`kokoro/kokoro-multi-lang-v1_1-axmodel_bck/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/kokoro/kokoro-multi-lang-v1_1-axmodel_bck/tokens.txt) | 分词器 / 字典，必须配套 |

仓库提交：`45cbc485b03f48064e67c47839022c448f0391e1`。仓库中的 50 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/tree/45cbc485b03f48064e67c47839022c448f0391e1)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是包含模型与机器人接口的组合应用；本页只整理本地模型部署依赖。模型子目录的 config.json 不能证明整个应用均使用 AXCL。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/tree/45cbc485b03f48064e67c47839022c448f0391e1)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/README.md)。

返回[完整模型目录](../catalog.mdx)。
