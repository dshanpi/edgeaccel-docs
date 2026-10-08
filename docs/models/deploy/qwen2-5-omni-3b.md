---
title: "Qwen2.5-Omni-3B 部署指南"
sidebar_label: "Qwen2.5-Omni-3B"
description: "Qwen2.5-Omni-3B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-Omni-3B 部署指南

Qwen2.5-Omni-3B 用于图片与视频理解、文字及语音回答。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 准备本例依赖

以下命令在 RK3576 主机执行。本例使用固定图片和视频，生成文字与完整语音。图片保留完整画面并缩放为 308 × 308，视频使用官方 `videos/1.mp4`。

配套程序使用 `AXCLRTExecutionProvider` 在设备 0 执行编译模型；两个 ONNX 投影模型在主机 CPU 运行。

| 项目 | 本例环境 |
| --- | --- |
| 主机 | RK3576，ARM64 Linux，4GB 内存 |
| 算力卡 | AX8850，16GB |
| AXCL / 固件 | 3.16.0 |
| Python | 3.12 |
| 模型文件 | 105 个部署文件，约 8.11GB |

准备至少 12GB 可用存储空间，用于模型、独立 Python 环境和运行结果。8GB 算力卡不在本页这次实测的范围内。

安装系统依赖：

```bash
sudo apt update
sudo apt install -y python3-venv ffmpeg libsndfile1 libgomp1
axcl-smi
```

## 下载配套程序与模型

下载[单卡 AXCL 配套程序](/examples/qwen2-5-omni-3b-axcl.tar.gz)，将下载文件重命名为 `qwen2-5-omni-3b-axcl.tar.gz`，保存到 RK3576 的 `~/Downloads`。配套包包含运行入口、依赖安装脚本、模型校验表、图片样例和独立的 Omni 处理器源码。下载后先校验压缩包：

```bash
echo "f1c293593c0d09be602d2aa04cb3f644b5e445bc8c224b475d9ee65619bac62e  $HOME/Downloads/qwen2-5-omni-3b-axcl.tar.gz" | sha256sum -c -
```

```bash
mkdir -p ~/edgeaccel/examples
tar -xzf ~/Downloads/qwen2-5-omni-3b-axcl.tar.gz -C ~/edgeaccel/examples
cd ~/edgeaccel/examples/qwen2-5-omni-3b-axcl

python3 -m venv ~/edgeaccel/omni-env
source ~/edgeaccel/omni-env/bin/activate
python -m pip install --no-cache-dir -r requirements-base.txt
python -m pip check
python install_runtime.py --target ~/edgeaccel/omni-runtime
```

`pip check` 应无依赖冲突。安装脚本校验配套文件，将 Omni 专用处理器和补充依赖放入 `omni-runtime`，完成后输出 `installed: true`。

模型使用固定提交 `38c42b43ece9cca5acf024aeddd8d0a188eca44d`。首次下载先按[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)准备 `hf`；代理和离线复制方法也见该页。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-omni-3b/38c42b43ece9
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-Omni-3B \
  --revision 38c42b43ece9cca5acf024aeddd8d0a188eca44d \
  --exclude '*.bfloat16.bin' '*.float32.bin' \
  --local-dir "$MODEL_DIR"
```

保留 `.npy` 形式的 embedding 权重；排除项是本例不读取的两组重复 `.bin` 文件。

## 运行图片与视频示例

在配套程序目录执行，沿用上一步的 `MODEL_DIR`。先检查模型校验值、Python 依赖和运行参数：

```bash
source ~/edgeaccel/omni-env/bin/activate
cd ~/edgeaccel/examples/qwen2-5-omni-3b-axcl
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case chinese-video \
  --output ~/edgeaccel/omni-result-zh \
  --check-only
```

输出应包含 `modelFilesVerified: 105`。该步骤检查文件和 CPU 环境，尚未执行算力卡推理。

运行图片示例。`image-description` 提问为“请用中文简短描述这张图片。”，`image-count` 提问为“图片中有几个人、几只狗？他们在做什么？”：

```bash
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case image-description \
  --output ~/edgeaccel/omni-image-description

python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case image-count \
  --output ~/edgeaccel/omni-image-count
