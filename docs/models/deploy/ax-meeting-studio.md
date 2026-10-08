---
title: "AX-Meeting-Studio 部署指南"
sidebar_label: "AX-Meeting-Studio"
description: "AX-Meeting-Studio 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# AX-Meeting-Studio 部署指南

AX-Meeting-Studio 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/AX-Meeting-Studio` 的固定版本。下面下载本页选用的 35 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/ax-meeting-studio/5ff3c960c78a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/AX-Meeting-Studio \
  --include "README.md" "models/README.md" "models/cam++/campplus.axmodel" "models/fireredasr/cmvn.ark" "models/fireredasr/decoder_loop.axmodel" "models/fireredasr/dict.txt" "models/fireredasr/encoder.axmodel" "models/fireredasr/pe.npy" "models/fireredasr/train_bpe1000.model" "models/punc/model.axmodel" "models/punc/tokens.json" "models/sensevoice/am.mvn" "models/sensevoice/auto.npy" "models/sensevoice/chn_jpn_yue_eng_ko_spectok.bpe.model" "models/sensevoice/config.yaml" "models/sensevoice/en.npy" "models/sensevoice/event_emo.npy" "models/sensevoice/ja.npy" "models/sensevoice/ko.npy" "models/sensevoice/sensevoice.axmodel" "models/sensevoice/withitn.npy" "models/sensevoice/yue.npy" "models/sensevoice/zh.npy" "models/vad/am.mvn" "models/vad/config.yaml" "models/vad/vad.axmodel" "requirements-runtime.txt" "run_web_studio.sh" "src/ax_meeting_cpp/resources/model_assets.json" "tools/verify_assets.py" "wav/002.mp3" "wav/20200327_2P.wav" "wav/2speakers_example.wav" "wav/vad_example.wav" "wheel/ax_meeting_studio-0.3.0+axcl-py3-none-linux_aarch64.whl" \
  --revision 5ff3c960c78a6726c9e4968b1deb090c4beb1764 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装 AXCL 会议转录组件

本例在连接算力卡的 ARM64 Linux 主机上处理 PCM WAV 文件，输出说话人编号、时间段和转录文本。SenseVoice 与 FireRed/Punc 使用各自的识别模型；会议总结还需要单独运行大模型服务。

以下命令沿用下载步骤中的 `MODEL_DIR`。在 Python 环境中安装固定版本的 AXCL wheel：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'sentencepiece==0.2.1' \
  'scipy==1.17.1' 'scikit-learn==1.9.1' setuptools wheel
python -m pip install --no-deps --no-build-isolation 'fastcluster==1.2.6'
python -m pip install --no-deps \
  "$MODEL_DIR/wheel/ax_meeting_studio-0.3.0+axcl-py3-none-linux_aarch64.whl"
export AXMEETING_AXCL_DEVICE=0
python - <<'PY'
import ax_meeting_studio
import ax_meeting_studio._core as core
assert core._native_backend().decode().lower() == 'axcl'
assert ax_meeting_studio.ax_runtime_available()
print('AXCL 原生运行时可用。')
PY
```

使用文件名含 `+axcl` 的 wheel。安装后应输出 `AXCL 原生运行时可用。`；若出现动态库版本错误，先核对 Linux 主机的 AXCL 安装和系统版本。本例使用 Python 3.12、glibc 2.39。

## 使用 SenseVoice 转录会议

```bash
mkdir -p ~/edgeaccel/results/meeting-studio
python -m ax_meeting_studio.cli \
  --wav "$MODEL_DIR/wav/vad_example.wav" \
  --model-dir "$MODEL_DIR/models" \
  --task meeting \
  --asr-backend sensevoice \
  --output ~/edgeaccel/results/meeting-studio/sensevoice.json
```

输入为完整样例录音。程序依次执行语音分段、说话人处理和转录，结果保存在 `sensevoice.json`。

## 使用 FireRed/Punc 转录同一录音

上一条命令结束后，再执行：

```bash
python -m ax_meeting_studio.cli \
  --wav "$MODEL_DIR/wav/vad_example.wav" \
  --model-dir "$MODEL_DIR/models" \
  --task meeting \
  --asr-backend firered_punc \
  --output ~/edgeaccel/results/meeting-studio/firered_punc.raw.json
```

两种后端分别保存结果，便于对照同一录音检查识别文本、标点及说话人边界。一次运行一种后端，避免并行占用同一张卡。

本次 FireRed/Punc 样例的原始末段结束时间比录音长约 79 毫秒。保留原文件，并将转录结束时间限制在输入音频范围内，文本不作修改：

