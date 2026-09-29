---
title: "Sherpa-ONNX-KWS.AXERA 部署指南"
sidebar_label: "Sherpa-ONNX-KWS.AXERA"
description: "Sherpa-ONNX-KWS.AXERA 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Sherpa-ONNX-KWS.AXERA 部署指南

Sherpa-ONNX-KWS.AXERA 用于语音活动或唤醒检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Sherpa-ONNX-KWS.AXERA` 的固定版本。下面下载本页选用的 30 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/sherpa-onnx-kws-axera/7420e0d67d20
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Sherpa-ONNX-KWS.AXERA \
  "README.md" \
  "audio/sherpa/en_0.wav" \
  "audio/sherpa/en_1.wav" \
  "audio/sherpa/zh_0.wav" \
  "audio/sherpa/zh_1.wav" \
  "audio/sherpa/zh_2.wav" \
  "audio/sherpa/zh_3.wav" \
  "audio/sherpa/zh_4.wav" \
  "audio/sherpa/zh_5.wav" \
  "audio/sherpa/zh_6.wav" \
  "config.json" \
  "config/keywords.txt" \
  "config/keywords_raw.txt" \
  "config/sherpa_decoder_initial.bin" \
  "config/sherpa_decoder_initial.npy" \
  "config/tokens.txt" \
  "manifest.json" \
  "models/650/sherpa__decoder-epoch-13-avg-2-chunk-16-left-64.axmodel" \
  "models/650/sherpa__decoder-epoch-13-avg-2-chunk-8-left-64.axmodel" \
  "models/650/sherpa__encoder-epoch-13-avg-2-chunk-16-left-64.axmodel" \
  "models/650/sherpa__encoder-epoch-13-avg-2-chunk-8-left-64.axmodel" \
  "models/650/sherpa__joiner-epoch-13-avg-2-chunk-16-left-64.axmodel" \
  "models/650/sherpa__joiner-epoch-13-avg-2-chunk-8-left-64.axmodel" \
  "reference/local_inference_results.json" \
  "requirements.txt" \
  "scripts/generate_keyword_tokens.py" \
  "scripts/runtime.py" \
  "scripts/sherpa_kws_ax.py" \
  "scripts/sherpa_kws_ax630c.py" \
  "scripts/sherpa_kws_ax650.py" \
  --revision 7420e0d67d20c246b0cd58b5255a0f89d0e4c42e \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装 Python 依赖

本页使用官方 Python 单路径关键词检测流程，在 RK3576 + AX8850 16GB M.2 算力卡上对比 `chunk 8`、`chunk 16` 两种配置。每种配置均运行编码器、解码器和连接器三个模型，主机负责音频特征提取及关键词匹配。

完成 [Python 接口](../../usage/python.md) 配置后，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'kaldi-native-fbank==1.22.3' 'pypinyin==0.55.0'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本页使用 `models/650` 中的模型，经 AXCL 运行；仓库中的原生 AX650 二进制使用不同运行接口，不要直接作为 M.2 算力卡程序启动。

## 运行两种分块配置

完成上方固定版本下载后，保留 `$MODEL_DIR`。下载 [关键词检测算力卡示例](../../../static/examples/sherpa_kws_card.py)，保存为 `~/edgeaccel/sherpa_kws_card.py`，串行执行：

```bash
python ~/edgeaccel/sherpa_kws_card.py \
  --model-dir "$MODEL_DIR" --chunk-size 8 \
  --output ~/edgeaccel/results/sherpa-kws-chunk8-01

python ~/edgeaccel/sherpa_kws_card.py \
  --model-dir "$MODEL_DIR" --chunk-size 16 \
  --output ~/edgeaccel/results/sherpa-kws-chunk16-01
