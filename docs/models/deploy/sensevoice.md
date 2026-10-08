---
title: "SenseVoice 部署指南"
sidebar_label: "SenseVoice"
description: "SenseVoice 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SenseVoice 部署指南

SenseVoice 用于语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/SenseVoice` 的固定版本。下面下载本页选用的 12 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/sensevoice/6ef7cf855a8f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SenseVoice \
  "python/SenseVoiceAx.py" \
  "python/frontend.py" \
  "python/requirements.txt" \
  "sensevoice_ax650/sensevoice.axmodel" \
  "sensevoice_ax650/am.mvn" \
  "sensevoice_ax650/tokens.txt" \
  "sensevoice_ax650/chn_jpn_yue_eng_ko_spectok.bpe.model" \
  "example/zh.mp3" \
  "example/en.mp3" \
  "example/yue.mp3" \
  "example/ja.mp3" \
  "example/ko.mp3" \
  --revision 6ef7cf855a8f1661c29e2015abdb628e9258fa98 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装文件转写依赖

本例使用非流式模型处理仓库内的五段短音频。音频解码、FBank 和文字后处理在主机执行，模型推理使用 M.2 卡。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install numpy==1.26.4 torch==2.5.1 librosa==0.9.1 \
  kaldi-native-fbank==1.22.3 soundfile==0.14.0
```

下载 [sensevoice_file.py](../../../static/examples/sensevoice_file.py)，通过 scp 或 SFTP 复制到 Linux 主机的 `$MODEL_DIR/sensevoice_file.py`。

## 指定 AXCL 后端

在模型目录执行以下修改。脚本保留原文件；重新下载上游源码后需要再次执行。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path("python/SenseVoiceAx.py")
s = p.read_text(encoding="utf-8")
old = "axe.InferenceSession(model_path)"
new = 'axe.InferenceSession(model_path, providers=["AXCLRTExecutionProvider"])'
if old in s:
    backup = p.with_suffix(".py.upstream")
    if not backup.exists():
        backup.write_text(s, encoding="utf-8")
    p.write_text(s.replace(old, new), encoding="utf-8")
else:
    assert new in s, "源码与本页固定版本不匹配"
PY
```

## 转写样例音频

```bash
cd "$MODEL_DIR"
test -s sensevoice_file.py
set -o pipefail
python sensevoice_file.py --model-dir . \
  --languages zh en yue ja ko \
  --out sensevoice-result.json 2>&1 | tee run.log
