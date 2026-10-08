---
title: "Qwen3-VL-8B-Instruct 部署指南"
sidebar_label: "Qwen3-VL-8B-Instruct"
description: "Qwen3-VL-8B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-8B-Instruct 部署指南

Qwen3-VL-8B-Instruct 用于图像与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-8B-Instruct` 的固定版本。下面下载本页选用的 83 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-8b-instruct/f3c9f23de6de
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-8B-Instruct \
  --include "*" \
  --revision f3c9f23de6de9aa5c78b5cc9177094e1be7d913f \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16。模型目录至少预留 15GB 可用空间。程序依赖 OpenCV 4.6，词嵌入读取约占 1.16 GiB 主机内存；文件校验脚本需要 Python 3.11 或更高版本。

下载[配套运行包](/examples/qwen3-vl8-fixed-20261003.tar.gz)，复制到连接算力卡的 Linux 主机并命名为 `~/edgeaccel/qwen3-vl8-fixed-20261003.tar.gz`。保留前文设置的 `MODEL_DIR`，在该 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl8-fixed-20261003.tar.gz
chmod +x qwen3-vl8-fixed/main_axcl_aarch64
ldd qwen3-vl8-fixed/main_axcl_aarch64
python3 qwen3-vl8-fixed/verify_models.py "$MODEL_DIR"
```

`ldd` 不应出现 `not found`，校验应输出 `Verified 83 model files`。校验失败时先重新下载对应固定文件。运行包内的原生词表由本模型仓库的分词文件导出，无需启动分词服务。

保留下载目录结构，权重位于 `Qwen3-VL-8B-Instruct-AX650-c128_p1152` 子目录。命令中的 `--model-dir` 仍指向包含 `images`、`video` 和该权重子目录的仓库根目录。配套程序使用设备 0、贪心解码和独立进程，输入上限为 1152 token。

## 运行图片问答

先识别官方骑乘场景中的两种动物：

```bash
python3 ~/edgeaccel/qwen3-vl8-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_horse.jpg" \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.'
```

保留同一图片，将问题改为 `请用一句中文说出图片前景中的两种动物。`，可查看中文回答。人数问题为 `画面中有几个人清晰可见？只回答人数。`；对照下方原图判断哪些人物纳入计数。

再描述官方街景图片：

```bash
python3 ~/edgeaccel/qwen3-vl8-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_car.jpg" \
  --prompt '请用一句中文描述图片中的主要内容。'
```

每条命令等待回答完成后再运行下一条。视觉编码器、36 个文本层和输出层在算力卡运行；分词、图片预处理和词嵌入读取在主机执行。

## 运行视频帧问答

使用仓库 `video` 目录内的八张 JPEG 帧：

```bash
python3 ~/edgeaccel/qwen3-vl8-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

英文问题可使用 `Describe what the two animals are doing in these video frames. Use two sentences.`。

当前入口接受八帧 JPEG 目录，按文件名顺序、1 fps 解释输入，目录内不应混入其他文件。1 fps 是本页的输入配置，未核实原视频时基；本页未覆盖 MP4 解码、实时视频或多轮问答。

## 检查运行结果

日志应出现 `termination_reason=eos last_token=151645`，随后输出完整回答并退出。每条命令完成后执行：

```bash
echo $?
axcl-smi
```

退出码应为 `0`，设备列表不应继续显示该推理进程。`context-limit` 表示输出触及上限，不能当作完整回答结束。对照原图检查对象、人数和文字，对照视频帧检查可见动作；实际回答及偏差见下方效果展示。

本轮进程耗时包含网络读取模型、加载和推理，不代表本地存储性能。结果来自 16GB 卡；其他容量和连续运行需独立验证。

## 查看配套源码

运行包包含固定源码、分词文件来源、编译信息和校验值。程序基于 AXERA 的 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7`，使用本页提供的配套版本。请保持程序、词表和模型版本一致。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成五组图片与八帧视频问答，展示原始输出和核对结果。

**五组图片问答**

以下展示固定输入和原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方输入 ssd_horse.jpg：骑乘者、马和狗](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/ssd_horse.jpg)

<figcaption>官方输入 ssd_horse.jpg：骑乘者、马和狗</figcaption>
</figure>

<figure>

