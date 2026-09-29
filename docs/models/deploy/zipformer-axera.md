---
title: "Zipformer.axera 部署指南"
sidebar_label: "Zipformer.axera"
description: "Zipformer.axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Zipformer.axera 部署指南

Zipformer.axera 用于语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Zipformer.axera` 的固定版本。下面下载本页选用的 16 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/zipformer-axera/a690cb0f701b
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Zipformer.axera \
  "README.md" \
  "ax_pretrained_infer.py" \
  "inputs/axmodels_650N/decoder.axmodel" \
  "inputs/axmodels_650N/encoder.axmodel" \
  "inputs/axmodels_650N/joiner.axmodel" \
  "inputs/lang_char_bpe/tokens.txt" \
  "inputs/test_wavs/0.wav" \
  "inputs/test_wavs/002.mp3" \
  "inputs/test_wavs/1.wav" \
  "inputs/test_wavs/2.wav" \
  "inputs/test_wavs/3.wav" \
  "inputs/test_wavs/4.wav" \
  "inputs/test_wavs/46.wav" \
  "inputs/test_wavs/demo.wav" \
  "inputs/test_wavs/fileid_144.wav" \
  "inputs/test_wavs/fileid_249.wav" \
  --revision a690cb0f701b11274505209cb3dec6bf7bd91e4b \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

先按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，再安装本例依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchaudio==2.5.1' 'soundfile==0.13.1' 'kaldi-native-fbank==1.22.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本例使用 `inputs/axmodels_650N/` 下的 encoder、decoder 和 joiner，经 AXCL 在 M.2 算力卡上执行。

## 运行音频转写

下载 [Zipformer 算力卡示例](../../../static/examples/zipformer_card.py)，保存为 `~/edgeaccel/zipformer_card.py`。沿用上方下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/zipformer_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/zipformer-01
```

输出目录须尚不存在。默认处理仓库中的十段 WAV/MP3，再重复第一段，并检查三秒静音。每个文件开始前重置编码器缓存。

示例保留固定版本官方代码中的缓存更新和贪心解码。词表直接读取 `tokens.txt`；前处理使用 `kaldi-native-fbank`，并逐文件与 Torchaudio 的 Kaldi FBank 对照，无需为本入口安装 K2 和 Kaldifeat。

## 查看实际转写

输出目录中：

- `input-*`：本次实际音频。
- `deployment-result.json`：原始转写、token、处理耗时、实际模型调用次数，以及前处理对照误差。
- `raw-*.npz`：音频特征、对照特征、编码器输入和 joiner logits，用于本地复核。

`samples[].output` 是原始文本，英文保留模型输出的大小写；`rtf` 为处理耗时除以音频时长。耗时包含音频读取、前处理、传输、推理、解码及记录校验值，不含模型加载、额外前处理对照和结果保存。

本流程按官方设置补 0.3 秒静音尾部，以 103 帧输入、96 帧步长处理；最后不足一块的特征不会单独刷新。句尾文字与短音频需结合原音频核对，不应只检查程序退出码。

## 转写自己的音频

```bash
python ~/edgeaccel/zipformer_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/example.wav \
  --output ~/edgeaccel/results/zipformer-custom-01
```

本入口接受最长 60 秒的文件，优先使用 16 kHz 单声道 WAV。多声道使用第一声道；其他采样率需另外安装 Librosa 完成重采样。程序会重复第一段输入并追加静音测试。本页验证的是文件分块推理，麦克风实时采集、并发服务和更长音频需进一步验证。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

三份 AX650N 权重已通过 AXCL 完成十段官方音频、重复识别和静音测试；下方提供实际音频与原始转写。

**十段官方音频的实际转写**

包含中文、英文、中英混合和一段MP3。以下原样保留输出，部分内容有不自然用词，英文样例末尾出现“NE”；尚未根据人工标注计算字词错误率。

| 音频 | 实际转写 |
| --- | --- |
| 0.wav | 昨天是 MONDAY TODAY IS TOMORROW |
| 002.mp3 | 那么一般是非本人医院的嗯单位厅堡的时候如果是给您妻子填写检测停保原因或者说如果单位情报原因停止了导致你妻子身孕育今天这个申请试验金申请的这个原因就本人医院医院中间这个原因不符合的那么需要提供身身体湿液晶面提供一个单位开具的解除劳动关系证明鉴明具体解除劳动关系原因证明是对本人医院的 |
| 1.wav | 这是第一种第二种叫呃与 ALWAYS什么 |
| 2.wav | 这个是频繁的啊不认识记下来 FREQUENTLY平凡的 |
| 3.wav | 第一句是个什么时态加了 YES是一般现在时对后面它时态系形状 |
| 4.wav | 嗯 ON TIME要准时 IN TIME是及时叫他总是准时教他的作业那用一般现在时是没有什么感情色彩呢陈述一个事实下一句话为什么要用现在进行时态的意思并不是说他现在正在教 |
| 46.wav | 你好石头把厨房扫脱下 |
| demo.wav | 甚至出现交易几乎停滞的情况 |
| fileid_144.wav | HE GOES ABOUT BEGGING FROM HOUSE TO HOUSE AND HAS NE |
| fileid_249.wav | SUCH A DASH |

