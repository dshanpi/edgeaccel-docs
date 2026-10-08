---
title: "dinov3_vits_pretrain_lvd1689m 部署指南"
sidebar_label: "dinov3_vits_pretrain_lvd1689m"
description: "dinov3_vits_pretrain_lvd1689m 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# dinov3_vits_pretrain_lvd1689m 部署指南

dinov3_vits_pretrain_lvd1689m 用于图像特征提取。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/dinov3_vits_pretrain_lvd1689m` 的固定版本。下面下载本页选用的 5 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/dinov3-vits-pretrain-lvd1689m/79b5d51c3d7c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/dinov3_vits_pretrain_lvd1689m \
  "README.md" \
  "scripts/infer_dinov3_backbone_axmodel.py" \
  "models-ax650/dinov3-vits16-pretrain-lvd1689m.axmodel" \
  "examples/ILSVRC2012_val_00000001.jpeg" \
  "examples/ILSVRC2012_val_00000005.jpeg" \
  --revision 79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16 \
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

## 提取图片特征

```bash
cd "$MODEL_DIR"
python vision_card.py --model-dir . --task dinov3 --variant vits16 \
  --output results/features
```

例程依次输入官方的 `ILSVRC2012_val_00000001.jpeg`、`ILSVRC2012_val_00000005.jpeg`，再重复第一张图片，使用官方 `preprocess_image` 函数。每张图片的 `pooler_output` 保存为 384 维 `.npy` 向量。

查看 `results/features/deployment-result.json` 中的向量维度、范数和余弦相似度。该模型输出图片特征，不生成分类名称；相似度不能解释为分类准确率。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两张图片均得到 384 维特征；保存的不同图片向量余弦相似度为 0.017665。运行记录中的重复输入余弦相似度接近 1，尚未独立确认两次完整向量逐元素一致。

**图片特征与重复输入**

pooler_output 为 1×384，last_hidden_state 为 1×201×384。保存向量未做单位归一化，余弦计算除以两者 L2 范数；每次输入一张图片，不使用文本分词器。下表重复输入一行来自原始运行记录，未独立复核完整向量相等。

<div className="model-effect-gallery">

<figure>

[![ILSVRC2012_val_00000001.jpeg](../../../static/validation/effects/dinov3-vits-pretrain-lvd1689m-20260924/dinov3-vits16/ILSVRC2012_val_00000001.jpeg)](../../../static/validation/effects/dinov3-vits-pretrain-lvd1689m-20260924/dinov3-vits16/ILSVRC2012_val_00000001.jpeg)

<figcaption>ILSVRC2012_val_00000001.jpeg</figcaption>
</figure>

<figure>

[![ILSVRC2012_val_00000005.jpeg](../../../static/validation/effects/dinov3-vits-pretrain-lvd1689m-20260924/dinov3-vits16/ILSVRC2012_val_00000005.jpeg)](../../../static/validation/effects/dinov3-vits-pretrain-lvd1689m-20260924/dinov3-vits16/ILSVRC2012_val_00000005.jpeg)

<figcaption>ILSVRC2012_val_00000005.jpeg</figcaption>
</figure>

</div>

| 对比 | 余弦相似度 |
| --- | --- |
| 图片 1 与图片 2 | 0.017665 |
| 图片 1 与重复输入 | 1.000000 |

**使用时注意：**

- 现有完整向量文件只保留图片 1 的末次输出与图片 2 的输出，不能独立复核图片 1 首次和重复输出的逐元素一致性；相关图片及检索效果仍待验证。
- 结论限于 RK3576 + AX8850 16GB 的上述固定样例，不等同于 8GB 容量验证或长期稳定性测试。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16`。

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
| dinov3-vits16 / dinov3-vits16-pretrain-lvd1689m.axmodel | 20.124 ms（3 次平均） | AXCL session.run 调用，含输入输出传输；不含模型加载和前后处理，未剔除首轮。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`scripts/infer_dinov3_backbone_axmodel.py`](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/blob/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16/scripts/infer_dinov3_backbone_axmodel.py) | Python 程序 / 前后处理 |
| [`models-ax650/dinov3-vits16-pretrain-lvd1689m.axmodel`](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/blob/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16/models-ax650/dinov3-vits16-pretrain-lvd1689m.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/blob/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16/config.json) | 运行配置 |
| [`scripts/requirements.txt`](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/blob/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16/scripts/requirements.txt) | Python 依赖清单 |

仓库提交：`79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/tree/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/tree/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/blob/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16/README.md)。
- [主要程序入口：scripts/infer_dinov3_backbone_axmodel.py](https://huggingface.co/AXERA-TECH/dinov3_vits_pretrain_lvd1689m/blob/79b5d51c3d7c46aa0195b8b4df1d8c9b84ed9a16/scripts/infer_dinov3_backbone_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