```

运行中文示例，提问为“请简短描述视频中的乐器和声音。”：

```bash
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case chinese-video \
  --output ~/edgeaccel/omni-result-zh
```

运行官方英文示例：

```bash
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case official-video \
  --output ~/edgeaccel/omni-result-en
```

每次使用一个尚不存在的输出目录。完成后，终端打印文字回答、音频路径和时长；对应目录应包含 `answer.txt`、`output.wav` 和 `result.json`。程序异常退出时先检查错误信息，不将中途生成的文件视为完整结果。



## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成图片两问、视频中英文回答及语音生成。图片中的人数和狗的数量正确，动作、朝向等细节有误；下方保留完整原始输出，作为部署效果对照。

**中文图片描述**

输入真实照片，保留完整模型回答。

<div className="model-effect-gallery">

<figure>

[![输入照片：海边的一名女子与一只狗](../../../static/validation/effects/qwen2-5-omni-3b-20261004/input.jpg)](../../../static/validation/effects/qwen2-5-omni-3b-20261004/input.jpg)

<figcaption>输入照片：海边的一名女子与一只狗</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用中文简短描述这张图片。
```

**实际回复**

```text
嗯，这张图片里有个人和一只狗。人坐在沙滩上，背对着镜头，狗在她旁边，好像在看海呢。海特别美，太阳也落山了。你要是还有啥想法，咱们可以再聊聊。
```

识别出人、狗和沙滩；“背对镜头”“看海”与画面不符。实际是女子和狗面对面，手与前爪相接；不能据此确认日落时间。

| 输出 | 本次结果 |
| --- | --- |
| 语音格式 | 24 kHz / 单声道 WAV |
| 语音时长 | 14.32 秒 |
| 完整语音段数 | 4 |

中文图片描述生成的完整语音

<audio controls preload="metadata" src="/validation/effects/qwen2-5-omni-3b-20261004/image-description.wav" aria-label="中文图片描述生成的完整语音"></audio>

[下载音频](../../../static/validation/effects/qwen2-5-omni-3b-20261004/image-description.wav)

**图片数量与动作问答**

同一照片，改问人数、狗的数量和动作；通过配套命令实际运行。

<div className="model-effect-gallery">

<figure>

[![输入照片：海边的一名女子与一只狗](../../../static/validation/effects/qwen2-5-omni-3b-20261004/input.jpg)](../../../static/validation/effects/qwen2-5-omni-3b-20261004/input.jpg)

<figcaption>输入照片：海边的一名女子与一只狗</figcaption>
</figure>

</div>

**示例 1：输入**

```text
图片中有几个人、几只狗？他们在做什么？
```

**实际回复**

```text
图片里有一个人，一只狗。人坐在沙滩上，狗在旁边，人好像在给狗喂东西呢。你要是还有啥想法，也可以和我说说呀。
```

“一个人、一只狗”数量正确。“喂东西”的动作判断不符；照片中女子抬手与狗的前爪相接。合成语音自动回转写出现“娘是”等差异，仍需人工复听。

| 输出 | 本次结果 |
| --- | --- |
| 语音格式 | 24 kHz / 单声道 WAV |
| 语音时长 | 10.76 秒 |
| 完整语音段数 | 3 |

图片数量与动作问答生成的完整语音

<audio controls preload="metadata" src="/validation/effects/qwen2-5-omni-3b-20261004/image-count.wav" aria-label="图片数量与动作问答生成的完整语音"></audio>

[下载音频](../../../static/validation/effects/qwen2-5-omni-3b-20261004/image-count.wav)

**中文视频与声音理解**

官方短视频带音轨，使用中文问题生成文字与语音。

**示例 1：输入**

```text
请简短描述视频中的乐器和声音。
```

**实际回复**

```text
嗯…视频里有钢琴，还有音乐声。钢琴是红色的，放在木制的桌子上。音乐声是那种轻快的，像是在弹奏钢琴曲呢。你要是还有啥想法，也可以和我说说呀。
```

识别出红色键盘乐器并提到音乐。画面中乐器位于木质桌面下方，“放在木制桌子上”的位置表述不够准确。

| 输出 | 本次结果 |
| --- | --- |
| 语音格式 | 24 kHz / 单声道 WAV |
| 语音时长 | 14.36 秒 |
| 完整语音段数 | 4 |

