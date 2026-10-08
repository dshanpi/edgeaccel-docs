---
title: "SenseVoice_AgenticRAG 部署指南"
sidebar_label: "SenseVoice_AgenticRAG"
description: "SenseVoice_AgenticRAG 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SenseVoice_AgenticRAG 部署指南

SenseVoice_AgenticRAG 用于多语言语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/SenseVoice_AgenticRAG` 的固定版本。下面下载本页选用的 14 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/sensevoice-agenticrag/748b06f6b0e4
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SenseVoice_AgenticRAG \
  --include "README.md" "example/en.mp3" "example/ja.mp3" "example/ko.mp3" "example/yue.mp3" "example/zh.mp3" "python/SenseVoiceAx.py" "python/frontend.py" "python/main.py" "sensevoice_ax650/am.mvn" "sensevoice_ax650/chn_jpn_yue_eng_ko_spectok.bpe.model" "sensevoice_ax650/sensevoice.axmodel" "sensevoice_ax650/streaming_sensevoice.axmodel" "sensevoice_ax650/tokens.txt" \
  --revision 748b06f6b0e43660f2092dbcf158189f543ab88c \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装依赖与运行包

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0，运行官方仓库中的整段识别与分块识别程序。仓库名称包含 AgenticRAG，但这里提供的是语音识别流程，不包含检索问答应用。

在已安装 PyAXEngine 的 Python 环境中执行：

```bash
python -m pip install numpy==1.26.4 librosa==0.11.0 soundfile==0.13.1 \
  kaldi-native-fbank==1.22.3 online-fbank==0.0.4
python -c "import axengine; print(axengine.get_available_providers())"
```

提供器列表应包含 `AXCLRTExecutionProvider`。音频解码使用主机 CPU，识别模型使用 M.2 算力卡。

下载[配套运行包](/examples/agentic-sensevoice-20261001.tar.gz)到 `~/edgeaccel`，保留前文设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf agentic-sensevoice-20261001.tar.gz
python agentic-sensevoice/verify_models.py --model-dir "$MODEL_DIR"
mkdir -p sensevoice-results
```

应输出 `Verified 14 model files`。本例使用 `sensevoice_ax650` 目录中的两个不同权重。AX630C 权重不适用于此流程；仓库中的同内容嵌套副本不需要重复下载。

## 识别完整音频

识别仓库中的中文音频：

```bash
python agentic-sensevoice/run.py --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/example/zh.mp3" --language zh \
  --output sensevoice-results/zh.json
```

终端打印识别文字，`zh.json` 保存 `transcript`、音频长度、推理耗时及实时率。实时率为处理耗时除以音频时长，不包含模型加载和音频解码。

识别英文音频：

```bash
python agentic-sensevoice/run.py --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/example/en.mp3" --language en \
  --output sensevoice-results/en.json
```

`--language` 支持 `auto`、`zh`、`en`、`yue`、`ja`、`ko`。替换输入时使用自己的音频文件路径，并选择相应语言。

## 分块识别音频

```bash
python agentic-sensevoice/run.py --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/example/zh.mp3" --language zh --streaming \
  --output sensevoice-results/zh-streaming.json
```

程序将音频按 100ms 分块送入官方流式前端，终端依次显示阶段结果；JSON 中的 `streamUpdates` 保留这些文字和时间戳，`transcript` 保存最后一次结果。这是音频文件分块处理，不包含麦克风采集或实时播放节奏。

## 检查结果与设备释放

```bash
echo $?
cat sensevoice-results/zh.json
axcl-smi
```

退出码应为 `0`，JSON 中 `provider` 应为 `AXCLRTExecutionProvider`，并生成非空识别文字。对照实际音频检查人名、数字和专有名词；程序正常退出不等同于文字完全准确。进程结束后，算力卡应释放本次模型占用。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡运行五种语言的整段与分块语音识别，下面保留实际音频和转写。

**英语识别结果**

整段结果表达酋长召见男孩并赠予 50 枚金币，与仓库示例文字对应；分块结果出现粘连、重复及 code 等差异。

| 模式 | 实际转写 | 音频时长 / s | 处理耗时 / s | 实时率 |
| --- | --- | --- | --- | --- |
| 整段识别 | The tribal chieftain called for the boy and presented him with 50 pieces of gold. | 7.176 | 2.694 | 0.375 |
| 100ms 分块识别 | thetribalheef thencalled for thethe boyand presentedlened himwith 50pieces of code | 7.176 | 3.691 | 0.514 |

英语：本次输入音频

<audio controls preload="metadata" src="/validation/effects/sensevoice-agenticrag-20261001/en.mp3" aria-label="英语：本次输入音频"></audio>

[下载音频](../../../static/validation/effects/sensevoice-agenticrag-20261001/en.mp3)

**普通话识别结果**

整段转写为“开饭时间”，分块转写为“开放时间”但重复“点”。请对照音频核对，不能将两种输出视为相同。

