---
title: "Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 部署指南"
sidebar_label: "Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047"
description: "Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 部署指南

Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 用于图像与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047` 的固定版本。下面下载本页选用的 75 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047/cf4b904ba59e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 \
  --include "*" \
  --revision cf4b904ba59e66fefd17668af196fc9c199ab70f \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16。为模型预留至少 4GB 存储空间；词嵌入读取约占 594 MiB 主机内存。程序依赖 OpenCV 4.6，文件校验脚本需要 Python 3.11 或更高版本。

下载[配套运行包](/examples/qwen3-vl2-p1536-fixed-20261003.tar.gz)，复制到连接算力卡的 Linux 主机并命名为 `~/edgeaccel/qwen3-vl2-p1536-fixed-20261003.tar.gz`。保留前文设置的 `MODEL_DIR`，在连接算力卡的 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl2-p1536-fixed-20261003.tar.gz
chmod +x qwen3-vl2-p1536-fixed/main_axcl_aarch64
ldd qwen3-vl2-p1536-fixed/main_axcl_aarch64
python3 qwen3-vl2-p1536-fixed/verify_models.py "$MODEL_DIR"
```

`ldd` 输出不应出现 `not found`，文件校验应输出 `Verified 75 model files`。校验失败时重新下载对应固定版本文件后再运行。

运行包使用本仓库自带的原生分词文件，无需启动分词服务。视觉编码器、28 个文本层和输出层在算力卡执行；分词、图片预处理和词嵌入读取在主机完成。程序固定使用设备 0、贪心解码 `top_k=1`，每条命令启动独立进程。

## 选择视觉编码器

通过 `--encoder` 选择仓库中的视觉权重，文本权重保持相同。

| 参数 | 视觉输入 | 权重文件名 | 本页视频样例 |
| --- | --- | --- | --- |
| `384` | 384 × 384 | `Qwen3-VL-2B-Instruct_vision.axmodel` | 官方八帧 |
| `640` | 640 × 640 | `Qwen3-VL-2B-Instruct_vision_640x640.axmodel` | 官方序列的前六帧 |
| `u8` | 384 × 384 | `Qwen3-VL-2B-Instruct_vision_u8.axmodel` | 官方八帧 |

`u8` 是独立权重文件的名称，本页分别验证三个编码器。当前程序输入上限为 1536 token；640 编码器处理八帧时，仅视觉内容就需要 1600 token，入口会直接报错。该上限来自模型与程序配置，增加算力卡内存不会自动扩大输入窗口。

## 运行图片问答

先用普通 384 编码器识别动物：

```bash
python3 ~/edgeaccel/qwen3-vl2-p1536-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_horse.jpg" \
  --encoder 384 \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.'
```

等待加载和推理完成，终端会输出回答并退出。日志应出现 `termination_reason=eos last_token=151645`。再测试 640 编码器的中文描述：

```bash
python3 ~/edgeaccel/qwen3-vl2-p1536-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_car.jpg" \
  --encoder 640 \
  --prompt '请用一句中文描述图片中的主要内容。'
```

将 `--encoder` 改为 `u8` 可测试第三个编码器；替换 `--input` 和 `--prompt` 可使用自己的单张图片与问题。更长问题仍需满足输入长度上限。

## 运行视频帧问答

使用仓库内八张 JPEG 帧，按文件名顺序、1 fps 解释，每两帧组成一个视觉组：

```bash
python3 ~/edgeaccel/qwen3-vl2-p1536-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" \
  --encoder 384 \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

同一组八帧也可使用 `--encoder u8`。640 编码器改用运行包内的 `video-six`，其中六张图片与官方序列的前六帧逐字节相同：

```bash
python3 ~/edgeaccel/qwen3-vl2-p1536-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input ~/edgeaccel/qwen3-vl2-p1536-fixed/video-six \
  --encoder 640 \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

这里的 1 fps 是输入配置，未核实原视频的实际帧率。本页展示已抽帧序列的推理结果，未覆盖 MP4 解码、实时视频、多轮问答或任意长度的视频输入。

## 检查运行结果

每条推理命令完成后执行：

```bash
echo $?
axcl-smi
```

退出码应为 `0`，日志应记录真实 EOS，设备列表不应继续显示该推理进程。`context-limit` 表示输出触及上下文上限，不能作为完整回答结束。对照输入核对对象、人数、文字和动作，原始回答及核对结果见下方效果展示。

本轮进程耗时包含网络模型读取、加载和推理，不代表本地存储性能。实际 8GB 卡、更多输入和连续运行仍需独立验证。

## 查看配套源码

