---
title: "Spoken-Communication.axera 部署指南"
sidebar_label: "Spoken-Communication.axera"
description: "Spoken-Communication.axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Spoken-Communication.axera 部署指南

Spoken-Communication.axera 用于语音识别、问答与合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Spoken-Communication.axera` 的固定版本。下面下载本页选用的 122 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/spoken-communication-axera/ecd09194a4ed
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Spoken-Communication.axera \
  --include "*" \
  --revision ecd09194a4ed417f6466dedebcd85192118a7bc8 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装依赖与运行包

本例面向 RK3576 主机和 AX8850 16GB M.2 算力卡，使用 AXCL 3.16.0，应用和配套权重均保存于板载文件系统。语音应用约 471MB，配套 Qwen 权重约 2.46GB，建议预留至少 5GB 存储空间。退出其他推理应用，用 `axcl-smi` 确认设备 0 可用。启动服务前，用 `grep MemAvailable /proc/meminfo` 确认主机至少有 2400MiB 可用内存；主机内存与算力卡 CMM 分开计算。

在已安装 PyAXEngine 的 Python 环境中执行：

```bash
sudo apt-get install -y espeak-ng libespeak-ng1
python -m pip install torch==2.5.1 torchaudio==2.5.1 numpy==1.26.4 \
  transformers==4.51.3 tokenizers==0.21.4 onnxruntime==1.20.1 \
  funasr==1.2.7 kaldi-native-fbank==1.22.3 cn2an==0.5.24 \
  pypinyin==0.55.0 phonemizer==3.3.0 num2words==0.5.14 \
  soundfile==0.13.1 librosa==0.11.0 sentencepiece==0.2.1
python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。使用以上配套依赖，避免直接执行仓库中要求另一版 Torch 的安装列表。

## 下载配套 Qwen 模型

保留前文的 `MODEL_DIR`。语音应用调用同一主机上的 Qwen API，另外下载该 API 配套的上下文模型：

```bash
QWEN_DIR=~/edgeaccel/models/qwen2.5-1.5b-speech/eaa03390b75f
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-1.5B-Instruct \
  --revision eaa03390b75ff42286b46ad492d007ce536b303d \
  --include 'qwen2.5-1.5b-ctx-ax650/*' \
  --local-dir "$QWEN_DIR"
```

模型目录需包含 28 个文本层、`qwen2_post.axmodel` 和 BF16 词嵌入。不能替换为同仓库中的 Int4 分片。

## 启动分词与问答服务

使用三个终端，并在每个终端激活同一 Python 环境，设置相同的 `MODEL_DIR` 和 `QWEN_DIR`。

每个终端先设置本机服务绕过下载代理，并限制主机计算线程：

```bash
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1
```

终端一启动分词服务：

```bash
cd "$MODEL_DIR/libaxllm"
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

终端二启动 ARM64 算力卡 API：

```bash
cd "$MODEL_DIR/libaxllm"
chmod +x main_api_axcl_aarch64
WEIGHTS="$QWEN_DIR/qwen2.5-1.5b-ctx-ax650"
./main_api_axcl_aarch64 \
  --system_prompt 'You are a helpful assistant.' \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --devices 0
```

等待模型加载和 API 监听完成。应用通过 `http://127.0.0.1:8000` 访问本机服务。

## 运行语音问答

下载[配套运行包](/examples/spoken-communication-20261001-v2.tar.gz)，将下载文件重命名为 `spoken-communication-20261001-v2.tar.gz`，放到 `~/edgeaccel/`。终端三执行：

```bash
cd ~/edgeaccel
tar -xzf spoken-communication-20261001-v2.tar.gz
python spoken-communication/verify_models.py \
  --app-dir "$MODEL_DIR" --companion-dir "$QWEN_DIR"
python spoken-communication/run.py --app-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input_question/Q1.wav" --output "$HOME/edgeaccel/output/spoken-q1"
```

校验应分别确认 122 个应用文件和 30 个配套权重文件。处理完成后，输出目录中应生成 `result.json` 和 `synthesized.wav`；前者包含识别文本、回答及处理耗时，后者为本次合成音频。

保持两个服务运行，再处理另外两条问题：

```bash
python spoken-communication/run.py --app-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input_question/Q2.wav" --output "$HOME/edgeaccel/output/spoken-q2"
python spoken-communication/run.py --app-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input_question/Q3.wav" --output "$HOME/edgeaccel/output/spoken-q3"
```

