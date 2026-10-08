---
title: "VoxCPM 部署指南"
sidebar_label: "VoxCPM"
description: "VoxCPM 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# VoxCPM 部署指南

VoxCPM 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/VoxCPM` 的固定版本。下面下载本页选用的 97 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/voxcpm/4362ceca842a
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/VoxCPM \
  --include "README.md" "VoxCPM-0.5B/*" "assets/*" "axmodels/*" "base_lm-axmodels/*" "feat_decoder_estimator_decoder-axmodels/*" "feat_encoder_encoder-axmodels/*" "residual_lm-axmodels/*" "onnxruntime-aarch64-none-gnu-1.16.0/*" "config.json" "main_ax650" "run_ax650.py" "run_ax650.sh" "tokenizer.py" \
  --revision 4362ceca842ace15a8f7e67a2302f72143a60f06 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备语音运行程序

本例在 RK3576 + AX8850 16GB M.2 算力卡上运行 VoxCPM。语言模型、声学模型及输入投影通过 `AXCLRTExecutionProvider` 执行；音频编解码使用官方提供的 ONNX 文件在主机 CPU 执行。

下载[本页配套运行包](/examples/voxcpm-20261002.tar.gz)，保存为 `~/edgeaccel/voxcpm-20261002.tar.gz`。包内提供本次固定源码、运行脚本和依赖版本，使用 Python 3.12 环境。保留前文设置的 `MODEL_DIR`，在连接算力卡的 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf voxcpm-20261002.tar.gz
cd voxcpm-card
mkdir source
tar -xzf official-source.tar.gz -C source
source ~/edgeaccel/python-env/bin/activate
python -m pip install -r requirements.txt
python verify_models.py --model-dir "$MODEL_DIR"
```

若前文使用了其他虚拟环境路径，将 `~/edgeaccel/python-env` 替换为已安装 PyAXEngine 的环境。校验应输出 `Verified 97 model files`。本页使用固定版本的全部文件，约 1.9 GB；保留原有目录结构，不能只下载 `.axmodel`。

## 合成参考音色语音

以下命令使用官方英文参考音频和配套文本。输出目录需要是一个尚不存在的新目录；重复运行时换一个目录名。

```bash
cd ~/edgeaccel/voxcpm-card
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
python voxcpm_card.py --projection-backend axcl \
  --model-dir "$MODEL_DIR" --source ./source \
  --text 'Streaming text to speech is easy with VoxCPM!' \
  --reference-audio assets/en_woman1.mp3 \
  --reference-text 'But many of these southern girls have the same trouble, said Holly.' \
  --output ~/edgeaccel/results/voxcpm-english
```

成功后结果目录包含 `generated.wav` 和 `deployment-result.json`。音频为 16 kHz 单声道；结果中的 `completed` 和 `naturalStop` 都应为 `true`。使用桌面播放器打开 WAV，或在主机已配置音频输出时执行：

```bash
aplay ~/edgeaccel/results/voxcpm-english/generated.wav
```

`--text` 是待合成文本；`--reference-audio` 是下载目录中的参考音频相对路径，`--reference-text` 必须与参考音频内容对应。`--projection-backend axcl` 使用算力卡执行输入投影；改为 `cpu` 可使用原有 ONNX 投影。

本页固定随机种子 1234、10 步声学采样及最多 128 个语音块；达到长度上限而没有自然结束时，脚本报告失败，避免把截断音频作为完整结果。

本例关闭外部文本规范化和降噪，直接使用给定文本与官方清晰参考音频。调整为含数字、日期、缩写或噪声的输入后，需要另行检查读法和效果。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 VoxCPM 英文语音合成，生成 4.08 秒单声道音频。

**NPU 输入投影语音合成**

输入投影使用官方 AXMODEL 在算力卡上执行，音频编解码使用 CPU ONNX；参考音频、文本和随机种子固定，生成到模型结束信号为止。先播放参考音频，再播放本次原始 WAV；辅助转写仅供对照，不替代人工听音或音色相似度评估。

