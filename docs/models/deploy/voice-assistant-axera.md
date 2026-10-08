---
title: "Voice_Assistant.AXERA 部署指南"
sidebar_label: "Voice_Assistant.AXERA"
description: "Voice_Assistant.AXERA 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Voice_Assistant.AXERA 部署指南

Voice_Assistant.AXERA 用于离线语音检测、识别、问答与合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 获取适配运行包

下载 [离线语音助手运行包](../../../static/examples/voice-assistant-20261002.tar.gz)，保存为 `voice-assistant-20261002.tar.gz`，复制到开发板的 `~/edgeaccel/apps` 目录。包内包含程序、匹配运行库、固定模型清单和两条输入音频。

在开发板执行：

```bash
cd ~/edgeaccel/apps
echo "4ce7d92e99c7b7d5c90cd5491f9ee3988c82b35af9a05c0e4fbcccbce47be9a6  voice-assistant-20261002.tar.gz" | sha256sum -c -
tar -xzf voice-assistant-20261002.tar.gz
cd voice-assistant
```

本配置使用 AX-FSMN 检测语音、FireRedASR2 识别问题、Qwen3.5-0.8B 生成回答、MeloTTS 合成语音。适用环境为 RK3576、Linux aarch64、Python 3.12、AXCL 3.16.0 与 AX8850 16GB M.2 算力卡。8GB 配置尚未完成回归。

## 安装 Python 依赖

在开发板上确认 `axcl-smi` 能识别算力卡，保持风扇运行。安装目录预留至少 5GB 可用空间；模型文件约 2.56GB，另需程序、Python 依赖和生成音频空间。

在本目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。包内 PyAXEngine wheel 与本次测试版本一致。系统须已安装 AXCL 驱动及 `libsndfile1`。

## 下载模型

```bash
.venv/bin/python prepare.py
.venv/bin/python prepare.py --check
```

程序从固定提交下载模型并校验 SHA256。末尾显示 `All package and model files verified.` 后继续。如已有同目录布局的模型，可用 `--reuse /已有安装目录` 校验并复用文件。

需要代理时，在下载前按实际代理地址设置 `http_proxy` 和 `https_proxy`。下载完成后推理不需要外网连接。

## 运行音频问答

在开发板第一个终端启动应用：

```bash
sudo .venv/bin/python run.py --port 8008
```

在第二个终端进入同一目录，发送两条配套样本：

```bash
.venv/bin/python send_wav.py --input samples/Q1.wav samples/Q3.wav --output output-demo
```

首次加载模型需要等待。完成后，`output-demo/result.json` 保存识别文本和模型回答，`answer-*.wav` 保存实际生成的44.1kHz语音片段。输出目录不能预先存在；再次运行时更换目录名。文件问答结束后会停止模型服务，网页入口仍保留。退出应用时在第一个终端按 Ctrl+C。

使用自己的输入时，提供0至10秒、16kHz、单声道、PCM16 WAV 文件。一次请求只提出一个简短问题。回复为模型生成内容，需要自行核实。

## 打开网页

在电脑终端建立端口转发，将 `开发板IP` 替换为实际地址：

```bash
ssh -L 8008:127.0.0.1:8008 baiwen@开发板IP
```

浏览器访问 `http://127.0.0.1:8008`，点击“一键启动服务”，确认三个模型服务就绪后再开始对话。麦克风需浏览器授权；当前实测使用音频文件经WebSocket输入，物理麦克风与扬声器效果需结合现场设备确认。

本运行包只列出已配置的离线组合。仓库其他组合使用不同模型与运行库，不能直接替换权重路径。

## 核对版本与输出

`deployment-manifest.json` 包含程序、运行库和模型的逐文件SHA256及固定来源；`runtime/sources` 保留源码版本和适配补丁。两条配套输入来自 `AXERA-TECH/Spoken-Communication.axera@ecd09194a4ed417f6466dedebcd85192118a7bc8`，由原始24kHz样本转为16kHz PCM16。

语音检测、识别、文本模型和语音解码器使用算力卡；音频预处理、文本前端和Melo ONNX编码器使用RK3576主机CPU。默认未启用Qwen图像输入，不能据此认定视觉分支通过。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已用独立运行包完成两轮语音检测→FireRed识别→Qwen3.5回答→Melo合成，下面展示本次实际文字与音频。

**连续语音问答 1**

**示例 1：输入**

```text
人工智能和人类智能最本质的区别是什么
```

**实际回复**

```text
人工智能和人类智能的最本质区别在于，人工智能是**计算模型**（由代码和算法驱动），它擅长处理数据、进行逻辑推理、执行任务和优化结果，但这只是其能力的一部分；而人类智能是**复杂意识与情感**，它涉及自我意识、创造性思维、伦理判断、共情能力以及真正的“理解”与“意图”，这是机器无法完全模拟的。
```

识别文本与样本问题一致，已返回完整语音。保留模型原始回答，未进行人工听审及内容质量验收。

| 输出项 | 实测结果 |
| --- | --- |
| 语音片段 | 7 |
| 合并音频时长 | 22.468 秒 |
| 音频格式 | 44.1kHz / 单声道 / PCM16 |

输入问题音频

<audio controls preload="metadata" src="/validation/effects/voice-assistant-axera-20261002/input-1.wav" aria-label="输入问题音频"></audio>

[下载音频](../../../static/validation/effects/voice-assistant-axera-20261002/input-1.wav)

本次生成的回答音频

<audio controls preload="metadata" src="/validation/effects/voice-assistant-axera-20261002/answer-1.wav" aria-label="本次生成的回答音频"></audio>

[下载音频](../../../static/validation/effects/voice-assistant-axera-20261002/answer-1.wav)