每次运行会重置对话，将识别出的语音问题交给本机 Qwen 服务回答，并要求回答限制在 100 个字以内。输出目录必须尚不存在；复测时换一个目录名。处理自己的录音时，将 `--audio` 改为音频文件的绝对路径。

VAD、SenseVoice 和 MeloTTS 解码器在算力卡运行；Qwen 的 29 个 AXModel 由本机 API 服务调用。音频预处理、分词和 MeloTTS 的 ONNX 编码器在 RK3576 主机执行。当前使用 `ZH_MIX_EN` 合成流程，不切换到仓库中的独立英文解码器。

## 检查回答与合成音频

逐项对照输入音频、识别文本、回答和生成音频。回答启用了采样，复测措辞可能不同，需检查是否回应问题，而不是要求逐字一致。生成回答与音频质量正确属于不同检查项。可将 WAV 下载到桌面播放，也可在已配置声卡的 Linux 主机执行：

```bash
aplay "$HOME/edgeaccel/output/spoken-q1/synthesized.wav"
```

处理程序退出码应为 `0`，文本不能为空，音频应能播放。测试结束后，在 API 和分词服务终端分别按 `Ctrl+C`。两个服务均退出后，校验并释放模型文件的主机缓存，再检查设备状态：

```bash
python spoken-communication/release_cache.py \
  --app-dir "$MODEL_DIR" --companion-dir "$QWEN_DIR"
axcl-smi
```

缓存释放程序应确认 152 个文件校验通过；该操作保留磁盘文件，复用模型时无需重新下载。`axcl-smi` 应显示设备 0，且不再有本次推理进程。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在16GB M.2算力卡完成三条语音问题的识别、Qwen回答与语音合成，下面展示本次实际输出。

**语音问答 1**

**示例 1：输入**

```text
回答(限制在100个字以内)：人工智能和人类智能最本质的区别是什么？。（音频：input_question/Q1.wav）
```

**实际回复**

```text
人工智能和人类智能最本质的区别在于，人工智能是基于算法和数据进行学习和决策，而人类智能是基于经验和直觉进行思考和判断。
```

回答围绕算法、数据与人类经验展开，满足本次100字以内的长度要求；内容是模型生成的概括，不作为科学结论。

| 项目 | 本次结果 |
| --- | --- |
| 完整音频请求 / s | 12.536 |
| 输出时长 / s | 13.569 |
| 输出格式 | 44100Hz / 单声道 WAV |

输入音频：input_question/Q1.wav

<audio controls preload="metadata" src="/validation/effects/spoken-communication-axera-20261001/input-1.wav" aria-label="输入音频：input_question/Q1.wav"></audio>

[下载音频](../../../static/validation/effects/spoken-communication-axera-20261001/input-1.wav)

本次生成的回答音频

<audio controls preload="metadata" src="/validation/effects/spoken-communication-axera-20261001/generated-1.wav" aria-label="本次生成的回答音频"></audio>

[下载音频](../../../static/validation/effects/spoken-communication-axera-20261001/generated-1.wav)

**语音问答 2**

**示例 1：输入**

```text
回答(限制在100个字以内)：人工智能没有思想，为什么他能创作出震撼人心的艺术？。（音频：input_question/Q2.wav）
```

**实际回复**

```text
人工智能创作艺术，是因为通过算法和大数据训练，能够模拟和学习人类的创作过程，虽然没有真正的思想，但可以产生与人类相似的艺术作品。
```

回答围绕算法与训练数据解释创作过程，满足长度要求。识别结果保留了原始的“他”和末尾多余标点。

| 项目 | 本次结果 |
| --- | --- |
| 完整音频请求 / s | 12.768 |
| 输出时长 / s | 14.347 |
| 输出格式 | 44100Hz / 单声道 WAV |

输入音频：input_question/Q2.wav

<audio controls preload="metadata" src="/validation/effects/spoken-communication-axera-20261001/input-2.wav" aria-label="输入音频：input_question/Q2.wav"></audio>

[下载音频](../../../static/validation/effects/spoken-communication-axera-20261001/input-2.wav)

本次生成的回答音频

<audio controls preload="metadata" src="/validation/effects/spoken-communication-axera-20261001/generated-2.wav" aria-label="本次生成的回答音频"></audio>

