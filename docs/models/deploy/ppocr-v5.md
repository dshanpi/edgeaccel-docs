---
title: "PPOCR_v5 部署指南"
sidebar_label: "PPOCR_v5"
description: "PPOCR_v5 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# PPOCR_v5 部署指南

PPOCR_v5 用于文字检测与识别。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。本页选择 `ax650/det_npu3.axmodel`。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页包含 **RK3576 DshanPi A1 + AX8850 16GB M.2** 与 **RK3576 DshanPi A1 + AX8850 8GB M.2** 的样例。按效果展示中的权重和容量对应使用，不同环境的结果不能互相替代。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/PPOCR_v5` 的固定版本。下面下载本页选用的 14 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/ppocr-v5/fed5e0b6eaac
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/PPOCR_v5 \
  "11.jpg" \
  "README.md" \
  "config.json" \
  "infer_axmodel.py" \
  "infer_onnx.py" \
  "ppocrv5_dict.txt" \
  "requirements.txt" \
  "simfang.ttf" \
  "ax650/cls_npu1.axmodel" \
  "ax650/det_npu1.axmodel" \
  "ax650/rec_npu1.axmodel" \
  "ax650/det_npu3.axmodel" \
  "ax650/rec_npu3.axmodel" \
  "ax650/cls_npu3.axmodel" \
  --revision fed5e0b6eaac3e34b01cb3919e0df7810296d850 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 配置 Python 后端

激活已安装 PyAXEngine 的主机虚拟环境。先检查可用 provider：

```bash
source ~/edgeaccel/python-env/bin/activate
python -c "import axengine; print(axengine.get_available_providers())"
```

必须包含 `AXCLRTExecutionProvider`。保留已安装的 PyAXEngine，按下面命令安装本例依赖。

在已激活的环境中安装该入口直接使用的依赖；以下依赖用于本页的命令行示例：

```bash
python -m pip install Pillow numpy==1.26.4 ml-dtypes==0.5.3 opencv-python-headless==4.11.0.86 pyclipper==1.4.0 shapely==2.0.7
```


按本页已核对的修改配置 AXCL 后端。脚本在首次修改前保留 `.upstream` 备份；原表达式不匹配时停止，避免误改其他版本。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
edits = [
    {"path": "infer_axmodel.py", "old": "ort.InferenceSession(args.det_model_dir)", "new": "ort.InferenceSession(args.det_model_dir, providers=[\"AXCLRTExecutionProvider\"])"},
    {"path": "infer_axmodel.py", "old": "ort.InferenceSession(args.rec_model_dir)", "new": "ort.InferenceSession(args.rec_model_dir, providers=[\"AXCLRTExecutionProvider\"])"},
    {"path": "infer_axmodel.py", "old": "ort.InferenceSession(args.cls_model_dir)", "new": "ort.InferenceSession(args.cls_model_dir, providers=[\"AXCLRTExecutionProvider\"])"}
]
for edit in edits:
    path = Path(edit.get("path", "infer_axmodel.py"))
    source = path.read_text(encoding="utf-8")
    if edit["old"] not in source:
        assert edit["new"] in source, f"补丁目标不匹配：{path}"
        continue
    backup = path.with_name(path.name + ".upstream")
    if not backup.exists():
        backup.write_text(source, encoding="utf-8")
    path.write_text(source.replace(edit["old"], edit["new"]), encoding="utf-8")
    print(f"已修改 {path}")
PY
```

重新下载原始源码后，需要再次执行此修改。

## 运行模型

在模型根目录执行，输入与权重使用该提交的实际路径：

```bash
cd "$MODEL_DIR"
test -s ax650/det_npu3.axmodel
test -s 11.jpg
set -o pipefail
python infer_axmodel.py --img_path 11.jpg --det_model_dir ax650/det_npu3.axmodel --rec_model_dir ax650/rec_npu3.axmodel --cls_model_dir ax650/cls_npu3.axmodel --character_dict_path ppocrv5_dict.txt 2>&1 | tee run.log
```

日志中的实际执行后端应为 `AXCLRTExecutionProvider`。检查 `res_ax.jpg` 是本次新生成的文件，内容与输入相符。使用仓库现成结果图或只检查程序退出码均不足以判断效果。

参数依据：[`infer_axmodel.py` 源码](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/infer_axmodel.py)。

## 运行 NPU1 完整链路

前面的下载命令同时包含本节三个权重。在已配置 AXCL 后端的 Python 环境中执行，保留对应版本的字典、字体及前后处理。本节组合在16GB卡上实测。

| 权重 | 阶段 |
| --- | --- |
| `ax650/cls_npu1.axmodel` | 方向分类 |
| `ax650/det_npu1.axmodel` | 文本检测 |
| `ax650/rec_npu1.axmodel` | 文字识别 |

