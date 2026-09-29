---
title: "Janus-Pro-1B 部署指南"
sidebar_label: "Janus-Pro-1B"
description: "Janus-Pro-1B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Janus-Pro-1B 部署指南

Janus-Pro-1B 用于视觉问答与文生图。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Janus-Pro-1B` 的固定版本。下面下载本页选用的 44 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/janus-pro-1b/6627e1e38ec2
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Janus-Pro-1B \
  "README.md" \
  "embeds/codebook_entry_embedding.pt" \
  "embeds/gen_embed.npy" \
  "img_gen_onnx/gen_aligner.onnx" \
  "img_gen_onnx/gen_vision_model_decode_sim.onnx" \
  "img_gen_onnx/post_head.onnx" \
  "img_gen_onnx/post_norm.onnx" \
  "imgs/image.jpg" \
  "imgs/image.png" \
  "infer_axmodel_gen.py" \
  "infer_axmodel_und.py" \
  "janus_pro_1b_axmodel/llama_p640_l0_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l10_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l11_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l12_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l13_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l14_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l15_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l16_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l17_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l18_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l19_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l1_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l20_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l21_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l22_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l23_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l2_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l3_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l4_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l5_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l6_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l7_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l8_together.axmodel" \
  "janus_pro_1b_axmodel/llama_p640_l9_together.axmodel" \
  "janus_pro_1b_axmodel/llama_post.axmodel" \
  "janus_pro_1b_axmodel/model.embed_tokens.weight.npy" \
  "janus_pro_1b_tokenizer/config.json" \
  "janus_pro_1b_tokenizer/preprocessor_config.json" \
  "janus_pro_1b_tokenizer/processor_config.json" \
  "janus_pro_1b_tokenizer/special_tokens_map.json" \
  "janus_pro_1b_tokenizer/tokenizer.json" \
  "janus_pro_1b_tokenizer/tokenizer_config.json" \
  "vit_axmodel/janus_warp_vit.axmodel" \
  --revision 6627e1e38ec2a3ef0d94e4249e8b5f619522ad70 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备图文与生成环境

本例在 **RK3576 + AX8850 16GB M.2** 上使用 Janus-Pro-1B，分别完成图像理解和文生图。语言模型与图像理解编码器通过 AXCL 运行；文生图的输出头、对齐层和图像解码器使用主机 CPU ONNX Runtime。

在已安装 PyAXEngine 的 Python 环境中准备依赖：

```bash
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'ml-dtypes==0.5.3' 'onnxruntime==1.20.1' \
  'timm==0.9.16' 'attrdict==2.0.1' 'einops==0.8.1' 'loguru==0.7.3' \
  'sentencepiece==0.2.1' 'Pillow==11.3.0' tqdm
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认列表包含 `AXCLRTExecutionProvider`，设备 0 可用。本例使用 PyAXEngine `0.1.3.rc3`。前面的模型下载约 3.17 GB，包含两条流程所需文件；另留空间保存输出。

获取官方 Janus 处理器固定提交，指定一个尚不存在的目录：

```bash
JANUS_DIR=~/edgeaccel/src/janus-1daa72fa
git clone --no-checkout https://github.com/deepseek-ai/Janus.git "$JANUS_DIR"
git -C "$JANUS_DIR" checkout --detach 1daa72fa409002d40931bd7b36a9280362469ead
```

已有该目录时，核对 `git -C "$JANUS_DIR" rev-parse HEAD` 与固定提交一致后复用。运行示例直接导入该目录，不需要额外安装 Janus 软件包。

下载 [Janus 算力卡运行示例](../../../static/examples/janus_card.py)，保存为 `~/edgeaccel/janus_card.py`。例程检查官方代码版本，明确指定 AXCL，并保留官方处理器、提示词格式和推理流程。Embedding 使用只读内存映射，减少主机内存拷贝。

## 运行图像理解

保持下载步骤中的 `MODEL_DIR`、上面的 `JANUS_DIR`，指定尚不存在的结果目录：

```bash
python ~/edgeaccel/janus_card.py --mode understand \
  --model-dir "$MODEL_DIR" --janus-dir "$JANUS_DIR" \
  --output ~/edgeaccel/results/janus-understand-01
```

