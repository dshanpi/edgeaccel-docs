---
title: "Qwen3-TTS-12Hz-0.6B-Base-AX650 部署指南"
sidebar_label: "Qwen3-TTS-12Hz-0.6B-Base-AX650"
description: "Qwen3-TTS-12Hz-0.6B-Base-AX650 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-TTS-12Hz-0.6B-Base-AX650 部署指南

Qwen3-TTS-12Hz-0.6B-Base-AX650 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。
## 核对运行配置

配置文件：`talker/config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650` |
| 分词器类型（tokenizer_type） | `Qwen3` |
| 多模态类型（vlm_type） | 不启用 |
| Transformer 层数 | 28 |
| 分片命名模板 | `qwen3_tts_talker_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `talker/qwen3_tts_talker_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `talker/talker.model.text_embedding.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `talker/qwen3_tokenizer.txt` | 已找到 |
| `post_config_path` | `talker/post_config.json` | 已找到 |

逐层核对 28 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`infer.py`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/infer.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`assets/zero_shot_prompt.wav`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-tts-12hz-0-6b-base-ax650/3b3fde9cb90b
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650 \
  --revision 3b3fde9cb90b3646c7c9fdeefe083402c0399c2f \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 回放生成音频，检查文字是否完整、读音、音色、停顿和尾部截断。
- 记录采样率、音频时长、生成时间与 RTF；长文本、参考音色和多语言分别验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer.py`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/infer.py) | Python 程序 / 前后处理 |
| [`talker/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/config.json) | 运行配置 |
| [`talker/qwen3_tts_talker_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/qwen3_tts_talker_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`talker/talker.model.text_embedding.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/talker.model.text_embedding.weight.bfloat16.bin) | Embedding 权重 |
| [`talker/qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`talker/post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/post_config.json) | 运行配置 |
| [`code-predictor/code_predictor_lm_head_0.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_0.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_1.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_1.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_10.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_10.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_11.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_11.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_12.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_12.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`3b3fde9cb90b3646c7c9fdeefe083402c0399c2f`。仓库中的 65 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/tree/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是 talker、code predictor 与音频解码器组成的语音链路。子目录中的 axllm 配置只能表示其中一个阶段，不应当作普通文本模型启动整个 TTS。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/tree/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/README.md)。
- [主要程序入口：infer.py](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/infer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-qwen3_tts)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