```bash
cd "$MODEL_DIR"
INPUT="$MODEL_DIR/11.jpg"
OUT=~/edgeaccel/results/ppocr-v5-npu1/original
mkdir -p "$OUT"
set -o pipefail
python infer_axmodel.py \
  --img_path "$INPUT" --det_model_dir ax650/det_npu1.axmodel \
  --rec_model_dir ax650/rec_npu1.axmodel --cls_model_dir ax650/cls_npu1.axmodel \
  --character_dict_path ppocrv5_dict.txt 2>&1 | tee "$OUT/run.log"
cp res_ax.jpg "$OUT/result.jpg"
```

识别文本逐行写入 `run.log`，结果图为 `OUT/result.jpg`。检查三个模型均加载成功、没有设备错误，并逐行比对图片中的文字。标题正确不代表金额、编号和细字全部正确。

### 检查倒置图片

在同一终端生成180°旋转输入，并设置独立输出目录：

```bash
OUT=~/edgeaccel/results/ppocr-v5-npu1/rotated180
mkdir -p "$OUT"
python - "$MODEL_DIR/11.jpg" "$OUT/input.png" <<'PY'
import cv2, sys
image = cv2.imread(sys.argv[1])
assert image is not None
assert cv2.imwrite(sys.argv[2], cv2.rotate(image, cv2.ROTATE_180))
PY
INPUT="$OUT/input.png"
python infer_axmodel.py \
  --img_path "$INPUT" --det_model_dir ax650/det_npu1.axmodel \
  --rec_model_dir ax650/rec_npu1.axmodel --cls_model_dir ax650/cls_npu1.axmodel \
  --character_dict_path ppocrv5_dict.txt 2>&1 | tee "$OUT/run.log"
cp res_ax.jpg "$OUT/result.jpg"
```

查看倒置输入对应的新结果图及识别文字。方向分类纠正的是文本裁剪，输出可视化仍保留倒置原图；两种输入的检测框或文字不一定完全相同。


## 查看部署效果

### NPU1完整链路：16GB卡样例

**已运行，效果仍需评估** · RK3576 DshanPi A1 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

检测、方向分类、识别三个NPU1权重完成完整链路。官方原图独立运行两次，再运行180°倒置输入；保存原始输出并独立解码文字。

**原图**

完整检测、方向分类和识别链路产生16个文本裁剪，最终保留16项识别结果。方向分类中0个裁剪预测为180°且分数超过0.9。四个短字段的精确子串核对命中4/4，仅用于样例对照。结果图标出文本行并列出中文识别文字，标题、编号与净含量可核对；标点与空格仍应逐项检查。 原图两次独立进程的输入张量、输出张量、识别文字和结果图完全一致。

<div className="model-effect-gallery">

<figure>

[![原图实际输入](../../../static/validation/effects/ppocr-v5-variants-20261005/input-0.png)](../../../static/validation/effects/ppocr-v5-variants-20261005/input-0.png)

<figcaption>原图实际输入</figcaption>
</figure>

<figure>

[![原图实际识别输出](../../../static/validation/effects/ppocr-v5-variants-20261005/output-0.jpg)](../../../static/validation/effects/ppocr-v5-variants-20261005/output-0.jpg)

<figcaption>原图实际识别输出</figcaption>
</figure>

</div>