[![官方输入 ssd_car.jpg：双层巴士与街道](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/ssd_car.jpg)

<figcaption>官方输入 ssd_car.jpg：双层巴士与街道</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
A man is riding a brown horse while a brown dog sits on the ground nearby.
```

输入：ssd_horse.jpg。正确识别马和狗，狗坐在地面的描述与图片相符；骑乘者性别未作独立标注。

**示例 2：输入**

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
2
```

输入：ssd_horse.jpg。回答 2，与骑乘者和右侧红衣人物两名清晰对象相符；远处小目标不计入本页核对标准。

**示例 3：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在伦敦街头，身后是一辆经典的红色双层巴士，巴士上印有广告标语“当你说了‘是’，事情就变得更刺激”。
```

输入：ssd_car.jpg。人物、红色双层巴士和广告语大意与图片相符；“伦敦”地名未独立核实。

**示例 4：输入**

```text
请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
前景中有一匹马和一只狗。
```

输入：ssd_horse.jpg。正确识别前景中的马和狗，回答为一句中文。

**示例 5：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
A man is riding a brown horse while a brown dog sits on the ground nearby.
```

输入：ssd_horse.jpg。与首次英文回答完全一致；仅说明此固定输入重复两次一致。

| 问题 | 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- | --- |
| 动物识别（英文） | ssd_horse.jpg | 309.529 | 703 |
| 清晰可见人数 | ssd_horse.jpg | 300.343 | 111 |
| 街景描述 | ssd_car.jpg | 330.649 | 1295 |
| 动物识别（中文） | ssd_horse.jpg | 327.996 | 407 |
| 重复动物识别 | ssd_horse.jpg | 307.540 | 703 |

**官方八帧视频问答**

以下展示固定输入和原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方八帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/frame_0000.jpg)

<figcaption>官方八帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![官方八帧输入：第 4 帧](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/frame_0024.jpg)

<figcaption>官方八帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![官方八帧输入：第 8 帧](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/frame_0056.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-20261003/frame_0056.jpg)

<figcaption>官方八帧输入：第 8 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只松鼠在山间岩石上互相追逐嬉戏，前爪挥舞，姿态活泼。它们时而对视，时而转身，展现出灵动的自然野趣。
```

输入：8 帧。两只动物、前爪挥动、相互接触和转身与帧中可见内容相符，回答为两句；这些帧不足以确认“互相追逐”，“嬉戏”属于意图推测，“松鼠”的具体物种称呼未独立标注。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
Two marmots are playfully interacting on a rocky hillside, with one reaching out to touch the other’s face. Their lively movements and curious postures suggest a friendly, social encounter in their natural mountain habitat.
```

输入：8 帧。两只动物在岩石上互动、前爪触及另一只面部与画面相符，回答为两句；marmots 的物种称呼未独立确认，玩耍与友好社交属于模型对意图的推测。

| 问题 | 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- | --- |
| 动作描述（中文） | 8 帧 | 330.163 | 1591 |
| 动作描述（英文） | 8 帧 | 329.607 | 1849 |

**使用时注意：**

- 街景回答中的“伦敦”地名、骑乘者性别和视频动物的具体物种未独立标注。广告语大意与图片相符，本轮未做逐词翻译评测。
- 视频中文回答包含给定帧无法证实的“互相追逐”；中英文的嬉戏、友好社交等判断属于意图推测。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`f3c9f23de6de9aa5c78b5cc9177094e1be7d913f`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 固定 AXCL C++ 配套程序 / AX-LLM 3be4cc3 + 本页修复 / 本地原生分词 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输入覆盖 | 2 张图片 / 8 帧视频 | 5 条图片问题，2条视频问题，共7个独立进程。 |
| 算力卡执行 | 38 个 AXModel | 视觉编码器、36个文本层和输出层均执行并释放，共6659次调用。 |
| 视觉输入 | 384 × 384 | 单图1组；八帧视频4组视觉执行。 |

适用范围：

- 两条视频回答均为两句；图片英文问题重复两次得到相同文字。这些固定样例不代表数据集准确率或长期稳定性。
- 本页模型权重、两张图片、八帧样例和分词源文件均来自同一个固定8B仓库版本。
- 视频按文件名排序、1 fps解释。未核实原视频时基，未验证MP4解码或实时视频。
- 7条问题均以 EOS=151645 结束。本次最多643个输入token，程序输入上限1152；未覆盖多轮、长上下文、连续运行及所有中间张量的浮点对照。
- 实际8GB卡仍需独立验证。进程耗时包含网络读取和加载，不代表本地存储性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/run_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`tokenizer_images.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/tokenizer_images.py) | 旧版分词服务入口 |
| [`tokenizer_video.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/tokenizer_video.py) | 旧版分词服务入口 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152/Qwen3-VL-8B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/Qwen3-VL-8B-Instruct-AX650-c128_p1152/Qwen3-VL-8B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/Qwen3-VL-8B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/config.json) | 运行配置 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/images/demo.jpg) | 示例输入 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/post_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/qwen3-vl-tokenizer/config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/qwen3-vl-tokenizer/generation_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/qwen3-vl-tokenizer/preprocessor_config.json) | 运行配置 |

仓库提交：`f3c9f23de6de9aa5c78b5cc9177094e1be7d913f`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/tree/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/tree/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/README.md)。
- [主要程序入口：tokenizer_images.py](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct/blob/f3c9f23de6de9aa5c78b5cc9177094e1be7d913f/tokenizer_images.py)。
- [配套项目：AXERA-TECH/Qwen3-VL.AXERA](https://github.com/AXERA-TECH/Qwen3-VL.AXERA)。

返回[完整模型目录](../catalog.mdx)。
