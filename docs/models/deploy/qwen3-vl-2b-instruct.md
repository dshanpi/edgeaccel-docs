---
title: "Qwen3-VL-2B-Instruct 部署指南"
sidebar_label: "Qwen3-VL-2B-Instruct"
description: "Qwen3-VL-2B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-2B-Instruct 部署指南

Qwen3-VL-2B-Instruct 用于图像与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-2B-Instruct` 的固定版本。下面下载本页选用的 72 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-2b-instruct/b88b51a9b583
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-2B-Instruct \
  --include "*" \
  --revision b88b51a9b583a5480717de7955a7b10a28dde9d4 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套程序

本例使用约 4GB RAM 的 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16。下载前为模型预留至少 4GB 存储空间；词嵌入读取约占 594 MiB 主机内存。程序依赖 OpenCV 4.6，当前结果仅覆盖 16GB 卡。

下载[配套运行包](/examples/qwen3-vl2-standard-fixed-20261002.tar.gz)，保存到 `~/edgeaccel/`。保留前文设置的 `MODEL_DIR`，在连接算力卡的 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl2-standard-fixed-20261002.tar.gz
chmod +x qwen3-vl2-standard-fixed/main_axcl_aarch64
ldd qwen3-vl2-standard-fixed/main_axcl_aarch64
python3 qwen3-vl2-standard-fixed/verify_models.py "$MODEL_DIR"
```

`ldd` 输出不应出现 `not found`，校验程序应输出 `Verified 72 model files`。文件校验失败时，重新下载对应固定版本文件后再运行。

运行包使用本模型导出的本地分词文件，无需启动 HTTP 分词服务。图像编码器、28 个文本层和输出层在算力卡执行；分词、图像预处理和词嵌入读取在主机完成。配套入口固定使用设备 0、384 × 384 视觉输入和 `top_k=1` 贪心解码。

## 运行图片问答

在同一终端执行：

```bash
python3 ~/edgeaccel/qwen3-vl2-standard-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_horse.jpg" \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.'
```

等待加载和推理完成，终端会输出回答并退出。程序应报告 `termination_reason=eos last_token=151645`。再使用巴士图片测试中文描述：

```bash
python3 ~/edgeaccel/qwen3-vl2-standard-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/images/ssd_car.jpg" \
  --prompt '请用一句中文描述图片中的主要内容。'
```

替换 `--input` 为自己的单张图片路径、`--prompt` 为问题即可测试新输入。每次命令启动独立进程，完成后释放模型。

## 运行视频帧问答

本例输入是仓库内已经抽取的八张 JPEG 帧。按文件名顺序、1 fps 解释帧序列，每两帧组成一个视觉组，共四组。这里的 1 fps 是输入配置，不代表原始视频的实际帧率。

```bash
python3 ~/edgeaccel/qwen3-vl2-standard-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

配套入口仅接受包含八张 JPEG 的目录。本例未覆盖 MP4 解码、实时视频、多轮问答或任意长度视频。新增场景需单独检查抽帧顺序、输入长度和结果。

## 检查运行结果

```bash
echo $?
axcl-smi
```

退出码应为 `0`，日志应包含真实 EOS 结束记录，设备列表不应继续显示该推理进程。`context-limit` 表示到达上下文上限，不能作为正常回答结束。对照输入核对对象、人数和动作，原始回答及本次核对结果见下方效果展示。

本轮进程耗时包含网络模型读取、加载和推理，不代表模型存放在本地存储时的性能。实际 8GB 卡、更多输入和连续运行仍需独立验证。

## 查看配套源码

运行包包含固定源码、修改差异、编译信息、词表导出记录和文件校验值。程序基于 AXERA 的 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7`，使用本页复测配套版本；请保持程序、分词文件和模型版本一致。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成五组图片问答与两组八帧视频问答，展示原始输出及核对结果。

**五组图片问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方输入：骑乘者、马和狗](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/ssd_horse.jpg)

<figcaption>官方输入：骑乘者、马和狗</figcaption>
</figure>

<figure>