| 序号 | 实际识别文本 | 分数 |
| --- | --- | --- |
| 1 | 纯臻营养护发素 | 0.9881 |
| 2 | 产品信息/参数 | 0.9942 |
| 3 | (45元/每公斤，100公斤起订） | 0.9549 |
| 4 | 每瓶22元，1000瓶起订） | 0.9522 |
| 5 | 【品牌】：代加工方式/OEMODM | 0.9873 |
| 6 | 【品名】：纯臻营养护发素 | 0.9896 |
| 7 | 【产品编号】：YM-X-3011 | 0.9854 |
| 8 | ODMOEM | 0.8155 |
| 9 | 【净含量】：220ml | 0.9779 |
| 10 | 【适用人群】：适合所有肤质 | 0.9893 |
| 11 | 【主要成分】：鲸蜡硬脂醇、燕麦β-葡聚 | 0.9715 |
| 12 | 糖、椰油酰胺丙基甜菜碱、泛醌 | 0.9864 |
| 13 | (成品包材) | 0.8738 |
| 14 | 【主要功能】：可紧致头发磷层，从而达到 | 0.9911 |
| 15 | 即时持久改善头发光泽的效果，给干燥的头 | 0.9936 |
| 16 | 发足够的滋养 | 0.9879 |

| 人工读取的样图字段 | 精确子串核对 |
| --- | --- |
| 纯臻营养护发素 | 命中 |
| 产品信息/参数 | 命中 |
| YM-X-3011 | 命中 |
| 220ml | 命中 |

**180°倒置图**

完整检测、方向分类和识别链路产生16个文本裁剪，最终保留16项识别结果。方向分类中16个裁剪预测为180°且分数超过0.9。四个短字段的精确子串核对命中4/4，仅用于样例对照。倒置图的16个文本裁剪均触发180°纠正，文字列表恢复为正向阅读。结果图保留原图朝向，文本顺序随检测位置改变。

<div className="model-effect-gallery">

<figure>

[![180°倒置图实际输入](../../../static/validation/effects/ppocr-v5-variants-20261005/input-180.png)](../../../static/validation/effects/ppocr-v5-variants-20261005/input-180.png)

<figcaption>180°倒置图实际输入</figcaption>
</figure>

<figure>

[![180°倒置图实际识别输出](../../../static/validation/effects/ppocr-v5-variants-20261005/output-180.jpg)](../../../static/validation/effects/ppocr-v5-variants-20261005/output-180.jpg)

<figcaption>180°倒置图实际识别输出</figcaption>
</figure>

</div>

| 序号 | 实际识别文本 | 分数 |
| --- | --- | --- |
| 1 | 发足够的滋养 | 0.9854 |
| 2 | 即时持久改善头发光泽的效果，给干燥的头 | 0.9959 |
| 3 | 【主要功能】：可紧致头发磷层，从而达到 | 0.9936 |
| 4 | (成品包材) | 0.8870 |
| 5 | 糖、椰油酰胺丙基甜菜碱、泛醌 | 0.9866 |
| 6 | 【主要成分】：鲸蜡硬脂醇、燕麦β-葡聚 | 0.9839 |
| 7 | 【适用人群】：适合所有肤质 | 0.9938 |
| 8 | ODMOEM | 0.8755 |
| 9 | 【净含量】：220ml | 0.9723 |
| 10 | 【产品编号】：YM-X-3011 | 0.9834 |
| 11 | 【品名】：纯臻营养护发素 | 0.9872 |
| 12 | 【品牌】：代加工方式/OEMODM | 0.9812 |
| 13 | 每瓶22元，1000瓶起订） | 0.9547 |
| 14 | (45元/每公斤，100公斤起订） | 0.9350 |
| 15 | 产品信息/参数 | 0.9942 |
| 16 | 纯臻营养护发素 | 0.9491 |

| 人工读取的样图字段 | 精确子串核对 |
| --- | --- |
| 纯臻营养护发素 | 命中 |
| 产品信息/参数 | 命中 |
| YM-X-3011 | 命中 |
| 220ml | 命中 |

识别内容节选：

```text
纯臻营养护发素
YM-X-3011
220ml
```

**使用时注意：**

- 仅一张官方样图及其旋转版本；四个短字段命中不等于整页无错，未计算整页CER/WER，也未验证独立数据集精度。
- 16GB卡实测不能替代新增权重的8GB回归；图片中的细字、竖排和相近汉字仍需逐项核对。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### 原规格：8GB卡样例

**固定样例已核对** · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

对 500×500 护发素商品图逐区核对：输出 16 个文本区域，标题“纯臻营养护发素”、产品编号“YM-X-3011”、净含量“220ml”、价格和主要说明与原图基本一致，竖排瓶身文字也被检出。识别文本存在空格合并和标点宽度差异。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/ppocr-v5/inputs/11.jpg)](../../../static/validation/effects/ppocr-v5/inputs/11.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![实际输出](../../../static/validation/effects/ppocr-v5/outputs/res_ax.jpg)](../../../static/validation/effects/ppocr-v5/outputs/res_ax.jpg)

<figcaption>实际输出</figcaption>
</figure>

</div>

识别内容节选：

```text
纯臻营养护发素
YM-X-3011
220ml
```

**使用时注意：**

- correctness 仅表示这张固定图片的主要字词经过人工对照，不是数据集准确率或全文逐字符无误认证。
- 原图品牌行 OEM ODM 被输出为 OEMODM，瓶身 ODM OEM 被输出为 ODMOEM；括号存在全半角差异。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**NPU1完整链路：16GB卡样例**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 16GB M.2。模型版本：`fed5e0b6eaac3e34b01cb3919e0df7810296d850`。

