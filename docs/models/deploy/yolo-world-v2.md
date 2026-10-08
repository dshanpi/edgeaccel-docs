---
title: "YOLO-World-V2 部署指南"
sidebar_label: "YOLO-World-V2"
description: "YOLO-World-V2 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# YOLO-World-V2 部署指南

YOLO-World-V2 用于开放词汇检测。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/YOLO-World-V2` 的固定版本。下面下载本页选用的 11 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/yolo-world-v2/a1f2c183776e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/YOLO-World-V2 \
  "README.md" \
  "football.jpg" \
  "host.jpg" \
  "install/lib/axcl_aarch64/libyoloworld.so" \
  "models/clip_b1_u16_ax650.axmodel" \
  "models/yolo_u16_ax650.axmodel" \
  "pyyoloworld/example.py" \
  "pyyoloworld/pyaxdev.py" \
  "pyyoloworld/pyyoloworld.py" \
  "pyyoloworld/requirements.txt" \
  "vocab.txt" \
  --revision a1f2c183776eaf127649c227ecfa27d9aeddd269 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备官方 AXCL 检测环境

本例在 RK3576 + AX8850 16GB M.2 上使用官方 YOLO-World-V2 SDK，根据四条英文类别词检测图片中的目标。使用 `install/lib/axcl_aarch64/libyoloworld.so`，配合 AX650 编译权重。

在 Linux 主机执行：

```bash
python -m pip install 'numpy==1.26.4' 'Pillow==11.3.0'
axcl-smi
```

确认设备 0 可用。保留前面下载步骤的 `MODEL_DIR`，检查库依赖：

```bash
ldd "$MODEL_DIR/install/lib/axcl_aarch64/libyoloworld.so"
```

依赖列表不得出现 `not found`。本例直接使用系统 ARM64 Python 环境；若其他环境中的 `libstdc++` 不兼容，先切换至配套系统环境再运行。

## 运行两张图片与两组词表

下载 [YOLO-World 算力卡示例](../../../static/examples/yoloworld_card.py)，保存为 `~/edgeaccel/yoloworld_card.py`，使用尚不存在的输出目录：

```bash
python ~/edgeaccel/yoloworld_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/yoloworld-01
```

例程校验官方动态库与 Python 接口，把 ARM64 AXCL 库复制到 SDK 的 `pyyoloworld/aarch64` 加载目录，显式选择 `axcl_device`、设备 0。

程序对 `host.jpg`、`football.jpg` 分别运行以下词表，每种组合重复检测两次：

| 词表 | 类别词 |
| --- | --- |
| 第一组 | `person`, `dog`, `car`, `horse` |
| 第二组 | `man`, `shoes`, `ball`, `person` |

词表是发送给模型的查询文本。返回标签用于观察本次模型响应，不应视作人物身份或属性的认定。

## 查看输出文件

| 文件 | 查看内容 |
| --- | --- |
| `deployment-result.json` | `completed: true`、四组检测框、类别、分数及重复结果 |
| `host-input.png` / `football-input.png` | 实际输入 |
| `*-set1-result.png` | 第一组词表结果 |
| `*-set2-result.png` | 第二组词表结果 |

控制台应出现 `AXCLWorker start with devid 0`，结束时释放模型与设备。`sessions` 不包含逐权重的底层调用跟踪，本例记录的是官方 SDK 完整流程和 `yw_set_classes`、`yw_detect` 的主机侧耗时。

## 接入自己的类别与图片

在示例代码中修改 `sets` 内的四条英文类别词，以及 `for file in ['host.jpg','football.jpg']` 中的文件名，将图片放入模型目录。每组保持四个类别词，每个词的 UTF-8 编码长度小于 64 字节，重新运行时使用新的输出目录。

SDK 接收连续内存的 RGB、`uint8` 图像。更换类别后先调用 `set_classes`，再调用 `detect`；无需每张图片重新创建模型。类别词之间含义接近时，检测类别与保留框可能变化，需要结合业务图片核对。

## 对照部署效果

下方展示两图两组词表的全部结果，包括零检测结果。阈值固定为 0.1，保留低分框；检测框数不是实际物体数量。

检测耗时包含 SDK 内部前处理、数据传输、推理和后处理，不含图片读取、模型加载、绘图和保存。词表更新时间单独记录，不计入检测均值。当前结果用于检查基本运行，未进行完整精度或视频吞吐测试。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两图两词表的完整结果与重复输出已核对，新增逐提示词数量与分数范围。足球图第二组词表的 7 框中有 4 框低于 0.25；实际检测仍使用 0.1，未更改阈值或隐藏输出。

**两张图片与两组词表统计**

同一官方SDK实例中切换四词查询集合，四种组合各重复检测两次，返回框、类别和分数一致。检测时间含SDK前后处理，词表编码时间单独统计。 两组词表合计七个不同提示词，本组没有 horse 正例。下方按每个提示词列出零检测和分数范围；0.25 仅用于描述分数分布，实际运行阈值仍为 0.1，未重新筛选或运行模型。

| 图片 | 查询词表 | 返回类别与框数 | 检测均值 / ms | 更新词表 / ms |
| --- | --- | --- | --- | --- |
| host.jpg | person, dog, car, horse | dog: 1, car: 3 | 28.164 | 18.341 |
| host.jpg | man, shoes, ball, person | 无检测 | 27.594 | 19.900 |
| football.jpg | person, dog, car, horse | person: 8 | 33.827 | 20.370 |
| football.jpg | man, shoes, ball, person | man: 2, ball: 2, person: 1, shoes: 2 | 33.637 | 19.680 |

**host-set1：按词表检测**

狗所在区域返回1框，画面中的车辆返回3框；图中仍保留边缘处的车辆框。 阈值0.1，未隐藏低分框。

<div className="model-effect-gallery">

<figure>

[![host.jpg · 实际输入](../../../static/validation/effects/yolo-world-v2-20260928/host-input.png)](../../../static/validation/effects/yolo-world-v2-20260928/host-input.png)

<figcaption>host.jpg · 实际输入</figcaption>
</figure>

<figure>

[![host.jpg · person, dog, car, horse](../../../static/validation/effects/yolo-world-v2-20260928/host-set1-result.png)](../../../static/validation/effects/yolo-world-v2-20260928/host-set1-result.png)

<figcaption>host.jpg · person, dog, car, horse</figcaption>
</figure>

</div>

| 实际提示词 | 返回框数 | 分数范围 | 其中分数低于 0.25 |
| --- | --- | --- | --- |
| person | 0 | 未检出 | 0 |
| dog | 1 | 0.879624–0.879624 | 0 |
| car | 3 | 0.603217–0.879624 | 0 |
| horse | 0 | 未检出 | 0 |

**host-set2：按词表检测**

把查询改为 man、shoes、ball、person 后，本图没有返回达到阈值的检测框，结果按实际保留。 阈值0.1，未隐藏低分框。

<div className="model-effect-gallery">

<figure>

[![host.jpg · man, shoes, ball, person](../../../static/validation/effects/yolo-world-v2-20260928/host-set2-result.png)](../../../static/validation/effects/yolo-world-v2-20260928/host-set2-result.png)

<figcaption>host.jpg · man, shoes, ball, person</figcaption>
</figure>

</div>

| 实际提示词 | 返回框数 | 分数范围 | 其中分数低于 0.25 |
| --- | --- | --- | --- |
| man | 0 | 未检出 | 0 |
| shoes | 0 | 未检出 | 0 |
| ball | 0 | 未检出 | 0 |
| person | 0 | 未检出 | 0 |

**football-set1：按词表检测**

第一组词表返回8个person类框，包含边缘、远处及局部候选；数量不等于实际人数。 阈值0.1，未隐藏低分框。

<div className="model-effect-gallery">

<figure>

[![football.jpg · 实际输入](../../../static/validation/effects/yolo-world-v2-20260928/football-input.png)](../../../static/validation/effects/yolo-world-v2-20260928/football-input.png)

<figcaption>football.jpg · 实际输入</figcaption>
</figure>

<figure>

[![football.jpg · person, dog, car, horse](../../../static/validation/effects/yolo-world-v2-20260928/football-set1-result.png)](../../../static/validation/effects/yolo-world-v2-20260928/football-set1-result.png)

<figcaption>football.jpg · person, dog, car, horse</figcaption>
</figure>

</div>

| 实际提示词 | 返回框数 | 分数范围 | 其中分数低于 0.25 |
| --- | --- | --- | --- |
| person | 8 | 0.101892–0.879624 | 2 |
| dog | 0 | 未检出 | 0 |
| car | 0 | 未检出 | 0 |
| horse | 0 | 未检出 | 0 |

**football-set2：按词表检测**

第二组词表返回7个框：man标签2个、person标签1个、ball标签2个、shoes标签2个。标签反映查询下的模型输出，鞋类框分数较低。 阈值0.1，未隐藏低分框。

<div className="model-effect-gallery">

<figure>

[![football.jpg · man, shoes, ball, person](../../../static/validation/effects/yolo-world-v2-20260928/football-set2-result.png)](../../../static/validation/effects/yolo-world-v2-20260928/football-set2-result.png)

<figcaption>football.jpg · man, shoes, ball, person</figcaption>
</figure>

</div>

| 实际提示词 | 返回框数 | 分数范围 | 其中分数低于 0.25 |
| --- | --- | --- | --- |
| man | 2 | 0.132682–0.449073 | 1 |
| shoes | 2 | 0.103785–0.117830 | 2 |
| ball | 2 | 0.377450–0.402052 | 0 |
| person | 1 | 0.147506–0.147506 | 1 |

**使用时注意：**

- 只验证官方SDK整体检测流程，未跟踪每份权重的底层engine调用，也未进行CPU参考或有标注数据集评估。
- 同义或近义词会影响类别竞争；边缘、局部和低分框须按业务样例复核，不以框数作为人数或物体总数。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`a1f2c183776eaf127649c227ecfa27d9aeddd269`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 官方 libyoloworld.so ARM64 AXCL SDK / Python ctypes，显式 axcl_device、设备0 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| SDK检测平均耗时 | 30.805 ms | 四种组合各两次，共8次yw_detect；含前后处理和传输，不含词表更新、加载及文件操作。 |
| 词表更新时间 | 18.341–20.370 ms | 四次yw_set_classes，每次四个词，单独计时。 |

适用范围：

- 本次为16GB卡，真实8GB、摄像头视频、多用户与连续运行仍需回归。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`pyyoloworld/gradio_example.py`](https://huggingface.co/AXERA-TECH/YOLO-World-V2/blob/a1f2c183776eaf127649c227ecfa27d9aeddd269/pyyoloworld/gradio_example.py) | Python 程序 / 前后处理 |
| [`models/clip_b1_u16_ax650.axmodel`](https://huggingface.co/AXERA-TECH/YOLO-World-V2/blob/a1f2c183776eaf127649c227ecfa27d9aeddd269/models/clip_b1_u16_ax650.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/yolo_u16_ax650.axmodel`](https://huggingface.co/AXERA-TECH/YOLO-World-V2/blob/a1f2c183776eaf127649c227ecfa27d9aeddd269/models/yolo_u16_ax650.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`pyyoloworld/requirements.txt`](https://huggingface.co/AXERA-TECH/YOLO-World-V2/blob/a1f2c183776eaf127649c227ecfa27d9aeddd269/pyyoloworld/requirements.txt) | Python 依赖清单 |

仓库提交：`a1f2c183776eaf127649c227ecfa27d9aeddd269`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/YOLO-World-V2/tree/a1f2c183776eaf127649c227ecfa27d9aeddd269)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 程序需要配套文本特征二进制与类别列表；-t 接收特征文件路径，不是中文提示词。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/YOLO-World-V2/tree/a1f2c183776eaf127649c227ecfa27d9aeddd269)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/YOLO-World-V2/blob/a1f2c183776eaf127649c227ecfa27d9aeddd269/README.md)。
- [主要程序入口：pyyoloworld/gradio_example.py](https://huggingface.co/AXERA-TECH/YOLO-World-V2/blob/a1f2c183776eaf127649c227ecfa27d9aeddd269/pyyoloworld/gradio_example.py)。
- [配套项目：AXERA-TECH/ONNX-YOLO-World-Open-Vocabulary-Object-Detection](https://github.com/AXERA-TECH/ONNX-YOLO-World-Open-Vocabulary-Object-Detection)。
- [配套项目：AXERA-TECH/yoloworld.axera](https://github.com/AXERA-TECH/yoloworld.axera)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/YOLO-World-V2)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
