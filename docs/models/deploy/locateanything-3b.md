---
title: "LocateAnything-3B 部署指南"
sidebar_label: "LocateAnything-3B"
description: "LocateAnything-3B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# LocateAnything-3B 部署指南

LocateAnything-3B 用于开放词汇检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需匹配运行时与配置。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

已找到运行配置，但仍有运行时类型或文件配套关系需要确认。先完成下列核对，不直接套用同系列聊天命令。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/LocateAnything-3B` |
| 分词器类型（tokenizer_type） | `LocateAnything` |
| 多模态类型（vlm_type） | `LocateAnythingVL` |
| Transformer 层数 | 36 |
| 分片命名模板 | `qwen2_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen2_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen2_5_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `image_encoder_mlp.axmodel` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 36 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`gradio_locateanything_axengine.py`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/gradio_locateanything_axengine.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |
| [`locateanything_webui.py`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/locateanything_webui.py) | 需要继续核对后端与依赖 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`assert/ocr.jpg`、`assert/person.jpg`、`assert/phrase_grounding.jpg`、`pexels-images/pexels-amina-bawa-1033985337-35788485.jpg`、`pexels-images/pexels-caleb-falkenhagen-216813613-28807789.jpg`、`pexels-images/pexels-hengga-wang-2148790340-33689544.jpg`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/LocateAnything-3B` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/locateanything-3b/c6ad2b1a52a6
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/LocateAnything-3B \
  --revision c6ad2b1a52a6c75ca604e3e4eb775240aa31718a \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 核对文本特征与类别列表顺序，再用包含目标和不含目标的图片测试。
- 分别测试同义词与不同提示词；词表或编码器变更后重新计算文本特征。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`gradio_locateanything_axengine.py`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/gradio_locateanything_axengine.py) | Python 程序 / 前后处理 |
| [`locateanything_webui.py`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/locateanything_webui.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/config.json) | 运行配置 |
| [`qwen2_post.axmodel`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen2_5_tokenizer.txt`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2_5_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`image_encoder_mlp.axmodel`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/image_encoder_mlp.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/post_config.json) | 运行配置 |
| [`qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2.5_tokenizer/config.json) | 运行配置 |
| [`qwen2.5_tokenizer/configuration_qwen2.py`](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/qwen2.5_tokenizer/configuration_qwen2.py) | 旧版分词服务入口 |

仓库提交：`c6ad2b1a52a6c75ca604e3e4eb775240aa31718a`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/LocateAnything-3B/tree/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/LocateAnything-3B/tree/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/README.md)。
- [主要程序入口：gradio_locateanything_axengine.py](https://huggingface.co/AXERA-TECH/LocateAnything-3B/blob/c6ad2b1a52a6c75ca604e3e4eb775240aa31718a/gradio_locateanything_axengine.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