| 组件 | 版本或配置 |
| --- | --- |
| AXCL / 固件 | V3.16.0_20260729180218 / V3.16.0 |
| Python依赖 | NumPy1.26.4、OpenCV4.11.0、Shapely2.0.7、pyclipper1.4.0、PyYAML6.0.3 |
| 后端与输入 | AXCLRTExecutionProvider；官方11.jpg及其180°旋转图，原图独立启动两次 |
| 设备状态 | 每次程序退出后恢复空闲18MiB，主机及卡启动标识保持不变 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 原图 / cls_npu1.axmodel | 16次；3.120–3.603 ms | session.run墙钟，含数据传输，不含模型加载、前后处理及存盘；含首次调用，不代表持续吞吐。 |
| 原图 / det_npu1.axmodel | 1次；118.707–118.707 ms | session.run墙钟，含数据传输，不含模型加载、前后处理及存盘；含首次调用，不代表持续吞吐。 |
| 原图 / rec_npu1.axmodel | 16次；18.201–20.415 ms | session.run墙钟，含数据传输，不含模型加载、前后处理及存盘；含首次调用，不代表持续吞吐。 |
| 180°倒置图 / cls_npu1.axmodel | 16次；3.052–3.534 ms | session.run墙钟，含数据传输，不含模型加载、前后处理及存盘；含首次调用，不代表持续吞吐。 |
| 180°倒置图 / det_npu1.axmodel | 1次；118.968–118.968 ms | session.run墙钟，含数据传输，不含模型加载、前后处理及存盘；含首次调用，不代表持续吞吐。 |
| 180°倒置图 / rec_npu1.axmodel | 16次；20.331–20.552 ms | session.run墙钟，含数据传输，不含模型加载、前后处理及存盘；含首次调用，不代表持续吞吐。 |

</details>

**原规格：8GB卡样例**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。模型版本：`fed5e0b6eaac3e34b01cb3919e0df7810296d850`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| C++ 视觉示例提交 | cbfa4c76891758983ca2b0c99c11d6621d59af39 |
| Python 后端 | Python 3.12.3；PyAXEngine 0.1.3.rc3 发布的 0.1.3 wheel；NumPy 1.26.4 / ml-dtypes 0.5.3 |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 检出并识别的文本区域 | 16 | run.log 的 16 条文字结果；已对照输入图与 res_ax.jpg |
| 检测 session.run 时延 | 112.25 | 毫秒；1 次主机墙钟，包含 AXCL 调用及复制，排除张量统计 |
| 文本识别平均 session.run 时延 | 16.23 | 毫秒/裁剪；同图 16 次识别调用的算术平均，包含 AXCL 调用及复制 |
| 方向分类平均 session.run 时延 | 2.32 | 毫秒/裁剪；同图 16 次分类调用的算术平均，包含 AXCL 调用及复制 |
| 输入图片尺寸 | 500×500 | 实际 11.jpg 文件头；可视化输出 res_ax.jpg 为 1200×600 拼图 |
| session.run：det_npu3.axmodel | 112.251 ms / 1 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |
| session.run：rec_npu3.axmodel | 16.225 ms / 16 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |
| session.run：cls_npu3.axmodel | 2.320 ms / 16 次 | 实际 AXCL Python 调用墙钟，含数据复制；不含返回后的张量统计。含首次调用，非统一预热基准；多阶段模型各自计时 |

适用范围：

- 未计算 CER/WER，未测试倾斜、低光、密集文本或其它字体。模型置信度不等于人工确认的准确率。
- 检测、识别与方向分类分别计时，识别与分类均为同一图片的 16 个文本裁剪，不能当作 16 次独立整图测试。
- 运行源码包含显式 AXCL 后端或本页说明的适配修改；result.json 保存逐项替换及修改后 SHA256。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`ax650/det_npu3.axmodel`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/ax650/det_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`11.jpg`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/11.jpg) | 示例输入 |
| [`ax650/rec_npu3.axmodel`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/ax650/rec_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax650/cls_npu3.axmodel`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/ax650/cls_npu3.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ppocrv5_dict.txt`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/ppocrv5_dict.txt) | 分词器 / 字典，必须配套 |
| [`simfang.ttf`](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/simfang.ttf) | 配套资源 |

仓库提交：`fed5e0b6eaac3e34b01cb3919e0df7810296d850`。仓库中的 15 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/PPOCR_v5/tree/fed5e0b6eaac3e34b01cb3919e0df7810296d850)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 需要文本检测、裁剪和识别模型及字典；各阶段输入尺寸不同。
- 完整输入集合还包括 ppocrv5_dict.txt 和 simfang.ttf；缺少字典会影响字符映射，缺少字体会影响中文结果图。检测、识别、方向分类三个 AXCL 会话分别检查。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/PPOCR_v5/tree/fed5e0b6eaac3e34b01cb3919e0df7810296d850)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/README.md)。
- [主要程序入口：infer_axmodel.py](https://huggingface.co/AXERA-TECH/PPOCR_v5/blob/fed5e0b6eaac3e34b01cb3919e0df7810296d850/infer_axmodel.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/PPOCR_v5)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
