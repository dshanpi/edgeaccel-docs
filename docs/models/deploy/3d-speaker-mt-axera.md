---
title: "3D-Speaker-MT.Axera 部署指南"
sidebar_label: "3D-Speaker-MT.Axera"
description: "3D-Speaker-MT.Axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# 3D-Speaker-MT.Axera 部署指南

3D-Speaker-MT.Axera 用于音频理解与记录。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/3D-Speaker-MT.Axera` 的固定版本。下面下载本页选用的 57 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/3d-speaker-mt-axera/3592794622a5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/3D-Speaker-MT.Axera \
  --include "README.md" "ax_meeting/__init__.py" "ax_meeting/ax_model/auto.npy" "ax_meeting/ax_model/campplus.axmodel" "ax_meeting/ax_model/chn_jpn_yue_eng_ko_spectok.bpe.model" "ax_meeting/ax_model/en.npy" "ax_meeting/ax_model/event_emo.npy" "ax_meeting/ax_model/ja.npy" "ax_meeting/ax_model/ko.npy" "ax_meeting/ax_model/sensevoice.axmodel" "ax_meeting/ax_model/sensevoice/am.mvn" "ax_meeting/ax_model/sensevoice/config.yaml" "ax_meeting/ax_model/vad.axmodel" "ax_meeting/ax_model/vad/am.mvn" "ax_meeting/ax_model/vad/config.yaml" "ax_meeting/ax_model/withitn.npy" "ax_meeting/ax_model/yue.npy" "ax_meeting/ax_model/zh.npy" "ax_meeting/axengine_loader.py" "ax_meeting/config.py" "ax_meeting/diar_asr_cli.py" "ax_meeting/diar_utils.py" "ax_meeting/engines.py" "ax_meeting/model_bundle.py" "ax_meeting/pipeline.py" "ax_meeting/positional.py" "ax_meeting/server.py" "ax_meeting/static/app.js" "ax_meeting/static/index.html" "ax_meeting/static/style.css" "ax_meeting/summarize_cli.py" "ax_meeting/summarizer.py" "ax_meeting/text_cleaner.py" "ax_meeting/utils/__init__.py" "ax_meeting/utils/ax_cam_bin.py" "ax_meeting/utils/ax_model_bin.py" "ax_meeting/utils/ax_vad_bin.py" "ax_meeting/utils/cluster_utils.py" "ax_meeting/utils/ctc_alignment.py" "ax_meeting/utils/frontend.py" "ax_meeting/utils/infer_func.py" "ax_meeting/utils/infer_utils.py" "ax_meeting/utils/sentencepiece_tokenizer.py" "ax_meeting/utils/speaker_fbank.py" "ax_meeting/utils/speakerlab/process/augmentation.py" "ax_meeting/utils/speakerlab/process/processor.py" "ax_meeting/utils/speakerlab/utils/fileio.py" "ax_meeting/utils/speakerlab/utils/utils.py" "ax_meeting/utils/utils/__init__.py" "ax_meeting/utils/utils/e2e_vad.py" "ax_meeting/utils/utils/frontend.py" "ax_meeting/utils/utils/utils.py" "ax_meeting/utils/vad_utils.py" "ax_meeting/vad_asr_cli.py" "requirements.txt" "wav/002.mp3" "wav/vad_example.wav" \
  --revision 3592794622a5627aca47c81fdc2569e632ffc910 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备会议转录依赖

本例在 RK3576 主机与 AX8850 **16GB M.2 算力卡**上运行离线会议转录：检测语音、提取说话人特征、聚类，再输出带说话人标签和时间段的文本。模型与配套文件约 277MB，另需预留 Python 依赖和结果空间。

在已安装 [PyAXEngine](../../usage/python.md) 的主机虚拟环境中执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'scipy==1.17.1' \
  'scikit-learn==1.9.1' 'soundfile==0.13.1' 'torch==2.5.1' \
  'kaldi-native-fbank==1.22.3' 'sentencepiece==0.2.1' \
  'jieba==0.42.1' 'PyYAML==6.0.3' 'loguru==0.7.3' setuptools wheel
```

本次使用 Python 3.12。ARM64 环境中的 `fastcluster 1.2.6` 需要源码编译。在主机安装编译工具，然后回到虚拟环境执行安装：

```bash
sudo apt-get install -y build-essential python3-dev
python -m pip install --no-deps --no-build-isolation 'fastcluster==1.2.6'
python -c "import axengine, fastcluster; print(axengine.get_available_providers()); print(fastcluster.__version__)"
```

输出应包含 `AXCLRTExecutionProvider` 和版本 `1.2.6`。如果虚拟环境使用了自行安装的 Python，开发头文件也须匹配该 Python 版本。

下载[运行脚本](../../../static/examples/meeting_mt_card.py)，保存为 `~/edgeaccel/meeting_mt_card.py`。将[文件校验清单](../../../static/validation/effects/3d-speaker-mt-axera-20260930/download-manifest.json)保存为 `$MODEL_DIR/.validation-download.json`。

## 运行会议音频转录

在连接算力卡的 Linux 主机执行：

