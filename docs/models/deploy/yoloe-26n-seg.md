---
title: "yoloe-26n-seg 部署指南"
sidebar_label: "yoloe-26n-seg"
description: "yoloe-26n-seg 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# yoloe-26n-seg 部署指南

yoloe-26n-seg 用于图像分割。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/yoloe-26n-seg` 的固定版本。下面下载本页选用的 17 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/yoloe-26n-seg/92b80871e4f4
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/yoloe-26n-seg \
  "README.md" \
  "models/yoloe_26n_seg_m1.axmodel" \
  "models/4_m1_cut_yoloe-26n-seg_640_post.onnx" \
  "models/4_m1_cut_yoloe-26n-seg_640_pulsar2.onnx" \
  "datasets/yoloe-26n-seg_class_names.json" \
  "datasets/annotations_val2017/annotations/instances_val2017.json" \
  "src/infer/e2e_infer_axmodel.py" \
  "src/tool/evaluate_yoloe.py" \
  "datasets/coco2017val_5000/000000000139.jpg" \
  "datasets/coco2017val_5000/000000001268.jpg" \
  "datasets/coco2017val_5000/000000001503.jpg" \
  "datasets/coco2017val_5000/000000001675.jpg" \
  "datasets/coco2017val_5000/000000002006.jpg" \
  "datasets/coco2017val_5000/000000002532.jpg" \
  "datasets/coco2017val_5000/000000002592.jpg" \
  "datasets/coco2017val_5000/000000004134.jpg" \
  "datasets/coco2017val_5000/000000005001.jpg" \
  --revision 92b80871e4f4d1223cd4824015931503c4b78879 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装推理依赖

本页在 RK3576 + AX8850 16GB M.2 算力卡上运行检测与实例分割。算力卡执行 `.axmodel`，主机执行配套 ONNX 后处理并还原掩码。当前权重固定为 COCO 80 类，不能直接输入文字更换类别。

完成 [Python 接口](../../usage/python.md) 配置后，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' \
  'onnxruntime==1.20.1'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。上方下载步骤固定了模型、后处理图、类别表和样例版本，不要混用其他版本的文件。下载清单也包含九图评测所需的标注和浮点参考模型。

## 运行检测与分割

保留下载步骤中的 `$MODEL_DIR`。下载 [YOLOE-26n 算力卡示例](../../../static/examples/yoloe26_card.py)，保存为 `~/edgeaccel/yoloe26_card.py`：

```bash
python ~/edgeaccel/yoloe26_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/yoloe26-01
```

输出目录须尚不存在。程序运行仓库中的九张图片，再重复首图并处理一张空白图。虽然输入目录名包含 `5000`，该固定版本实际只提供九张样例，不是完整 COCO 验证集。

退出码为 0 且 `deployment-result.json` 中 `completed: true` 表示全部样例执行完成。打开输出目录中的 `*-segmentation.png` 查看检测框和实例掩码，文件名前缀对应输入图片 ID。

## 检查检测框与掩码

图片使用 0.25 分数阈值，按类别过滤重叠框，IoU 阈值为 0.45。彩色区域为模型输出的实例掩码；`displayDetections` 记录展示类别、分数、原图坐标和掩码像素数。

本次九张图分别展示 13、5、4、2、3、1、2、18、13 个目标。重复首图结果一致，空白图在展示阈值下无目标。下方保留了杯子场景中的 `bed` 误检，用于说明部署成功与实际检测质量的区别。

为了后续评测，程序还保存 0.001 低阈值的候选和完整掩码。空白图在该阈值下有 16 个候选，因此不能将“展示图无目标”理解为所有阈值下都没有误报。

## 更换输入图片

```bash
python ~/edgeaccel/yoloe26_card.py \
  --model-dir "$MODEL_DIR" \
  --image ~/edgeaccel/images/test.jpg \
  --output ~/edgeaccel/results/yoloe26-custom-01
