---
title: "FireRedASR-AED 部署指南"
sidebar_label: "FireRedASR-AED"
description: "FireRedASR-AED 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# FireRedASR-AED 部署指南

FireRedASR-AED 用于语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/FireRedASR-AED` 的固定版本。下面下载本页选用的 20 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/fireredasr-aed/1303e5340080
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/FireRedASR-AED \
  "README.md" \
  "axmodel/cmvn.ark" \
  "axmodel/decoder_loop.axmodel" \
  "axmodel/dict.txt" \
  "axmodel/encoder.axmodel" \
  "axmodel/pe.npy" \
  "axmodel/train_bpe1000.model" \
  "fsmn_vad/am.mvn" \
  "fsmn_vad/fsmn_vad_10s_fp32.axmodel" \
  "openai/firered_asr.py" \
  "openai/fsmn_vad_post.py" \
  "openai/openai_client.py" \
  "openai/openai_server.py" \
  "requirements.txt" \
  "wav/BAC009S0764W0121.wav" \
  "wav/IT0011W0001.wav" \
  "wav/TEST_MEETING_T0000000001_S00000.wav" \
  "wav/TEST_NET_Y0000000000_-KTKHdZ2fb8_S00000.wav" \
  "wav/text" \
  "wav/wav.scp" \
  --revision 1303e534008032d79b4f15996589f36f2543e10d \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

本例在 RK3576 主机完成音频读取、特征提取和解码控制；通过 AXCL 在 M.2 算力卡上运行 FSMN-VAD、语音编码器及解码器。

按 [Python 接口](../../usage/python.md) 建好环境后，安装本例用到的依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'soundfile==0.13.1' 'kaldiio==2.18.1' 'kaldi-native-fbank==1.22.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本入口使用官方 NumPy 推理代码，无需安装训练用的 Torch 和 Torchaudio。

## 运行语音识别

下载 [FireRedASR 算力卡示例](../../../static/examples/firered_card.py)，保存为 `~/edgeaccel/firered_card.py`。沿用上方下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/firered_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/firered-01
```

输出目录须尚不存在。程序依次识别四段官方音频，再重复第一段，并检查三秒静音。每段音频按 10 秒分块；VAD 检出的语音不足 1 秒时，该块不进入语音识别。

每块最多生成 128 个 token。结果中的 `chunks[].hitEos` 为 `true` 才表示该块正常结束；达到上限时应检查是否截断。

## 查看转写和耗时

结果保存在输出目录：

- `input-*.wav`：本次实际输入，可播放核对。
- `deployment-result.json`：原始转写、官方参考文本、VAD 区间、逐块 token 和运行耗时。
- `reference-text.txt`：官方样例参考文本。
- `raw-*.npz`：用于复核的特征、VAD 分数和解码 logits。

`processSeconds` 包含文件读取、特征提取、传输、推理、解码及记录校验值的开销，不含模型加载和结果文件保存。`rtf` 等于处理时间除以输入音频时长；小于 1 才表示这次处理快于音频播放速度。

参考文本用于比较这几段样例，不能代表所有语音的识别准确率。模型可能漏字、错字；保留原始转写后再做业务侧处理。

## 使用自己的音频

```bash
python ~/edgeaccel/firered_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/example.wav \
  --output ~/edgeaccel/results/firered-custom-01
```

示例接受不超过 60 秒的音频，并重复该文件及检查静音。优先使用 16 kHz、单声道 PCM16 WAV；其他采样率会按官方代码插值到 16 kHz，多声道会平均混为单声道。该入口处理已有音频文件，未包含麦克风采集或实时流式服务。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

16GB 卡完成四段官方音频、重复识别和静音门控。对固定官方标注逐字复核共 1/89 字符差异（1.124%）：会议样例“说完的”输出为“说完了”；其余三个样例文字一致。

**官方语音样例 1**

转写与去除空格后的官方参考一致。

| 文本类型 | 内容 |
| --- | --- |
| 官方参考 | 甚至  出现  交易  几乎  停滞  的  情况 |
| 实际转写 | 甚至出现交易几乎停滞的情况 |

| 音频时长 | 处理耗时 | RTF | 样例 CER | 结束状态 |
| --- | --- | --- | --- | --- |
| 4.203938 s | 8.300395 s | 1.974433 | 0.000% | 1块均EOS |

实际输入 1：BAC009S0764W0121.wav，4.204 秒

<audio controls preload="metadata" src="/validation/effects/fireredasr-aed-20260928/input-1.wav" aria-label="实际输入 1：BAC009S0764W0121.wav，4.204 秒"></audio>

[下载音频](../../../static/validation/effects/fireredasr-aed-20260928/input-1.wav)

**官方语音样例 2**

转写与去除空格后的官方参考一致。

| 文本类型 | 内容 |
| --- | --- |
| 官方参考 | 换一首歌 |
| 实际转写 | 换一首歌 |

| 音频时长 | 处理耗时 | RTF | 样例 CER | 结束状态 |
| --- | --- | --- | --- | --- |
| 1.992000 s | 3.616581 s | 1.815552 | 0.000% | 1块均EOS |

实际输入 2：IT0011W0001.wav，1.992 秒

<audio controls preload="metadata" src="/validation/effects/fireredasr-aed-20260928/input-2.wav" aria-label="实际输入 2：IT0011W0001.wav，1.992 秒"></audio>

[下载音频](../../../static/validation/effects/fireredasr-aed-20260928/input-2.wav)

**官方语音样例 3**

会议音频分两块处理；参考中的“说完的”被识别为“说完了”，存在一处替换。