[下载音频](../../../static/validation/effects/spoken-communication-axera-20261001/generated-2.wav)

**语音问答 3**

**示例 1：输入**

```text
回答(限制在100个字以内)：人工智能最终会统治人类吗？。（音频：input_question/Q3.wav）
```

**实际回复**

```text
这是一个复杂的问题，没有简单答案。人工智能的发展可能会带来巨大的社会影响，但目前来看，人类有能力控制和管理人工智能的发展。
```

回答围绕社会影响与人为管理展开，满足长度要求；其中对未来可控性的判断是模型生成内容，不作为预测结论。

| 项目 | 本次结果 |
| --- | --- |
| 完整音频请求 / s | 11.370 |
| 输出时长 / s | 13.674 |
| 输出格式 | 44100Hz / 单声道 WAV |

输入音频：input_question/Q3.wav

<audio controls preload="metadata" src="/validation/effects/spoken-communication-axera-20261001/input-3.wav" aria-label="输入音频：input_question/Q3.wav"></audio>

[下载音频](../../../static/validation/effects/spoken-communication-axera-20261001/input-3.wav)

本次生成的回答音频

<audio controls preload="metadata" src="/validation/effects/spoken-communication-axera-20261001/generated-3.wav" aria-label="本次生成的回答音频"></audio>

[下载音频](../../../static/validation/effects/spoken-communication-axera-20261001/generated-3.wav)

**使用时注意：**

- 识别结果含多余标点；回答为模型生成内容，未进行完整问答质量评估、ASR人工转写对照或合成语音听审。
- 本次使用ZH_MIX_EN合成流程；独立英文编码器/解码器、实时麦克风模式、8GB容量与长期服务尚未验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`ecd09194a4ed417f6466dedebcd85192118a7bc8`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12 / AXCLRTExecutionProvider；本机原生Qwen AXCL API；CPU ONNX编码器 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 模型存储 | 板载文件系统 | 应用文件及配套Qwen权重使用同一板载存储路径。 |
| 算力卡执行 | 32个AXModel | 3个语音权重和配套Qwen的29个权重；ONNX编码器与音频前处理在RK3576主机运行。 |
| 输入覆盖 | 3条官方音频 | 各完成一次识别→回答→合成，配套客户命令另行复测。 |
| Qwen首次加载 | 47.605s | 单独计时，表中的完整音频请求耗时不包含首次模型加载。 |

适用范围：

- 表中处理耗时包含输入输出记录开销，不作为峰值性能或服务吞吐指标。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_spoken_communication_demo.py`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/ax_spoken_communication_demo.py) | Python 程序 / 前后处理 |
| [`libaxllm/qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libaxllm/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`ax_model/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/ax_model/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/vad.axmodel`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/ax_model/vad.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`libmelotts/models/decoder-en.axmodel`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libmelotts/models/decoder-en.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`libmelotts/models/decoder-zh.axmodel`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libmelotts/models/decoder-zh.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/config.json) | 运行配置 |
| [`libaxllm/post_config.json`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libaxllm/post_config.json) | 运行配置 |
| [`libaxllm/qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libaxllm/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_ax650_api.sh`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libaxllm/run_qwen2.5_1.5b_ctx_ax650_api.sh) | 启动或构建脚本 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libaxllm/run_qwen2.5_1.5b_ctx_axcl_aarch64_api.sh) | 启动或构建脚本 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libaxllm/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh) | 启动或构建脚本 |
| [`libmelotts/models/lexicon.txt`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libmelotts/models/lexicon.txt) | 分词器 / 字典，必须配套 |
| [`libmelotts/models/tokens.txt`](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/libmelotts/models/tokens.txt) | 分词器 / 字典，必须配套 |

仓库提交：`ecd09194a4ed417f6466dedebcd85192118a7bc8`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/tree/ecd09194a4ed417f6466dedebcd85192118a7bc8)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/tree/ecd09194a4ed417f6466dedebcd85192118a7bc8)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/README.md)。
- [主要程序入口：ax_spoken_communication_demo.py](https://huggingface.co/AXERA-TECH/Spoken-Communication.axera/blob/ecd09194a4ed417f6466dedebcd85192118a7bc8/ax_spoken_communication_demo.py)。

返回[完整模型目录](../catalog.mdx)。
