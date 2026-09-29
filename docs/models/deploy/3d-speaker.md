---
title: "3D-Speaker 部署指南"
sidebar_label: "3D-Speaker"
description: "3D-Speaker 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# 3D-Speaker 部署指南

3D-Speaker 用于声纹特征提取与说话人比对。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/3D-Speaker` 的固定版本。下面下载本页选用的 11 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/3d-speaker/19be2b978d86
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/3D-Speaker \
  "ax650/ecapa-tdnn.axmodel" \
  "ecapa-tdnn.onnx" \
  "ax650/res2netv2.axmodel" \
  "res2netv2.onnx" \
  "run_axmodel_ecapa_tdnn.py" \
  "run_axmodel_res2netv2.py" \
  "run_onnx_ecapa_tdnn.py" \
  "run_onnx_res2netv2.py" \
  "wavs/speaker1_a_cn_16k.wav" \
  "wavs/speaker1_b_cn_16k.wav" \
  "wavs/speaker2_a_cn_16k.wav" \
  --revision 19be2b978d867ad8a2f3f2acf9bd91aa949d8b91 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装音频依赖与运行脚本

本例比较 ECAPA-TDNN 和 ERes2NetV2 两套模型。音频前处理在 RK3576 上执行，`.axmodel` 推理明确使用 AXCL；CPU ONNX 仅用于核对量化前后的向量。

在已安装 PyAXEngine 的 Python 环境执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install numpy==1.26.4 torch==2.5.1 torchaudio==2.5.1 \
  onnxruntime==1.20.1 soundfile==0.14.0
```

下载本站的 [speaker_compare.py](../../../static/examples/speaker_compare.py)，通过 scp 或 SFTP 将它复制到 Linux 主机的 `$MODEL_DIR/speaker_compare.py`。