```bash
python ~/edgeaccel/meeting_mt_card.py \
  --model-dir "$MODEL_DIR" \
  --audio wav/vad_example.wav \
  --output ~/edgeaccel/results/meeting-01
```

`--audio` 是模型目录内的相对路径，输出目录须尚不存在。程序调用固定版本的官方离线处理流程，将 VAD、CAMPPlus 和 SenseVoice 三个模型明确交给 AXCL 执行。

完成后生成 `transcript.txt`、`deployment-result.json` 和逐次调用记录 `calls.jsonl`。

## 查看说话人和转录文本

```bash
cat ~/edgeaccel/results/meeting-01/transcript.txt
python - <<'PY'
import json
from pathlib import Path
r = json.loads((Path.home() / 'edgeaccel/results/meeting-01/deployment-result.json').read_text())
assert r['completed'] and len(r['sessions']) == 3
assert all(s['calls'] > 0 and s['provider'] == 'AXCLRTExecutionProvider'
           for s in r['sessions'])
print('音频时长：', round(r['audio']['durationSeconds'], 3), 's')
print('说话人标签数：', r['speakerCount'])
print('文件处理流程：', round(r['elapsedSeconds'], 3), 's')
PY
```

输出格式为 `Speaker_编号: [开始秒数 结束秒数] 转录文本`。标签只区分本次录音中的聚类结果，不代表说话人的真实身份。

播放原始音频，检查切换说话人的位置、漏字、错字和重复。本页下方保留本次实际输出，包括识别错误及未清除的特殊标记。

## 替换输入音频

将自己的 WAV 或 MP3 放入 `$MODEL_DIR/wav/`，再更换输入路径和输出目录。程序沿用官方处理方式：多声道取均值，必要时重采样到 16kHz。本次样例均为 16kHz，不据此评价其他采样率的处理效果。

```bash
python ~/edgeaccel/meeting_mt_card.py \
  --model-dir "$MODEL_DIR" \
  --audio wav/002.mp3 \
  --output ~/edgeaccel/results/meeting-02
```

当前已验证离线文件转录。浏览器麦克风、实时 WebSocket、多人长会议及大模型纪要总结仍需单独验证；本页命令不会调用外部总结服务。

流程计时包含官方模块导入、模型加载、音频处理、推理和运行后校验，不含 Python 启动及运行前校验。逐次 AXCL 调用计时包含 PCIe 传输，不能等同于常驻服务吞吐。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两段文件已完成离线转录，但九个 ASR 切片均有词级时间戳超出本切片长度，时间边界检查未通过；自然录音还保留特殊标记。现有时间戳不能直接用于逐词字幕同步。

**会议音频：说话人分段**

输入使用仓库中的完整音频。下表保留原始转录，包括错字、标点和特殊标记；说话人标签尚无独立人工标注校验。词级时间边界检查未通过：每个 ASR 切片均有时间戳超出其实际时长。新增表中的时间以各切片起点为零；最终文本中的时间段经过合并，不能替代逐词对齐验证。接入字幕或按词定位播放前，需要修正并复测时间边界。

| 说话人标签 | 时间段（秒） | 实际转录 |
| --- | --- | --- |
| Speaker_0 | 0.000–63.810 | 试错的过程很简单。而且特别是今天报名仓雪卡的同学，你们可以。听到后面的有专门的活动课，他会大大降低你的试绸成本。其实你也可以不来听课。为什么你自己写嘛？我先今天写5个点，我就试试试验一下，反正这5个点不行，我再写5个点，这试再不行。那再写5个点吧。你总会所谓的活动大神和所谓的高手都是只有一个。把所有的错，所有的坑全国趟一遍，留下正确的，你就是所谓的大神，。明白吗？所以说关于活动通过这一块，我只送给你们四个字啊，换位思考。如果说你要想降低。你的试错成本，今天来这里你们就是对的。。因为有畅血畅血卡这个机会，所以说关于活动过于不过这个问题，或者活动很难通过这个话题。呃，如果真的。那要坐下来聊的话，要聊一天。但是我觉得我刚才说的四个字足够。好，谢谢。 |
| Speaker_1 | 63.810–70.471 | 好，非常感谢那个三茂老师的回答。三茂老师说，我们在。整个店铺的这个活动当中，我们要学会换位思考。其实。 |

| 音频时长 | 文件处理流程 | AXCL 调用合计 | 调用次数 |
| --- | --- | --- | --- |
| 70.471 s | 20.406 s | 1.660 s | 95 |

| 内部 ASR 切片 | 实际输入时长 | 最晚词级时间戳 | 超出切片末尾的词条数 |
| --- | --- | --- | --- |
| segment_0 | 6.480000 s | 7.650 s | 1 |
| segment_1 | 17.190000 s | 23.010 s | 1 |
| segment_2 | 14.540000 s | 15.330 s | 2 |
| segment_3 | 11.700000 s | 15.330 s | 1 |
| segment_4 | 9.910000 s | 15.330 s | 1 |
| segment_5 | 10.650625 s | 15.330 s | 1 |

播放本次输入音频

<audio controls preload="metadata" src="/validation/effects/3d-speaker-mt-axera-20260930/meeting-mt-offline-a.wav" aria-label="播放本次输入音频"></audio>

