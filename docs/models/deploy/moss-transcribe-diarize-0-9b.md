---
title: "MOSS-Transcribe-Diarize-0.9B 部署指南"
sidebar_label: "MOSS-Transcribe-Diarize-0.9B"
description: "MOSS-Transcribe-Diarize-0.9B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MOSS-Transcribe-Diarize-0.9B 部署指南

MOSS-Transcribe-Diarize-0.9B 用于语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `MOSS-Transcribe-Diarize-0.9B` |
| 分词器类型（tokenizer_type） | `MossTranscribeDiarize` |
| 多模态类型（vlm_type） | `MossTranscribeDiarizeVL` |
| Transformer 层数 | 28 |
| 分片命名模板 | `qwen3_p256_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen3_tokenizer.txt` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 28 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`infer_moss_axengine.py`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/infer_moss_axengine.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |
| [`moss_openai_api.py`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/moss_openai_api.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`wav/002.mp3`、`wav/20200327_2P_lenovo_iphonexr_66902_part00.wav`、`wav/2speakers_example.wav`、`wav/R8001_M8004_MS801_5s_to_6m.wav`、`wav/vad_example.wav`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/MOSS-Transcribe-Diarize-0.9B` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/moss-transcribe-diarize-0-9b/c627e9bad59a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MOSS-Transcribe-Diarize-0.9B \
  --revision c627e9bad59af4074d95c4bc24a87483141d5cc7 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 保存输入音频的采样率、通道数和参考转写，逐句比较漏词、错词和语言标记。
- 流式模式还需检查分块边界和最终文本合并；分别记录端到端耗时与纯模型耗时。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer_moss_axengine.py`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/infer_moss_axengine.py) | Python 程序 / 前后处理 |
| [`moss_openai_api.py`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/moss_openai_api.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/config.json) | 运行配置 |
| [`qwen3_post.axmodel`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/post_config.json) | 运行配置 |
| [`qwen3_p256_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_p256_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p256_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_p256_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p256_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_p256_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p256_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_p256_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p256_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/qwen3_p256_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`preprocessor_config.json`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/preprocessor_config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/requirements.txt) | Python 依赖清单 |

仓库提交：`c627e9bad59af4074d95c4bc24a87483141d5cc7`。仓库中的 30 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/tree/c627e9bad59af4074d95c4bc24a87483141d5cc7)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 同时输出转写、时间戳和说话人编号。除文字准确性外，还需检查时间单位、分段顺序和同一说话人的编号连续性。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/tree/c627e9bad59af4074d95c4bc24a87483141d5cc7)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/README.md)。
- [主要程序入口：infer_moss_axengine.py](https://huggingface.co/AXERA-TECH/MOSS-Transcribe-Diarize-0.9B/blob/c627e9bad59af4074d95c4bc24a87483141d5cc7/infer_moss_axengine.py)。
- [配套项目：AXERA-TECH/ax-llm.git](https://github.com/AXERA-TECH/ax-llm.git)。

返回[完整模型目录](../catalog.mdx)。
