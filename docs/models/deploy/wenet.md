---
title: "WeNet 部署指南"
sidebar_label: "WeNet"
description: "WeNet 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# WeNet 部署指南

WeNet 用于语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/WeNet` 的固定版本。下面下载本页选用的 9 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/wenet/000242476968
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/WeNet \
  "LICENSE" \
  "README.md" \
  "ax_common.py" \
  "axmodel/decoder/decoder.axmodel" \
  "axmodel/encoder_offline/encoder_offline.axmodel" \
  "axmodel/encoder_online/encoder_online.axmodel" \
  "demo.wav" \
  "requirements_ax.txt" \
  "run_ax.py" \
  --revision 00024247696833df2b74c226b2c6cdf3fe5fe13b \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备语音识别环境

本例在 RK3576 + AX8850 16GB M.2 上运行官方 WeNet 中文识别模型，比较离线识别、文件分块识别，以及两种解码方式。在已安装 PyAXEngine 的 Python 环境执行：

```bash
python -m pip install 'numpy==1.26.4' 'PyYAML==6.0.3'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认包含 `AXCLRTExecutionProvider`，设备 0 可用。本例使用官方 NumPy 音频前端，不需要安装完整训练环境。

## 下载训练配置和字表

保留前面模型下载步骤设置的 `MODEL_DIR`。AXERA 模型仓库中的推理例程还需要对应的 `train.yaml` 和 `units.txt`，从其上游固定版本获取：

```bash
CONFIG_ARCHIVE_DIR=~/edgeaccel/downloads/wenet-config
CONFIG_DIR=~/edgeaccel/configs/wenet-90acd57d
mkdir -p "$CONFIG_ARCHIVE_DIR" "$CONFIG_DIR"
~/edgeaccel/hf-env/bin/hf download openspeech/wenet-models \
  aishell_u2pp_conformer_exp.tar.gz \
  --revision 90acd57d17169a15d5ceab462c6e7db3bd003921 \
  --local-dir "$CONFIG_ARCHIVE_DIR"
printf '%s  %s\n' \
  b8daacf7f1eda37ade020e219d14b0c471a101e2c90ef8e2e2919a465e3af9a2 \
  "$CONFIG_ARCHIVE_DIR/aishell_u2pp_conformer_exp.tar.gz" | sha256sum -c -
```

确认校验结果为 `OK` 后，只解压配置文件：

```bash
tar -xzf "$CONFIG_ARCHIVE_DIR/aishell_u2pp_conformer_exp.tar.gz" \
  -C "$CONFIG_DIR" --strip-components=1 \
  aishell_u2pp_conformer_exp/train.yaml \
  aishell_u2pp_conformer_exp/units.txt \
  aishell_u2pp_conformer_exp/global_cmvn
```

下载 [WeNet 算力卡示例](../../../static/examples/wenet_card.py)，保存为 `~/edgeaccel/wenet_card.py`。示例核对官方推理源码、配置和字表的校验值，并显式使用 AXCL。

## 运行四种识别组合

```bash
python ~/edgeaccel/wenet_card.py \
  --model-dir "$MODEL_DIR" --config-dir "$CONFIG_DIR" \
  --output ~/edgeaccel/results/wenet-01
```

输出目录须尚不存在。程序读取官方 `demo.wav`，依次运行以下组合，每种重复两次：

| 输入方式 | 解码方式 | 使用的模型 |
| --- | --- | --- |
| 离线 | CTC 前缀束搜索 | 离线编码器 |
| 离线 | 注意力重评分 | 离线编码器、解码器 |
| 分块在线 | CTC 前缀束搜索 | 在线编码器 |
| 分块在线 | 注意力重评分 | 在线编码器、解码器 |

`deployment-result.json` 中 `completed: true` 表示八次识别完成；`sessions` 记录三份权重的实际调用，`samples` 包含每次识别文本、处理时间与 RTF。输出目录同时保存实际输入 `input.wav` 和音频特征 `features.npy`。

## 识别自己的音频

准备 **16 kHz、单声道、16 位 PCM WAV**。本例限制为 10 秒以内短语音，避免超过离线编码器的固定窗口。替换文件路径并使用新的输出目录：

```bash
python ~/edgeaccel/wenet_card.py \
  --model-dir "$MODEL_DIR" --config-dir "$CONFIG_DIR" \
  --audio ~/edgeaccel/inputs/speech.wav \
  --output ~/edgeaccel/results/wenet-custom-01
```

在线模式将已有音频文件按块送入模型，并在每次识别前重置缓存。本例未接入麦克风，不将其耗时当作实时采集延迟。

## 查看识别文本与速度

下方展示实际音频和四种组合的输出。处理时间包含读取音频、特征提取、算力卡推理和解码，不包含模型加载与结果保存。RTF 为处理时间除以音频时长，小于 1 表示处理速度快于该文件的播放速度。

相同音频的重复结果用于检查本次运行的一致性，不能代替中文识别准确率、长语音和噪声适应性评估。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