[下载音频](../../../static/validation/effects/3d-speaker-mt-axera-20260930/meeting-mt-offline-a.wav)

**自然中文录音：原始识别结果**

输入使用仓库中的完整音频。下表保留原始转录，包括错字、标点和特殊标记；说话人标签尚无独立人工标注校验。词级时间边界检查未通过：每个 ASR 切片均有时间戳超出其实际时长。新增表中的时间以各切片起点为零；最终文本中的时间段经过合并，不能替代逐词对齐验证。接入字幕或按词定位播放前，需要修正并复测时间边界。

| 说话人标签 | 时间段（秒） | 实际转录 |
| --- | --- | --- |
| Speaker_0 | 0.000–29.952 | 有的，那么一般是非本人医院的。嗯，单位停保的时候，如实给你妻子填写停保原因，或者说呃如。过单位停报原因填写错了，导致你妻子生育津贴这个呃申请失业金申请的这个原因，就是非本人。医院中断这个原因不符合的，那么需要提呃申请失业金的时候，提供一个单位开具的解除劳动关系证明，写明具体。解除劳动关系原因证明是非本人意愿的。&lt;\|EMO_UNKNOWN\|&gt;&lt;\|Speech\|&gt;&lt;\|woitn\|&gt;. |

| 音频时长 | 文件处理流程 | AXCL 调用合计 | 调用次数 |
| --- | --- | --- | --- |
| 29.952 s | 14.996 s | 0.811 s | 45 |

| 内部 ASR 切片 | 实际输入时长 | 最晚词级时间戳 | 超出切片末尾的词条数 |
| --- | --- | --- | --- |
| segment_0 | 2.820000 s | 7.650 s | 2 |
| segment_1 | 25.780000 s | 30.690 s | 1 |
| segment_2 | 1.300000 s | 7.650 s | 4 |

播放本次输入音频

<audio controls preload="metadata" src="/validation/effects/3d-speaker-mt-axera-20260930/meeting-mt-natural-a.mp3" aria-label="播放本次输入音频"></audio>

[下载音频](../../../static/validation/effects/3d-speaker-mt-axera-20260930/meeting-mt-natural-a.mp3)

**使用时注意：**

- 本次仅验证 16GB 卡上的离线文件流程；真实 8GB、实时 WebSocket、浏览器麦克风与大模型纪要总结尚未验证。
- 输出存在识别错字和未清除的特殊标记。没有独立人工标注文本与说话人边界，未报告 CER、WER 或说话人分离错误率。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`3592794622a5627aca47c81fdc2569e632ffc910`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际执行模型 | 3 个 AXModel | VAD、CAMPPlus 和 SenseVoice 均使用 AXCL。 |
| 输入覆盖 | 70.471 秒 / 29.952 秒 | 仓库自带 WAV 和 MP3，均使用完整输入。 |
| 实际调用 | 140 次 | 两个案例分别为 95 次和 45 次，权重及代码运行前后校验一致。 |

适用范围：

- Speaker 标签是单段录音的聚类编号，不能视为真实身份；不同录音的同一编号不代表同一个人。
- 两段输入均为 16kHz；更长会议、重叠说话、其他采样率、并发和持续运行需要额外验证。
- 文件流程计时包含加载、校验及记录开销，不代表纯 NPU 速度或常驻服务吞吐。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_meeting/utils/infer_func.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_func.py) | Python 程序 / 前后处理 |
| [`ax_meeting/utils/infer_utils.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_utils.py) | Python 程序 / 前后处理 |
| [`ax_meeting/ax_model/campplus.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/ax_model/campplus.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_meeting/ax_model/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/ax_model/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_meeting/ax_model/vad.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/ax_model/vad.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/campplus.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_model/campplus.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_model/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assert/gradio_demo.JPG`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/assert/gradio_demo.JPG) | 配套资源 |
| [`assert/meeting_demo.png`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/assert/meeting_demo.png) | 示例输入 |
| [`ax_meeting/utils/sentencepiece_tokenizer.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/sentencepiece_tokenizer.py) | 旧版分词服务入口 |
| [`build/lib/ax_meeting/utils/sentencepiece_tokenizer.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/build/lib/ax_meeting/utils/sentencepiece_tokenizer.py) | 旧版分词服务入口 |
| [`config.json`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/requirements.txt) | Python 依赖清单 |
| [`utils/sentencepiece_tokenizer.py`](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/utils/sentencepiece_tokenizer.py) | 旧版分词服务入口 |

仓库提交：`3592794622a5627aca47c81fdc2569e632ffc910`。仓库中的 9 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/tree/3592794622a5627aca47c81fdc2569e632ffc910)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/tree/3592794622a5627aca47c81fdc2569e632ffc910)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/README.md)。
- [主要程序入口：ax_meeting/utils/infer_func.py](https://huggingface.co/AXERA-TECH/3D-Speaker-MT.Axera/blob/3592794622a5627aca47c81fdc2569e632ffc910/ax_meeting/utils/infer_func.py)。

返回[完整模型目录](../catalog.mdx)。
