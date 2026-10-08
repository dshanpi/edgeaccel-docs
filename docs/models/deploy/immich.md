---
title: "immich 部署指南"
sidebar_label: "immich"
description: "immich 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# immich 部署指南

immich 用于图文匹配。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/immich` 的固定版本。下面下载本页选用的 3 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/immich/81c75d735f40
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/immich \
  --include "README.md" "requirements.txt" "immich_ml-2.7.5-py3-none-any.whl" \
  --revision 81c75d735f4087a4359ff152646436da1685af1c \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装图片检索服务

本页使用 Immich 2.7.5 官方 ML 服务，通过 M.2 算力卡生成图片与文本向量。中英文各使用一套 CLIP 编码器，每个向量为 768 维。本例验证的是 ML 检索接口；完整相册的上传、索引任务和网页界面另行部署。

下载[本页配套运行包](../../../static/examples/immich-ml-20261001.tar.gz)，保存到 Linux 主机的 `~/edgeaccel`。运行包包含服务启动器、固定依赖清单和三张官方样图，不包含模型权重。保留前文的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf immich-ml-20261001.tar.gz
sudo apt-get install -y python3-venv python3-dev build-essential libgl1
python3 -m venv ~/edgeaccel/immich-env
source ~/edgeaccel/immich-env/bin/activate
python -m pip install -c ~/edgeaccel/immich-ml/constraints.txt \
  setuptools wheel Cython 'numpy==1.26.4'
python -m pip install --no-build-isolation \
  -c ~/edgeaccel/immich-ml/constraints.txt \
  "$MODEL_DIR/immich_ml-2.7.5-py3-none-any.whl" \
  'onnxruntime>=1.23.2,<2' 'opencv-python-headless==4.11.0.86' requests cffi
python -m pip check
python -c 'import immich_ml.main; print("Immich ML 导入成功")'
```

本次环境为 Python 3.12.3。服务使用官方 wheel 内置的 AXEngine 接口；启动器强制指定 `AXCLRTExecutionProvider`，按模型实际输入名称绑定图片或文本张量，并串行执行请求。ONNX Runtime 是服务的导入依赖，本例四个编码器均在 AXCL 后端运行。

## 下载中英文编码器

Immich 应用仓库不包含 `.axmodel`。将下面两套固定版本权重放到同一目录下的两个子目录，不要混用中英文文本与图片编码器。

```bash
CLIP_ROOT=~/edgeaccel/models/immich-clips
mkdir -p "$CLIP_ROOT"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/ViT-L-14-336__axera \
  --revision d461cbe322991aaec35a359b0defc81356c8db46 \
  --include 'config.json' 'textual/*' 'visual/*' \
  --local-dir "$CLIP_ROOT/ViT-L-14-336__axera"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/ViT-L-14-336-CN__axera \
  --revision c99ea50e6f0e3ae9146239035a8217998bb0eda7 \
  --include 'config.json' 'textual/*' 'visual/*' \
  --local-dir "$CLIP_ROOT/ViT-L-14-336-CN__axera"
python ~/edgeaccel/immich-ml/verify_models.py --root "$CLIP_ROOT"
```

两套模型共约 980 MB。校验应显示 18 个文件全部一致；失败时先核对下载文件，不继续启动模型。存储不足时，可将 `CLIP_ROOT` 和虚拟环境放在已挂载且空间充足的存储设备上。

## 运行中英文检索

使用新的结果目录名。程序启动本机 ML 服务，依次发送鸟、猫、狗图片与对应中英文短文本，每项重复两次；结束后自动关闭服务。

```bash
cd ~/edgeaccel/immich-ml
python immich_retrieval_card.py \
  --models "$CLIP_ROOT" \
  --wheel "$MODEL_DIR/immich_ml-2.7.5-py3-none-any.whl" \
  --fixtures fixtures \
  --service-script immich_service_trace.py \
  --output ~/edgeaccel/results/immich-retrieval-01
```

成功后，`deployment-result.json` 中应有 `completed: true`、24 条 HTTP 200 请求和两套相似度矩阵。每套矩阵的行按鸟、猫、狗图片排列，列为对应文本；余弦相似度越高，表示当前模型判断越相关，不是识别概率。

```bash
python - <<'PY'
import json
from pathlib import Path
r = json.loads((Path.home() / 'edgeaccel/results/immich-retrieval-01/deployment-result.json').read_text())
assert r['completed'] and len(r['requests']) == 24
for item in r['retrieval']:
    print(item['language'], item['texts'])
    for scores in item['cosine']:
        print([round(value, 4) for value in scores])
    print('文本检索到的图片序号：', item['textToImageTop'])
PY
```

## 接入自己的图片与文本

需要单独调用接口时，在前台启动服务，保持该终端运行：

```bash
python ~/edgeaccel/immich-ml/immich_service_trace.py \
  --models "$CLIP_ROOT" \
  --wheel "$MODEL_DIR/immich_ml-2.7.5-py3-none-any.whl" \
  --output ~/edgeaccel/results/immich-service-01 --port 3003
```

在主机另一终端执行：