```bash
export MODEL_DIR
python - <<'PY'
import json, os, wave
from pathlib import Path
root = Path.home() / 'edgeaccel/results/meeting-studio'
model = Path(os.environ['MODEL_DIR'])
with wave.open(str(model / 'wav/vad_example.wav'), 'rb') as wav:
    end_ms = round(wav.getnframes() * 1000 / wav.getframerate())
result = json.loads((root / 'firered_punc.raw.json').read_text())
for segment in result['meeting']['transcripts']:
    assert 0 <= segment['start_ms'] <= segment['end_ms']
    assert segment['start_ms'] <= end_ms
    if segment['end_ms'] > end_ms:
        assert segment['end_ms'] - end_ms <= 100, '时间超出较多，请先核对输入与原始结果'
        segment['end_ms'] = end_ms
(root / 'firered_punc.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
```

更换录音时，同步修改此处 WAV 路径。`firered_punc.raw.json` 保留原始输出，`firered_punc.json` 用于查看和后续处理。

## 查看分段文本

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path.home() / 'edgeaccel/results/meeting-studio'
for backend in ['sensevoice', 'firered_punc']:
    result = json.loads((root / (backend + '.json')).read_text())
    assert result['task'] == 'meeting' and result['asr_backend'] == backend
    segments = result['meeting']['transcripts']
    assert segments and any(segment['text'].strip() for segment in segments)
    print('\n' + backend)
    for segment in segments:
        print(f"[{segment['start_ms'] / 1000:.3f}, {segment['end_ms'] / 1000:.3f}] "
              f"Speaker_{segment['speaker']}: {segment['text']}")
