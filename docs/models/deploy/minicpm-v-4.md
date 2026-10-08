---
title: "MiniCPM-V-4 部署指南"
sidebar_label: "MiniCPM-V-4"
description: "MiniCPM-V-4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM-V-4 部署指南

MiniCPM-V-4 用于图片问答与场景描述。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MiniCPM-V-4` 的固定版本。下面下载本页选用的 52 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/minicpm-v-4/b7e4aaefa66d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MiniCPM-V-4 \
  --include "embed_tokens.pth" "minicpm-v-4_axmodel/llama_p320_l0_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l10_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l11_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l12_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l13_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l14_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l15_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l16_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l17_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l18_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l19_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l1_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l20_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l21_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l22_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l23_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l24_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l25_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l26_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l27_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l28_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l29_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l2_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l30_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l31_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l3_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l4_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l5_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l6_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l7_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l8_together.axmodel" "minicpm-v-4_axmodel/llama_p320_l9_together.axmodel" "minicpm-v-4_axmodel/llama_post.axmodel" "minicpmv4_tokenizer/config.json" "minicpmv4_tokenizer/configuration_minicpm.py" "minicpmv4_tokenizer/generation_config.json" "minicpmv4_tokenizer/image_processing_minicpmv.py" "minicpmv4_tokenizer/model.safetensors.index.json" "minicpmv4_tokenizer/modeling_minicpmv.py" "minicpmv4_tokenizer/modeling_navit_siglip.py" "minicpmv4_tokenizer/preprocessor_config.json" "minicpmv4_tokenizer/processing_minicpmv.py" "minicpmv4_tokenizer/resampler.py" "minicpmv4_tokenizer/special_tokens_map.json" "minicpmv4_tokenizer/tokenization_minicpmv_fast.py" "minicpmv4_tokenizer/tokenizer.json" "minicpmv4_tokenizer/tokenizer_config.json" "resampler.axmodel" "run_axmodel.py" "show_demo.jpg" "siglip.axmodel" \
  --revision b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装依赖与运行包

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0。模型文件约 5.15GB，建议为模型及输出预留至少 7GB 存储空间。退出其他推理程序，确认 `axcl-smi` 能识别设备。

在已安装 PyAXEngine 的 Python 环境中安装依赖：

```bash
python -m pip install torch==2.5.1 transformers==4.51.3 tokenizers==0.21.4 \
  numpy==1.26.4 Pillow==11.3.0 ml-dtypes==0.5.3 tqdm
python -c "import axengine; print(axengine.get_available_providers())"
grep MemAvailable /proc/meminfo
```

提供器列表应包含 `AXCLRTExecutionProvider`，主机 `MemAvailable` 至少保留 2400MiB。词嵌入由主机加载，FP32 权重约占 717MiB；它不属于算力卡内存。

下载[配套运行包](/examples/minicpm-v4-20261001.tar.gz)，保存到 `~/edgeaccel`。保留前文下载模型后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf minicpm-v4-20261001.tar.gz
python minicpm-v4/verify_models.py --model-dir "$MODEL_DIR"
```

校验应输出 `Verified 52 model files`。分词和图像配置来自模型目录中的 `minicpmv4_tokenizer`，运行时无需再次联网下载模型。配套入口调用固定版本官方脚本，并明确使用算力卡提供器。

## 运行英文图片问答

```bash
python minicpm-v4/run.py --model-dir "$MODEL_DIR" \
  --image "$MODEL_DIR/show_demo.jpg" \
  --question 'Describe the visible scenery in two sentences.'
```

等待模型加载和回答完成。终端最后的 `[完整回答]` 按本次生成的 token 一次性解码，用于核对最终文本；`[结束 token]` 为 `73440` 或 `2` 表示输出以模型的结束标记收尾。

图像按官方示例缩放到 448 × 448，并关闭图像切片。SigLIP、重采样器、32 个文本层和输出层共 35 个 AXModel 在算力卡运行；分词、词嵌入及部分图像处理在主机执行。

## 运行中文图片问答

上一条命令退出后再执行：

```bash
python minicpm-v4/run.py --model-dir "$MODEL_DIR" \
  --image "$MODEL_DIR/show_demo.jpg" \
  --question '请用两句话描述图中可以直接看到的景物。'
```

每次命令独立加载模型。首次加载耗时与存储读取速度有关，效果展示中的单次问答耗时不包含首次加载。

## 使用自己的图片并检查结果

将 `--image` 替换为主机上图片的绝对路径，修改 `--question` 提问。先使用短问题和单张图片，检查回答是否符合图片中的实际内容。当前流程不覆盖多图、图像切片或视频输入。

```bash
echo $?
axcl-smi
```

