---
title: "Qwen2.5-VL-3B-Instruct 部署指南"
sidebar_label: "Qwen2.5-VL-3B-Instruct"
description: "Qwen2.5-VL-3B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-VL-3B-Instruct 部署指南

Qwen2.5-VL-3B-Instruct 用于图像与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-VL-3B-Instruct` 的固定版本。下面下载本页选用的 80 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-vl-3b-instruct/d967363ac68e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-VL-3B-Instruct \
  --include "*" \
  --revision d967363ac68ee8c46a46110b8ee92f0f0cb332cb \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 AXCL 运行程序

本例适用于 RK3576 + AX8850 16GB M.2 算力卡、Ubuntu 24.04 ARM64、Python 3.12 和 AXCL 3.16。使用官方标准版 W8A16 权重，图片输入为 448×448，视频帧输入为 308×308。模型文件约 5.95 GB，建议预留至少 8 GB 存储空间。

下载[配套运行包](/examples/qwen25-vl3b-standard-20261002.tar.gz)，保存到连接算力卡的 Linux 主机 `~/edgeaccel/`。包内包含已测试的 ARM64 程序、分词服务、配置及适配源码。

```bash
cd ~/edgeaccel
tar -xzf qwen25-vl3b-standard-20261002.tar.gz
cd qwen25-vl3b-standard
sudo apt update
sudo apt install -y libopencv-dev libssl-dev
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'transformers==4.51.3' 'torch==2.5.1'
python verify_models.py "$MODEL_DIR"
ldd ./main_axcl_aarch64
```

`MODEL_DIR` 沿用前文的下载目录。校验应输出 `Verified 80 model files`；`ldd` 不应出现 `not found`。若已有 Python 虚拟环境使用其他路径，替换激活路径。Python 服务负责分词和解码，原生 AXCL 程序执行推理。

## 运行图片问答

在第一个终端启动图片分词服务，并保留运行：

```bash
cd ~/edgeaccel/qwen25-vl3b-standard
source ~/edgeaccel/python-env/bin/activate
python tokenizer_image.py --host 127.0.0.1 --port 8511
```

在连接算力卡的第二个终端执行：

```bash
cd ~/edgeaccel/qwen25-vl3b-standard
source ~/edgeaccel/python-env/bin/activate
MODEL_DIR=~/edgeaccel/models/qwen2-5-vl-3b-instruct/d967363ac68e
python run_model.py image --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/image/ssd_car.jpg" \
  --prompt 'Describe the main vehicle and its color in this image.'
python run_model.py image --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/image/ssd_horse.jpg" \
  --prompt '请用两句中文描述画面前景中的动物和人物。'
python run_model.py image --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/image/ssd_horse.jpg" \
  --prompt 'How many dogs are visible in the foreground? Reply with only the number.'
```

每条命令重新加载模型，输出回答后退出并释放资源。实际回答见下方效果展示。启动日志应出现 `load config:`。问答结束时确认 `termination_reason=eos last_token=151645`、进程退出码为 0，并检查回答内容和设备空闲状态。

## 运行视频帧问答

在第一个终端按 `Ctrl+C` 停止图片分词服务，切换为视频分词服务：

```bash
python tokenizer_video.py --host 127.0.0.1 --port 8511
```

在保留 `MODEL_DIR` 的第二个终端执行：

```bash
python run_model.py video --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" --prompt '描述这个视频的内容'
python run_model.py video --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" --prompt 'Describe this video.'
```

本例读取官方 `video` 目录内按文件名排序的 8 张 JPEG，按 1 fps 输入，视觉编码器每两帧执行一次。此配置的输入长度上限为 512 token，8 帧及上述问题共占用 509 token；不要直接增加帧数或改成长问题。1 fps 用于这组帧序列，不代表原视频真实帧率。原始视频解码、抽帧和实时输入需另行接入。

运行结束后检查 `axcl-smi`，确认测试进程已退出。本页实测使用经校验的主机只读网络挂载目录；进程耗时包含文件读取、模型加载和推理，不能用作本地 SSD 的速度基准。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成三组图片问答和两组八帧视频问答，展示原始输出及核对结果。

**三组图片问答**

以下为固定官方输入的原始回答。每次问答使用独立进程；耗时包含网络文件读取、模型加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方输入：红色双层巴士与街道](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/ssd_car.jpg)](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/ssd_car.jpg)

<figcaption>官方输入：红色双层巴士与街道</figcaption>
</figure>

<figure>

[![官方输入：骑乘者、马和狗](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/ssd_horse.jpg)](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/ssd_horse.jpg)

<figcaption>官方输入：骑乘者、马和狗</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Describe the main vehicle and its color in this image.
```

**实际回复**

```text
The main vehicle in the image is a red double-decker bus.
```

识别出的红色双层巴士与输入图片相符。

**示例 2：输入**

```text
请用两句中文描述画面前景中的动物和人物。
```

**实际回复**

```text
前景中是一只棕色的狗，它正张着嘴，似乎在叫或吠叫。
```

回答只描述狗，遗漏同一画面中的马和骑乘者，且未按要求给出两句话；狗是否在吠叫无法从静态图片确认。

**示例 3：输入**

```text
How many dogs are visible in the foreground? Reply with only the number.
```

**实际回复**

```text
1
```

前景可见一只狗，回答与图片一致，并遵守只输出数字的要求。