```

日志中的 provider 应为 `AXCLRTExecutionProvider`。结果文件按音频记录实际转写、时长与端到端耗时；只测试中文时将参数改为 `--languages zh`。

`wallRTF` 是本脚本一次文件转写耗时除以音频时长，包含音频加载和前后处理，不是纯 NPU 延迟。第一次运行可能包含音频库初始化。非流式短文件结果不代表已经验证麦克风采集、流式识别或长录音分段。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

五段官方短音频均完成文件转写，实际输出覆盖中文、英文、粤语、日语和韩语。下方保留可播放输入与完整文本；本次确认非流式识别基本运行，没有独立标注稿用于准确率评测。

以下为五段官方样例的实际转写。可播放原音频逐句核对；本次没有独立人工标注稿，未计算字错率或词错率。

**中文 · 5.622 秒**

<audio controls preload="metadata" src="/validation/effects/sensevoice/inputs/zh.mp3" aria-label="SenseVoice 中文输入"></audio>

[下载音频](../../../static/validation/effects/sensevoice/inputs/zh.mp3)

实际转写：

```text
开放时间早上9点至下午5点。
```

**英文 · 7.180 秒**

<audio controls preload="metadata" src="/validation/effects/sensevoice/inputs/en.mp3" aria-label="SenseVoice 英文输入"></audio>

[下载音频](../../../static/validation/effects/sensevoice/inputs/en.mp3)

实际转写：

```text
The tribal chieftain called for the boy and presented him with 50 pieces of gold.
```

**粤语 · 5.208 秒**

<audio controls preload="metadata" src="/validation/effects/sensevoice/inputs/yue.mp3" aria-label="SenseVoice 粤语输入"></audio>

[下载音频](../../../static/validation/effects/sensevoice/inputs/yue.mp3)

实际转写：

```text
呢几个字都表达唔到我想讲嘅意思。
```

**日语 · 7.230 秒**

<audio controls preload="metadata" src="/validation/effects/sensevoice/inputs/ja.mp3" aria-label="SenseVoice 日语输入"></audio>

[下载音频](../../../static/validation/effects/sensevoice/inputs/ja.mp3)

实际转写：

```text
うちの中学は弁当制で持っていきない場合は50円の学校販売のパンを買う。
```

**韩语 · 4.652 秒**

<audio controls preload="metadata" src="/validation/effects/sensevoice/inputs/ko.mp3" aria-label="SenseVoice 韩语输入"></audio>

[下载音频](../../../static/validation/effects/sensevoice/inputs/ko.mp3)

实际转写：

```text
조금만 생각을 하면서 살면 훨씬 편할 거야.
```

| 输入 | 文件转写耗时 | 实时率（RTF） |
| --- | --- | --- |
| zh.mp3 | 3.220 s | 0.573 |
| en.mp3 | 0.619 s | 0.086 |
| yue.mp3 | 0.876 s | 0.168 |
| ja.mp3 | 0.599 s | 0.083 |
| ko.mp3 | 1.325 s | 0.285 |

RTF 为处理时间除以音频时长，小于 1 表示处理速度快于音频播放速度。耗时包含文件加载、音频前处理、推理与文字后处理；第一次请求包含音频库初始化，不单独解释为 NPU 性能。

**使用时注意：**

- 未独立人工听写五种语言的参考文本，未计算 CER/WER；不能把非空输出解释为识别准确。
- 只使用 AX650 非流式模型和短文件，未测试麦克风、流式模式、长音频分段或并发。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`6ef7cf855a8f1661c29e2015abdb628e9258fa98`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |
| 音频后端与依赖 | PyAXEngine 0.1.3，AXCLRTExecutionProvider；Torch / TorchAudio 2.5.1，NumPy 1.26.4，ONNX Runtime 1.20.1 |
| 音频测试方式 | 三个应用串行使用设备 0；文件解码、FBank、文本处理与 ONNX 编码在主机执行 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/gradio_demo.py`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/python/gradio_demo.py) | Python 程序 / 前后处理 |
| [`python/main.py`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/python/main.py) | Python 程序 / 前后处理 |
| [`sensevoice_ax650/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax650/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/sensevoice/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax650/sensevoice/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/sensevoice/streaming_sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax650/sensevoice/streaming_sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`sensevoice_ax650/streaming_sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax650/streaming_sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/python/requirements.txt) | Python 依赖清单 |
| [`sensevoice_ax620q/sensevoice/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax620q/sensevoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax620q/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax620q/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax630c/sensevoice/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax630c/sensevoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax630c/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax630c/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax650/sensevoice/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax650/sensevoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`sensevoice_ax650/tokens.txt`](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/sensevoice_ax650/tokens.txt) | 分词器 / 字典，必须配套 |

仓库提交：`6ef7cf855a8f1661c29e2015abdb628e9258fa98`。仓库中的 11 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SenseVoice/tree/6ef7cf855a8f1661c29e2015abdb628e9258fa98)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页使用 sensevoice_ax650/sensevoice.axmodel 的非流式版本；主机处理音频，M.2 卡执行 AXCL 推理。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SenseVoice/tree/6ef7cf855a8f1661c29e2015abdb628e9258fa98)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/README.md)。
- [主要程序入口：python/gradio_demo.py](https://huggingface.co/AXERA-TECH/SenseVoice/blob/6ef7cf855a8f1661c29e2015abdb628e9258fa98/python/gradio_demo.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/SenseVoice)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
