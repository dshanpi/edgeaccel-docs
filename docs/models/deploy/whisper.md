---
title: "Whisper 部署指南"
sidebar_label: "Whisper"
description: "Whisper 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Whisper 部署指南

Whisper 用于语音识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `models-ax650/tiny/tiny-encoder.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Whisper` 的固定版本。下面下载本页选用的 8 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/whisper/143121c8a628
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Whisper \
  "models-ax650/tiny/tiny-encoder.axmodel" \
  "models-ax650/tiny/tiny-decoder.axmodel" \
  "models-ax650/tiny/tiny_config.json" \
  "models-ax650/tiny/tiny-tokens.txt" \
  "python/whisper_ax.py" \
  "python/whisper_cli.py" \
  "python/requirements.txt" \
  "demo.wav" \
  --revision 143121c8a628bbb463bf4e19e8e7711dd2192e27 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 配置 Python 后端

激活已安装 PyAXEngine 的主机虚拟环境。先检查可用 provider：

```bash
source ~/edgeaccel/python-env/bin/activate
python -c "import axengine; print(axengine.get_available_providers())"
```

必须包含 `AXCLRTExecutionProvider`。保留已安装的 PyAXEngine，按下面命令安装本例依赖。

在已激活的环境中安装该入口直接使用的依赖；以下依赖用于本页的命令行示例：

```bash
python -m pip install numpy==1.26.4 ml-dtypes==0.5.3 librosa==0.9.1 setuptools==75.8.0 soundfile zhconv
```


按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 `.upstream` 备份；原表达式不匹配时停止，避免误改其他版本。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
edits = [
    {"path": "python/whisper_ax.py", "old": "AxEngineExecutionProvider", "new": "AXCLRTExecutionProvider"}
]
for edit in edits:
    path = Path(edit.get("path", "python/whisper_cli.py"))
    source = path.read_text(encoding="utf-8")
    if edit["old"] not in source:
        assert edit["new"] in source, f"补丁目标不匹配：{path}"
        continue
    backup = path.with_name(path.name + ".upstream")
    if not backup.exists():
        backup.write_text(source, encoding="utf-8")
    path.write_text(source.replace(edit["old"], edit["new"]), encoding="utf-8")
    print(f"已修改 {path}")
PY
```

重新下载原始源码后，需要再次执行此修改。

## 运行模型

在模型根目录执行，输入与权重使用该提交的实际路径：

```bash
cd "$MODEL_DIR"
test -s models-ax650/tiny/tiny-encoder.axmodel
test -s demo.wav
set -o pipefail
python python/whisper_cli.py --model_type tiny --model_path models-ax650 --wav demo.wav --language zh --task transcribe 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。保留控制台输出，逐句核对实际转写内容。该入口不生成单独结果文件。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`python/whisper_cli.py` 源码](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/python/whisper_cli.py)。

## 查看部署效果

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

使用 tiny 模型转写下方 4.204 秒中文音频。三次运行的文本一致，开头“擅职”与上游参考“甚至”不同，尚未通过识别质量核对。

**输入音频：16 kHz / 单声道 / PCM16**

<audio controls preload="metadata" src="/validation/effects/whisper/inputs/demo.wav" aria-label="Whisper 实测输入音频"></audio>

[下载输入音频](../../../static/validation/effects/whisper/inputs/demo.wav)

**实际转写**

```text
擅职出现交易几乎停止的情况
```

**上游参考文本**

```text
甚至出现交易几乎停止的情况
```

**核对同一音频的参考文字**