| 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| ssd_car.jpg | 131.460 | 628 |
| ssd_horse.jpg | 134.269 | 887 |
| ssd_horse.jpg | 128.232 | 147 |

**两组八帧视频问答**

以下为固定官方输入的原始回答。每次问答使用独立进程；耗时包含网络文件读取、模型加载和推理。

<div className="model-effect-gallery">

<figure>

[![视频帧输入：第 1 帧](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/frame_0000.jpg)](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/frame_0000.jpg)

<figcaption>视频帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 4 帧](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/frame_0024.jpg)](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/frame_0024.jpg)

<figcaption>视频帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![视频帧输入：第 8 帧](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/frame_0056.jpg)](../../../static/validation/effects/qwen2-5-vl-3b-instruct-20261002/frame_0056.jpg)

<figcaption>视频帧输入：第 8 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
描述这个视频的内容
```

**实际回复**

```text
视频展示了两只松鼠在户外的场景。背景是模糊的山脉和蓝天，前景中有松鼠在互动。松鼠的毛色是棕色和灰色的混合，它们的爪子是橙色的。松鼠似乎在互相玩耍或争抢，它们的爪子和嘴巴都伸向对方。整个场景显得非常自然和生动。
```

两只动物、山地背景和相互接近的描述与输入帧基本相符。“松鼠”“玩耍或争抢”属于模型推测，未作为物种或行为标签验收。

**示例 2：输入**

```text
Describe this video.
```

**实际回复**

```text
The video shows two ground squirrels engaging in a playful interaction on a rocky path. The squirrels are facing each other, and their front paws are raised, as if they are playfully bumping or scratching each other. The background features a scenic mountain landscape with green hills and a clear blue sky. The squirrels' fur is a mix of brown, white, and black, and they appear to be enjoying their playful moment in the natural environment.
```

两只动物在岩石上相向、抬起前肢的描述与帧序列相符。“ground squirrels”“playful”及“enjoying”属于未经确认的物种、行为或情绪推测。

| 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- |
| video | 151.214 | 2924 |
| video | 154.956 | 3553 |

**使用时注意：**

- 中文图片回答遗漏马和骑乘者，且未按要求给出两句话；本次仅确认基本运行，不代表回答完整性达标。
- 视频中的物种名称、玩耍或争抢及情绪描述为模型生成内容，未经独立标注确认。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`d967363ac68ee8c46a46110b8ee92f0f0cb332cb`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 固定 AXCL C++ 配套程序 / techshoww/ax-llm 9c2921c + mRoPE、KV 缓存与配置修复 / HTTP 分词 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输入覆盖 | 2 张图片 / 8 帧视频 | 3 条图片问题、2 条视频问题，五个独立进程。 |
| 算力卡执行 | 39 个 AXModel | 图片和视频使用不同视觉模型；全部实际执行并释放，共 8139 次原生调用。 |
| 视觉输入 | 图片 448×448 / 视频 308×308 | 图片每次 1 组、8 帧视频每次 4 组视觉执行。 |

适用范围：

- 视频为官方八张 JPEG 按 1 fps 输入；未验证原始视频抽帧或实时视频。八帧加本例短问题占 509 token，输入上限为 512 token。
- 请使用本页配套的固定版本运行程序。五次问答均正常结束；尚未进行全部张量与浮点参考模型对照。
- 实际 8GB 卡、长上下文、多轮及连续运行仍需独立验证；本次网络模型读取耗时不代表本地存储性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_qwen2_5_vl_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/run_qwen2_5_vl_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen2_tokenizer_images.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_tokenizer_images.py) | 旧版分词服务入口 |
| [`qwen2_tokenizer_video_308.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_tokenizer_video_308.py) | 旧版分词服务入口 |
| [`Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/Qwen2.5-VL-3B-Instruct_vision_nchw448.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/Qwen2.5-VL-3B-Instruct_vision_nchw448.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/Qwen2.5-VL-3B-Instruct_vision_nhwc.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/Qwen2.5-VL-3B-Instruct_vision_nhwc.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/qwen2_5_vl_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/qwen2_5_vl_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/qwen2_5_vl_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/qwen2_5_vl_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/qwen2_5_vl_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/Qwen2.5-VL-3B-Instruct-AX650-chunk_prefill_512/qwen2_5_vl_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/config.json) | 运行配置 |
| [`qwen2_5-vl-tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_5-vl-tokenizer/config.json) | 运行配置 |
| [`qwen2_5-vl-tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_5-vl-tokenizer/generation_config.json) | 运行配置 |
| [`qwen2_5-vl-tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_5-vl-tokenizer/preprocessor_config.json) | 运行配置 |
| [`qwen2_5-vl-tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_5-vl-tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2_5_vl_image.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/run_qwen2_5_vl_image.sh) | 启动或构建脚本 |

仓库提交：`d967363ac68ee8c46a46110b8ee92f0f0cb332cb`。仓库中的 39 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/tree/d967363ac68ee8c46a46110b8ee92f0f0cb332cb)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/tree/d967363ac68ee8c46a46110b8ee92f0f0cb332cb)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/README.md)。
- [主要程序入口：qwen2_tokenizer_images.py](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct/blob/d967363ac68ee8c46a46110b8ee92f0f0cb332cb/qwen2_tokenizer_images.py)。
- [配套项目：AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera](https://github.com/AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera)。

返回[完整模型目录](../catalog.mdx)。