16GB 卡完成 WeNet 离线/分块、CTC/注意力四种组合及重复运行。8 次均输出“甚至出现交易几乎停止的情况”；同文件的官方标注使用“停滞”，每次有 1/13 字符差异（7.692%），不能仅凭重复一致判为识别准确。

**官方中文音频：四种识别组合**

4.2039375 秒官方音频，四种组合各运行两次，均输出“甚至出现交易几乎停止的情况”。相同模式的重复模型输入输出校验值一致；这里展示实际识别文本，不将其作为人工标注真值。

| 输入方式 | 解码方式 | 识别文本 | 平均处理时间 / s | 平均 RTF |
| --- | --- | --- | --- | --- |
| 离线 | CTC 前缀束搜索 | 甚至出现交易几乎停止的情况 | 0.491145 | 0.116830 |
| 离线 | 注意力重评分 | 甚至出现交易几乎停止的情况 | 0.500570 | 0.119072 |
| 分块在线 | CTC 前缀束搜索 | 甚至出现交易几乎停止的情况 | 0.735614 | 0.174982 |
| 分块在线 | 注意力重评分 | 甚至出现交易几乎停止的情况 | 0.714190 | 0.169886 |

实际输入：官方 demo.wav，16 kHz 单声道 PCM16

<audio controls preload="metadata" src="/validation/effects/wenet-20260928/input.wav" aria-label="实际输入：官方 demo.wav，16 kHz 单声道 PCM16"></audio>

[下载音频](../../../static/validation/effects/wenet-20260928/input.wav)

**核对同一音频的参考文字**

音频文件 SHA256 与 FireRedASR 的 BAC009S0764W0121.wav 完全一致，使用其固定版本的[官方文字标注](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/wav/text)“甚至出现交易几乎停滞的情况”作单句对照。去除空白与 Unicode 标点后按字符计算编辑距离，不合并同音字或同义词。这不是独立人工听写或完整数据集准确率。 四种组合的两个重复结果均为“停止”，与该标注相差“滞→止”一字。重复运行不增加独立音频样本数。

| 参考文字 | 实际转写 | 字符差异 / 参考字数 | 本句 CER |
| --- | --- | --- | --- |
| 甚至出现交易几乎停滞的情况 | 甚至出现交易几乎停止的情况 | 1 / 13 | 7.692% |

**使用时注意：**

- 仅一段官方音频；已对照同文件的固定文字标注得到 1/13 字符差异，仍无独立人工标注集或 CPU 浮点参考。
- 分块在线模式读取已有文件，未验证麦克风采集、长语音、并发和连续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`00024247696833df2b74c226b2c6cdf3fe5fe13b`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际音频时长 | 4.203938 s | 16 kHz、单声道、16位PCM，特征形状1 × 418 × 80。 |
| 平均处理时间 | 0.491–0.736 s | 每种模式两次平均，包含音频读取、特征、传输、推理和解码，不含模型加载和保存。 |
| 实际模型调用 | 离线4次 / 在线28次 / 解码4次 | 在线每段音频7块；模型加载不计为有效推理。 |

适用范围：

- 本次为16GB算力卡，真实8GB容量仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`generate_data.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/generate_data.py) | Python 程序 / 前后处理 |
| [`run_ax.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/run_ax.py) | Python 程序 / 前后处理 |
| [`axmodel/decoder/decoder.axmodel`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/axmodel/decoder/decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodel/encoder_offline/encoder_offline.axmodel`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/axmodel/encoder_offline/encoder_offline.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodel/encoder_online/encoder_online.axmodel`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/axmodel/encoder_online/encoder_online.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/config.json) | 运行配置 |
| [`demo.wav`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/demo.wav) | 示例输入 |
| [`requirements_ax.txt`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/requirements_ax.txt) | Python 依赖清单 |
| [`requirements_x86.txt`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/requirements_x86.txt) | Python 依赖清单 |
| [`wenet/text/base_tokenizer.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/wenet/text/base_tokenizer.py) | 旧版分词服务入口 |
| [`wenet/text/bpe_tokenizer.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/wenet/text/bpe_tokenizer.py) | 旧版分词服务入口 |
| [`wenet/text/char_tokenizer.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/wenet/text/char_tokenizer.py) | 旧版分词服务入口 |
| [`wenet/text/hugging_face_tokenizer.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/wenet/text/hugging_face_tokenizer.py) | 旧版分词服务入口 |
| [`wenet/text/paraformer_tokenizer.py`](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/wenet/text/paraformer_tokenizer.py) | 旧版分词服务入口 |

仓库提交：`00024247696833df2b74c226b2c6cdf3fe5fe13b`。仓库中的 3 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/WeNet/tree/00024247696833df2b74c226b2c6cdf3fe5fe13b)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/WeNet/tree/00024247696833df2b74c226b2c6cdf3fe5fe13b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/README.md)。
- [主要程序入口：generate_data.py](https://huggingface.co/AXERA-TECH/WeNet/blob/00024247696833df2b74c226b2c6cdf3fe5fe13b/generate_data.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/WeNet)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
