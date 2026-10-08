---
title: "Qwen3-TTS-12Hz-0.6B-Base-AX650 部署指南"
sidebar_label: "Qwen3-TTS-12Hz-0.6B-Base-AX650"
description: "Qwen3-TTS-12Hz-0.6B-Base-AX650 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-TTS-12Hz-0.6B-Base-AX650 部署指南

Qwen3-TTS-12Hz-0.6B-Base-AX650 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650` 的固定版本。下面下载本页选用的 91 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-tts-12hz-0-6b-base-ax650/3b3fde9cb90b
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650 \
  --include "README.md" "assets/*" "code-predictor/*" "configuration.json" "extract_speaker_embedding_3s.axmodel" "infer.py" "infer.sh" "speech_tokenizer/*" "talker/*" \
  --revision 3b3fde9cb90b3646c7c9fdeefe083402c0399c2f \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备语音运行程序

本例在 RK3576 主机通过 AXCL 驱动 M.2 算力卡，使用 Qwen3-TTS 0.6B 的参考音频和文本生成一句中文语音。已验证环境为 AX8850 16GB、AXCL 3.16.0；运行程序为 Linux ARM64 版本。

下载[本页配套运行包](/examples/qwen3tts-base-20261001.tar.gz)，保存为主机上的 `~/edgeaccel/qwen3tts-base-20261001.tar.gz`。包内包含本次使用的程序、固定源码、AXCL 适配文件和文件校验工具。保留前文下载模型后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3tts-base-20261001.tar.gz
sudo apt-get install -y libopencv-dev
chmod +x ~/edgeaccel/qwen3tts-base/bin/axllm
ldd ~/edgeaccel/qwen3tts-base/bin/axllm
~/edgeaccel/qwen3tts-base/bin/axllm tts_voice_clone "$MODEL_DIR" --help
```

`ldd` 应能找到所有动态库，帮助信息应包含 `tts_voice_clone`。程序基于官方 AX-LLM 提交 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`，补齐 AXCL 设备 0 的工作线程初始化与释放、两组形状模型的 K/V 缓冲区绑定。该程序对应本页 0.6B 权重，不直接用于 1.7B VoiceDesign 版本。

## 校验模型文件

确认下载目录保留 `talker`、`code-predictor`、`speech_tokenizer` 和 `assets` 子目录。校验本页固定版本的 91 个文件：

```bash
python3 ~/edgeaccel/qwen3tts-base/verify_models.py --model-dir "$MODEL_DIR"
```

输出 `Verified 91 model files` 后继续。权重与配套文件约 1.9 GB；存储空间不足时，将 `MODEL_DIR` 指向已挂载的存储设备。校验失败时先检查下载文件，不能跳过校验运行。

## 生成中文语音

使用官方自带参考音频，保持参考文本与音频内容一致。下面的参数与本次实测相同：

```bash
mkdir -p ~/edgeaccel/results/qwen3tts-base
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ~/edgeaccel/qwen3tts-base/bin/axllm tts_voice_clone "$MODEL_DIR" \
  --ref_audio "$MODEL_DIR/assets/zero_shot_prompt.wav" \
  --ref_text '希望你以后能够做的比我还好呦。' \
  --text '你好，欢迎使用算力卡语音合成。' \
  --language Chinese --seed 1234 --max_new_tokens 160 \
  --output ~/edgeaccel/results/qwen3tts-base/generated.wav
