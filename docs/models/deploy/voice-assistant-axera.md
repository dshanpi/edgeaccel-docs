---
title: "Voice_Assistant.AXERA 部署指南"
sidebar_label: "Voice_Assistant.AXERA"
description: "Voice_Assistant.AXERA 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Voice_Assistant.AXERA 部署指南

Voice_Assistant.AXERA 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`models/Vad/ax_meeting_transc_demo.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/Vad/ax_meeting_transc_demo.py) | 仅文件清单已确认，调用方式待核对 |
| [`models/Vad/utils/infer_utils.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/Vad/utils/infer_utils.py) | 仅文件清单已确认，调用方式待核对 |
| [`models/zipvoice/scripts/common_infer.py`](https://huggingface.co/AXERA-TECH/Voice_Assistant.AXERA/blob/1af3f0baa89d48a11e0177445d15290892ce1a07/models/zipvoice/scripts/common_infer.py) | 仅文件清单已确认，调用方式待核对 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`models/Vad/wav/002.mp3`、`models/Vad/wav/vad_example.wav`、`models/zipvoice/assets/moss_prompts/en_4_4p5s.wav`、`models/zipvoice/assets/moss_prompts/zh_1_4p5s.wav`、`models/zipvoice/zipvoice/assets/moss_prompts/en_4_4p5s.wav`、`models/zipvoice/zipvoice/assets/moss_prompts/zh_1_4p5s.wav`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。本页列出的目标路径包括 `models/SenseVoiceSmall/ax650/model-10-seconds.axmodel`、`models/SenseVoiceSmall/ax650/model-5-seconds.axmodel`。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。分别完成各子模型后，才能连接完整应用。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/Voice_Assistant.AXERA` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/voice-assistant-axera/1af3f0baa89d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Voice_Assistant.AXERA \
  --revision 1af3f0baa89d48a11e0177445d15290892ce1a07 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 分别验证每个模型阶段的真实输入、输出和后端，再启动完整应用。
- 检查服务地址、错误传播、超时与资源释放；某个子模型运行不代表整条链路完成。

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
