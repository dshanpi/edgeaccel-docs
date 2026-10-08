---
title: "Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650 部署指南"
sidebar_label: "Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650"
description: "Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650 部署指南

Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

在 RK3576 的 Linux 终端执行。本例已在 **AX8850 16GB M.2 算力卡、AXCL 3.16.0** 上验证，用文字描述音色并生成中文语音，无需参考录音。

先完成[驱动与设备检查](../../usage/device-check.md)，保持风扇正常运行。运行前执行 `axcl-smi`，确认设备 0 可用。准备至少 4 GiB 可用存储；模型与配套文件约 2.79 GB。

下载[VoiceDesign 配套运行包](/examples/qwen3tts-voicedesign-20261004.tar.gz)，保存到主机的 `~/edgeaccel/`，然后执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3tts-voicedesign-20261004.tar.gz
sudo apt-get install -y libopencv-dev libblas3
chmod +x qwen3tts-voicedesign/bin/axllm
ldd qwen3tts-voicedesign/bin/axllm
```

`ldd` 输出中不能出现 `not found`。包内程序适用于 Linux ARM64，包含本页 1.7B VoiceDesign 的接口和输出尺度适配，请与本页固定权重配套使用。

## 下载并校验模型

设置模型目录。存储不足时，将 `MODEL_DIR` 改为已挂载存储设备上的目录，后续命令继续使用同一个变量：

```bash
MODEL_DIR=~/edgeaccel/models/qwen3tts-voicedesign
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
python3 ~/edgeaccel/qwen3tts-voicedesign/setup_models.py \
  --model-dir "$MODEL_DIR"
```

下载工具使用 Python 3.11 或更新版本的标准库，逐个核对文件大小和 SHA-256。输出 `Verified 87 runtime files` 后继续。已有且校验一致的文件会跳过；下载失败后可重新执行同一命令。

若 Hugging Face 无法直连，在运行下载命令前设置可用代理。以下地址仅为局域网示例，需替换为主机可访问的地址：

```bash
export http_proxy="http://192.168.1.38:7897"
export https_proxy="$http_proxy"
```

文件由三部分组成：

| 内容 | 固定来源 | 运行位置 |
| --- | --- | --- |
| VoiceDesign 1.7B 权重与嵌入 | AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650，`3d4e2e701313` | 50 个 AXModel 在算力卡运行 |
| 公用语音解码器与词表 | AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650，`3b3fde9cb90b` | 11 个解码 AXModel 在算力卡运行 |
| 文本投影、预测器解码投影、Talker 归一化 | Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign，`5ecdb67327fd` | 使用原始权重在 RK3576 CPU 运行，已随运行包提供 |

使用公用解码器不会替换 1.7B 的文本与语音码生成模型。完整文件来源、版本和校验值见包内 `runtime-files.json`。

## 运行语音生成

下面的输入、音色描述和参数与本页实测一致：

```bash
python3 ~/edgeaccel/qwen3tts-voicedesign/setup_models.py \
  --model-dir "$MODEL_DIR" --verify-only
mkdir -p ~/edgeaccel/results/qwen3tts-voicedesign
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ~/edgeaccel/qwen3tts-voicedesign/bin/axllm tts_voice_design "$MODEL_DIR" \
  --text '你好，欢迎使用算力卡语音合成。' \
  --instruct '用温柔清晰的女声朗读，语速适中。' \
  --language Chinese --seed 1234 --max_new_tokens 160 \
  --non_streaming_mode \
  --output ~/edgeaccel/results/qwen3tts-voicedesign/generated.wav
```

`--text` 指定朗读内容，`--instruct` 描述音色和语速。程序完成后输出 `voice design wav saved`，生成 24 kHz、单声道 WAV。此次样例生成 43 帧语音码后自然结束，音频为 3.44 秒。

用桌面音频播放器打开文件，或在主机已配置音频输出时执行：

```bash
aplay ~/edgeaccel/results/qwen3tts-voicedesign/generated.wav
```

本页只验证上述中文短句。配套解码器的单次容量为 128 帧；先使用短句，长文本按句拆分。达到生成上限、出现容量错误或输出头范围错误时，保留提示并停止，不能将被截断的音频视为完整结果。

<details>
<summary>需要重新编译运行程序时展开</summary>

包内 `source.tar.gz` 为本次实际使用的完整源码，已包含固定版本子模块及适配。AX-LLM 基础提交为 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`。

