---
title: "MobileCLIP 部署指南"
sidebar_label: "MobileCLIP"
description: "MobileCLIP 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MobileCLIP 部署指南

MobileCLIP 用于图文相似度比较。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MobileCLIP` 的固定版本。下面下载本页选用的 7 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/mobileclip/a21f67267a09
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MobileCLIP \
  "README.md" \
  "run_axmodel.py" \
  "tokenizer.py" \
  "bpe_simple_vocab_16e6.txt.gz" \
  "zebra.jpg" \
  "mobileclip2_s2/AX650/mobileclip2_s2_image_encoder.axmodel" \
  "mobileclip2_s2/AX650/mobileclip2_s2_text_encoder.axmodel" \
  --revision a21f67267a09dd50fdb035dbb8b2018f7a7b5343 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

本例还需要以下前处理依赖：

```bash
python -m pip install 'torch==2.5.1' 'torchvision==0.20.1'
```

```bash
python -m pip install 'ftfy==6.3.1' 'regex==2025.9.18'
```

## 对比图片与候选文本

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task mobileclip --variant s2 \
  --output results/s2
```

本页运行 MobileCLIP2-S2 的 AX650 配套图像、文本编码器。输入为 `zebra.jpg`，候选文本为 `a zebra`、`a dog`、`two zebras`。图像使用官方 v1 前处理；文本长度为 77，本模型一次接收 3 条候选文本。

查看 `results/s2/deployment-result.json` 的余弦相似度与 `probabilityWithinCandidates`。后者是在本组三条候选文本中计算的 softmax 相对分数，改变候选文本后会变化。仓库内 S4、S0 与其他微调版本不包含在本页实测结论中。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

输入图中有两只斑马。MobileCLIP2-S2 将 two zebras 排在 a zebra、a dog 之前，与该图相符；这是单图、三条候选的匹配结果，尚未完成重复输入与其他权重验证。

**MobileCLIP2-S2**

图中两只斑马与 two zebras 对应，余弦相似度 0.330743 高于 a zebra 和 a dog。0.879615 是这三条候选内的 softmax 分数，不是整体分类准确率。

<div className="model-effect-gallery">

<figure>

[![官方图文匹配输入](../../../static/validation/effects/mobileclip-20260924/mobileclip-s2/input.jpg)](../../../static/validation/effects/mobileclip-20260924/mobileclip-s2/input.jpg)

<figcaption>官方图文匹配输入</figcaption>
</figure>

</div>

| 候选文本 | 余弦相似度 | 三选一 softmax 分数 |
| --- | --- | --- |
| a zebra | 0.310855 | 0.120385 |
| a dog | 0.016523 | 0.000000 |
| two zebras | 0.330743 | 0.879615 |

**使用时注意：**

- 本次未重复同一输入，未保存完整嵌入向量用于独立归一化复核；表中 softmax 只在这三条候选内归一化。
- 只测试 S2 的 AX650 图文组合及一张图片；S4、S0 和其他微调权重尚未实测。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`a21f67267a09dd50fdb035dbb8b2018f7a7b5343`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel；AXCLRTExecutionProvider |
| NumPy / OpenCV / Pillow | 1.26.4 / 4.11.0.86 / 11.3.0 |
| Torch / Torchvision | 2.5.1 / 0.20.1 |
| 图文前处理 | Transformers 4.51.3 / Tokenizers 0.21.4；ftfy 6.3.1 / regex 2025.9.18 |
| VAD SDK | silero-vad-axera 0.1.2，复用 SileroAx；权重来自页面固定仓库提交 |
| C++ 检测 | axcl-samples cbfa4c76891758983ca2b0c99c11d6621d59af39 / OpenCV 4.6.0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| mobileclip-s2 / mobileclip2_s2_image_encoder.axmodel | 28.473 ms（1 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |
| mobileclip-s2 / mobileclip2_s2_text_encoder.axmodel | 8.405 ms（1 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |

适用范围：

- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axmodel.py`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/run_axmodel.py) | Python 程序 / 前后处理 |
| [`mobileclip2_s0/AX650/mobileclip2_s0_image_encoder.axmodel`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/mobileclip2_s0/AX650/mobileclip2_s0_image_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`mobileclip2_s2/AX650/MobileCLIP2-S2_img_finetune.axmodel`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/mobileclip2_s2/AX650/MobileCLIP2-S2_img_finetune.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`mobileclip2_s2/AX650/MobileCLIP2-S2_text_finetune.axmodel`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/mobileclip2_s2/AX650/MobileCLIP2-S2_text_finetune.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`mobileclip2_s2/AX650/mobileclip2_s2_image_encoder.axmodel`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/mobileclip2_s2/AX650/mobileclip2_s2_image_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`mobileclip2_s2/AX650/mobileclip2_s2_text_encoder.axmodel`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/mobileclip2_s2/AX650/mobileclip2_s2_text_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/config.json) | 运行配置 |
| [`tokenizer.py`](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/tokenizer.py) | 旧版分词服务入口 |

仓库提交：`a21f67267a09dd50fdb035dbb8b2018f7a7b5343`。仓库中的 11 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MobileCLIP/tree/a21f67267a09dd50fdb035dbb8b2018f7a7b5343)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 图像编码器与文本编码器必须是同一模型版本；准备相互匹配和不匹配的图文对，比较相似度排序。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MobileCLIP/tree/a21f67267a09dd50fdb035dbb8b2018f7a7b5343)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/README.md)。
- [主要程序入口：run_axmodel.py](https://huggingface.co/AXERA-TECH/MobileCLIP/blob/a21f67267a09dd50fdb035dbb8b2018f7a7b5343/run_axmodel.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/MobileCLIP)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
