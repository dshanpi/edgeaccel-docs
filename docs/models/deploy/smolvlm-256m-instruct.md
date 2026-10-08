---
title: "SmolVLM-256M-Instruct 部署指南"
sidebar_label: "SmolVLM-256M-Instruct"
description: "SmolVLM-256M-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SmolVLM-256M-Instruct 部署指南

SmolVLM-256M-Instruct 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/SmolVLM-256M-Instruct` 的固定版本。下面下载本页选用的 50 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/smolvlm-256m-instruct/a41ab40883f1
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SmolVLM-256M-Instruct \
  "README.md" \
  "post_config.json" \
  "run_smolvlm_ax650.sh" \
  "smolvlm-256m-ax650/SmolVLM-256M-Instruct_vision_nhwc.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l0_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l10_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l11_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l12_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l13_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l14_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l15_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l16_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l17_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l18_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l19_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l1_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l20_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l21_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l22_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l23_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l24_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l25_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l26_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l27_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l28_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l29_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l2_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l3_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l4_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l5_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l6_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l7_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l8_together.axmodel" \
  "smolvlm-256m-ax650/llama_p128_l9_together.axmodel" \
  "smolvlm-256m-ax650/llama_post.axmodel" \
  "smolvlm-256m-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "smolvlm_tokenizer/added_tokens.json" \
  "smolvlm_tokenizer/chat_template.json" \
  "smolvlm_tokenizer/config.json" \
  "smolvlm_tokenizer/configuration.json" \
  "smolvlm_tokenizer/generation_config.json" \
  "smolvlm_tokenizer/merges.txt" \
  "smolvlm_tokenizer/preprocessor_config.json" \
  "smolvlm_tokenizer/processor_config.json" \
  "smolvlm_tokenizer/special_tokens_map.json" \
  "smolvlm_tokenizer/tokenizer.json" \
  "smolvlm_tokenizer/tokenizer_config.json" \
  "smolvlm_tokenizer/vocab.json" \
  "smolvlm_tokenizer_512.py" \
  "ssd_car.jpg" \
  --revision a41ab40883f156fd50bb3371acdfaed626ca38d6 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

本例在 RK3576 主机通过 AXCL 运行 SmolVLM-256M 的图像编码器、30 层解码器及输出层。先按 [Python 接口](../../usage/python.md) 创建 `~/edgeaccel/python-env`，再激活并安装依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'transformers==4.51.3' 'ml_dtypes==0.5.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。模型下载目录应包含 `smolvlm-256m-ax650/`、`smolvlm_tokenizer/`、`smolvlm_tokenizer_512.py` 和 `ssd_car.jpg`。这里使用 AX650 权重，经 M.2 卡运行；不执行用于裸片开发板的 `main`。

## 运行图片问答

下载 [SmolVLM-256M 算力卡示例](../../../static/examples/smolvlm256_card.py)，保存为 `~/edgeaccel/smolvlm256_card.py`。保持前面下载步骤中的 `MODEL_DIR`，执行：

```bash
python ~/edgeaccel/smolvlm256_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/smolvlm256-01
```

输出目录须尚不存在。程序使用官方公交车图片进行描述、颜色问答和重复描述，最后执行一道纯文本问题。生成采用贪心选择，默认最多 160 个新 token，每次请求重新初始化 KV 缓存。

图像按官方 C++ 示例缩放为 512×512 RGB，由图像编码器生成 64 个视觉 token。分词与提示格式沿用本页固定版本的官方脚本；BF16 词嵌入通过只读内存映射加载，不需要下载原始浮点大模型。

## 查看输出与结束原因

打开输出目录中的 `deployment-result.json`：

- `samples[].output`：模型原始回答。
- `samples[].stopReason`：`eos` 表示正常结束，`length` 表示达到输出上限，`context` 表示达到上下文限制。
- `samples[].firstTokenSeconds` 和 `generationSeconds`：请求开始至首 token、请求完成的实测耗时，包含分词、图片处理及推理，不含模型加载。
- `sessions`：32 份 AXMODEL 的实际调用次数、输入规格和耗时。

`input-*.jpg` 为实际输入图片，`vision-*.npz` 保留输入像素和视觉特征。模型能生成回答不等于每条回答均正确，应结合输入图片核对内容。达到长度限制的结果可能未完整回答问题。

## 换成自己的图片

```bash
python ~/edgeaccel/smolvlm256_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/Pictures/example.jpg \
  --question 'Describe this image in one sentence.' \
  --max-new-tokens 160 \
  --output ~/edgeaccel/results/smolvlm256-custom-01