运行包包含固定源码、修改差异、编译信息、原生词表来源和文件校验值。程序基于 AXERA 的 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7`，使用本页配套版本。请保持程序、分词文件和模型版本一致。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成三个视觉编码器的图片与视频帧问答，展示原始输出及核对结果。

**384 标准编码器：五组图片问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方输入：骑乘者、马和狗](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_horse.jpg)

<figcaption>官方输入：骑乘者、马和狗</figcaption>
</figure>

<figure>

[![官方输入：红色双层巴士与街道](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_car.jpg)

<figcaption>官方输入：红色双层巴士与街道</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

正确识别前景的马和狗。

**示例 2：输入**

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
2
```

回答 2，与骑乘者和右侧红衣人物两名清晰对象相符。

**示例 3：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在一辆红色双层巴士前，巴士上写着“当你说话时，事情会变得更有趣”（Things get more exciting when you say yes）的广告。
```

女士和红色双层巴士识别正确；广告语的中文翻译不准确。

**示例 4：输入**

```text
请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
图片前景中的两种动物是马和狗。
```

中文正确识别前景的马和狗。

**示例 5：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

重复运行与首次英文回答一致；仅说明此固定输入两次一致。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动物识别（英文） | 83.972 | 435 |
| 人数统计 | 81.017 | 87 |
| 街景描述（中文） | 86.493 | 1102 |
| 动物识别（中文） | 82.260 | 348 |
| 重复动物识别 | 83.867 | 435 |

**384 标准编码器：两组八帧视频问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![视频帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0000.jpg)

<figcaption>视频帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 4 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0024.jpg)

<figcaption>视频帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 8 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0056.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0056.jpg)

<figcaption>视频帧输入：第 8 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只土拨鼠在山地草地上互相推搡，它们的前爪在空中挥舞，似乎在进行一场激烈的争斗。
```

描述了相互推搡、挥动前爪等动作；“激烈的争斗”属于意图推测，且未按要求分成两句。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
The two badgers are engaging in a playful fight, with one pushing the other with its front paws. The badger on the left is pushing the other badger with its front paws.
```

描述了前爪接触和推搡；“playful fight”属于意图推测，badgers 与中文“土拨鼠”的物种称呼不一致。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动作描述（中文） | 89.191 | 1015 |
| 动作描述（英文） | 92.172 | 1333 |

**640 编码器：五组图片问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方输入：骑乘者、马和狗](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_horse.jpg)

<figcaption>官方输入：骑乘者、马和狗</figcaption>
</figure>

<figure>

[![官方输入：红色双层巴士与街道](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_car.jpg)

<figcaption>官方输入：红色双层巴士与街道</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

正确识别前景的马和狗。

**示例 2：输入**

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
2
```

回答 2，与两名清晰可见的人物相符。

**示例 3：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在一辆红色双层巴士前，背景是伦敦的街道。
```

女士和红色双层巴士识别正确；“伦敦”地名未经独立核实，此回答没有测试广告翻译是否准确。

**示例 4：输入**

```text
请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
图片前景中两种动物是马和狗。
```

中文正确识别前景的马和狗。

**示例 5：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

重复运行与首次英文回答一致；仅说明此固定输入两次一致。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动物识别（英文） | 88.290 | 491 |
| 人数统计 | 85.218 | 143 |
| 街景描述（中文） | 88.392 | 578 |
| 动物识别（中文） | 86.619 | 404 |
| 重复动物识别 | 86.682 | 491 |

**640 编码器：两组六帧视频问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![视频帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0000.jpg)

<figcaption>视频帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 4 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0024.jpg)

<figcaption>视频帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 6 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0040.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0040.jpg)

<figcaption>视频帧输入：第 6 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只山地犬在岩石上激烈地互相推搡，它们的前爪在空中挥舞，似乎在进行一场激烈的争斗。
```

描述了前爪挥动和相互推搡；“山地犬”与图中动物外观不符，未按要求分成两句，“激烈的争斗”也无法仅凭这些帧确认。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
The two animals are play fighting with each other. They are both standing on their hind legs and pushing each other with their paws.
```

站立、抬爪接触和相互推搡与画面相符；“play fighting”属于意图推测。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动作描述（中文） | 97.757 | 1154 |
| 动作描述（英文） | 97.074 | 1067 |

**384 vision_u8 编码器：五组图片问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方输入：骑乘者、马和狗](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_horse.jpg)

<figcaption>官方输入：骑乘者、马和狗</figcaption>
</figure>

<figure>

[![官方输入：红色双层巴士与街道](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/ssd_car.jpg)

<figcaption>官方输入：红色双层巴士与街道</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

正确识别前景的马和狗。

**示例 2：输入**

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
3
```