| 文本类型 | 内容 |
| --- | --- |
| 官方参考 | 好首先说一下刚才这个经理说完的这个销售问题咱再说一下咱们的商场问题首先咱们商场上半年业这个先各部门儿汇报一下就是业绩 |
| 实际转写 | 好首先说一下刚才这个经理说完了这个销售问题咱再说一下咱们的商场问题首先咱们商场上半年业这个先各部门儿汇报一下就是业绩 |

| 音频时长 | 处理耗时 | RTF | 样例 CER | 结束状态 |
| --- | --- | --- | --- | --- |
| 12.369000 s | 33.592258 s | 2.715843 | 1.724% | 2块均EOS |

实际输入 3：TEST_MEETING_T0000000001_S00000.wav，12.369 秒

<audio controls preload="metadata" src="/validation/effects/fireredasr-aed-20260928/input-3.wav" aria-label="实际输入 3：TEST_MEETING_T0000000001_S00000.wav，12.369 秒"></audio>

[下载音频](../../../static/validation/effects/fireredasr-aed-20260928/input-3.wav)

**官方语音样例 4**

转写与去除空格后的官方参考一致。

| 文本类型 | 内容 |
| --- | --- |
| 官方参考 | 我有的时候说不清楚你们知道吗 |
| 实际转写 | 我有的时候说不清楚你们知道吗 |

| 音频时长 | 处理耗时 | RTF | 样例 CER | 结束状态 |
| --- | --- | --- | --- | --- |
| 1.800000 s | 9.175451 s | 5.097473 | 0.000% | 1块均EOS |

实际输入 4：TEST_NET_Y0000000000_-KTKHdZ2fb8_S00000.wav，1.800 秒

<audio controls preload="metadata" src="/validation/effects/fireredasr-aed-20260928/input-4.wav" aria-label="实际输入 4：TEST_NET_Y0000000000_-KTKHdZ2fb8_S00000.wav，1.800 秒"></audio>

[下载音频](../../../static/validation/effects/fireredasr-aed-20260928/input-4.wav)

**重复识别与静音**

第一段音频重复运行，转写、每次模型输入和输出哈希均一致。三秒静音只运行VAD，未调用语音编码器和解码器。

| 输入 | 实际结果 | 处理耗时 | 编码 / 解码 / VAD 调用 |
| --- | --- | --- | --- |
| 重复第一段音频 | 甚至出现交易几乎停滞的情况 | 8.690243 s | 1 / 14 / 1 |
| 三秒全零静音 | 空字符串 | 0.187520 s | 0 / 0 / 1 |

**核对四段官方标注**

对照[固定版本官方文字标注](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/wav/text)，四段独立音频共 89 个参考字符，只有会议样例第 15 字“的→了”一处替换。合计 CER 为 1/89 = 1.124%；重复音频不再次计入分母，静音门控也不计入文本 CER。该小样例集不能代表方言、噪声或长录音准确率。

| 样例 | 参考字符数 | 编辑差异 | 具体差异 |
| --- | --- | --- | --- |
| 1 | 13 | 0 | 文字一致 |
| 2 | 4 | 0 | 文字一致 |
| 3 | 58 | 1 | 的 → 了 |
| 4 | 14 | 0 | 文字一致 |

**使用时注意：**

- 仅四段官方中文样例，CER不是通用准确率；没有CPU浮点参考或独立大规模标注集。
- 当前Python部署含输入输出校验记录开销，尚不满足实时语音处理；没有测试麦克风、API服务、并发或长时间连续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`1303e534008032d79b4f15996589f36f2543e10d`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 四段样例 CER | 1.124%（1 / 89） | 去除Unicode标点和空白、转小写后按字符编辑距离统计；89个参考字符、1处替换，非完整数据集准确率。 |
| 语音处理耗时 | 3.617–33.592 s / 文件 | 四段首次运行，包含特征、传输、推理、解码和记录校验值；不含加载与文件保存。 |
| 四段样例 RTF | 1.816–5.097 | 当前带记录的Python流程慢于音频播放速度；不引用AX650N裸片或C++ SDK性能替代本次结果。 |
| 实际模型调用 | 编码6次 / 解码108次 / VAD7次 | 包括一次重复和一次静音；所有进入识别的音频块均生成EOS。 |

适用范围：

- VAD按10秒块门控；极短语音、噪声、远场和边界漏检仍需独立测试。
- 本次在16GB卡验证，真实8GB容量仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`openai/openai_server.py`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/openai/openai_server.py) | Python 程序 / 前后处理 |
| [`axmodel/decoder_loop.axmodel`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/axmodel/decoder_loop.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodel/encoder.axmodel`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/axmodel/encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fsmn_vad/fsmn_vad_10s_fp32.axmodel`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/fsmn_vad/fsmn_vad_10s_fp32.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/config.json) | 运行配置 |
| [`fireredasr/tokenizer/aed_tokenizer.py`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/fireredasr/tokenizer/aed_tokenizer.py) | 旧版分词服务入口 |
| [`fireredasr/tokenizer/llm_tokenizer.py`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/fireredasr/tokenizer/llm_tokenizer.py) | 旧版分词服务入口 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/requirements.txt) | Python 依赖清单 |

仓库提交：`1303e534008032d79b4f15996589f36f2543e10d`。仓库中的 3 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/FireRedASR-AED/tree/1303e534008032d79b4f15996589f36f2543e10d)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/FireRedASR-AED/tree/1303e534008032d79b4f15996589f36f2543e10d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/README.md)。
- [主要程序入口：openai/openai_server.py](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/openai/openai_server.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/FireRedASR-AED)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
