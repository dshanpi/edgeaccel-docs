---
title: "jina-embeddings-v5-omni-small 部署指南"
sidebar_label: "jina-embeddings-v5-omni-small"
description: "jina-embeddings-v5-omni-small 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# jina-embeddings-v5-omni-small 部署指南

jina-embeddings-v5-omni-small 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

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
| 运行时模型名称 | `AXERA-TECH/jina-embeddings-v5-omni-small` |
| 分词器类型（tokenizer_type） | `Qwen3Omni` |
| 多模态类型（vlm_type） | `Qwen3Omni` |
| Transformer 层数 | 28 |
| 分片命名模板 | `jina_embeddings_v5_omni_p256_l%d_together.axmodel` |
| Embedding 模式 | 是，使用 /v1/embeddings |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `jina_embeddings_v5_omni_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `jina_v5_omni_tokenizer.txt` | 已找到 |
| `filename_image_encoder_axmodel` | `jina_v5_omni_small_vision_tower_256x256.axmodel` | 已找到 |

逐层核对 28 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`demo/openai_task_switch_web.py`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/demo/openai_task_switch_web.py) | 需要继续核对后端与依赖 |
| [`scripts/test_retrieval_clustering.py`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/scripts/test_retrieval_clustering.py) | 需要继续核对后端与依赖 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`assets/cat_0.jpeg`、`assets/cat_1.jpeg`、`assets/cat_2.jpg`、`assets/dog_0.jpeg`、`assets/dog_1.jpg`、`assets/dog_2.jpeg`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/jina-embeddings-v5-omni-small` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/jina-embeddings-v5-omni-small/3369e03364b2
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/jina-embeddings-v5-omni-small \
  --revision 3369e03364b29a2af7d1fd766d0e59f31b92d5b8 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 检查向量维度、有限数值及是否需要归一化；文本与图片使用配套编码器。
- 用匹配对、不匹配对比较相似度排序，再建立小型索引；更换模型后重建索引。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`demo/openai_task_switch_web.py`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/demo/openai_task_switch_web.py) | Python 程序 / 前后处理 |
| [`scripts/test_retrieval_clustering.py`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/scripts/test_retrieval_clustering.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/config.json) | 运行配置 |
| [`jina_embeddings_v5_omni_post.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`jina_v5_omni_tokenizer.txt`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_v5_omni_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`jina_v5_omni_small_vision_tower_256x256.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_v5_omni_small_vision_tower_256x256.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`jina_embeddings_v5_omni_p256_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/jina_embeddings_v5_omni_p256_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`lora/classification/source_adapter_config.json`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/lora/classification/source_adapter_config.json) | 运行配置 |
| [`lora/clustering/source_adapter_config.json`](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/lora/clustering/source_adapter_config.json) | 运行配置 |

仓库提交：`3369e03364b29a2af7d1fd766d0e59f31b92d5b8`。仓库中的 39 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/tree/3369e03364b29a2af7d1fd766d0e59f31b92d5b8)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/tree/3369e03364b29a2af7d1fd766d0e59f31b92d5b8)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/README.md)。
- [主要程序入口：demo/openai_task_switch_web.py](https://huggingface.co/AXERA-TECH/jina-embeddings-v5-omni-small/blob/3369e03364b29a2af7d1fd766d0e59f31b92d5b8/demo/openai_task_switch_web.py)。
- [配套项目：AXERA-TECH/jina_embeddings_v5_omni.axera](https://github.com/AXERA-TECH/jina_embeddings_v5_omni.axera)。

返回[完整模型目录](../catalog.mdx)。