| 音频 | 音频时长 | 处理耗时 | RTF |
| --- | --- | --- | --- |
| 0.wav | 10.053125 s | 1.931149 s | 0.192094 |
| 002.mp3 | 29.952000 s | 5.658110 s | 0.188906 |
| 1.wav | 5.100000 s | 0.826652 s | 0.162089 |
| 2.wav | 4.690000 s | 0.836729 s | 0.178407 |
| 3.wav | 8.830000 s | 1.469078 s | 0.166373 |
| 4.wav | 17.640000 s | 3.183654 s | 0.180479 |
| 46.wav | 3.900562 s | 0.715705 s | 0.183488 |
| demo.wav | 4.203938 s | 0.751617 s | 0.178789 |
| fileid_144.wav | 3.000000 s | 0.566320 s | 0.188773 |
| fileid_249.wav | 3.000000 s | 0.526408 s | 0.175469 |

实际输入：0.wav，10.053 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-1.wav" aria-label="实际输入：0.wav，10.053 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-1.wav)

实际输入：002.mp3，29.952 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-2.mp3" aria-label="实际输入：002.mp3，29.952 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-2.mp3)

实际输入：1.wav，5.100 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-3.wav" aria-label="实际输入：1.wav，5.100 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-3.wav)

实际输入：2.wav，4.690 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-4.wav" aria-label="实际输入：2.wav，4.690 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-4.wav)

实际输入：3.wav，8.830 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-5.wav" aria-label="实际输入：3.wav，8.830 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-5.wav)

实际输入：4.wav，17.640 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-6.wav" aria-label="实际输入：4.wav，17.640 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-6.wav)

实际输入：46.wav，3.901 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-7.wav" aria-label="实际输入：46.wav，3.901 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-7.wav)

实际输入：demo.wav，4.204 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-8.wav" aria-label="实际输入：demo.wav，4.204 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-8.wav)

实际输入：fileid_144.wav，3.000 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-9.wav" aria-label="实际输入：fileid_144.wav，3.000 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-9.wav)

实际输入：fileid_249.wav，3.000 秒

<audio controls preload="metadata" src="/validation/effects/zipformer-axera-20260928/input-10.wav" aria-label="实际输入：fileid_249.wav，3.000 秒"></audio>

[下载音频](../../../static/validation/effects/zipformer-axera-20260928/input-10.wav)

**重复识别与静音**

重复第一段音频，实际模型输入输出哈希与转写均一致。三秒静音输出为空；它仍经过编码、解码和joiner，没有额外VAD门控。

| 输入 | 输出 | 处理耗时 | 编码 / 解码 / joiner |
| --- | --- | --- | --- |
| 0.wav（重复） | 昨天是 MONDAY TODAY IS TOMORROW | 1.744736 s | 10 / 14 / 240 |
| silence-3s.wav | 空字符串 | 0.520522 s | 3 / 1 / 72 |

**使用时注意：**

- 转写未经完整人工标注评分，不能将有文字输出视作识别准确率通过；原始文本中的不自然用词保留。
- 按官方流程补0.3秒尾部，最后不足103帧不单独刷新，英文句尾和短音频需进一步核对。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`a690cb0f701b11274505209cb3dec6bf7bd91e4b`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 首次处理耗时 | 0.526–5.658 s / 文件 | 十段官方样例，音频3–29.952秒；包含读取、特征、传输、推理、解码与记录，不含加载和额外前处理对照。 |
| 首次样例 RTF | 0.162–0.192 | 本次文件分块处理速度，不代表麦克风、并发服务或纯NPU性能。 |
| 实际模型调用 | 105 / 356 / 2520 | 依次为encoder、decoder和joiner，包括重复与静音。 |
| 前处理对照 | 平均绝对误差不超过4.30×10⁻⁶ | 同一音频、同一Kaldi参数，对照Torchaudio FBank；不是CPU浮点模型精度比较。 |

适用范围：

- 转写未经完整人工标注评分，不能将有文字输出视作识别准确率通过；原始文本中的不自然用词保留。
- 按官方流程补0.3秒尾部，最后不足103帧不单独刷新，英文句尾和短音频需进一步核对。
- 当前只测AX650N权重的文件分块推理，未验证AX630C权重、麦克风实时采集或长时间连续运行。
- 本次为16GB卡，真实8GB容量仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_pretrained_infer.py`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/ax_pretrained_infer.py) | Python 程序 / 前后处理 |
| [`inputs/axmodels_630C/decoder.axmodel`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/axmodels_630C/decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`inputs/axmodels_630C/encoder.axmodel`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/axmodels_630C/encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`inputs/axmodels_630C/joiner.axmodel`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/axmodels_630C/joiner.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`inputs/axmodels_650N/decoder.axmodel`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/axmodels_650N/decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`inputs/axmodels_650N/encoder.axmodel`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/axmodels_650N/encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/config.json) | 运行配置 |
| [`inputs/lang_char_bpe/lexicon.txt`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/lang_char_bpe/lexicon.txt) | 分词器 / 字典，必须配套 |
| [`inputs/lang_char_bpe/tokens.txt`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/lang_char_bpe/tokens.txt) | 分词器 / 字典，必须配套 |
| [`inputs/test_wavs/demo.wav`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/inputs/test_wavs/demo.wav) | 示例输入 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/requirements.txt) | Python 依赖清单 |

仓库提交：`a690cb0f701b11274505209cb3dec6bf7bd91e4b`。仓库中的 6 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Zipformer.axera/tree/a690cb0f701b11274505209cb3dec6bf7bd91e4b)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Zipformer.axera/tree/a690cb0f701b11274505209cb3dec6bf7bd91e4b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/README.md)。
- [主要程序入口：ax_pretrained_infer.py](https://huggingface.co/AXERA-TECH/Zipformer.axera/blob/a690cb0f701b11274505209cb3dec6bf7bd91e4b/ax_pretrained_infer.py)。

返回[完整模型目录](../catalog.mdx)。
