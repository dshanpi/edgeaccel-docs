---
title: "campplus.AXERA 部署指南"
sidebar_label: "campplus.AXERA"
description: "campplus.AXERA 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# campplus.AXERA 部署指南

campplus.AXERA 用于说话人识别与分段。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/campplus.AXERA` 的固定版本。下面下载本页选用的 16 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/campplus-axera/906ada2445ac
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/campplus.AXERA \
  ".gitignore" \
  "README.md" \
  "configuration.json" \
  "models/campplus.axmodel" \
  "models/model_meta.json" \
  "python/README.md" \
  "python/campplus_sdk/__init__.py" \
  "python/campplus_sdk/clustering.py" \
  "python/campplus_sdk/inference.py" \
  "python/example.py" \
  "python/requirements.txt" \
  "requirements.txt" \
  "run_ax650.sh" \
  "samples/speaker1_a_cn_16k.wav" \
  "samples/speaker1_b_cn_16k.wav" \
  "samples/speaker2_a_cn_16k.wav" \
  --revision 906ada2445acad77cddd465a312ee8569d818ba6 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，并使用以下依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchaudio==2.5.1' 'soundfile==0.13.1'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本例通过 AXCL 调用 M.2 算力卡，使用官方 Python 特征提取流程。模型目录应保留 `models/`、`python/campplus_sdk/` 和 `samples/`。

## 提取特征并比较音频

下载 [CAM++ 算力卡示例](../../../static/examples/campplus_card.py)，保存为 `~/edgeaccel/campplus_card.py`。沿用前面下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/campplus_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/campplus-01
```

输出目录须尚不存在。程序对三段官方音频分别执行单次特征提取和滑窗提取，再重复第一段；最后计算三组余弦相似度。

单次提取使用前 360 帧特征，约对应开头 3.6 秒。短输入按官方流程循环补齐。滑窗模式以 1.5 秒为窗口、0.75 秒为步长，每个窗口单独补齐后推理，实际区间写入结果。

## 查看相似度和分块结果

打开输出目录中的 `deployment-result.json`：

- `pairs`：三组实际余弦相似度。
- `samples`：输入音频、单次或滑窗模式、窗口区间、输出维度及耗时。
- `sessions`：实际 AXCL 调用次数、模型输入输出校验值。

`raw-*.npz` 保存特征与 192 维向量，便于本地复核；`input-*.wav` 是实际输入。`processSeconds` 包含特征处理、传输、推理和记录校验值的时间，不含音频加载和结果保存。

相似度越高表示这两段样例的特征越接近。它不是概率，也没有通用的同人判定阈值；需要使用自己的有标注数据评估误接受率和误拒绝率。本入口不执行说话人聚类或身份检索。

## 比较自己的两段音频

准备 16 kHz 单声道 WAV，每段建议 1.5–60 秒：

```bash
python ~/edgeaccel/campplus_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/a.wav \
  --audio ~/Music/b.wav \
  --output ~/edgeaccel/results/campplus-custom-01
```

程序依次处理两段音频并重复第一段；使用新的输出目录保留每次结果。长录音应检查滑窗区间，不要把单次提取结果当作整段音频的完整表示。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已通过 AXCL 完成三段音频的特征提取、滑窗处理与重复运行；下方展示原始音频、两两相似度和实际耗时。

**三段官方音频的相似度**

以下标签来自官方样例文件名。speaker1_a 与 speaker1_b 的分数高于两组跨标签比较；这不是概率或身份判定阈值。

| 音频 A | 音频 B | 实际余弦相似度 |
| --- | --- | --- |
| speaker1_a_cn_16k.wav | speaker1_b_cn_16k.wav | 0.666755 |
| speaker1_a_cn_16k.wav | speaker2_a_cn_16k.wav | 0.067015 |
| speaker1_b_cn_16k.wav | speaker2_a_cn_16k.wav | 0.039977 |

官方样例：speaker1_a_cn_16k.wav

<audio controls preload="metadata" src="/validation/effects/campplus-axera-20260928/input-1.wav" aria-label="官方样例：speaker1_a_cn_16k.wav"></audio>

