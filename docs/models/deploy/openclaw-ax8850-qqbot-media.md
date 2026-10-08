---
title: "openclaw-ax8850-qqbot-media 部署指南"
sidebar_label: "openclaw-ax8850-qqbot-media"
description: "openclaw-ax8850-qqbot-media 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# openclaw-ax8850-qqbot-media 部署指南

openclaw-ax8850-qqbot-media 用于本地语音、图片和视频处理及 QQ 机器人媒体接入。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本地媒体功能已实测，完整应用尚未验证。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页部署仓库中的本地媒体功能：语音转文字、文字转语音、图片问答和视频问答。实测环境为 **RK3576 + AX8850 16GB M.2 算力卡、AXCL 3.16**。QQ 账号接入和 OpenClaw 对话调度尚未验证，不能将下面的本地结果视为 QQ 机器人完整部署通过。

先完成[驱动与设备检查](../../usage/device-check.md)，确认 `axcl-smi` 能识别算力卡。板端需要 Python 3.11 或更新版本；安装音视频工具和只读挂载工具：

```bash
sudo apt update
sudo apt install -y python3 ffmpeg rclone fuse3
python3 --version
```

模型可存放在 PC，通过 SSH 只读挂载供板端加载。以下步骤采用该方式；PC 需要保持开机，并安装 Python 3.11 或更新版本。模型推理在 M.2 算力卡执行。

## 下载部署包与模型

在 PC 下载并解压[本地媒体 AXCL 部署包](/examples/openclaw-media-axcl-20261004.zip)。进入解压后的 `openclaw-media-axcl` 目录，在 PowerShell 执行：

```powershell
# 根据实际网络修改代理地址；可直接访问 Hugging Face 时省略这两行。
$env:http_proxy = 'http://192.168.1.38:7897'
$env:https_proxy = 'http://192.168.1.38:7897'
python download_models.py --models-dir .\models
python verify_models.py --models-dir .\models
```

看到 `verifiedFiles: 874` 表示本页所需的 43 个 `.axmodel` 及分词器、字典、ONNX 组件等配套文件均已核对。下载脚本固定仓库提交，并逐文件检查 SHA-256；中断后可重跑，已校验的文件会跳过。不要混用仓库内的 SoC 运行程序与本页 AXCL 程序。

将部署包的 `board` 目录复制到 RK3576。下方以 `baiwen@192.168.1.44` 为例，按实际用户名与地址修改：

```powershell
ssh baiwen@192.168.1.44 "mkdir -p ~/openclaw-media-axcl"
scp -r .\board baiwen@192.168.1.44:~/openclaw-media-axcl/
```

PC 终端一启动只读文件服务，并保持运行：

```powershell
python serve_models.py --models-dir .\models --port 18867
```

PC 终端二建立 SSH 转发，并保持连接：

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -R 127.0.0.1:18868:127.0.0.1:18867 baiwen@192.168.1.44
```

在 RK3576 终端以普通用户挂载模型，不加 `sudo`：

```bash
mkdir -p ~/openclaw-media-axcl/models
rclone mount :http: ~/openclaw-media-axcl/models \
  --http-url http://127.0.0.1:18868/ \
  --read-only --vfs-cache-mode off --buffer-size 0 \
  --vfs-read-chunk-size 8M --vfs-read-chunk-size-limit 32M \
  --config /dev/null --daemon

cd ~/openclaw-media-axcl/board
export MODELS="$HOME/openclaw-media-axcl/models"
python3 run_media.py --models-dir "$MODELS" check
```

确认输出包含 `verifiedModelFiles: 874`，并显示算力卡信息。如果读取失败，先检查两个 PC 终端和 SSH 连接。板端已有足够存储时，也可将 `models` 完整复制到板端，再将 `MODELS` 指向该目录。

## 运行语音识别

在 RK3576 终端识别仓库随附的中文录音：

```bash
python3 run_media.py --models-dir "$MODELS" asr \
  "$MODELS/media/SenseVoiceSmall-axmodel/test_wavs/zh.wav" --language zh
```

终端输出实际转写文字。换用 `en.wav` 并指定 `--language en` 可识别英文样例。自有录音使用绝对路径；`--language auto` 开启自动语言识别。超过 10 秒的音频由脚本先做语音活动检测，再分段识别。

## 运行语音合成

在 RK3576 终端生成 WAV 文件：

```bash
python3 run_media.py --models-dir "$MODELS" tts \
  "$PWD/kokoro-v1_0.wav" '你好，欢迎使用算力卡。' --version 1_0

python3 run_media.py --models-dir "$MODELS" tts \
  "$PWD/kokoro-v1_1.wav" '你好，欢迎使用算力卡。' --version 1_1