| 项目 | 本次结果 |
| --- | --- |
| 合成文本 | Streaming text to speech is easy with VoxCPM! |
| 辅助转写 |  Streaming text to speech is easy with VoxyPM. |
| 音频格式 | 16 kHz / 单声道 / 4.08 秒 |
| 生成语音块 | 51 |
| 合成流程 | 109.434 s（含 CPU 处理和逐次校验） |
| 模型加载 | 16.617 s |
| 算力卡执行 | 50 个 AXModel / 12,450 次调用 |

播放官方参考音频

<audio controls preload="metadata" src="/validation/effects/voxcpm-20261002/reference.mp3" aria-label="播放官方参考音频"></audio>

[下载音频](../../../static/validation/effects/voxcpm-20261002/reference.mp3)

播放本次生成的英文语音

<audio controls preload="metadata" src="/validation/effects/voxcpm-20261002/generated.wav" aria-label="播放本次生成的英文语音"></audio>

[下载音频](../../../static/validation/effects/voxcpm-20261002/generated.wav)

**使用时注意：**

- 辅助转写将末尾专名 VoxCPM 识别为 VoxyPM；专名发音与整体听感仍需人工核对，不能据此认定语音质量通过。
- 本次为 16GB 算力卡上的单句英文基础部署；8GB、中文、长文本和连续运行仍需独立验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`4362ceca842ace15a8f7e67a2302f72143a60f06`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12 / PyAXEngine 0.1.3 / AXCLRTExecutionProvider + CPU ONNX |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际输出 | 4.08 s / 16 kHz | 固定官方参考音频与英文句子，模型自然结束。 |
| 算力卡调用 | 50 个 AXModel | 按实际调用记录统计；CPU ONNX 音频编解码单独列出。 |
| 合成流程耗时 | 109.434 s | 包含参考音频处理、CPU ONNX、PCIe 传输和逐次输出校验；另计模型加载，不代表实时服务性能。 |

适用范围：

- 音频编解码仍使用 CPU ONNX；语言模型、声学模型和输入投影使用算力卡。
- 关闭了外部文本规范化和降噪；数字、缩写和噪声参考音频需要补充测试。
- 未进行人工听音或音色相似度评分；独立 ASR 仅作内容核对的辅助。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_ax650.py`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/run_ax650.py) | Python 程序 / 前后处理 |
| [`tokenizer.py`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/tokenizer.py) | 旧版分词服务入口 |
| [`axmodels/enc_to_lm_proj.axmodel`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/axmodels/enc_to_lm_proj.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodels/feat_encoder.in_proj.axmodel`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/axmodels/feat_encoder.in_proj.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodels/fsq_layer.axmodel`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/axmodels/fsq_layer.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodels/lm_to_dit_proj.axmodel`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/axmodels/lm_to_dit_proj.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`axmodels/locdit.part1.axmodel`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/axmodels/locdit.part1.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`VoxCPM-0.5B/config.json`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/VoxCPM-0.5B/config.json) | 运行配置 |
| [`VoxCPM-0.5B/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/VoxCPM-0.5B/tokenizer_config.json) | 运行配置 |
| [`config.json`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/config.json) | 运行配置 |
| [`run_ax650.sh`](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/run_ax650.sh) | 启动或构建脚本 |

仓库提交：`4362ceca842ace15a8f7e67a2302f72143a60f06`。仓库中的 50 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/VoxCPM/tree/4362ceca842ace15a8f7e67a2302f72143a60f06)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/VoxCPM/tree/4362ceca842ace15a8f7e67a2302f72143a60f06)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/README.md)。
- [主要程序入口：run_ax650.py](https://huggingface.co/AXERA-TECH/VoxCPM/blob/4362ceca842ace15a8f7e67a2302f72143a60f06/run_ax650.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/VoxCPM)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