[下载音频](../../../static/validation/effects/campplus-axera-20260928/input-1.wav)

官方样例：speaker1_b_cn_16k.wav

<audio controls preload="metadata" src="/validation/effects/campplus-axera-20260928/input-2.wav" aria-label="官方样例：speaker1_b_cn_16k.wav"></audio>

[下载音频](../../../static/validation/effects/campplus-axera-20260928/input-2.wav)

官方样例：speaker2_a_cn_16k.wav

<audio controls preload="metadata" src="/validation/effects/campplus-axera-20260928/input-3.wav" aria-label="官方样例：speaker2_a_cn_16k.wav"></audio>

[下载音频](../../../static/validation/effects/campplus-axera-20260928/input-3.wav)

**单次与滑窗提取**

单次提取使用前360帧；滑窗模式保留各窗口的192维结果。首次调用耗时明显较长，原值保留；两种模式重复第一段音频，原始特征与输出向量均完全一致。

| 输入 | 模式 | 输出维度 | 处理耗时 |
| --- | --- | --- | --- |
| speaker1_a_cn_16k.wav | 单次 | 1 × 192 | 2.901679 s |
| speaker1_b_cn_16k.wav | 单次 | 1 × 192 | 0.036354 s |
| speaker2_a_cn_16k.wav | 单次 | 1 × 192 | 0.035154 s |
| speaker1_a_cn_16k.wav（重复） | 单次 | 1 × 192 | 0.029303 s |
| speaker1_a_cn_16k.wav | 滑窗 | 4 × 192 | 0.103515 s |
| speaker1_b_cn_16k.wav | 滑窗 | 6 × 192 | 0.143437 s |
| speaker2_a_cn_16k.wav | 滑窗 | 7 × 192 | 0.174111 s |
| speaker1_a_cn_16k.wav（重复） | 滑窗 | 4 × 192 | 0.100875 s |

**使用时注意：**

- 只有三段官方音频，没有CPU浮点参考、独立验证集、EER或业务阈值标定。
- 单次提取只使用前360帧；本页同时验证滑窗特征，但未执行说话人聚类、身份检索或会议分段效果。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`906ada2445acad77cddd465a312ee8569d818ba6`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际模型调用 | 25次 | 4次单次提取与21个滑窗；包括两种模式下的重复请求。 |
| AXCL调用平均耗时 | 4.960 ms | 25次实际session.run，包含AXCL传输，不含特征提取及模型加载。 |
| 首轮 / 重复提取 | 2.902 s / 0.029 s | 同一段speaker1_a，包含Python特征提取与记录；不将首次开销混同稳定状态。 |

适用范围：

- 只有三段官方音频，没有CPU浮点参考、独立验证集、EER或业务阈值标定。
- 单次提取只使用前360帧；本页同时验证滑窗特征，但未执行说话人聚类、身份检索或会议分段效果。
- 真实8GB容量、噪声、长音频和连续运行仍待验证。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/example.py`](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/python/example.py) | Python 程序 / 前后处理 |
| [`models/campplus.axmodel`](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/models/campplus.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/config.json) | 运行配置 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/python/requirements.txt) | Python 依赖清单 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/requirements.txt) | Python 依赖清单 |
| [`run_ax650.sh`](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/run_ax650.sh) | 启动或构建脚本 |

仓库提交：`906ada2445acad77cddd465a312ee8569d818ba6`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/campplus.AXERA/tree/906ada2445acad77cddd465a312ee8569d818ba6)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 先用两段单说话人音频检查 embedding 相似度，再验证长音频中的说话人分段。不要把余弦相似度直接当成身份概率。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/campplus.AXERA/tree/906ada2445acad77cddd465a312ee8569d818ba6)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/README.md)。
- [主要程序入口：python/example.py](https://huggingface.co/AXERA-TECH/campplus.AXERA/blob/906ada2445acad77cddd465a312ee8569d818ba6/python/example.py)。

返回[完整模型目录](../catalog.mdx)。