ffprobe -v error -show_entries stream=sample_rate,channels kokoro-v1_0.wav
```

输出应为 24 kHz、单声道音频。默认使用音色编号 1、正常语速。Kokoro 的 6 个 AXModel 阶段在卡端运行，时长预测及声码器尾部使用配套 ONNX；发音和文本完整性需结合试听检查。

在 PC 下载录音后播放：

```powershell
scp baiwen@192.168.1.44:~/openclaw-media-axcl/board/kokoro-v1_0.wav .
scp baiwen@192.168.1.44:~/openclaw-media-axcl/board/kokoro-v1_1.wav .
```

## 运行图片与视频问答

语音命令结束后，在 RK3576 终端一启动视觉语言服务：

```bash
cd ~/openclaw-media-axcl/board
export MODELS="$HOME/openclaw-media-axcl/models"
python3 run_media.py --models-dir "$MODELS" serve
```

等待模型加载完成。RK3576 终端二检查服务，再提交仓库随附图片：

```bash
cd ~/openclaw-media-axcl/board
export MODELS="$HOME/openclaw-media-axcl/models"
curl --noproxy '*' --fail http://127.0.0.1:8120/health

python3 run_media.py --models-dir "$MODELS" image \
  "$MODELS/media/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/image.png"
```

服务返回图片描述。也可在图片路径后添加问题，例如 `'图中有几位宇航员？请只回答数量。'`。

下载下方的[实测视频片段](/validation/effects/openclaw-ax8850-qqbot-media-20261004/stone-mill-10s.mp4)，将文件名改为 `stone-mill-10s.mp4`，复制到 RK3576 的 `~/openclaw-media-axcl/board/`，再执行：

```bash
python3 run_media.py --models-dir "$MODELS" video "$PWD/stone-mill-10s.mp4"
```

默认均匀采样 8 帧，再间隔选取 4 帧，以原生视频输入提交；默认最多生成 512 token。下方保留原始问题的实际回复。该示例存在字幕与动作描述偏差，不能据此判断完整视频内容准确性。

若需要聚焦问题，可在视频路径后添加一句具体提问。不要通过不断增加帧数来处理长视频；修改采样和生成参数后需重新检查模型容量与结果。

## 停止服务

在视觉语言服务终端按 `Ctrl+C`，等待进程退出后检查 `axcl-smi`。同一部署目录会限制同时加载模型；如需继续语音处理，先退出视觉语言服务。

全部测试结束后，在 RK3576 终端执行：

```bash
fusermount3 -u ~/openclaw-media-axcl/models
```

再结束 PC 上的 SSH 转发和文件服务。原始模型仍保存在 PC，可供下一次使用。


## 查看部署效果

**本地媒体功能已实测，完整应用尚未验证** · RK3576 + AX8850 16GB。

部署包已完成本地语音识别、Kokoro 1.0/1.1 合成、图片问答和原生视频问答。以下展示实际输入与输出；QQ 机器人完整链路尚未验证。

**语音识别：中文录音**

输入为仓库随附的 zh.wav（5.592 秒）；下方是部署包的实际转写。识别结果中“开饭时间”存在文字偏差，未做人工修正。

**示例 1：输入**

```text
识别 zh.wav，语言 zh
```

**实际回复**

```text
开饭时间早上九点至下午五点
```

完整命令约 11.52 秒，包含模型文件校验、加载与识别。

输入录音：zh.wav

<audio controls preload="metadata" src="/validation/effects/openclaw-ax8850-qqbot-media-20261004/asr-zh.wav" aria-label="输入录音：zh.wav"></audio>

[下载音频](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/asr-zh.wav)

**语音合成：比较 Kokoro 两个版本**

两个版本使用相同文本“你好，欢迎使用算力卡。”，音色编号 1，正常语速。音频文件来自本次部署包运行；发音质量仍需试听评估。

| 版本 | 音频长度 | 完整命令耗时 |
| --- | --- | --- |
| 1.0 | 2.479 秒 | 22.34 秒 |
| 1.1 | 2.538 秒 | 22.91 秒 |

Kokoro 1.0：2.479 秒，24 kHz 单声道

<audio controls preload="metadata" src="/validation/effects/openclaw-ax8850-qqbot-media-20261004/tts-1_0.wav" aria-label="Kokoro 1.0：2.479 秒，24 kHz 单声道"></audio>

[下载音频](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/tts-1_0.wav)

Kokoro 1.1：2.538 秒，24 kHz 单声道

<audio controls preload="metadata" src="/validation/effects/openclaw-ax8850-qqbot-media-20261004/tts-1_1.wav" aria-label="Kokoro 1.1：2.538 秒，24 kHz 单声道"></audio>

[下载音频](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/tts-1_1.wav)

**图片问答：宇航员图片**

使用模型仓库随附的图片，询问主体、环境与可见文字。输出与画面中的三名宇航员及森林背景相符。

<div className="model-effect-gallery">

<figure>

[![实际输入：三名宇航员站在森林中](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/astronauts.png)](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/astronauts.png)

<figcaption>实际输入：三名宇航员站在森林中</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用中文极简要列出图中主体、环境、可见文字（如有）。
```

