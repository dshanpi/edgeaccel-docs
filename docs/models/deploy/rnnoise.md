---
title: "rnnoise 部署指南"
sidebar_label: "rnnoise"
description: "rnnoise 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# rnnoise 部署指南

rnnoise 用于语音增强与分离。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/rnnoise` 的固定版本。下面下载本页选用的 16 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/rnnoise/f2b2f8760357
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/rnnoise \
  "LICENSE" \
  "README.md" \
  "python/demo.py" \
  "python/requirements.txt" \
  "python/rnnoise_sdk/README.md" \
  "python/rnnoise_sdk/__init__.py" \
  "python/rnnoise_sdk/dsp.py" \
  "python/rnnoise_sdk/example.py" \
  "python/rnnoise_sdk/inference.py" \
  "python/rnnoise_sdk/inference_npu.py" \
  "python/rnnoise_sdk/postprocess.py" \
  "python/rnnoise_sdk/preprocess.py" \
  "python/rnnoise_sdk/requirements.txt" \
  "python/sample_speech.pcm" \
  "rnnoise_ax650/model.axmodel" \
  "rnnoise_ax650/model_meta.json" \
  --revision f2b2f87603576f27b303f0b3b033ad4aac0acc18 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

先按 [Python 接口](../../usage/python.md) 创建 `~/edgeaccel/python-env` 并安装 PyAXEngine，再在连接 M.2 算力卡的主机上激活环境。示例显式选择 `AXCLRTExecutionProvider`，保留官方 SDK 的特征提取、状态传递和音频合成。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。

## 运行降噪

下载本页配套的 [RNNoise 算力卡示例](../../../static/examples/rnnoise_card.py)，保存为 `~/edgeaccel/rnnoise_card.py`。保持下载步骤中的 `MODEL_DIR` 变量，执行：

```bash
python ~/edgeaccel/rnnoise_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/rnnoise-01
```

输出目录须尚不存在。再次运行时将末尾目录名改为 `rnnoise-02` 等新名称。

示例依次处理官方录音、添加固定随机噪声的录音和静音，每份输入重置状态后运行两次。音频格式为 48 kHz 单声道，每帧 480 点；模型输入使用 16-bit PCM 等价浮点幅度，不除以 32768。当前固定版本的官方 PCM 文件实际长度为 **1 秒**。

## 播放输入与输出

在输出目录中对照播放以下 WAV。文件均使用相同幅度比例保存，未分别归一化响度：

| 输入 | 输出 | 用途 |
| --- | --- | --- |
| `official-input.wav` | `official-output.wav` | 官方录音对比 |
| `added-noise-input.wav` | `added-noise-output.wav` | 固定加噪录音对比 |
| `silence-input.wav` | `silence-output.wav` | 检查静音输出 |

`deployment-result.json` 保存帧数、AXCL 调用次数、输出数值检查和两次重复运行的比较结果；原始浮点 PCM、逐帧 VAD 数组也会保留。

加噪样例的噪声功率比源录音低 6 dB，随机种子为 `20260927`。源录音并非独立标注的纯净参考，因此这里不提供降噪质量分数。静音由官方 SDK 的静音分支处理，不调用 NPU；语音与加噪样例的神经网络推理通过 AXCL 完成。

本次 Python 完整处理速度慢于音频播放速度，尚不满足实时麦克风降噪要求；下面保留实际耗时与可试听结果。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-27 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

通过 AXCL 完成官方录音和固定加噪录音的逐帧降噪，另检查静音分支；每份输入重复两次，输出一致。下方可试听实际输入与输出。

**官方录音**

48 kHz 单声道，1.0 秒、100 帧。重置状态后运行两次，浮点音频和 VAD 输出逐项一致。两次各调用 AXCL 100 次，模型输出均为有限数值；尚未完成人工听音评分。

| 项目 | 实际值 |
| --- | --- |
| 两次完整处理耗时 | 4.881 s / 4.683 s |
| 两次 AXCL 调用次数 | 100 / 100 |
| VAD > 0.5 的帧数 | 100 / 100 |
| VAD 范围 | 0.671978 ～ 0.999865 |

官方录音 · 输入

<audio controls preload="metadata" src="/validation/effects/rnnoise-20260927/official-input.wav" aria-label="官方录音 · 输入"></audio>

[下载音频](../../../static/validation/effects/rnnoise-20260927/official-input.wav)

官方录音 · 实际输出

<audio controls preload="metadata" src="/validation/effects/rnnoise-20260927/official-output.wav" aria-label="官方录音 · 实际输出"></audio>

[下载音频](../../../static/validation/effects/rnnoise-20260927/official-output.wav)

**固定加噪录音**

48 kHz 单声道，1.0 秒、100 帧。重置状态后运行两次，浮点音频和 VAD 输出逐项一致。两次各调用 AXCL 100 次，模型输出均为有限数值；尚未完成人工听音评分。

| 项目 | 实际值 |
| --- | --- |
| 两次完整处理耗时 | 4.636 s / 4.781 s |
| 两次 AXCL 调用次数 | 100 / 100 |
| VAD > 0.5 的帧数 | 100 / 100 |
| VAD 范围 | 0.515197 ～ 0.999865 |

固定加噪录音 · 输入

<audio controls preload="metadata" src="/validation/effects/rnnoise-20260927/added-noise-input.wav" aria-label="固定加噪录音 · 输入"></audio>

[下载音频](../../../static/validation/effects/rnnoise-20260927/added-noise-input.wav)

固定加噪录音 · 实际输出

<audio controls preload="metadata" src="/validation/effects/rnnoise-20260927/added-noise-output.wav" aria-label="固定加噪录音 · 实际输出"></audio>

[下载音频](../../../static/validation/effects/rnnoise-20260927/added-noise-output.wav)

**静音**

48 kHz 单声道，1.0 秒、100 帧。重置状态后运行两次，浮点音频和 VAD 输出逐项一致。静音分支跳过神经网络推理，输出保持全零。

| 项目 | 实际值 |
| --- | --- |
| 两次完整处理耗时 | 3.134 s / 3.114 s |
| 两次 AXCL 调用次数 | 0 / 0 |
| VAD > 0.5 的帧数 | 0 / 100 |
| VAD 范围 | 0.000000 ～ 0.000000 |

静音 · 输入

<audio controls preload="metadata" src="/validation/effects/rnnoise-20260927/silence-input.wav" aria-label="静音 · 输入"></audio>

[下载音频](../../../static/validation/effects/rnnoise-20260927/silence-input.wav)

静音 · 实际输出

<audio controls preload="metadata" src="/validation/effects/rnnoise-20260927/silence-output.wav" aria-label="静音 · 实际输出"></audio>

[下载音频](../../../static/validation/effects/rnnoise-20260927/silence-output.wav)

**使用时注意：**

- 仅测试三份 1 秒输入；未完成人工听音评分，也未用独立纯净参考计算 PESQ、STOI 或信噪比改善。
- Python 全流程每秒音频约需 3～5 秒，尚不满足实时处理；耗时记录包含主机 NumPy 前后处理，不代表 NPU 单独性能。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-27。模型版本：`f2b2f87603576f27b303f0b3b033ad4aac0acc18`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 环境 | Python 3.12 / NumPy 1.26.4 / PyAXEngine 0.1.3.rc3 |
| 后端 | AXCLRTExecutionProvider；前后处理为官方 NumPy SDK |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| AXCL 单帧调用平均耗时 | 9.379 ms（400 次） | 包含 session.run 的传输与推理；不含前后处理、模型加载和保存，未剔除首轮。 |

适用范围：

- 仅测试三份 1 秒输入；未完成人工听音评分，也未用独立纯净参考计算 PESQ、STOI 或信噪比改善。
- Python 全流程每秒音频约需 3～5 秒，尚不满足实时处理；耗时记录包含主机 NumPy 前后处理，不代表 NPU 单独性能。
- 静音分支没有 NPU 调用，其成功不能单独证明模型推理通过。仅在 16GB 卡测试，未验证 8GB、长音频、麦克风或连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/demo.py`](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/python/demo.py) | Python 程序 / 前后处理 |
| [`rnnoise_ax650/model.axmodel`](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/rnnoise_ax650/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/python/requirements.txt) | Python 依赖清单 |
| [`python/rnnoise_sdk/requirements.txt`](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/python/rnnoise_sdk/requirements.txt) | Python 依赖清单 |

仓库提交：`f2b2f87603576f27b303f0b3b033ad4aac0acc18`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/rnnoise/tree/f2b2f87603576f27b303f0b3b033ad4aac0acc18)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 噪声抑制的特征提取和循环状态与网络一起构成完整处理链路；AX650 与 AX620E 编译产物不能混用。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/rnnoise/tree/f2b2f87603576f27b303f0b3b033ad4aac0acc18)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/README.md)。
- [主要程序入口：python/demo.py](https://huggingface.co/AXERA-TECH/rnnoise/blob/f2b2f87603576f27b303f0b3b033ad4aac0acc18/python/demo.py)。

返回[完整模型目录](../catalog.mdx)。