```

成功后出现 `voice clone wav saved`，结果目录生成 24 kHz、单声道 WAV。用桌面音频播放器打开文件，或在主机已配置音频输出时执行：

```bash
aplay ~/edgeaccel/results/qwen3tts-base/generated.wav
```

`--text` 是待合成文本；`--ref_audio` 与 `--ref_text` 用于参考音色和上下文。换用自己的参考音频时，同时修改对应文本。`--max_new_tokens` 限制生成语音码帧数，本例为 160；达到上限时应检查是否截断，不能仅凭生成文件判断整句已经完成。

<details>
<summary>在其他主机重新编译时展开</summary>


若 ARM64 程序的动态库版本与系统不匹配，可使用包内相同源码和适配文件重新编译。以下步骤使用现有 AXCL 头文件和库：

```bash
sudo apt-get install -y build-essential cmake libopencv-dev
cd ~/edgeaccel/qwen3tts-base
mkdir source
tar -xzf official-source.tar.gz -C source
cp -r adapted/src/. source/src/
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON
cmake --build build --target axllm -j1
```

将前面命令中的 `bin/axllm` 换成 `build/axllm`。固定源码包已包含对应版本的子模块，无需在编译时重新拉取分支。

</details>


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 Qwen3-TTS 0.6B 中文语音合成，生成可播放的 3.36 秒音频。

**中文参考音色合成**

使用官方参考音频合成下列中文句子，生成 42 帧语音码后自然结束。下面是本次生成的原始 WAV。Whisper 辅助转录将“算力卡”识别为“三立卡”；这条差异保留供对照，不等同于人工发音或音色相似度判定。

| 项目 | 实际内容 |
| --- | --- |
| 合成文本 | 你好，欢迎使用算力卡语音合成。 |
| 辅助转录 | 你好,欢迎使用三立卡语音合成 |
| 音频格式 | 24 kHz / 单声道 / 3.36 秒 |
| 完整进程耗时 | 98.482 s（含加载和调用记录） |
| 模型与调用 | 65 个 AXModel / 5,881 次 AXCL 调用 |

播放本次生成的中文语音（3.36 秒）

<audio controls preload="metadata" src="/validation/effects/qwen3-tts-12hz-0-6b-base-ax650-20261001/generated.wav" aria-label="播放本次生成的中文语音（3.36 秒）"></audio>

[下载音频](../../../static/validation/effects/qwen3-tts-12hz-0-6b-base-ax650-20261001/generated.wav)

**使用时注意：**

- 本次为 16GB 卡的单句基础部署；真实 8GB 容量、长文本、多语言和连续运行尚未验证。
- 使用官方参考音频，未进行人工试听评分或音色相似度评估；辅助 ASR 文本保留原始差异。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`3b3fde9cb90b3646c7c9fdeefe083402c0399c2f`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | AX-LLM a51df2d + AXCL 设备与 K/V 缓冲区适配 / Linux ARM64 / AXCL C API |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 语音输出 | 24 kHz / 3.36 s | 单声道原始 WAV，生成过程自然结束。 |
| 完整运行链路 | 65 个 AXModel | 参考音频编码、说话人特征、Talker、语音码预测和解码器均有实际 AXCL 调用。 |
| 本次进程耗时 | 98.482 s | 含模型加载、处理、逐步日志和调用记录，不代表常驻服务延迟或纯 NPU 运算时间。 |

适用范围：

- 本页运行包含 AXCL 工作线程与两组形状 K/V 缓冲区适配，不是未经修改的官方可执行程序。
- 原生调用记录验证加载、执行和释放，输出音频已检查有限数值；未据此判定所有中间张量的数值精度。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer.py`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/infer.py) | Python 程序 / 前后处理 |
| [`talker/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/config.json) | 运行配置 |
| [`talker/qwen3_tts_talker_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/qwen3_tts_talker_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`talker/talker.model.text_embedding.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/talker.model.text_embedding.weight.bfloat16.bin) | Embedding 权重 |
| [`talker/qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`talker/post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/talker/post_config.json) | 运行配置 |
| [`code-predictor/code_predictor_lm_head_0.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_0.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_1.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_1.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_10.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_10.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_11.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_11.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`code-predictor/code_predictor_lm_head_12.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/code-predictor/code_predictor_lm_head_12.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`3b3fde9cb90b3646c7c9fdeefe083402c0399c2f`。仓库中的 65 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/tree/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是 talker、code predictor 与音频解码器组成的语音链路。子目录中的 axllm 配置只能表示其中一个阶段，不应当作普通文本模型启动整个 TTS。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/tree/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/README.md)。
- [主要程序入口：infer.py](https://huggingface.co/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650/blob/3b3fde9cb90b3646c7c9fdeefe083402c0399c2f/infer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-qwen3_tts)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