程序读取官方 `imgs/image.png`，分别要求一句话描述画面和回答宇航员数量。两个问题独立运行，每个回答最多生成 128 个 token；只有生成 EOS 结束标记才计为完整回答。

替换为自己的图片和简短问题：

```bash
python ~/edgeaccel/janus_card.py --mode understand \
  --model-dir "$MODEL_DIR" --janus-dir "$JANUS_DIR" \
  --image ~/edgeaccel/inputs/photo.jpg \
  --question 'Describe the image in one sentence.' \
  --output ~/edgeaccel/results/janus-understand-custom-01
```

将 `photo.jpg` 替换为实际图片。图像按官方处理器转换为 384 × 384，占用 576 个视觉 token；本版预填充总长度为 640 个 token，系统提示词和问题也计入长度。提示过长时缩短问题后重试，程序不会静默截断。

## 运行文生图

下面生成“小红机器人给绿植浇水”的 384 × 384 图片：

```bash
python ~/edgeaccel/janus_card.py --mode generate \
  --model-dir "$MODEL_DIR" --janus-dir "$JANUS_DIR" \
  --description 'A small red robot watering a green plant on a wooden desk, warm sunlight, clean illustration.' \
  --seed 0 \
  --output ~/edgeaccel/results/janus-generate-01
```

程序完整生成 576 个图像 token，再调用 CPU 解码器保存 `generated_samples/img_0.jpg`。参数沿用官方实现：单张输出、CFG 权重 5、temperature 为 1。该流程包含两条条件分支和主机与卡之间的数据传输，耗时明显长于单次视觉推理。

`--seed` 固定抽样随机种子，不能代替跨平台一致性验证。自定义描述应保持简短；加入模板后最多 448 个 token，以给完整图像序列预留上下文。

## 查看回答与生成图片

| 文件或字段 | 内容 |
| --- | --- |
| `input-1.png`、`input-2.png` | 图像理解实际输入 |
| `generated_samples/img_0.jpg` | 文生图实际输出 |
| `deployment-result.json` 的 `samples` | 问题、原始回答或描述、输出 token、耗时和图片校验 |
| `sessions` / `cpuSessions` | 分别记录 AXCL 与 CPU ONNX 的实际调用 |
| `completed` | 本次全部样例正常完成时为 `true` |

图像理解的回答若达到长度或上下文上限，会保留已有输出并以非零状态退出；可在输入允许的范围内调整 `--max-new-tokens`，换用新的结果目录重试。文生图须生成完整 576 个 token 并保存图片，不能用中途进度代替成功结果。

下方保留本次实际回答、图片和耗时。样例耗时包含模型加载与处理，执行整条命令还包括 Python 启动和外层依赖导入。生成阶段耗时从相应模型加载完成后开始，图像理解时不包含此前的视觉编码。各项均为主机侧墙钟计时，不是纯 NPU 计算时间。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已完成同图两次问答和一张完整文生图，实际输入、原始回答、生成图片及耗时如下。

**图像理解：画面描述与人数问答**

同一张图片分别提问两次，每次独立加载和执行。以下保留原始英文回答，两次均生成 EOS 结束标记。

**示例 1：输入**

[![图像理解示例 1 的实际输入](../../../static/validation/effects/janus-pro-1b-20260928/input-1.png)](../../../static/validation/effects/janus-pro-1b-20260928/input-1.png)

```text
Describe the image in one sentence.
```

**实际回复**

```text
The image shows three astronauts in a forested area, dressed in white space suits, standing amidst tall grasses and trees.
```

画面中可见三名穿白色宇航服的人物、树木和地面植被，回答的主体、数量及场景与图片相符。植物细节未逐项标注。

**示例 2：输入**

[![图像理解示例 2 的实际输入](../../../static/validation/effects/janus-pro-1b-20260928/input-2.png)](../../../static/validation/effects/janus-pro-1b-20260928/input-2.png)

```text
How many astronauts?
```

**实际回复**

```text
There are three astronauts in the image.
```