```bash
curl --noproxy '*' http://127.0.0.1:3003/ping
curl --noproxy '*' http://127.0.0.1:3003/predict \
  -F 'entries={"clip":{"textual":{"modelName":"ViT-L-14-336-CN__axera","options":{}}}}' \
  -F 'text=一只猫'
curl --noproxy '*' http://127.0.0.1:3003/predict \
  -F 'entries={"clip":{"visual":{"modelName":"ViT-L-14-336-CN__axera","options":{}}}}' \
  -F "image=@$HOME/edgeaccel/immich-ml/fixtures/images/cat.jpg"
```

将最后一条命令的图片路径替换为自己的文件。`/ping` 返回 `pong`；`/predict` 的 `clip` 字段为 JSON 编码的向量。先分别对图片和文本向量作 L2 归一化，再计算点积并排序。关闭服务时在服务终端按 `Ctrl+C`。

启动器仅启用本页的两套 CLIP，使用固定本地文件，不自动下载人脸或 OCR 模型。更换检索模型后，应重新生成全部图片向量，不能沿用旧模型的索引。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡运行官方 Immich 2.7.5 ML 服务，完成中英文图文检索与重复输入检查。

**实际 ML 服务：中英文图片检索**

本次六个中英文短文本查询均将对应图片排在第一位，三张图片反查文本的首选也一致。每个输入重复两次，原始 768 维向量逐元素一致。表中使用 L2 归一化后的余弦相似度，不是分类概率；三张样图的结果不能代表大规模图库准确率。

<div className="model-effect-gallery">

<figure>

[![输入图片：鸟](../../../static/validation/effects/immich-20261001/bird.jpg)](../../../static/validation/effects/immich-20261001/bird.jpg)

<figcaption>输入图片：鸟</figcaption>
</figure>

<figure>

[![输入图片：猫](../../../static/validation/effects/immich-20261001/cat.jpg)](../../../static/validation/effects/immich-20261001/cat.jpg)

<figcaption>输入图片：猫</figcaption>
</figure>

<figure>

[![输入图片：狗](../../../static/validation/effects/immich-20261001/dog-chai.jpeg)](../../../static/validation/effects/immich-20261001/dog-chai.jpeg)

<figcaption>输入图片：狗</figcaption>
</figure>

</div>

| 语言 | 文本查询 | 鸟图片 | 猫图片 | 狗图片 | 首选图片 |
| --- | --- | --- | --- | --- | --- |
| en | a bird | 0.2324 | 0.1590 | 0.1753 | 鸟 |
| en | a cat | 0.1416 | 0.2374 | 0.1912 | 猫 |
| en | a dog | 0.1374 | 0.1764 | 0.2457 | 狗 |
| zh | 一只鸟 | 0.2810 | 0.2384 | 0.2368 | 鸟 |
| zh | 一只猫 | 0.2139 | 0.3114 | 0.2484 | 猫 |
| zh | 一只狗 | 0.2085 | 0.2421 | 0.2880 | 狗 |

| HTTP 请求 | AXCL 调用 | 向量维度 | 完整流程耗时 |
| --- | --- | --- | --- |
| 24 次成功 | 24 次 | 768 | 36.299 s |

**使用时注意：**

- 本次为 16GB 卡的 ML HTTP 检索基本验证，完整相册网页、照片上传、任务队列、数据库索引、人脸和 OCR 未验证。
- 测试使用三张官方样图及六个中英文短文本；未完成大规模图库、复杂语义、多用户并发或长时间稳定性评估。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`81c75d735f4087a4359ff152646436da1685af1c`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12.3 / Immich ML 2.7.5 官方 wheel 内置 AXEngine / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 应用范围 | 真实 /predict 接口 | 24 次 HTTP 请求实际调用算力卡；完整相册网页、上传和索引任务尚未验证。 |
| 配套模型 | 中英文 4 个编码器 | 两个固定版本 CLIP 仓库，各含图片和文本编码器；不是 Immich 仓库内自带权重。 |
| 结果维度 | 768 | 保存原始向量，再作 L2 归一化计算相似度；同输入重复结果一致。 |

适用范围：

- 重复输入一致不代表数据集级精度通过；真实 8GB 容量回归另行执行。
- 完整流程耗时含服务启动、模型加载、文件校验、HTTP 请求和原始结果保存，不代表单次在线检索延迟。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/immich/blob/81c75d735f4087a4359ff152646436da1685af1c/config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/immich/blob/81c75d735f4087a4359ff152646436da1685af1c/requirements.txt) | Python 依赖清单 |

仓库提交：`81c75d735f4087a4359ff152646436da1685af1c`。该提交没有预编译 `.axmodel` 文件。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/immich/tree/81c75d735f4087a4359ff152646436da1685af1c)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 该提交未直接列出 .axmodel 文件；先核对模型卡指向的实际权重或程序仓库，不能将该目录直接交给 axcl_run_model。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/immich/tree/81c75d735f4087a4359ff152646436da1685af1c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/immich/blob/81c75d735f4087a4359ff152646436da1685af1c/README.md)。

返回[完整模型目录](../catalog.mdx)。