回答 3，与本页按骑乘者和右侧红衣人物两名清晰对象核对的标准不一致；背景远处小目标不计入该标准。

**示例 3：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在一辆红色的双层巴士前，背景是城市街道。
```

女士、红色双层巴士和街道描述与图片相符；未给出广告翻译，不能据此判断文字翻译能力。

**示例 4：输入**

```text
请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
图片前景中的两种动物是马和狗。
```

中文正确识别前景的马和狗。

**示例 5：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

重复运行与首次英文回答一致；仅说明此固定输入两次一致。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动物识别（英文） | 83.514 | 435 |
| 人数统计 | 80.101 | 87 |
| 街景描述（中文） | 83.566 | 522 |
| 动物识别（中文） | 82.720 | 348 |
| 重复动物识别 | 82.508 | 435 |

**384 vision_u8 编码器：两组八帧视频问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![视频帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0000.jpg)

<figcaption>视频帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 4 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0024.jpg)

<figcaption>视频帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 8 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0056.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047-20261003/frame_0056.jpg)

<figcaption>视频帧输入：第 8 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只土拨鼠在山地草地上激烈地互相扑打，它们的前爪在空中挥舞，似乎在进行一场激烈的争斗。
```

描述了前爪挥动和相互接触；“土拨鼠”的物种称呼未获独立确认，争斗意图不能仅凭画面确定，且未按要求分成两句。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
The two animals are engaging in a playful interaction, possibly a mock fight or a playful wrestling match. They are facing each other, with their paws and bodies in close contact, suggesting a playful or competitive interaction.
```

面对面、前爪及身体接触与画面相符；玩耍、模拟搏斗或竞争意图均属于模型推测。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动作描述（中文） | 90.111 | 1073 |
| 动作描述（英文） | 91.446 | 1420 |

**使用时注意：**

- 384 街景回答中的广告中文翻译不准确；640 与 vision_u8 未翻译广告，不能据此判断翻译问题已解决。
- vision_u8 人数回答为 3，与按两名清晰人物核对的标准不一致；计数任务需明确远处小目标是否纳入。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`cf4b904ba59e66fefd17668af196fc9c199ab70f`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 固定 AXCL C++ 配套程序 / AX-LLM 3be4cc3 + 本页修复 / 本地原生分词 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输入覆盖 | 2 张图片 / 8 帧视频 | 每个编码器 5 条图片问题、2 条视频问题，共 21 个独立进程；640 使用前六帧。 |
| 算力卡执行 | 32 个 AXModel | 三个图像编码器、28 个文本层与输出层均执行并释放，共 13403 次调用。 |
| 视觉输入 | 384 × 384 / 640 × 640 | 单图1组；384视频4组，640六帧视频3组视觉执行。 |

适用范围：

- 640 中文视频将动物称为“山地犬”，与画面外观不符；384 视频中英文物种称呼也不一致。
- 三个编码器的中文视频回答均未按要求分成两句。地点名称和玩耍、争斗、竞争等意图描述未独立核实。
- 384与vision_u8使用官方八张JPEG，640使用前六张；按文件名排序、1 fps解释，未验证原始视频时基、MP4解码或实时视频。
- 21条问题均以 EOS=151645 结束。本次最多1259个输入token；程序输入上限1536，640八帧输入已在入口拒绝。未覆盖多轮、长上下文或连续运行。
- 实际 8GB 卡仍需独立验证。进程耗时包含网络读取和加载，不代表本地存储性能；尚未完成所有中间张量的浮点对照。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/gradio_demo.py) | Python 程序 / 前后处理 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_640x640.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_640x640.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_u8.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_u8.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/config.json) | 运行配置 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/images/demo.jpg) | 示例输入 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/post_config.json) | 运行配置 |
| [`run_ax650_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_ax650_api.sh) | 启动或构建脚本 |
| [`run_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_axcl_aarch64_api.sh) | 启动或构建脚本 |
| [`run_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_axcl_x86_api.sh) | 启动或构建脚本 |
| [`run_image_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_image_ax650.sh) | 启动或构建脚本 |

仓库提交：`cf4b904ba59e66fefd17668af196fc9c199ab70f`。仓库中的 32 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/tree/cf4b904ba59e66fefd17668af196fc9c199ab70f)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/tree/cf4b904ba59e66fefd17668af196fc9c199ab70f)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/README.md)。
- [主要程序入口：gradio_demo.py](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/gradio_demo.py)。
- [配套项目：AXERA-TECH/Qwen3-VL.AXERA](https://github.com/AXERA-TECH/Qwen3-VL.AXERA)。

返回[完整模型目录](../catalog.mdx)。