| 模式 | 实际转写 | 音频时长 / s | 处理耗时 / s | 实时率 |
| --- | --- | --- | --- | --- |
| 整段识别 | 开饭时间早上9点至下午5点。 | 5.616 | 2.845 | 0.507 |
| 100ms 分块识别 | 开放时间早上九点点至下午五点 | 5.616 | 2.681 | 0.477 |

普通话：本次输入音频

<audio controls preload="metadata" src="/validation/effects/sensevoice-agenticrag-20261001/zh.mp3" aria-label="普通话：本次输入音频"></audio>

[下载音频](../../../static/validation/effects/sensevoice-agenticrag-20261001/zh.mp3)

**粤语识别结果**

整段输出为“呢几个字都表达唔到我想讲嘅意思。”；分块输出重复“几”“想”“意”。

| 模式 | 实际转写 | 音频时长 / s | 处理耗时 / s | 实时率 |
| --- | --- | --- | --- | --- |
| 整段识别 | 呢几个字都表达唔到我想讲嘅意思。 | 5.184 | 2.679 | 0.517 |
| 100ms 分块识别 | 呢几几个字都表达唔到我想想讲嘅意意思 | 5.184 | 2.332 | 0.450 |

粤语：本次输入音频

<audio controls preload="metadata" src="/validation/effects/sensevoice-agenticrag-20261001/yue.mp3" aria-label="粤语：本次输入音频"></audio>

[下载音频](../../../static/validation/effects/sensevoice-agenticrag-20261001/yue.mp3)

**日语识别结果**

两种模式都返回日文；分块结果出现“うう”“女性”“50県”等差异，未完成独立人工听写评估。

| 模式 | 实际转写 | 音频时长 / s | 处理耗时 / s | 实时率 |
| --- | --- | --- | --- | --- |
| 整段识别 | うちの中学は弁当制で持っていきない場合は50円の学校販売のパンを買う。 | 7.224 | 2.704 | 0.374 |
| 100ms 分块识别 | ううちの中学は弁当女性で持っていきない場合は50県の学校ご販売のパンを買う | 7.224 | 3.696 | 0.512 |

日语：本次输入音频

<audio controls preload="metadata" src="/validation/effects/sensevoice-agenticrag-20261001/ja.mp3" aria-label="日语：本次输入音频"></audio>

[下载音频](../../../static/validation/effects/sensevoice-agenticrag-20261001/ja.mp3)

**韩语识别结果**

两种模式都返回韩文；分块结果存在空格和词语差异，未完成独立人工听写评估。

| 模式 | 实际转写 | 音频时长 / s | 处理耗时 / s | 实时率 |
| --- | --- | --- | --- | --- |
| 整段识别 | 조금만 생각을 하면서 살면 훨씬 편할 거야. | 4.644 | 2.692 | 0.580 |
| 100ms 分块识别 | 조 금만생각 을면서 살 훨씬변할 거야 | 4.644 | 2.545 | 0.548 |

韩语：本次输入音频

<audio controls preload="metadata" src="/validation/effects/sensevoice-agenticrag-20261001/ko.mp3" aria-label="韩语：本次输入音频"></audio>

[下载音频](../../../static/validation/effects/sensevoice-agenticrag-20261001/ko.mp3)

**使用时注意：**

- 分块识别存在重复和错词，整段中文存在“开饭/开放”差异；建议先使用整段模式并人工核对重要文字。本页不声明五种语言准确率达标。
- 本例是语音文件识别，不包含 RAG 检索问答、麦克风采集、热词解码或持续在线服务。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`748b06f6b0e43660f2092dbcf158189f543ab88c`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 识别覆盖 | 5 种语言 / 10 次识别 | 普通话、英语、粤语、日语与韩语；每种语言分别运行整段与分块识别。 |
| 执行权重 | 2 个 AX650 AXModel | 两种模式共 49 次算力卡调用；同内容嵌套副本不重复计数。 |

适用范围：

- 仅验证 16GB 算力卡；8GB 容量与完整数据集识别精度另行验证。
- 耗时不含模型加载与音频解码，包含本次原始输出保存和校验开销；分块文件处理未模拟实时输入节奏。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/gradio_demo.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/gradio_demo.py) | Python 程序 / 前后处理 |
| [`python/main.py`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/main.py) | Python 程序 / 前后处理 |
| [`sensevoice_ax650/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/sensevoice/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/sensevoice/streaming_sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice/streaming_sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/streaming_sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/streaming_sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/requirements.txt) | Python 依赖清单 |
| [`sensevoice_ax630c/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax630c/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax650/sensevoice/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/sensevoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax650/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/sensevoice_ax650/tokens.txt) | 分词器 / 字典，必须配套 |

仓库提交：`748b06f6b0e43660f2092dbcf158189f543ab88c`。仓库中的 6 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/tree/748b06f6b0e43660f2092dbcf158189f543ab88c)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/tree/748b06f6b0e43660f2092dbcf158189f543ab88c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/README.md)。
- [主要程序入口：python/main.py](https://huggingface.co/AXERA-TECH/SenseVoice_AgenticRAG/blob/748b06f6b0e43660f2092dbcf158189f543ab88c/python/main.py)。

返回[完整模型目录](../catalog.mdx)。