**连续语音问答 2**

**示例 1：输入**

```text
人工智能最终会统治人类吗
```

**实际回复**

```text
不会。人工智能目前只是人类智能的辅助工具，它无法替代人类的情感、道德判断、创造力以及应对复杂伦理挑战的能力。人类在人工智能发展过程中始终扮演着引导者、监督者和伦理定义者的角色。
```

识别文本与样本问题一致，已返回完整语音。回答为模型生成内容，未作为事实结论或质量验收结果；其中“不会”等未来判断过于确定。

| 输出项 | 实测结果 |
| --- | --- |
| 语音片段 | 4 |
| 合并音频时长 | 14.674 秒 |
| 音频格式 | 44.1kHz / 单声道 / PCM16 |

输入问题音频

<audio controls preload="metadata" src="/validation/effects/voice-assistant-axera-20261002/input-2.wav" aria-label="输入问题音频"></audio>

[下载音频](../../../static/validation/effects/voice-assistant-axera-20261002/input-2.wav)

本次生成的回答音频

<audio controls preload="metadata" src="/validation/effects/voice-assistant-axera-20261002/answer-2.wav" aria-label="本次生成的回答音频"></audio>

[下载音频](../../../static/validation/effects/voice-assistant-axera-20261002/answer-2.wav)

**使用时注意：**

- 回答内容与语音自然度尚未完成质量验收；第二问的确定性未来判断不能作为事实。
- 本页运行包固定为AX-FSMN、FireRed、Qwen3.5-0.8B和Melo组合。其他配置需要对应模型及运行库。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`1af3f0baa89d48a11e0177445d15290892ce1a07`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 固件 | V3.16.0_20260729180218 / V3.16.0 |
| 应用 | Voice_Assistant.AXERA 1af3f0baa89d + AXCL适配包 |
| 运行方式 | Python3.12独立环境 / PyAXEngine0.1.3 / AXCL C API / AX-LLM8501c22b |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 本次完整链路 | 28个AXModel实际执行 | 1个VAD、1个FireRed、25个Qwen文本权重、1个Melo解码器；Qwen视觉权重仅加载，未验证视觉输入。 |
| 输入覆盖 | 2条官方问题音频 | 同一会话连续问答；文件PCM经WebSocket输入。 |
| 仓库组件覆盖 | 10份不同权重 | 原仓库15个路径对应10份权重，均有组件执行记录；重复路径按相同字节映射，不等于全部应用入口通过。 |

适用范围：

- 本次通过文件音频验证，未实测物理麦克风和扬声器。
- 合并语音按接收顺序拼接，不还原网络播放间隔；未将测试进程时长作为推理延迟。
- 仅在16GB算力卡验证，8GB和其他主机平台需要单独回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`models/Vad/ax_meeting_transc_demo.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/Vad/ax_meeting_transc_demo.py) | Python 程序 / 前后处理 |
| [`models/Vad/utils/infer_utils.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/Vad/utils/infer_utils.py) | Python 程序 / 前后处理 |
| [`models/SenseVoiceSmall/ax650/model-10-seconds.axmodel`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/SenseVoiceSmall/ax650/model-10-seconds.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/SenseVoiceSmall/ax650/model-5-seconds.axmodel`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/SenseVoiceSmall/ax650/model-5-seconds.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/zipvoice/zipvoice/zipvoice_distill_ax650/decoder_part0.axmodel`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/zipvoice/zipvoice_distill_ax650/decoder_part0.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/zipvoice/zipvoice/zipvoice_distill_ax650/decoder_part1.axmodel`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/zipvoice/zipvoice_distill_ax650/decoder_part1.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/zipvoice/zipvoice/zipvoice_distill_ax650/decoder_part2.axmodel`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/zipvoice/zipvoice_distill_ax650/decoder_part2.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/config.json) | 运行配置 |
| [`models/SenseVoiceSmall/tokens.txt`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/SenseVoiceSmall/tokens.txt) | 分词器 / 字典，必须配套 |
| [`models/zipvoice/resources/zipvoice_hf/zipvoice/tokens.txt`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/resources/zipvoice_hf/zipvoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`models/zipvoice/scripts/common_infer.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/scripts/common_infer.py) | Python 程序 / 前后处理 |
| [`models/zipvoice/scripts/local_tokenizer.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/scripts/local_tokenizer.py) | 旧版分词服务入口 |
| [`models/zipvoice/zipvoice/resources/zipvoice_hf/zipvoice/tokens.txt`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/zipvoice/resources/zipvoice_hf/zipvoice/tokens.txt) | 分词器 / 字典，必须配套 |
| [`models/zipvoice/zipvoice/zipvoice_distill_ax650/runtime_config.json`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/zipvoice/zipvoice_distill_ax650/runtime_config.json) | 运行配置 |

仓库提交：`1af3f0baa89d48a11e0177445d15290892ce1a07`。仓库中的 15 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/tree/1af3f0baa89d48a11e0177445d15290892ce1a07)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/tree/1af3f0baa89d48a11e0177445d15290892ce1a07)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/README.md)。
- [主要程序入口：models/Vad/ax_meeting_transc_demo.py](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/Vad/ax_meeting_transc_demo.py)。
- [配套项目：ABexit/ASR-LLM-TTS](https://github.com/ABexit/ASR-LLM-TTS)。
- [配套项目：AXERA-TECH/pyaxengine](https://github.com/AXERA-TECH/pyaxengine)。
- [配套项目：HumanAIGC-Engineering/OpenAvatarChat](https://github.com/HumanAIGC-Engineering/OpenAvatarChat)。

返回[完整模型目录](../catalog.mdx)。