该脚本采用配套 [FBank 前端参数](https://github.com/modelscope/3D-Speaker/blob/065629c313eaf1a01c65c640c46d77e61e9607b4/speakerlab/process/processor.py)：16 kHz、80 维、dither=0、均值归一化。超过模型帧数时截取前部；不足时仅在尾部补零，保留已有语音。它同时解决原始入口缺少 `processor.py`、板端 provider 和短音频处理问题。

## 提取声纹并比较录音

在模型根目录执行：

```bash
cd "$MODEL_DIR"
test -s speaker_compare.py
set -o pipefail
python speaker_compare.py --model-dir . --reference \
  --out speaker-result.json 2>&1 | tee run.log
```

`--reference` 使用本包同提交的两个 `.onnx` 模型做 CPU 对照。只需要卡端声纹时可省略该参数；示例音频和 `.axmodel` 仍须完整保留。

运行后检查日志中的实际 provider 为 `AXCLRTExecutionProvider`，并查看 `speaker-result.json`：

- `sameSpeaker`：speaker1 的两段录音之间的余弦相似度。
- `differentSpeaker`：speaker1 与 speaker2 录音之间的余弦相似度。
- `onnxComparison.embeddingCosine`：每段录音的卡端向量与 CPU ONNX 向量之间的相似度。

先比较本页样例的排序，再使用自己的录音标定业务阈值。相似度不是百分比准确率，也不能直接生成语音转写或说话人时间轴。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

两套声纹模型均通过 AXCL 完成三段录音的特征提取，按文件分组的同人分数均高于异人分数。ERes2NetV2 的卡端与 CPU ONNX 向量余弦约为 0.993–0.994；ECAPA-TDNN 仅约 0.36–0.41，仍存在明显差异。

下面使用仓库提供的三段录音；“同一人”和“不同人”按样例文件的分组解释，未独立核验说话人身份。

**输入 1：speaker1_a_cn_16k.wav · 3.715 秒**

<audio controls preload="metadata" src="/validation/effects/3d-speaker/inputs/speaker1_a_cn_16k.wav" aria-label="3D-Speaker 输入 1"></audio>

[下载音频](../../../static/validation/effects/3d-speaker/inputs/speaker1_a_cn_16k.wav)

**输入 2：speaker1_b_cn_16k.wav · 4.907 秒**

<audio controls preload="metadata" src="/validation/effects/3d-speaker/inputs/speaker1_b_cn_16k.wav" aria-label="3D-Speaker 输入 2"></audio>

[下载音频](../../../static/validation/effects/3d-speaker/inputs/speaker1_b_cn_16k.wav)

**输入 3：speaker2_a_cn_16k.wav · 5.312 秒**

<audio controls preload="metadata" src="/validation/effects/3d-speaker/inputs/speaker2_a_cn_16k.wav" aria-label="3D-Speaker 输入 3"></audio>

[下载音频](../../../static/validation/effects/3d-speaker/inputs/speaker2_a_cn_16k.wav)

**卡端实际声纹分数**

| 模型 | 输出维度 | 同组录音相似度 | 不同组录音相似度 |
| --- | --- | --- | --- |
| ecapa-tdnn | 192 | 0.755322 | 0.697590 |
| res2netv2 | 192 | 0.713553 | 0.078779 |

**使用相同前处理与配套 CPU ONNX 对照**

| 模型 | AXCL / ONNX 向量相似度（3 段） | ONNX 同组 / 不同组 |
| --- | --- | --- |
| ecapa-tdnn | 0.395690 / 0.408604 / 0.363399 | 0.603435 / 0.127503 |
| res2netv2 | 0.994452 / 0.993113 / 0.992998 | 0.729488 / 0.069311 |

余弦分数越大表示向量越接近，不是准确率。卡端与 ONNX 的差异按实际值保留，不能把两套模型的分数直接套用到同一个业务阈值。

**使用时注意：**

- ERes2NetV2 修正为卡端 [1,360,80,1]、CPU ONNX [1,1,360,80]；两者使用相同音频特征，仅转换布局。
- ECAPA-TDNN 虽完成推理，但与 ONNX 差异较大；未确认量化精度或业务识别阈值。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`19be2b978d867ad8a2f3f2acf9bd91aa949d8b91`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |
| 音频后端与依赖 | PyAXEngine 0.1.3，AXCLRTExecutionProvider；Torch / TorchAudio 2.5.1，NumPy 1.26.4，ONNX Runtime 1.20.1 |
| 音频测试方式 | 三个应用串行使用设备 0；文件解码、FBank、文本处理与 ONNX 编码在主机执行 |

适用范围：

- ERes2NetV2 修正为卡端 [1,360,80,1]、CPU ONNX [1,1,360,80]；两者使用相同音频特征，仅转换布局。
- ECAPA-TDNN 虽完成推理，但与 ONNX 差异较大；未确认量化精度或业务识别阈值。
- 样例说话人分组依据仓库文件名，未独立核验身份；三段录音不代表真实场景中的识别率。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axmodel_ecapa_tdnn.py`](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/run_axmodel_ecapa_tdnn.py) | Python 程序 / 前后处理 |
| [`ax650/ecapa-tdnn.axmodel`](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/ax650/ecapa-tdnn.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`wavs/speaker1_a_cn_16k.wav`](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/wavs/speaker1_a_cn_16k.wav) | 示例输入 |
| [`wavs/speaker1_b_cn_16k.wav`](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/wavs/speaker1_b_cn_16k.wav) | 示例输入 |
| [`wavs/speaker2_a_cn_16k.wav`](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/wavs/speaker2_a_cn_16k.wav) | 示例输入 |

仓库提交：`19be2b978d867ad8a2f3f2acf9bd91aa949d8b91`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/3D-Speaker/tree/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页同时比较 ECAPA-TDNN 与 ERes2NetV2，使用各自的输入布局；二者的分数和业务阈值不能直接互换。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/3D-Speaker/tree/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/README.md)。
- [主要程序入口：run_axmodel_ecapa_tdnn.py](https://huggingface.co/AXERA-TECH/3D-Speaker/blob/19be2b978d867ad8a2f3f2acf9bd91aa949d8b91/run_axmodel_ecapa_tdnn.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/3D-Speaker)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
