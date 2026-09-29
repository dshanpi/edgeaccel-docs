---
title: "SmolVLM2-500M-Video-Instruct-python 部署指南"
sidebar_label: "SmolVLM2-500M-Video-Instruct-python"
description: "SmolVLM2-500M-Video-Instruct-python 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SmolVLM2-500M-Video-Instruct-python 部署指南

SmolVLM2-500M-Video-Instruct-python 用于视觉问答。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/SmolVLM2-500M-Video-Instruct-python` 的固定版本。下面下载本页选用的 53 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/smolvlm2-500m-video-instruct-python/42557bc3bff1
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SmolVLM2-500M-Video-Instruct-python \
  "README.md" \
  "assets/bee.jpg" \
  "embeds/SmolVLMVisionEmbeddings.pkl" \
  "infer_axmodel.py" \
  "smolvlm2_axmodel/llama_p128_l0_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l10_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l11_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l12_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l13_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l14_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l15_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l16_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l17_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l18_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l19_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l1_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l20_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l21_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l22_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l23_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l24_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l25_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l26_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l27_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l28_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l29_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l2_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l30_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l31_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l3_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l4_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l5_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l6_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l7_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l8_together.axmodel" \
  "smolvlm2_axmodel/llama_p128_l9_together.axmodel" \
  "smolvlm2_axmodel/llama_post.axmodel" \
  "smolvlm2_axmodel/model.embed_tokens.weight.npy" \
  "smolvlm2_tokenizer/.gitattributes" \
  "smolvlm2_tokenizer/README.md" \
  "smolvlm2_tokenizer/added_tokens.json" \
  "smolvlm2_tokenizer/chat_template.json" \
  "smolvlm2_tokenizer/config.json" \
  "smolvlm2_tokenizer/generation_config.json" \
  "smolvlm2_tokenizer/merges.txt" \
  "smolvlm2_tokenizer/preprocessor_config.json" \
  "smolvlm2_tokenizer/processor_config.json" \
  "smolvlm2_tokenizer/special_tokens_map.json" \
  "smolvlm2_tokenizer/tokenizer.json" \
  "smolvlm2_tokenizer/tokenizer_config.json" \
  "smolvlm2_tokenizer/vocab.json" \
  "utils/infer_func.py" \
  "vit_model/vision_model.axmodel" \
  --revision 42557bc3bff11187d71d001e43e8cb011a1fbf7b \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

本例在 RK3576 主机运行官方 Python 图像问答流程。视觉嵌入与分词在主机 CPU 上执行；视觉编码器、32 层解码器和输出层通过 AXCL 在算力卡上执行。

先按 [Python 接口](../../usage/python.md) 创建 `~/edgeaccel/python-env`，再激活并安装依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' 'transformers==4.51.3' 'Pillow==11.3.0' 'ml_dtypes==0.5.3' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。模型目录应包含 `smolvlm2_axmodel/`、`smolvlm2_tokenizer/`、`vit_model/`、`embeds/`、`utils/` 和 `assets/bee.jpg`。

## 运行官方图片问答

下载 [SmolVLM2-500M 算力卡示例](../../../static/examples/smolvlm500_card.py)，保存为 `~/edgeaccel/smolvlm500_card.py`。保持前面下载步骤中的 `MODEL_DIR`，执行：

```bash
python ~/edgeaccel/smolvlm500_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/smolvlm500-01
```

输出目录须尚不存在。程序对官方花朵与蜜蜂图片执行描述、花瓣颜色问答和重复描述；每次请求清空 KV 缓存。使用只读 NPY 词嵌入，并按文件 SHA256 核对官方源码和 CPU 视觉嵌入文件。

CPU 视觉嵌入保留 `weights_only=True`，仅允许固定文件实际需要的 Torch 类。不要把其他来源的同名文件替换到该路径，也不要关闭限制来绕过校验。

图片先按官方入口调整为 512×512，再交由配套 processor 处理。若视觉编码器只接受 batch=1，程序逐块运行全部图像块，并按原顺序合并；不丢弃额外图像块。

## 查看模型回答

输出目录中的 `deployment-result.json` 保存输入 token、原始回答、CPU 与 AXCL 调用记录及耗时。查看：

- `samples[].output`：实际回答。
- `samples[].stopReason`：`eos` 为正常结束，`length` 为达到输出上限，`context` 为达到上下文限制。
- `samples[].pixelValuesShape` 与 `imageTokenCount`：本次 processor 的分块和视觉 token 数。
- `cpuEmbedding.calls` 与 `sessions`：CPU 视觉嵌入及每份 AXMODEL 的实际执行情况。

`generationSeconds` 包含主机预处理、传输和推理，不含模型加载；它不是纯 NPU 耗时。默认上限为 160 个新 token，达到上限的回答可能未完成。

## 使用自己的图片

```bash
python ~/edgeaccel/smolvlm500_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/Pictures/example.jpg \
  --question 'Describe this image in one sentence.' \
  --output ~/edgeaccel/results/smolvlm500-custom-01
