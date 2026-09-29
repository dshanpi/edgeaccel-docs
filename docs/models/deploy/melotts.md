---
title: "MeloTTS 部署指南"
sidebar_label: "MeloTTS"
description: "MeloTTS 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MeloTTS 部署指南

MeloTTS 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MeloTTS` 的固定版本。下面下载本页选用的 66 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/melotts/f49e047022ae
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MeloTTS \
  "decoder-ax650/decoder-zh.axmodel" \
  "encoder-onnx/encoder-zh.onnx" \
  "g-zh_mix_en.bin" \
  "nltk_data/corpora/cmudict.zip" \
  "nltk_data/corpora/cmudict/README" \
  "nltk_data/corpora/cmudict/cmudict" \
  "nltk_data/taggers/averaged_perceptron_tagger.zip" \
  "nltk_data/taggers/averaged_perceptron_tagger/averaged_perceptron_tagger.pickle" \
  "nltk_data/taggers/averaged_perceptron_tagger_eng.zip" \
  "nltk_data/taggers/averaged_perceptron_tagger_eng/averaged_perceptron_tagger_eng.classes.json" \
  "nltk_data/taggers/averaged_perceptron_tagger_eng/averaged_perceptron_tagger_eng.tagdict.json" \
  "nltk_data/taggers/averaged_perceptron_tagger_eng/averaged_perceptron_tagger_eng.weights.json" \
  "python/melotts.py" \
  "python/melotts_onnx.py" \
  "python/requirements.txt" \
  "python/split_utils.py" \
  "python/symbols.py" \
  "python/text/__init__.py" \
  "python/text/chinese.py" \
  "python/text/chinese_bert.py" \
  "python/text/chinese_mix.py" \
  "python/text/cleaner.py" \
  "python/text/cleaner_multiling.py" \
  "python/text/cmudict.rep" \
  "python/text/cmudict_cache.pickle" \
  "python/text/english.py" \
  "python/text/english_bert.py" \
  "python/text/english_utils/__init__.py" \
  "python/text/english_utils/abbreviations.py" \
  "python/text/english_utils/number_norm.py" \
  "python/text/english_utils/time_norm.py" \
  "python/text/es_phonemizer/__init__.py" \
  "python/text/es_phonemizer/base.py" \
  "python/text/es_phonemizer/cleaner.py" \
  "python/text/es_phonemizer/es_symbols.json" \
  "python/text/es_phonemizer/es_symbols.txt" \
  "python/text/es_phonemizer/es_symbols_v2.json" \
  "python/text/es_phonemizer/es_to_ipa.py" \
  "python/text/es_phonemizer/example_ipa.txt" \
  "python/text/es_phonemizer/gruut_wrapper.py" \
  "python/text/es_phonemizer/punctuation.py" \
  "python/text/es_phonemizer/spanish_symbols.txt" \
  "python/text/es_phonemizer/test.ipynb" \
  "python/text/fr_phonemizer/__init__.py" \
  "python/text/fr_phonemizer/base.py" \
  "python/text/fr_phonemizer/cleaner.py" \
  "python/text/fr_phonemizer/en_symbols.json" \
  "python/text/fr_phonemizer/example_ipa.txt" \
  "python/text/fr_phonemizer/fr_symbols.json" \
  "python/text/fr_phonemizer/fr_to_ipa.py" \
  "python/text/fr_phonemizer/french_abbreviations.py" \
  "python/text/fr_phonemizer/french_symbols.txt" \
  "python/text/fr_phonemizer/gruut_wrapper.py" \
  "python/text/fr_phonemizer/punctuation.py" \
  "python/text/french.py" \
  "python/text/french_bert.py" \
  "python/text/japanese.py" \
  "python/text/japanese_bert.py" \
  "python/text/ko_dictionary.py" \
  "python/text/korean.py" \
  "python/text/opencpop-strict.txt" \
  "python/text/spanish.py" \
  "python/text/spanish_bert.py" \
  "python/text/symbols.py" \
  "python/text/tone_sandhi.py" \
  "python/utils.py" \
  --revision f49e047022ae4a451a92e186b7d5a2ce187ff2a9 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装中文合成依赖

本例在 RK3576 上执行文本前处理与 ONNX 编码，在 M.2 卡上执行 AX650 解码模型。中文权重、`g-zh_mix_en.bin` 和配套 Python 文件必须来自同一提交。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install numpy==1.26.4 onnxruntime==1.20.1 \
  soundfile==0.14.0 torch==2.5.1 transformers==4.46.3 \
  cn2an==0.5.22 pypinyin==0.50.0 jieba==0.42.1 \
  g2p_en==2.1.0 inflect==7.3.1 num2words==0.5.12
```

本页只部署中文合成，不需要安装用于日语、韩语等其他语言的全部依赖。

## 下载分词资源并指定 AXCL 后端

中文入口同时导入中英混合文本处理模块，需要以下两套分词资源。保持指定目录名，避免运行时再次联网下载。

```bash
~/edgeaccel/hf-env/bin/hf download google-bert/bert-base-uncased \
  config.json tokenizer.json tokenizer_config.json vocab.txt \
  --revision 86b5e0934494bd15c9632b12f734a8a67f723594 \
  --local-dir "$MODEL_DIR/python/bert-base-uncased"
~/edgeaccel/hf-env/bin/hf download google-bert/bert-base-multilingual-uncased \
  config.json tokenizer.json tokenizer_config.json vocab.txt \
  --revision 7cbf9a625e29989f6b9c6c2fa68234c304f7e38f \
  --local-dir "$MODEL_DIR/python/bert-base-multilingual-uncased"
export NLTK_DATA="$MODEL_DIR/nltk_data"
```