```

指定 `--image` 后只处理该文件，输出 `custom-segmentation.png`。图像自动按比例缩放并补边到 640×640，检测框和掩码恢复到原图尺寸。

主机输入为 RGB、NHWC、`uint8`，归一化由编译模型处理。原仓库 README 的部分接口描述仍写着 FP32 NCHW；该格式用于浮点模型，不能直接替换本页算力卡输入。

## 复算九张图的标注指标

下载 [COCO 样例评测工具](../../../static/examples/evaluate_yoloe26.py)，保存为 `~/edgeaccel/evaluate_yoloe26.py`。在具备 Python 环境的主机执行；如在另一台电脑评测，先完整复制结果目录及标注文件。

```bash
python -m pip install 'pycocotools==2.0.10'
python ~/edgeaccel/evaluate_yoloe26.py \
  --result ~/edgeaccel/results/yoloe26-01 \
  --annotations "$MODEL_DIR/datasets/annotations_val2017/annotations/instances_val2017.json" \
  --output ~/edgeaccel/results/yoloe26-nine-image-metrics.json
```

输出 JSON 中的 `imageCount` 应为 9。工具按全部九个图片 ID 评测，包括没有检出目标的图片；重复样例和合成空白图不计入 COCO 指标。该命令不适用于没有配套标注的自定义图片。

本次九图检测框 AP@[0.50:0.95] 为 0.349675，分割 AP 为 0.330636。同版本浮点模型在电脑 CPU 上的参考值分别为 0.387118 和 0.329744，详见下方表格。评测候选阈值为 0.001，重叠框过滤阈值为 0.45，COCO 指标采用 `maxDets=100`。

九图子集不能代表完整 COCO 精度。量化输出存在同分候选，不同 NumPy 版本的同分排序可能改变被保留的重叠框；复现时应保持本页依赖版本。当前仍需完成全量数据集、实际业务场景及真实 8GB 卡验证。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

完成九张样例图、一次重复和空白图的检测分割；展示真实掩码、误检与九图标注/浮点参考对照。

**检测框与实例分割掩码**

以下为本次实际输入和输出。彩色区域为实例掩码。杯子场景中还有一个覆盖桌面区域的bed误检；该结果原样保留，同版本浮点参考在此图中也给出了bed候选。

<div className="model-effect-gallery">

<figure>

[![人物与手提包：本次输入](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001268-input.jpg)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001268-input.jpg)

<figcaption>人物与手提包：本次输入</figcaption>
</figure>

<figure>

[![000000001268：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001268-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001268-segmentation.png)

<figcaption>000000001268：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![雪地人物：本次输入](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002532-input.jpg)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002532-input.jpg)

<figcaption>雪地人物：本次输入</figcaption>
</figure>

<figure>

[![000000002532：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002532-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002532-segmentation.png)

<figcaption>000000002532：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![杯子与误检示例：本次输入](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002592-input.jpg)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002592-input.jpg)

<figcaption>杯子与误检示例：本次输入</figcaption>
</figure>

<figure>

[![000000002592：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002592-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002592-segmentation.png)

<figcaption>000000002592：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

</div>

**九张样例图的完整结果**

展示阈值为0.25，评测候选阈值为0.001，两列数量不可直接混用。这里只运行仓库实际提供的九张图，目录名称中的5000不代表本次运行了5000张。下方补充其余六张输出图，并汇总九图结果；表格中的图片ID省略文件名的前导0。

<div className="model-effect-gallery">

<figure>

[![000000000139：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000000139-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000000139-segmentation.png)

<figcaption>000000000139：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![000000001503：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001503-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001503-segmentation.png)

<figcaption>000000001503：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![000000001675：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001675-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000001675-segmentation.png)

<figcaption>000000001675：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![000000002006：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002006-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000002006-segmentation.png)

<figcaption>000000002006：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![000000004134：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000004134-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000004134-segmentation.png)

<figcaption>000000004134：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

<figure>

[![000000005001：本次AXCL分割输出，展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/000000005001-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/000000005001-segmentation.png)

<figcaption>000000005001：本次AXCL分割输出，展示阈值0.25</figcaption>
</figure>

</div>

| 图片ID | AXCL展示目标 | FP32展示目标 | AXCL展示类别 | AXCL评测候选 |
| --- | --- | --- | --- | --- |
| 139 | 13 | 16 | person × 2, bottle × 1, chair × 3, dining table × 1, tv × 1, microwave × 1, refrigerator × 1, clock × 1, vase × 2 | 191 |
| 1268 | 5 | 6 | person × 4, handbag × 1 | 205 |
| 1503 | 4 | 6 | tv × 1, laptop × 1, mouse × 1, keyboard × 1 | 217 |
| 1675 | 2 | 3 | cat × 1, keyboard × 1 | 117 |
| 2006 | 3 | 6 | person × 2, bus × 1 | 188 |
| 2532 | 1 | 1 | person × 1 | 118 |
| 2592 | 2 | 2 | cup × 1, bed × 1 | 164 |
| 4134 | 18 | 23 | person × 12, tie × 2, cup × 1, dining table × 2, laptop × 1 | 203 |
| 5001 | 13 | 15 | person × 12, frisbee × 1 | 165 |

**仅九张图的标注与浮点参考对照**

使用仓库COCO标注、同版FP32前半图和相同后处理图，对明确列出的九个图片ID计算指标。AP越高越好；这个小样本不能代表完整COCO精度，也不能据此断言量化提高了分割精度。FP32在电脑CPU执行，未与算力卡比较速度。

| 九图子集指标 | AXCL量化模型 | FP32 CPU参考 | 差值 AXCL−FP32 |
| --- | --- | --- | --- |
| 检测框 AP@[0.50:0.95] | 0.349675 | 0.387118 | -0.037443 |
| 检测框 AP@0.50 | 0.522832 | 0.556473 | -0.033640 |
| 分割掩码 AP@[0.50:0.95] | 0.330636 | 0.329744 | +0.000892 |
| 分割掩码 AP@0.50 | 0.496720 | 0.444797 | +0.051923 |

**重复输入与空白图**

第一张图重复一次，模型输入输出、CPU后处理输出及完整分割结果一致。空白图在0.25阈值下无目标，但在0.001阈值下有16个候选；不能描述为所有阈值下都无误报。

<div className="model-effect-gallery">

<figure>

[![本次空白图输出：展示阈值0.25](../../../static/validation/effects/yoloe-26n-seg-20260928/blank-segmentation.png)](../../../static/validation/effects/yoloe-26n-seg-20260928/blank-segmentation.png)

<figcaption>本次空白图输出：展示阈值0.25</figcaption>
</figure>

</div>

**实际调用耗时**

每种调用均统计11次，包含首次运行，无预热。AXCL时间含传输；不含CPU图、掩码解码、绘图和证据保存，不能直接换算成应用实时帧率。

| 阶段 | 调用次数 | 平均 / ms |
| --- | --- | --- |
| AXCL模型 | 11 | 74.368642 |
| CPU后处理图 | 11 | 17.442674 |

**使用时注意：**

- 杯子场景中存在bed误检；当前样例与小规模指标不足以宣称业务质量验收通过。
- 当前为固定COCO80类，不能直接传入任意文本更换检测类别；完整5000图、长时视频及真实8GB卡仍待验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`92b80871e4f4d1223cd4824015931503c4b78879`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际AXCL调用 | 11 次 | 九张官方图、重复首图、空白图，各接CPU后处理图。 |
| 九图检测框 AP | 0.349675 | 仅九图子集，IoU0.50:0.95；完整COCO尚未测试。 |
| 九图分割 AP | 0.330636 | 仅九图子集，不能替代完整数据集精度。 |
| 重复结果 | 输入输出与掩码一致 | 一次重复测试，不是长期稳定性结论。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`src/infer/e2e_infer_axmodel.py`](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/blob/92b80871e4f4d1223cd4824015931503c4b78879/src/infer/e2e_infer_axmodel.py) | Python 程序 / 前后处理 |
| [`src/tool/e2e_cut.py`](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/blob/92b80871e4f4d1223cd4824015931503c4b78879/src/tool/e2e_cut.py) | Python 程序 / 前后处理 |
| [`models/yoloe_26n_seg_m1.axmodel`](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/blob/92b80871e4f4d1223cd4824015931503c4b78879/models/yoloe_26n_seg_m1.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`src/infer/run_infer_axmodel.sh`](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/blob/92b80871e4f4d1223cd4824015931503c4b78879/src/infer/run_infer_axmodel.sh) | 启动或构建脚本 |

仓库提交：`92b80871e4f4d1223cd4824015931503c4b78879`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/tree/92b80871e4f4d1223cd4824015931503c4b78879)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/tree/92b80871e4f4d1223cd4824015931503c4b78879)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/blob/92b80871e4f4d1223cd4824015931503c4b78879/README.md)。
- [主要程序入口：src/infer/e2e_infer_axmodel.py](https://huggingface.co/AXERA-TECH/yoloe-26n-seg/blob/92b80871e4f4d1223cd4824015931503c4b78879/src/infer/e2e_infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
