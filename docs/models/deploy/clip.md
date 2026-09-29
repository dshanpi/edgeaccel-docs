---
title: "clip 部署指南"
sidebar_label: "clip"
description: "clip 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# clip 部署指南

clip 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/clip` 的固定版本。下面下载本页选用的 4 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/clip/8ff8b75dc765
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/clip \
  "README.md" \
  "clip_vit_l14_336px_image_encoder_all_u16_fc_u8.axmodel" \
  "clip_vit_l14_336px_text_encoder_u16.axmodel" \
  "vocab.txt" \
  --revision 8ff8b75dc7655ca132a6723d0faa1e11d16edbd1 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备图文样例

先按 [Python 接口](../../usage/python.md) 创建 `~/edgeaccel/python-env` 并安装 PyAXEngine，再在 RK3576 主机激活环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`，再继续准备样例。

获取官方样例的固定提交，保留其中 `images/` 目录：

```bash
SAMPLE_DIR=~/edgeaccel/src/clip-samples-8a330cf1
git clone --no-checkout https://github.com/AXERA-TECH/CLIP-ONNX-AX650-CPP.git "$SAMPLE_DIR"
git -C "$SAMPLE_DIR" checkout --detach 8a330cf1c3f7a881ba222f92d6485e5b6894f8d3
```

克隆目录须尚不存在。已准备过该目录时，核对 `git -C "$SAMPLE_DIR" rev-parse HEAD` 与上述提交一致后直接复用。

## 运行图文匹配

下载本页 [CLIP 算力卡示例](../../../static/examples/clip_card.py)，保存为 `~/edgeaccel/clip_card.py`。保持下载步骤中的 `MODEL_DIR` 变量，执行：

```bash
python ~/edgeaccel/clip_card.py \
  --model-dir "$MODEL_DIR" \
  --sample-dir "$SAMPLE_DIR" \
  --language en \
  --output ~/edgeaccel/results/clip-01
```

输出目录须尚不存在。程序通过 AXCL 运行配套图像和文本编码器，保存输入图片、原始向量、余弦相似度与候选分数。每份输入重复两次，检查向量是否一致。

## 检查匹配结果

打开输出目录中的 `deployment-result.json`，查看 `topLabels` 与下方实际结果。向量维度为 768，候选分数只表示这组三个候选之间的相对关系；新增或更换候选后，分数需要重新计算。

本例沿用官方 AXCL 示例的 RGB 标准化、336×336 直接缩放和简化分词规则。当前入口用于复现固定候选，接入任意文本检索时需要另行完善配套分词流程。


## 查看部署效果

**固定样例已核对** · 2026-09-27 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

CLIP 配套图像和文本编码器已完成三张官方图片的图文匹配，最高分分别为bird、cat、dog。

**clip_vit_l14_336px_image_encoder_all_u16_fc_u8.axmodel**

三张输入图片的主体已人工核对为鸟、猫、狗；在给定的三个候选中，最高分均对应画面主体。图像和文字分别得到 768 维向量，每份输入重复两次，向量逐项一致。

<div className="model-effect-gallery">

<figure>

[![本次输入 · 鸟](../../../static/validation/effects/clip-20260927/bird-input.webp)](../../../static/validation/effects/clip-20260927/bird-input.webp)

<figcaption>本次输入 · 鸟</figcaption>
</figure>

<figure>

[![本次输入 · 猫](../../../static/validation/effects/clip-20260927/cat-input.webp)](../../../static/validation/effects/clip-20260927/cat-input.webp)

<figcaption>本次输入 · 猫</figcaption>
</figure>

<figure>

[![本次输入 · 狗](../../../static/validation/effects/clip-20260927/dog-chai-input.webp)](../../../static/validation/effects/clip-20260927/dog-chai-input.webp)

<figcaption>本次输入 · 狗</figcaption>
</figure>

</div>

| 输入图片 | bird | cat | dog | 最高分候选 |
| --- | --- | --- | --- | --- |
| bird.jpg | 0.991869 | 0.005770 | 0.002361 | bird |
| cat.jpg | 0.004936 | 0.961482 | 0.033582 | cat |
| dog-chai.jpeg | 0.013075 | 0.021527 | 0.965398 | dog |

**使用时注意：**

- 仅核对三张图片在三个固定候选中的排序，未评估通用检索召回率、细粒度物种分类或复杂语句。
- 表内为余弦相似度乘 100 后，在三个候选中计算的 Softmax 分数，不是准确率；更换候选会改变分数。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-27。模型版本：`8ff8b75dc7655ca132a6723d0faa1e11d16edbd1`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 环境 | Python 3.12 / NumPy 1.26.4 / OpenCV 4.11.0 / PyAXEngine 0.1.3.rc3 |
| 后端 | 图像与文字均使用 AXCLRTExecutionProvider；匹配后处理在主机完成 |
| 前处理参考 | CLIP-ONNX-AX650-CPP 8a330cf1c3f7a881ba222f92d6485e5b6894f8d3 / axcl_runner |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| clip_vit_l14_336px_text_encoder_u16.axmodel | 8.670 ms（6 次平均） | session.run 墙钟，包含 AXCL 数据传输；不含加载、前后处理与保存，未剔除首轮。 |
| clip_vit_l14_336px_image_encoder_all_u16_fc_u8.axmodel | 81.220 ms（6 次平均） | session.run 墙钟，包含 AXCL 数据传输；不含加载、前后处理与保存，未剔除首轮。 |

适用范围：

- 仅核对三张图片在三个固定候选中的排序，未评估通用检索召回率、细粒度物种分类或复杂语句。
- 表内为余弦相似度乘 100 后，在三个候选中计算的 Softmax 分数，不是准确率；更换候选会改变分数。
- 按官方 AXCL 示例将图像直接缩放到 336×336；分词沿用该示例的词表规则，未实现任意文本的完整 BPE/WordPiece 处理。
- 仅在 16GB 卡完成这些固定样例，未验证 8GB、视频、多用户或持续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`clip_vit_l14_336px_image_encoder_all_u16_fc_u8.axmodel`](https://huggingface.co/AXERA-TECH/clip/blob/8ff8b75dc7655ca132a6723d0faa1e11d16edbd1/clip_vit_l14_336px_image_encoder_all_u16_fc_u8.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`clip_vit_l14_336px_text_encoder_u16.axmodel`](https://huggingface.co/AXERA-TECH/clip/blob/8ff8b75dc7655ca132a6723d0faa1e11d16edbd1/clip_vit_l14_336px_text_encoder_u16.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/clip/blob/8ff8b75dc7655ca132a6723d0faa1e11d16edbd1/config.json) | 运行配置 |

仓库提交：`8ff8b75dc7655ca132a6723d0faa1e11d16edbd1`。仓库中的 2 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/clip/tree/8ff8b75dc7655ca132a6723d0faa1e11d16edbd1)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/clip/tree/8ff8b75dc7655ca132a6723d0faa1e11d16edbd1)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/clip/blob/8ff8b75dc7655ca132a6723d0faa1e11d16edbd1/README.md)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/clip)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