**实际回复**

```text
- 三名宇航员
- 森林环境
- 无可见文字
```

本次命令约 7.55 秒，不含常驻视觉语言服务的加载时间。

**视频问答：十秒场景描述**

输入取自官方 VideoAgent 样例的 2:30–2:40。原生视频分支接收 4 帧，模型返回完整回复；字幕和部分动作描述不准确。

<div className="model-effect-gallery">

<figure>

[![实际采样帧 1](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/video-frame-0.jpg)](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/video-frame-0.jpg)

<figcaption>实际采样帧 1</figcaption>
</figure>

<figure>

[![实际采样帧 3](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/video-frame-2.jpg)](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/video-frame-2.jpg)

<figcaption>实际采样帧 3</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用中文概括整段视频在讲什么、关键物体与场景变化；若有可见文字请列出。
```

**实际回复**

```text
这是一段电视剧《三国演义》的视频截图，画面中主要展示了一位身穿古代服饰的男子，他身着浅色长袍，头戴黑色帽子，留着长须，站在人群之中。他正用右手抚摸着自己的长须，表情严肃，似乎在思考或等待着什么。他周围有许多人，他们穿着不同颜色的服饰，有的穿着红色或黑色的服装，有的则穿着浅色的衣物。背景中可以看到一些古代建筑的结构，如木柱和墙壁，以及一些其他的建筑元素。画面下方有“蜀中”、“蜀中”、“蜀中”等字样，这些可能是剧中人物的对话或旁白。整个场景发生在一个古代的街道或广场上，周围有许多人，气氛显得紧张而严肃。
```

画面字幕包含“挪磨盘啦”，回复却写成重复的“蜀中”，并加入未确认的动作细节。本次约 38.02 秒，包含抽帧和请求，不含服务加载；仅确认基本运行。

实际输入：10 秒视频片段

<video className="model-effect-video" controls playsInline preload="metadata" src="/validation/effects/openclaw-ax8850-qqbot-media-20261004/stone-mill-10s.mp4" aria-label="实际输入：10 秒视频片段"></video>

[下载视频](../../../static/validation/effects/openclaw-ax8850-qqbot-media-20261004/stone-mill-10s.mp4)

**适用范围：**

- 仅实测 16GB 卡，尚未完成实际 8GB 卡容量验证。
- 本地媒体功能运行不等于 QQ 机器人接入成功；QQ 账号、插件和 OpenClaw 调度仍需单独验证。
- 语音转写、发音及视频字幕和动作描述仍有偏差；本页不代表完整数据集精度或长期稳定性通过。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/config.json`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/config.json) | 运行配置 |
| [`SenseVoiceSmall-axmodel/ax650/model-10-seconds.axmodel`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/SenseVoiceSmall-axmodel/ax650/model-10-seconds.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/Qwen3-VL-2B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/Qwen3-VL-2B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/post_config.json`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/post_config.json) | 运行配置 |
| [`SenseVoiceSmall-axmodel/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/SenseVoiceSmall-axmodel/tokens.txt) | 分词器 / 字典，必须配套 |
| [`config.json`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/config.json) | 运行配置 |
| [`kokoro/kokoro-multi-lang-v1_0-axmodel/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/kokoro/kokoro-multi-lang-v1_0-axmodel/tokens.txt) | 分词器 / 字典，必须配套 |
| [`kokoro/kokoro-multi-lang-v1_1-axmodel/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/kokoro/kokoro-multi-lang-v1_1-axmodel/tokens.txt) | 分词器 / 字典，必须配套 |
| [`kokoro/kokoro-multi-lang-v1_1-axmodel_bck/tokens.txt`](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/kokoro/kokoro-multi-lang-v1_1-axmodel_bck/tokens.txt) | 分词器 / 字典，必须配套 |

仓库提交：`45cbc485b03f48064e67c47839022c448f0391e1`。仓库中的 50 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/tree/45cbc485b03f48064e67c47839022c448f0391e1)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页实测范围为 16GB M.2 算力卡上的本地媒体功能；QQ 账号接入和 OpenClaw 调度尚未验证。
- 使用配套 AXCL 运行时，保留官方模型权重。AX630C 权重、v1.1 备份目录及 8GB 卡未计入本页验证。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/tree/45cbc485b03f48064e67c47839022c448f0391e1)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/openclaw-ax8850-qqbot-media/blob/45cbc485b03f48064e67c47839022c448f0391e1/README.md)。

返回[完整模型目录](../catalog.mdx)。