中文视频与声音理解生成的完整语音

<audio controls preload="metadata" src="/validation/effects/qwen2-5-omni-3b-20261004/chinese.wav" aria-label="中文视频与声音理解生成的完整语音"></audio>

[下载音频](../../../static/validation/effects/qwen2-5-omni-3b-20261004/chinese.wav)

输入视频：演奏红色键盘乐器

<video className="model-effect-video" controls playsInline preload="metadata" src="/validation/effects/qwen2-5-omni-3b-20261004/input.mp4" aria-label="输入视频：演奏红色键盘乐器"></video>

[下载视频](../../../static/validation/effects/qwen2-5-omni-3b-20261004/input.mp4)

**官方英文视频示例**

保留官方仅输入视频的示例，输出英文文字与语音。

**示例 1：输入**

```text
输入官方短视频（包含音轨，不追加文字问题）。
```

**实际回复**

```text
It looks like you're playing the piano. That's really cool! Are you practicing a new song? If you want to talk about your playing or share some tips, feel free to keep the conversation going.
```

回答提到正在演奏键盘乐器，与画面主要内容一致。自动回转写与完整英文回答一致；本次未进行人工音质评分。

| 输出 | 本次结果 |
| --- | --- |
| 语音格式 | 24 kHz / 单声道 WAV |
| 语音时长 | 11.06 秒 |
| 完整语音段数 | 4 |

官方英文视频示例生成的完整语音

<audio controls preload="metadata" src="/validation/effects/qwen2-5-omni-3b-20261004/english.wav" aria-label="官方英文视频示例生成的完整语音"></audio>

[下载音频](../../../static/validation/effects/qwen2-5-omni-3b-20261004/english.wav)

输入视频：演奏红色键盘乐器

<video className="model-effect-video" controls playsInline preload="metadata" src="/validation/effects/qwen2-5-omni-3b-20261004/input.mp4" aria-label="输入视频：演奏红色键盘乐器"></video>

[下载视频](../../../static/validation/effects/qwen2-5-omni-3b-20261004/input.mp4)

**使用时注意：**

- 图片中的动作和朝向、视频中的物体位置有判断偏差；不用于据此判定真实行为。固定输入成功不代表任意图片或视频均可运行。
- 合成语音已完整保存；独立自动回转写在部分中文词语出现差异，尚未完成人工听音、自然度评分或长文本音质验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`38c42b43ece9cca5acf024aeddd8d0a188eca44d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12 / Torch 2.5.1 / PyAXEngine 0.1.3；Omni 处理器固定提交 cb39f7dd；2 个 ONNX 投影在主机 CPU，65/66 个 AXModel 在设备 0。 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实测输入 | 图片 2 问 / 视频中英文 2 问 | 同一真实照片与官方短视频；各保存完整文字和语音。 |
| 语音输出 | 24 kHz / 单声道 | 按原回复 token 分段生成，再拼接全部音频；不截断回答。 |

适用范围：

- 使用 16GB AX8850 和已核对依赖的 RK3576 环境。8GB 容量、全新存储环境、持续运行及更换媒体输入尚未验证。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/run_axinfer.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/python/run_axinfer.py) | Python 程序 / 前后处理 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/qwen2_5_omni_talker_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/generation_config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/preprocessor_config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-talker-chunk_prefill_512/tokenizer_config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/generation_config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/preprocessor_config.json) | 运行配置 |
| [`Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/Qwen2.5-Omni-3B-AX650-thinker-chunk_prefill_512/tokenizer_config.json) | 运行配置 |

仓库提交：`38c42b43ece9cca5acf024aeddd8d0a188eca44d`。仓库中的 66 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/tree/38c42b43ece9cca5acf024aeddd8d0a188eca44d)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/tree/38c42b43ece9cca5acf024aeddd8d0a188eca44d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/README.md)。
- [主要程序入口：python/run_axinfer.py](https://huggingface.co/AXERA-TECH/Qwen2.5-Omni-3B/blob/38c42b43ece9cca5acf024aeddd8d0a188eca44d/python/run_axinfer.py)。

返回[完整模型目录](../catalog.mdx)。