```

当前入口对应官方单图 Python 示例。视频、多图及更长输入需分别验证，不应直接用单图结果代替。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

34 份 AXMODEL 已通过 AXCL 完成三次单图问答；下面展示实际图片、原始回答及主机预处理耗时。

**花朵图片问答与重复运行**

每次请求清空 KV 缓存；三次均生成 EOS。下面保留原始回答，包括描述偏差。

**示例 1：输入**

[![实际输入：官方花朵与蜜蜂图片](../../../static/validation/effects/smolvlm2-500m-video-instruct-python-20260928/input.jpg)](../../../static/validation/effects/smolvlm2-500m-video-instruct-python-20260928/input.jpg)

```text
Describe this image in one sentence.
```

**实际回复**

```text
A close-up of a bee on a pink flower with a bee on a red flower in the background.
```

主体蜜蜂和粉色花朵与画面相符；画面背景可见红花，但未见回答所说的另一只蜜蜂，存在多描述细节。

**示例 2：输入**

```text
What color are the flower petals? Answer briefly.
```

**实际回复**

```text
Pink.
```

回答 Pink，与主体花瓣的粉紫色大致相符。

**示例 3：输入**

```text
Describe this image in one sentence.
```

**实际回复**

```text
A close-up of a bee on a pink flower with a bee on a red flower in the background.
```

重复相同图片和问题，回答 token、每步 logits 哈希及图像特征完全一致；重复一致不代表错误细节正确。

| 请求 | 总生成耗时 | 其中 CPU 视觉嵌入 | 内部首 token | 输出 token（含 EOS） |
| --- | --- | --- | --- | --- |
| 1 | 175.050 s | 145.804 s | 158.927 s | 23 |
| 2 | 158.570 s | 144.578 s | 156.985 s | 3 |
| 3 | 171.531 s | 144.284 s | 156.062 s | 23 |

**使用时注意：**

- 描述加入了画面中未见的背景蜜蜂，不能把基本运行通过视作视觉问答准确性通过。
- 仅核对一张图片、两种问题和重复请求；未做完整视觉问答数据集或CPU浮点参考评测。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`42557bc3bff11187d71d001e43e8cb011a1fbf7b`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际调用 | 视觉编码3次；每层解码器73次；输出层49次 | 32层解码器各27次prefill、46次decode；CPU视觉嵌入另外执行3次。 |
| 生成耗时 | 158.570–175.050 s / 请求 | 模型已加载；包含主机预处理、传输及推理，不是纯 NPU 耗时。 |
| CPU 视觉嵌入 | 144.284–145.804 s / 请求 | RK3576 上保留官方 BF16 CPU 模块；它占本次请求耗时的大部分。 |
| 图像输入 | 17个图像块 / 1088个视觉token | 先按官方入口缩放512×512，配套processor启用图像分块；每次视觉AXMODEL执行1次。 |

适用范围：

- 描述加入了画面中未见的背景蜜蜂，不能把基本运行通过视作视觉问答准确性通过。
- 仅核对一张图片、两种问题和重复请求；未做完整视觉问答数据集或CPU浮点参考评测。
- 当前只验证官方单图Python入口，尚未验证视频、多图、长上下文及多轮对话。
- 主机CPU视觉嵌入较慢，当前配置不适合实时互动；没有用纯解码耗时替代用户等待时间。
- 贪心生成，输出上限160token；三次均正常EOS。本次仅16GB卡，8GB与长期运行待回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`smolvlm2_axmodel/llama_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_axmodel/llama_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm2_axmodel/llama_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_axmodel/llama_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm2_axmodel/llama_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_axmodel/llama_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm2_axmodel/llama_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_axmodel/llama_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm2_axmodel/llama_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_axmodel/llama_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/config.json) | 运行配置 |
| [`smolvlm2_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_tokenizer/config.json) | 运行配置 |
| [`smolvlm2_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_tokenizer/generation_config.json) | 运行配置 |
| [`smolvlm2_tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_tokenizer/preprocessor_config.json) | 运行配置 |
| [`smolvlm2_tokenizer/processor_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_tokenizer/processor_config.json) | 运行配置 |
| [`smolvlm2_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/smolvlm2_tokenizer/tokenizer_config.json) | 运行配置 |

仓库提交：`42557bc3bff11187d71d001e43e8cb011a1fbf7b`。仓库中的 34 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/tree/42557bc3bff11187d71d001e43e8cb011a1fbf7b)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/tree/42557bc3bff11187d71d001e43e8cb011a1fbf7b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/README.md)。
- [主要程序入口：infer_axmodel.py](https://huggingface.co/AXERA-TECH/SmolVLM2-500M-Video-Instruct-python/blob/42557bc3bff11187d71d001e43e8cb011a1fbf7b/infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