```

输出目录须尚不存在。每次运行处理仓库中的 9 段语音、重复 `zh_0.wav`，再处理两秒静音。输入均为 16 kHz、单声道、PCM16 WAV；按官方流程补入 0.8 秒静音以推进解码。

运行结束时退出码为 0，结果目录中的 `deployment-result.json` 应包含 `completed: true`。该字段表示整套样例执行完成，检测是否符合预期仍须查看每段的 `detections`、`detection_match` 和下方结果表。

## 查看关键词检测结果

`samples[].result.detections` 保存检测到的关键词。空数组 `[]` 表示没有触发。本次两种配置都能触发英文 `LIGHT_UP`、`LOVELY_CHILD` 及部分中文关键词，但 `zh_0`、`zh_1`、`zh_2` 均未触发。

`reference_detections` 来自仓库固定版本的历史推理记录，`detection_match` 表示本次输出是否与其相同。这份参考不是人工标注的完整测试集，不能据此计算实际业务召回率。

本次 chunk 8 的 9 段语音与参考记录一致；chunk 16 有两段不同：`en_0` 新触发 `LIGHT_UP`，`zh_5` 只触发“落实”，没有触发参考记录中的“周望军”。下方同时展示本次与参考结果，差异保留为后续质量核对项。

重复 `zh_0.wav` 的每次模型输入输出校验值一致，两秒静音没有触发。仅此短静音样例不能证明长期无误唤醒。完整文件处理时间包含特征提取、关键词解码及原始证据压缩写入；单次 AXCL 调用时间另列。

## 配置中文关键词

关键词由 `$MODEL_DIR/config/keywords.txt` 定义，模型权重无需重新导出。先备份，再追加新词：

```bash
cd "$MODEL_DIR"
cp -n config/keywords.txt config/keywords.txt.original
python scripts/generate_keyword_tokens.py --text '打开台灯' --threshold 0.25 --append
```

工具检查拼音 token 是否存在于词表中；遇到 `tokens not present` 时，先更换或核对关键词。成功时新增行包含拼音、阈值和 `@打开台灯` 标签。已存在的完全相同行不会重复追加。

修改关键词后，用对应录音重新验证命中和误触发。示例的 `jobs` 列表可指定输入录音；如修改为自定义样例，同时调整固定 9 个文件的数量检查，并为每次运行选择新输出目录。原仓库参考结果不适用于新录音或新关键词，应以自己的标注为准。

当前 Python 示例采用单路径解码，`max_active_paths = 1`。官方 C++ 的多路径搜索是另一套流程，本页没有验证其 16 路或 32 路搜索效果；不要将两者的参数或性能直接互换。

## 判断是否适合业务

先用目标关键词、相似发音、远场与噪声录音检查漏检，再用持续背景录音统计单位时间误触发次数。阈值调整后须同时检查两项。本次展示用于复现固定输入的部署效果，尚未完成完整唤醒率、误唤醒率、长时间运行或真实 8GB 卡容量验收。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两种分块均完成AXCL关键词检测流程；下方列出九段录音的真实输出、未触发项及chunk 16的两项参考差异。

**九段录音：两种分块的实际检测结果**

chunk 8 与仓库历史推理记录9/9相同，chunk 16为7/9；差异见最后一列。三个中文样例均未触发，不能据此宣称全部唤醒词验证通过。参考记录不是人工标注的业务评测集。

| 录音 | 时长 | chunk 8 | chunk 16 | 与仓库参考对照 |
| --- | --- | --- | --- | --- |
| en_0.wav | 6.625 s | LIGHT_UP | LIGHT_UP | chunk 16 参考：未触发 |
| en_1.wav | 16.715 s | LOVELY_CHILD | LOVELY_CHILD | 两者均与参考相同 |
| zh_0.wav | 5.612 s | 未触发 | 未触发 | 两者均与参考相同 |
| zh_1.wav | 5.153 s | 未触发 | 未触发 | 两者均与参考相同 |
| zh_2.wav | 4.524 s | 未触发 | 未触发 | 两者均与参考相同 |
| zh_3.wav | 8.030 s | 法国 | 法国 | 两者均与参考相同 |
| zh_4.wav | 4.599 s | 蒋友伯、女儿 | 蒋友伯、女儿 | 两者均与参考相同 |
| zh_5.wav | 4.153 s | 周望军、落实 | 落实 | chunk 16 参考：周望军、落实 |
| zh_6.wav | 3.546 s | 朱丽楠 | 朱丽楠 | 两者均与参考相同 |

**听取对应输入录音**

以下为本次实际处理的九段官方录音，未变速、未裁剪。模型输出为上表关键词列表，不生成新的音频。

en_0.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/en_0.wav" aria-label="en_0.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/en_0.wav)

en_1.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/en_1.wav" aria-label="en_1.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/en_1.wav)

zh_0.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_0.wav" aria-label="zh_0.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_0.wav)

zh_1.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_1.wav" aria-label="zh_1.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_1.wav)

zh_2.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_2.wav" aria-label="zh_2.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_2.wav)

zh_3.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_3.wav" aria-label="zh_3.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_3.wav)

zh_4.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_4.wav" aria-label="zh_4.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_4.wav)

zh_5.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_5.wav" aria-label="zh_5.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_5.wav)

zh_6.wav：官方输入录音，对应上表同名行

<audio controls preload="metadata" src="/validation/effects/sherpa-onnx-kws-axera-20260928/zh_6.wav" aria-label="zh_6.wav：官方输入录音，对应上表同名行"></audio>

[下载音频](../../../static/validation/effects/sherpa-onnx-kws-axera-20260928/zh_6.wav)

**重复、静音与处理耗时**

两种配置下，重复zh_0的全部模型输入输出逐调用一致；两秒静音均未触发。下表为完整文件处理时间，含特征提取、解码及证据压缩写入，不含模型加载；重复时复用相同证据文件，不能用首轮与重复耗时直接比较推理速度。

| 输入 | 音频 / s | chunk 8 / s | chunk 16 / s |
| --- | --- | --- | --- |
| en_0.wav | 6.625 | 5.420487 | 3.364799 |
| en_1.wav | 16.715 | 11.949360 | 7.624649 |
| zh_0.wav | 5.612 | 4.213262 | 2.690636 |
| zh_1.wav | 5.153 | 3.802375 | 2.699310 |
| zh_2.wav | 4.524 | 3.298798 | 2.276793 |
| zh_3.wav | 8.030 | 5.646403 | 3.849669 |
| zh_4.wav | 4.599 | 3.282382 | 2.269801 |
| zh_5.wav | 4.153 | 2.914965 | 2.019956 |
| zh_6.wav | 3.546 | 2.736014 | 1.920967 |
| zh_0-repeat.wav | 5.612 | 2.475317 | 1.521292 |
| silence.wav | 2.000 | 1.372439 | 0.991083 |

**模型实际调用统计**

六个权重文件分别实际调用；其中两个分块版本的decoder、joiner文件内容相同，共四组不同权重。AXCL时间包含调用传输，不含CPU特征提取、关键词搜索或证据写入。

| chunk | 组件 | 实际调用 | 平均 / ms |
| --- | --- | --- | --- |
| 8 | encoder | 457 | 39.048851 |
| 8 | decoder | 73 | 2.137177 |
| 8 | joiner | 1828 | 2.772384 |
| 16 | encoder | 227 | 44.124229 |
| 16 | decoder | 69 | 2.258492 |
| 16 | joiner | 1816 | 2.835268 |

**使用时注意：**

- zh_0、zh_1、zh_2没有触发；chunk 16的en_0与zh_5不同于上游历史记录，须继续核对量化、解码和目标关键词覆盖。
- 当前为Python单路径解码，未验证原生C++多路径搜索；未完成人工标注召回率、误唤醒率或长期运行验收。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`7420e0d67d20c246b0cd58b5255a0f89d0e4c42e`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际模型调用 | 4470 次 | chunk 8与16各9段录音、一次重复和2秒静音；三模型均有实际调用。 |
| 历史参考对照 | chunk 8：9/9；chunk 16：7/9 | 只比较九段固定语音的关键词列表；参考为上游历史推理输出，不是召回率或完整精度。 |
| 重复输入 | 全部调用输入输出一致 | 每种配置均重复zh_0一次，并为每段录音重新初始化解码器缓存。 |
| 静音样例 | 两种配置均未触发 | 只验证两秒零输入，未覆盖真实背景声或长期误唤醒。 |

适用范围：

- zh_0、zh_1、zh_2没有触发；chunk 16的en_0与zh_5不同于上游历史记录，须继续核对量化、解码和目标关键词覆盖。
- 当前为Python单路径解码，未验证原生C++多路径搜索；未完成人工标注召回率、误唤醒率或长期运行验收。
- 本次16GB卡，真实8GB容量仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`scripts/generate_keyword_tokens.py`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/scripts/generate_keyword_tokens.py) | Python 程序 / 前后处理 |
| [`scripts/sherpa_kws_ax630c.py`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/scripts/sherpa_kws_ax630c.py) | Python 程序 / 前后处理 |
| [`models/630C/sherpa__decoder-epoch-13-avg-2-chunk-16-left-64.axmodel`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/models/630C/sherpa__decoder-epoch-13-avg-2-chunk-16-left-64.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/630C/sherpa__decoder-epoch-13-avg-2-chunk-8-left-64.axmodel`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/models/630C/sherpa__decoder-epoch-13-avg-2-chunk-8-left-64.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/630C/sherpa__encoder-epoch-13-avg-2-chunk-16-left-64.axmodel`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/models/630C/sherpa__encoder-epoch-13-avg-2-chunk-16-left-64.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/630C/sherpa__encoder-epoch-13-avg-2-chunk-8-left-64.axmodel`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/models/630C/sherpa__encoder-epoch-13-avg-2-chunk-8-left-64.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/630C/sherpa__joiner-epoch-13-avg-2-chunk-16-left-64.axmodel`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/models/630C/sherpa__joiner-epoch-13-avg-2-chunk-16-left-64.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/config.json) | 运行配置 |
| [`config/tokens.txt`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/config/tokens.txt) | 分词器 / 字典，必须配套 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/requirements.txt) | Python 依赖清单 |
| [`run_sherpa_kws_ax630c.sh`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/run_sherpa_kws_ax630c.sh) | 启动或构建脚本 |
| [`run_sherpa_kws_ax650.sh`](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/run_sherpa_kws_ax650.sh) | 启动或构建脚本 |

仓库提交：`7420e0d67d20c246b0cd58b5255a0f89d0e4c42e`。仓库中的 12 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/tree/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留 keyword token 文件与词表，流式输入必须延续解码状态。更换关键词后重新验证误唤醒。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/tree/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/README.md)。
- [主要程序入口：scripts/generate_keyword_tokens.py](https://huggingface.co/AXERA-TECH/Sherpa-ONNX-KWS.AXERA/blob/7420e0d67d20c246b0cd58b5255a0f89d0e4c42e/scripts/generate_keyword_tokens.py)。

返回[完整模型目录](../catalog.mdx)。