退出码应为 `0`。若没有生成结束标记，或回答与图像不符，应保留原始输出继续核对；不能仅根据程序退出判定回答正确。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成同一张图片的中英文问答，以下保留实际生成的完整文本。

**中英文图片问答**

同一张山水图片完成中英文问答，两次均生成结束标记。主要景物与画面相符；句数要求未满足，中文还包含未经确认的地点推测。

<div className="model-effect-gallery">

<figure>

[![图片输入：山地、河流与岸边植被](../../../static/validation/effects/minicpm-v-4-20261001/show_demo.jpg)](../../../static/validation/effects/minicpm-v-4-20261001/show_demo.jpg)

<figcaption>图片输入：山地、河流与岸边植被</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the visible scenery in two sentences.（输入：show_demo.jpg）
```

**实际回复**

```text
In this picture we can see the sky, hills, water and plants.
```

天空、山、水面和植被均可在原图中看到。回答只给出一句话，没有遵守两句话要求。

**示例 2：输入**

```text
请用两句话描述图中可以直接看到的景物。（输入：show_demo.jpg）
```

**实际回复**

```text
这幅图像展示了一个宁静而风景如画的环境，可能是一个以其独特的喀斯特地貌而闻名的地区，比如中国的桂林漓江。太阳正处于地平线附近，暗示着日出或日落的场景，给天空涂上温暖的色彩，映照在平静的水面上。周围的植被茂密，为这个自然美景的整体和谐与宁静做出了贡献。
```

水面、植被、山峰和接近山际的太阳与画面相符。桂林漓江属于未经确认的地点推测；输出三句话，未遵守两句话要求。日出或日落也不能仅凭这张图确定。

| 输入 | 首次加载 / s | 首 token / s | 完整请求 / s | 生成 token（含结束） | 结束 token |
| --- | --- | --- | --- | --- | --- |
| 英文描述 | 333.884 | 18.533 | 26.730 | 16 | 73440 |
| 中文描述 | 322.698 | 18.005 | 62.509 | 78 | 73440 |

**使用时注意：**

- 英文只输出一句，中文输出三句，均未严格满足两句话要求。中文提及桂林漓江只是模型推测，不能当作地点识别结果。本次只核对一张图片，未验证人数计数、更多场景或数据集准确率。
- 本次仅覆盖 16GB 基本运行；8GB、多图、切片、视频及长期服务尚未验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 固定官方 Python 流程 / Transformers 4.51.3 / PyAXEngine / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 算力卡执行 | 35 个 AXModel | SigLIP、重采样器、32 个文本层和输出层，两次独立加载共 3106 次调用。 |
| 输入覆盖 | 1 张图片 / 2 次问答 | 图像缩放到 448 × 448，关闭图像切片；使用官方脚本默认 top_k=1。 |

适用范围：

- 表中耗时包含输出记录和一致性检查开销，不作为模型的峰值性能；完整请求耗时不含首次加载。
- 完整回答按实际生成 token 一次性解码；原始脚本分块打印的空格和截断不作为文本真值。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axmodel.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/run_axmodel.py) | Python 程序 / 前后处理 |
| [`minicpm-v-4_axmodel/llama_p320_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpm-v-4_axmodel/llama_p320_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm-v-4_axmodel/llama_p320_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpm-v-4_axmodel/llama_p320_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm-v-4_axmodel/llama_p320_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpm-v-4_axmodel/llama_p320_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm-v-4_axmodel/llama_p320_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpm-v-4_axmodel/llama_p320_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm-v-4_axmodel/llama_p320_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpm-v-4_axmodel/llama_p320_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/config.json) | 运行配置 |
| [`minicpmv4_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/config.json) | 运行配置 |
| [`minicpmv4_tokenizer/configuration_minicpm.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/configuration_minicpm.py) | 旧版分词服务入口 |
| [`minicpmv4_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/generation_config.json) | 运行配置 |
| [`minicpmv4_tokenizer/image_processing_minicpmv.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/image_processing_minicpmv.py) | 旧版分词服务入口 |
| [`minicpmv4_tokenizer/modeling_minicpmv.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/modeling_minicpmv.py) | 旧版分词服务入口 |
| [`minicpmv4_tokenizer/modeling_navit_siglip.py`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/modeling_navit_siglip.py) | 旧版分词服务入口 |
| [`minicpmv4_tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/minicpmv4_tokenizer/preprocessor_config.json) | 运行配置 |

仓库提交：`b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3`。仓库中的 35 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/tree/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/tree/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/README.md)。
- [主要程序入口：run_axmodel.py](https://huggingface.co/AXERA-TECH/MiniCPM-V-4/blob/b7e4aaefa66d21dbc4aa0c59d618f79f3eae44c3/run_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