PY
```

对照原始录音检查文本、时间段和说话人切换。说话人编号是本段录音的聚类标签，不表示经过确认的真实身份。

## 更换会议录音

将 `--wav` 改为自己的未压缩 PCM WAV 文件，并为 `--output` 指定新文件名。建议先使用单声道、16 kHz 输入；其他采样率会由官方 CLI 重采样。

本节覆盖离线文件转录。Web 页面、麦克风实时输入、大模型总结和长期连续运行需要分别验证；不从离线结果推断这些功能的效果。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡运行官方离线会议转录 CLI，使用同一段完整录音验证 SenseVoice 与 FireRed/Punc 两种后端，输出说话人标签、时间段和转录文本。

**SenseVoice：说话人分段与转录**

以下为官方离线 CLI 的原始分段文本。可播放同一段输入录音对照；识别文本和说话人边界尚无独立人工标注核验。

| 说话人标签 | 时间段（秒） | 实际转录 |
| --- | --- | --- |
| Speaker_0 | 0.000–63.810 | 试错的过程很简单。而且特别是今天报名仓雪卡的同学，你们可以。听到后面的有专门的活动课，他会大大降低你的试绸成本。其实你也可以过来听课。为什么你自己写嘛？我先今天写5个点，我就试试试验一下，反正这5个点不行，我再写5个点，这是再不行。那再写五个点吧。你总会所谓的活动大神和所谓的高手都是只有一个。把所有的错，所有的坑全国趟一遍，留下正确的，你就是所谓的大神，。明白吗？所以说关于活动通过这一块，我只送给你们四个字啊，换位思考。如果说你要想降低。你的试错成本，今天来这里你们就是对的。因为有畅血畅血卡这个机会，所以说关于活动过于不过这个问题，或者活动很难通过这个话题。呃，如果真的。那要坐下来聊的话，要聊一天。但是我觉得我刚才说的四个字足够。好，谢谢。 |
| Speaker_1 | 63.810–70.471 | 好，非常感谢那个三茂老师的回答。三茂老师说，我们在。整个店铺的这个活动当中，我们要学会换位思考。其实。 |

| 音频时长 | CLI 总耗时 | AXCL 调用合计 | 调用次数 |
| --- | --- | --- | --- |
| 70.471 s | 15.323 s | 0.606 s | 95 |

播放两种后端共同使用的完整录音

<audio controls preload="metadata" src="/validation/effects/ax-meeting-studio-20261001/meeting-studio-input.wav" aria-label="播放两种后端共同使用的完整录音"></audio>

[下载音频](../../../static/validation/effects/ax-meeting-studio-20261001/meeting-studio-input.wav)

**FireRed/Punc：说话人分段与转录**

以下为官方离线 CLI 的原始分段文本。可播放同一段输入录音对照；识别文本和说话人边界尚无独立人工标注核验。 本例按输入音频长度处理时间边界：第 3 段结束时间由原始 70.550 秒裁剪为 70.471 秒，文本未修改；原始时间戳保留在输入输出记录中。

| 说话人标签 | 时间段（秒） | 实际转录 |
| --- | --- | --- |
| Speaker_0 | 0.070–28.990 | 试错的过程很简单啊，就特别是今天报名参选卡的同学，你们可以听到后面的有专门的活动课，它会大大降低你的试错成本。其实你也可以不要来听课。为什么你自己写嘛？我写今天写五个点，我就试试试验一下，发现这五个点不行，我再写五个点，这是再不行，那再写五个点嘛，你总会所谓的活动大神和所谓的高手， |
| Speaker_0 | 29.960–63.945 | 都是只有一个，把所有的错，所有的坑全给我趟一遍，留下正确的你就是所谓的大神明白吗？所以说关于活动通过这一块儿，我只送给你们四个字啊，换位思考。如果说你要想降低你的试错成本，今天来这里你们就是对的。因为有参选参选卡这个机会，所以说关于活动过于不过这个问题或者活动很难通过。这个话题啊，如果真的要坐下来聊的话要聊一天。但是我觉得我刚才说的四个字足够好，谢谢 |
| Speaker_1 | 63.945–70.471 | 好，非常感谢那个三胖老师的回答啊。三胖老师说我们在整个店铺的这个活动当中，我们要学会换位思考。 |

| 音频时长 | CLI 总耗时 | AXCL 调用合计 | 调用次数 |
| --- | --- | --- | --- |
| 70.471 s | 46.166 s | 10.423 s | 459 |

播放两种后端共同使用的完整录音

<audio controls preload="metadata" src="/validation/effects/ax-meeting-studio-20261001/meeting-studio-input.wav" aria-label="播放两种后端共同使用的完整录音"></audio>

[下载音频](../../../static/validation/effects/ax-meeting-studio-20261001/meeting-studio-input.wav)

**使用时注意：**

- 本次验证 16GB 卡的离线文件转录；真实 8GB、Web 页面、麦克风实时输入、大模型会议总结和长期连续运行尚未验证。
- 转录保留原始输出，可能包含错字和标点问题。没有独立人工标注，未报告 CER、WER 或说话人分离错误率。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`5ff3c960c78a6726c9e4968b1deb090c4beb1764`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 官方 ax_meeting_studio 0.3.0+axcl / AXCL C API / Python 3.12 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际执行模型 | 6 个 AXModel | 两个后端合计覆盖 VAD、CAM++、SenseVoice、FireRed 编码器与解码器、Punc。 |
| 实际调用 | 554 次 | 来自原生 AXCL 执行记录；各调用返回成功，两轮文件校验一致。 |
| 运行组件 | 0.3.0+axcl | 官方 ARM64 wheel，使用 AXCL C API。 |

适用范围：

- Speaker 标签是单段录音的聚类编号，不表示确认的真实身份。
- FireRed/Punc 原始末段结束时间略超出输入长度；本例保留原始结果，并按 WAV 实际时长裁剪转录结束时间。此处理不代表原始时间戳精度已通过。
- 原生调用记录覆盖模型加载、执行和释放，未截取底层输出张量，不能据此宣称数值精度通过。
- CLI 总耗时包含模型加载、音频处理与转录；AXCL 调用合计是接口调用耗时，两者都不代表常驻服务吞吐。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`models/cam++/campplus.axmodel`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/models/cam%2B%2B/campplus.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/fireredasr/decoder_loop.axmodel`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/models/fireredasr/decoder_loop.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/fireredasr/encoder.axmodel`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/models/fireredasr/encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/punc/model.axmodel`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/models/punc/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/sensevoice/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/models/sensevoice/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/config.json) | 运行配置 |
| [`requirements-runtime.txt`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/requirements-runtime.txt) | Python 依赖清单 |
| [`run_web_studio.sh`](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/run_web_studio.sh) | 启动或构建脚本 |

仓库提交：`5ff3c960c78a6726c9e4968b1deb090c4beb1764`。仓库中的 6 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/tree/5ff3c960c78a6726c9e4968b1deb090c4beb1764)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 会议应用包含音频输入、识别、说话人分段与总结服务。先逐个启动并检查各组件，再验证完整会议流程。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/tree/5ff3c960c78a6726c9e4968b1deb090c4beb1764)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/AX-Meeting-Studio/blob/5ff3c960c78a6726c9e4968b1deb090c4beb1764/README.md)。

返回[完整模型目录](../catalog.mdx)。