回答为三名宇航员，与本图中可见人物数量一致。

| 问题 | 样例耗时（含加载） | 生成阶段 | 生成 token / 结束 |
| --- | --- | --- | --- |
| 1 | 89.816 s | 37.966 s | 26 / EOS |
| 2 | 59.440 s | 18.224 s | 10 / EOS |

**文生图：机器人给绿植浇水**

画面生成了红色机器人、绿色盆栽、木质桌面和暖色窗光，主要对象与描述相符。机器人持红色容器朝向盆栽，但水流不清晰，不能据此判定浇水动作完整准确。 下图为本次板端生成的完整图片。

<div className="model-effect-gallery">

<figure>

[![本次实际生成：机器人与绿植，384 × 384](../../../static/validation/effects/janus-pro-1b-20260928/generated-robot-plant.jpg)](../../../static/validation/effects/janus-pro-1b-20260928/generated-robot-plant.jpg)

<figcaption>本次实际生成：机器人与绿植，384 × 384</figcaption>
</figure>

</div>

| 项目 | 本次设置或结果 |
| --- | --- |
| 英文描述 | A small red robot watering a green plant on a wooden desk, warm sunlight, clean illustration. |
| 随机种子 / CFG / temperature | 0 / 5 / 1 |
| 输出 | 384 × 384，576 个图像 token |
| 样例耗时（含加载） | 1447.500 s |
| 生成阶段 | 1403.282 s |

**使用时注意：**

- 图像理解仅一张图两道短问题，文生图仅一个描述和随机种子；不代表整体生成质量、中文能力或多轮表现。
- 文生图采用算力卡与主机 CPU 混合流程，完整生成耗时较长；未验证并发或实时交互。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`6627e1e38ec2a3ef0d94e4249e8b5f619522ad70`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 图像理解 | 2 次回答均到达 EOS | 一张官方图片；画面描述及人数问答。 |
| 完整文生图 | 576 token / 384 × 384 | 24 层语言模型经 AXCL 执行，4 个 ONNX 部件在主机 CPU 执行。 |
| 文生图生成阶段 | 1403.282 s | 模型加载后到保存图片的主机侧墙钟时间，包含条件分支、数据传输及 CPU 处理，不是纯 NPU 耗时。 |

适用范围：

- 图像理解仅一张图两道短问题，文生图仅一个描述和随机种子；不代表整体生成质量、中文能力或多轮表现。
- 文生图采用算力卡与主机 CPU 混合流程，完整生成耗时较长；未验证并发或实时交互。
- 本次为真实 16GB 算力卡，8GB 容量和长期连续运行需要单独回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer_axmodel_gen.py`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/infer_axmodel_gen.py) | Python 程序 / 前后处理 |
| [`infer_axmodel_und.py`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/infer_axmodel_und.py) | Python 程序 / 前后处理 |
| [`janus_pro_1b_axmodel/llama_p640_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_axmodel/llama_p640_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`janus_pro_1b_axmodel/llama_p640_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_axmodel/llama_p640_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`janus_pro_1b_axmodel/llama_p640_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_axmodel/llama_p640_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`janus_pro_1b_axmodel/llama_p640_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_axmodel/llama_p640_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`janus_pro_1b_axmodel/llama_p640_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_axmodel/llama_p640_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`janus_pro_1b_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_tokenizer/config.json) | 运行配置 |
| [`janus_pro_1b_tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_tokenizer/preprocessor_config.json) | 运行配置 |
| [`janus_pro_1b_tokenizer/processor_config.json`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_tokenizer/processor_config.json) | 运行配置 |
| [`janus_pro_1b_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/janus_pro_1b_tokenizer/tokenizer_config.json) | 运行配置 |

仓库提交：`6627e1e38ec2a3ef0d94e4249e8b5f619522ad70`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/tree/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/tree/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/README.md)。
- [主要程序入口：infer_axmodel_und.py](https://huggingface.co/AXERA-TECH/Janus-Pro-1B/blob/6627e1e38ec2a3ef0d94e4249e8b5f619522ad70/infer_axmodel_und.py)。

返回[完整模型目录](../catalog.mdx)。