音频文件 SHA256 与 FireRedASR 的 BAC009S0764W0121.wav 完全一致，使用其固定版本的[官方文字标注](https://huggingface.co/AXERA-TECH/FireRedASR-AED/blob/1303e534008032d79b4f15996589f36f2543e10d/wav/text)“甚至出现交易几乎停滞的情况”作单句对照。去除空白与 Unicode 标点后按字符计算编辑距离，不合并同音字或同义词。这不是独立人工听写或完整数据集准确率。 Whisper 自身模型卡示例使用“停止”，与上述标注的“停滞”不同；换参考会改变错误计数。这里同时保留两种来源，不将任何模型输出当作真值，也不从这一次 8GB 运行推断容量影响识别质量。
| 参考文字 | 实际转写 | 字符差异 / 参考字数 | 本句 CER |
| --- | --- | --- | --- |
| 甚至出现交易几乎停滞的情况 | 擅职出现交易几乎停止的情况 | 3 / 13 | 23.077% |

**使用时注意：**

- 原模型卡示例与同音频的 FireRedASR 官方标注存在“停止 / 停滞”差异，单句字符对照请查看上表。尚无独立人工标注集；文件转写未覆盖麦克风采集、长音频分段或流式识别。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`143121c8a628bbb463bf4e19e8e7711dd2192e27`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| C++ 视觉示例提交 | cbfa4c76891758983ca2b0c99c11d6621d59af39 |
| Python 后端 | Python 3.12.3；PyAXEngine 0.1.3.rc3 发布的 0.1.3 wheel；NumPy 1.26.4 / ml-dtypes 0.5.3 |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 音频时长 | 4.2039375 | 秒；直接读取真实 demo.wav 文件头，67263 帧/16000 Hz，非人工听音 |
| 音频格式 | 16kHz / 单声道 / PCM16 | 真实 demo.wav WAV 参数，未改写输入 |
| 裸跑 RTF | 0.499203 / 0.531010 | attempt-2/3 CLI 各自记录，model.run 秒数/音频秒数；含读取前处理和推理，不含构造 |
| 裸跑进程总耗时 | 10.03 / 10.31 | 秒；attempt-2/3 process-time.txt 的 GNU time 墙钟，包含进程启动、导入与模型构造 |

适用范围：

- 未独立人工听写。已对照同文件的 FireRedASR 官方标注计算单句字符差异；原 Whisper 模型卡使用不同文字“停止”，不将模型卡示例视为独立真值。
- 实际结果必须保留“擅职”，不能为展示效果替换成参考的“甚至”。两次结果相同表示短样例重复一致，不代表文字识别完全正确。
- RTF 的计时范围是 model.run，包含音频读取、前处理和模型推理，不含 Python 启动、导入及模型构造加载；不是纯 NPU 时延，也不代表含冷启动的完整进程实时。
- 测试只用一段 16kHz 中文短音频，未覆盖长音频、静音、噪声、多语言、流式或分段拼接；上游实现对超过约 30 秒的输入存在截断边界。
- 本次修改 python/whisper_ax.py 两个 session 的 provider 为 AXCLRTExecutionProvider；未经此修改的原版默认板端 provider 不能照抄到 RK3576 算力卡。
- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`models-ax650/tiny/tiny-encoder.axmodel`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/models-ax650/tiny/tiny-encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models-ax650/tiny/tiny-decoder.axmodel`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/models-ax650/tiny/tiny-decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models-ax650/tiny/tiny_config.json`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/models-ax650/tiny/tiny_config.json) | 运行配置 |
| [`models-ax650/tiny/tiny-tokens.txt`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/models-ax650/tiny/tiny-tokens.txt) | 分词器 / 字典，必须配套 |
| [`python/whisper_ax.py`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/python/whisper_ax.py) | Python 程序 / 前后处理 |
| [`python/whisper_cli.py`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/python/whisper_cli.py) | Python 程序 / 前后处理 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/python/requirements.txt) | Python 依赖清单 |
| [`demo.wav`](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/demo.wav) | 示例输入 |

仓库提交：`143121c8a628bbb463bf4e19e8e7711dd2192e27`。仓库中的 10 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Whisper/tree/143121c8a628bbb463bf4e19e8e7711dd2192e27)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页选择 models-ax650/tiny 下的 encoder、decoder、tiny_config.json 和 tiny-tokens.txt，保留完整目录。旧 whisper.axcl 的 encoder、decoder-main、decoder-loop 三段权重不能与本包混用。
- 在 python/whisper_ax.py 中将两处 AxEngineExecutionProvider 都替换为 AXCLRTExecutionProvider；编码器和解码器两个会话都必须使用 AXCL。启动入口仍为 python/whisper_cli.py。
- 在仓库根目录执行命令。--model_path 指向 models-ax650，--model_type tiny 由脚本选择 tiny 子目录；不要把路径改为该子目录后再重复拼接。
- 本次使用 Python 3.12、librosa 0.9.1 和 setuptools 75.8.0；按下方依赖安装即可，python/requirements.txt 中其他服务或开发依赖不是本次 CLI 路径的必需项。
- 该 CLI 将识别文本打印到控制台，不生成转写输出文件；保留 run.log，并逐字对照输入音频。退出码 0 及两个 AXCL 会话完成只说明基本运行。
- 本次 demo.wav 转写为“擅职出现交易几乎停止的情况”，开头存在误识别，因此只记录基本运行，不声明转写正确或给出准确率。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Whisper/tree/143121c8a628bbb463bf4e19e8e7711dd2192e27)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/README.md)。
- [主要程序入口：python/whisper_cli.py](https://huggingface.co/AXERA-TECH/Whisper/blob/143121c8a628bbb463bf4e19e8e7711dd2192e27/python/whisper_cli.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Whisper)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