```

当前入口每次接受一张图片；包含视觉 token 的完整输入不得超过 128 token。问题过长时程序停止，缩短问题后使用新的输出目录重试。纯文本问答可省略 `--image`。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

四次请求识别出公交车、汽车和路杆，车身颜色回答 Red；重复图片的回答一致。算术输出 2 + 3 = 5，违反只回答数字的要求，本次指令格式质量未通过。

**公交车图片问答与重复运行**

同一组权重完成四次独立请求，每次重置 KV 缓存。以下保留完整原始回答；四次均到达 EOS，未触及输出上限。

**示例 1：输入**

[![实际输入：官方 ssd_car.jpg](../../../static/validation/effects/smolvlm-256m-instruct-20260928/input.jpg)](../../../static/validation/effects/smolvlm-256m-instruct-20260928/input.jpg)

```text
Describe this image in one sentence.
```

**实际回复**

```text
In this image we can see a bus, a car, a pole and some objects.
```

画面中可见红色双层公交车、右侧汽车和路杆；回答列出了这些物体，描述较概括。

**示例 2：输入**

```text
What color is the main bus? Answer with one word.
```

**实际回复**

```text
Red.
```

回答 Red，与画面公交车的红色车身相符。

**示例 3：输入**

```text
Describe this image in one sentence.
```

**实际回复**

```text
In this image we can see a bus, a car, a pole and some objects.
```

重复相同图片和问题，回答 token、每步 logits 哈希及视觉特征均与第一次一致。

**示例 4：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
2 + 3 = 5
```

计算结果为 5，但输出了完整算式，没有严格遵守“只回答数字”的格式要求。

| 请求 | 生成耗时 | 内部首 token | 输出 token（含 EOS） | 结束状态 |
| --- | --- | --- | --- | --- |
| 1 | 6.007 s | 0.489 s | 19 | EOS |
| 2 | 1.183 s | 0.512 s | 3 | EOS |
| 3 | 7.295 s | 0.519 s | 19 | EOS |
| 4 | 3.181 s | 0.440 s | 9 | EOS |

**使用时注意：**

- 只核对一张图片、两种图像问题和一道算术题，未完成通用视觉问答数据集或CPU浮点参考评测。
- 算术结果正确，但不完全遵守“只输出数字”的要求；不能把基本运行视作格式遵循通过。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`a41ab40883f156fd50bb3371acdfaed626ca38d6`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际调用 | 图像编码3次；每层解码器与输出层各50次 | 30层decoder各4次prefill、46次decode；输出有限；不是仅加载权重。 |
| 生成耗时 | 1.183–7.295 s / 请求 | 已加载模型；包含分词、图像预处理、传输与推理，不含模型加载。 |
| 内部首 token | 0.440–0.519 s | 从请求处理开始到取得首token，不等于网页首字延迟。 |

适用范围：

- 当前为单图512×512、64视觉token、完整输入不超过128token；未验证视频、多图、长上下文或多轮。
- 贪心生成；没有沿用仓库默认的随机top-k=10，因此回答不必与README样例一致。
- 本次仅16GB卡，8GB和长期连续运行仍待回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`smolvlm_tokenizer_512.py`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm_tokenizer_512.py) | 旧版分词服务入口 |
| [`smolvlm-256m-ax650/SmolVLM-256M-Instruct_vision_nhwc.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm-256m-ax650/SmolVLM-256M-Instruct_vision_nhwc.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm-256m-ax650/llama_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm-256m-ax650/llama_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm-256m-ax650/llama_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm-256m-ax650/llama_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm-256m-ax650/llama_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm-256m-ax650/llama_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smolvlm-256m-ax650/llama_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm-256m-ax650/llama_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/post_config.json) | 运行配置 |
| [`run_smolvlm_ax630c.sh`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/run_smolvlm_ax630c.sh) | 启动或构建脚本 |
| [`run_smolvlm_ax650.sh`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/run_smolvlm_ax650.sh) | 启动或构建脚本 |
| [`smolvlm_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm_tokenizer/config.json) | 运行配置 |
| [`smolvlm_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm_tokenizer/generation_config.json) | 运行配置 |
| [`smolvlm_tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm_tokenizer/preprocessor_config.json) | 运行配置 |
| [`smolvlm_tokenizer/processor_config.json`](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm_tokenizer/processor_config.json) | 运行配置 |

仓库提交：`a41ab40883f156fd50bb3371acdfaed626ca38d6`。仓库中的 64 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/tree/a41ab40883f156fd50bb3371acdfaed626ca38d6)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是小型视觉语言模型，输入为图像与问题。与 SmolVLM2 系列保留不同的视觉编码器和 tokenizer。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/tree/a41ab40883f156fd50bb3371acdfaed626ca38d6)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/README.md)。
- [主要程序入口：smolvlm_tokenizer_512.py](https://huggingface.co/AXERA-TECH/SmolVLM-256M-Instruct/blob/a41ab40883f156fd50bb3371acdfaed626ca38d6/smolvlm_tokenizer_512.py)。

返回[完整模型目录](../catalog.mdx)。