在模型目录生成 `melotts_axcl.py`，保留原始入口。修改仅指定卡端解码后端并取消脚本内置的镜像地址；分词资源使用上一步下载的本地目录。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
source = Path("python/melotts.py").read_text(encoding="utf-8")
old = "sess_dec = axe.InferenceSession(dec_model)"
new = 'sess_dec = axe.InferenceSession(dec_model, providers=["AXCLRTExecutionProvider"])'
assert old in source, "源码与本页固定版本不匹配"
source = source.replace(old, new)
source = source.replace('os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"', '')
Path("python/melotts_axcl.py").write_text(source, encoding="utf-8")
PY
```

## 将中文文本合成为 WAV

必须从 `python` 目录运行，编码器、解码器和说话人特征通过其上一级路径读取。

```bash
cd "$MODEL_DIR/python"
export NLTK_DATA="$MODEL_DIR/nltk_data"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
mkdir -p ../outputs
set -o pipefail
python melotts_axcl.py \
  --sentence "你好，欢迎使用算力卡。" \
  --language ZH --speed 0.8 \
  --wav ../outputs/sample-1.wav 2>&1 | tee ../run.log
```

日志中应出现 `AXCLRTExecutionProvider`，末尾打印 `Save to`，并产生本次运行的 `outputs/sample-1.wav`。默认输出为 44.1 kHz、单声道；`ZH` 在该版本内部映射到 `ZH_MIX_EN`。

继续生成另外两段样例：

```bash
python melotts_axcl.py --sentence "模型已经加载完成，可以开始推理。" \
  --language ZH --speed 0.8 --wav ../outputs/sample-2.wav
python melotts_axcl.py --sentence "请检查电源连接，然后启动程序。" \
  --language ZH --speed 0.8 --wav ../outputs/sample-3.wav
```

将 WAV 下载到电脑播放，检查文字完整性、发音、停顿和尾部是否截断。更换文本时保留单句测试；本页未验证长文本、其他语言或音色克隆。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

三句中文均完成主机编码与卡端解码，生成 44.1 kHz 单声道 WAV。下方展示原始音频及输入文本，尚未完成人工听音质量核对。

下面三段 WAV 均由本次中文输入生成，可直接试听。采样率为 44.1 kHz，单声道，speed=0.8。

**示例 1：输入文本**

```text
你好，欢迎使用算力卡。
```

生成音频：2.454 秒。

<audio controls preload="metadata" src="/validation/effects/melotts/outputs/sample-1.wav" aria-label="MeloTTS 合成结果 1"></audio>

[下载音频](../../../static/validation/effects/melotts/outputs/sample-1.wav)

**示例 2：输入文本**

```text
模型已经加载完成，可以开始推理。
```

生成音频：3.557 秒。

<audio controls preload="metadata" src="/validation/effects/melotts/outputs/sample-2.wav" aria-label="MeloTTS 合成结果 2"></audio>

[下载音频](../../../static/validation/effects/melotts/outputs/sample-2.wav)

**示例 3：输入文本**

```text
请检查电源连接，然后启动程序。
```

生成音频：3.720 秒。

<audio controls preload="metadata" src="/validation/effects/melotts/outputs/sample-3.wav" aria-label="MeloTTS 合成结果 3"></audio>

[下载音频](../../../static/validation/effects/melotts/outputs/sample-3.wav)

本次保留原始合成音频，尚未完成人工听音或自然度评分。

**使用时注意：**

- 仅测试三句中文、默认音色与 speed=0.8；其他语言、长文本及音色克隆未测试。
- 程序完成和音频可读不代表发音、自然度或语音质量全部正确。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`f49e047022ae4a451a92e186b7d5a2ce187ff2a9`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |
| 音频后端与依赖 | PyAXEngine 0.1.3，AXCLRTExecutionProvider；Torch / TorchAudio 2.5.1，NumPy 1.26.4，ONNX Runtime 1.20.1 |
| 音频测试方式 | 三个应用串行使用设备 0；文件解码、FBank、文本处理与 ONNX 编码在主机执行 |

适用范围：

- 仅测试三句中文、默认音色与 speed=0.8；其他语言、长文本及音色克隆未测试。
- 程序完成和音频可读不代表发音、自然度或语音质量全部正确。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/melotts.py`](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/python/melotts.py) | Python 程序 / 前后处理 |
| [`decoder-ax650/decoder-en.axmodel`](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/decoder-ax650/decoder-en.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`decoder-ax650/decoder-jp.axmodel`](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/decoder-ax650/decoder-jp.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`decoder-ax650/decoder-zh.axmodel`](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/decoder-ax650/decoder-zh.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/python/requirements.txt) | Python 依赖清单 |

仓库提交：`f49e047022ae4a451a92e186b7d5a2ce187ff2a9`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MeloTTS/tree/f49e047022ae4a451a92e186b7d5a2ce187ff2a9)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页使用固定仓库的中文编码器、AX650 解码器与 g-zh_mix_en.bin，不能与社区其他下载包混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MeloTTS/tree/f49e047022ae4a451a92e186b7d5a2ce187ff2a9)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/README.md)。
- [主要程序入口：python/melotts.py](https://huggingface.co/AXERA-TECH/MeloTTS/blob/f49e047022ae4a451a92e186b7d5a2ce187ff2a9/python/melotts.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/MeloTTS)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