[![官方输入：红色双层巴士与街道](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/ssd_car.jpg)

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

正确识别出前景中的马和狗，并按要求用一句英文回答。

**示例 2：输入**

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
2
```

人数为 2，与画面中骑乘者和右后方红衣人物一致。

**示例 3：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在一辆红色的双层巴士前，巴士上写着“当你说‘你很兴奋’时，事情会变得更有趣”（Things get more exciting when you say 'yes'）。
```

前景女士和红色双层巴士识别正确；广告语的中文翻译不准确，不能作为文字翻译验收结果。

**示例 4：输入**

```text
请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
图片前景中是马和狗。
```

用一句中文正确识别出前景中的马和狗。

**示例 5：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

与第一次相同问题的回答一致；这是两个独立进程的重复样例，不代表长期稳定性。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动物识别（英文） | 104.548 | 435 |
| 人数统计 | 100.280 | 87 |
| 街景描述（中文） | 109.104 | 1247 |
| 动物识别（中文） | 102.338 | 290 |
| 重复动物识别 | 103.014 | 435 |

**两组八帧视频问答**

以下展示固定官方输入及原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![视频帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/frame_0000.jpg)

<figcaption>视频帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 4 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/frame_0024.jpg)

<figcaption>视频帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 8 帧](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/frame_0056.jpg)](../../../static/validation/effects/qwen3-vl-2b-instruct-20261002/frame_0056.jpg)

<figcaption>视频帧输入：第 8 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只土拨鼠在岩石上互相拍打，似乎在进行一场激烈的玩耍或争斗。它们的毛色是灰白相间的，耳朵和脸部有黑色斑点。背景是绿色的山坡和蓝天。
```

描述了两只动物相互拍打的动作，岩石、山坡和蓝天与输入帧相符。输出三句，未遵守“两句”的要求；物种名称尚未标注确认，“玩耍或争斗”属于模型推测。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
The two animals, which appear to be badgers, are standing on their hind legs and facing each other, with their front paws raised as if they are playfully engaging in a fight. They are both displaying a similar posture and facial expression, suggesting they are interacting in a manner that is both playful and competitive.
```

站立、抬爪和相互接触的动作与输入帧相符，并按要求用两句英文回答。但将动物称为 badgers，与中文回答的“土拨鼠”不一致；玩闹或竞争意图尚未核实。

| 问题 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| 动作描述（中文） | 115.265 | 1508 |
| 动作描述（英文） | 118.355 | 2029 |

**使用时注意：**

- 巴士图片的主要对象识别正确，但广告语中文翻译有误。
- 中文视频回答未遵守“两句”的格式要求；动物物种与玩耍、争斗等意图尚未核实。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`b88b51a9b583a5480717de7955a7b10a28dde9d4`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 固定 AXCL C++ 配套程序 / AX-LLM 3be4cc3 + 本页修复 / 本地原生分词 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输入覆盖 | 2 张图片 / 8 帧视频 | 5 条图片问题、2 条视频问题，七个独立进程。 |
| 算力卡执行 | 30 个 AXModel | 图像编码器、28 个文本层与输出层均执行并释放，共 6031 次调用。 |
| 视觉输入 | 384 × 384 | 单图 1 组、八帧视频 4 组视觉执行。 |

适用范围：

- 同一视频的中英文回答对动物物种判断不一致，不能作为物种识别结果。
- 视频使用官方八张 JPEG，按文件名排序并以 1 fps 解释；未验证原始视频时基、MP4 解码或实时视频。
- 七条问题均以 EOS=151645 结束。输入上限 1152 token；本例不包含多轮、长上下文和连续运行。
- 实际 8GB 卡仍需独立验证。进程耗时包含网络读取和加载，不代表本地存储性能；尚未完成所有中间张量的浮点对照。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/run_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen3_tokenizer.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/qwen3_tokenizer.py) | 旧版分词服务入口 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1152/Qwen3-VL-2B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/Qwen3-VL-2B-Instruct-AX650-c128_p1152/Qwen3-VL-2B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/Qwen3-VL-2B-Instruct-AX650-c128_p1152/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/config.json) | 运行配置 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/images/demo.jpg) | 示例输入 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/post_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/qwen3-vl-tokenizer/config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/qwen3-vl-tokenizer/generation_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/qwen3-vl-tokenizer/preprocessor_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/qwen3-vl-tokenizer/tokenizer_config.json) | 运行配置 |

仓库提交：`b88b51a9b583a5480717de7955a7b10a28dde9d4`。仓库中的 30 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/tree/b88b51a9b583a5480717de7955a7b10a28dde9d4)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/tree/b88b51a9b583a5480717de7955a7b10a28dde9d4)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/README.md)。
- [主要程序入口：qwen3_tokenizer.py](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct/blob/b88b51a9b583a5480717de7955a7b10a28dde9d4/qwen3_tokenizer.py)。
- [配套项目：AXERA-TECH/Qwen3-VL.AXERA](https://github.com/AXERA-TECH/Qwen3-VL.AXERA)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen3-VL-2B-Instruct)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