```bash
sudo apt-get install -y build-essential cmake libopencv-dev libblas3
cd ~/edgeaccel/qwen3tts-voicedesign
mkdir -p source
tar -xzf source.tar.gz -C source
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON
cmake --build build --target axllm -j1
```

编译后，将运行命令中的 `bin/axllm` 换成 `build/axllm`。编译时须已安装 AXCL 的头文件和库。

</details>


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 1.7B VoiceDesign 中文短句合成，生成可播放的 3.44 秒音频。

**文字描述音色并生成中文语音**

输入下列音色描述和文本，模型生成 43 帧语音码后自然结束，得到 3.44 秒音频。辅助转录把“算力卡”识别为“算栗塔”，保留原始结果供逐字对照；尚未进行人工发音或音色评分。

| 项目 | 本次结果 |
| --- | --- |
| 音色描述 | 用温柔清晰的女声朗读，语速适中。 |
| 朗读文本 | 你好，欢迎使用算力卡语音合成。 |
| 辅助转录 | 你好,欢迎使用算栗塔语音合成。 |
| 音频格式 | 24 kHz / 单声道 / 3.44 秒 |
| 完整进程耗时 | 149.720 s（含模型加载与调用记录） |
| 模型执行 | 61 个 AXModel / 5,844 次 AXCL 调用 |

播放本次生成的中文语音（3.44 秒）

<audio controls preload="metadata" src="/validation/effects/qwen3-tts-12hz-1-7b-voicedesign-ax650-20261004/generated.wav" aria-label="播放本次生成的中文语音（3.44 秒）"></audio>

[下载音频](../../../static/validation/effects/qwen3-tts-12hz-1-7b-voicedesign-ax650-20261004/generated.wav)

**使用时注意：**

- 本次为 RK3576 + 16GB 卡的单句基础部署；真实 8GB 容量、长文本、多语言和连续运行仍待验证。
- 音色描述已传入模型；未做人工音色评分。辅助转录存在“算力卡/算栗塔”差异，专有词读音需回放核对。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`3d4e2e70131378bd8bfbe307ef2de01192f0bc32`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | AX-LLM a51df2d + VoiceDesign 1.7B 适配 / Linux ARM64 / AXCL C API + 原始权重 CPU 算子 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 生成音频 | 24 kHz / 3.44 s | 43 帧语音码后自然结束，原始 WAV 可直接播放。 |
| 完整模型链路 | 61 个 AXModel | 1.7B 生成模型 50 个，公用语音解码模型 11 个，均有实际 AXCL 调用。 |
| 本次进程耗时 | 149.720 s | 包含模型加载和调用记录；本次模型文件经网络只读挂载，不代表本地存储或常驻服务性能。 |

适用范围：

- 使用本页配套适配程序。文本投影、预测器解码投影和 Talker 归一化在主机 CPU 执行；其余 61 个模型通过 AXCL 执行。
- 配套语音解码器单次容量为 128 帧；本例自然结束于 43 帧，不据此推断任意长文本均可运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`code-predictor/code_predictor_lm_head_0.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/blob/3d4e2e70131378bd8bfbe307ef2de01192f0bc32/code-predictor/code_predictor_lm_head_0.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_1.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/blob/3d4e2e70131378bd8bfbe307ef2de01192f0bc32/code-predictor/code_predictor_lm_head_1.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_10.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/blob/3d4e2e70131378bd8bfbe307ef2de01192f0bc32/code-predictor/code_predictor_lm_head_10.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_11.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/blob/3d4e2e70131378bd8bfbe307ef2de01192f0bc32/code-predictor/code_predictor_lm_head_11.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_12.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/blob/3d4e2e70131378bd8bfbe307ef2de01192f0bc32/code-predictor/code_predictor_lm_head_12.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`3d4e2e70131378bd8bfbe307ef2de01192f0bc32`。仓库中的 50 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/tree/3d4e2e70131378bd8bfbe307ef2de01192f0bc32)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- VoiceDesign 使用文字描述控制音色；不能沿用 Base 版本的参考音频接口。分别核对 talker、code predictor 和音频 tokenizer/decoder。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/tree/3d4e2e70131378bd8bfbe307ef2de01192f0bc32)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650/blob/3d4e2e70131378bd8bfbe307ef2de01192f0bc32/README.md)。

返回[完整模型目录](../catalog.mdx)。
