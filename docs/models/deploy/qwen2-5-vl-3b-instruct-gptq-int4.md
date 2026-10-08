---
title: "Qwen2.5-VL-3B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen2.5-VL-3B-Instruct-GPTQ-Int4"
description: "Qwen2.5-VL-3B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-VL-3B-Instruct-GPTQ-Int4 部署指南

Qwen2.5-VL-3B-Instruct-GPTQ-Int4 用于图像与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 实测未完成。[查看部署效果](#查看部署效果)。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4` 的固定版本。下面下载本页选用的 56 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-vl-3b-instruct-gptq-int4/3cccf4c9262c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4 \
  --include "*" \
  --revision 3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

> 配套程序正在更新，请暂缓使用本页运行包。后续将替换为复测通过的版本。

## 准备 AXCL 运行程序

本例适用于 RK3576 + AX8850 16GB M.2 算力卡、Ubuntu 24.04 ARM64、Python 3.12 和 AXCL 3.16。使用官方 Int4 权重、392×392 视觉输入和配套 AXCL 程序。模型约 3.70 GB，建议预留至少 5 GB 存储空间。

下载[配套运行包](/examples/qwen25-vl3b-int4-20261002.tar.gz)，保存到连接算力卡的 Linux 主机 `~/edgeaccel/`。包内包含已测试的 ARM64 程序、分词服务、固定配置和适配源码。

```bash
cd ~/edgeaccel
tar -xzf qwen25-vl3b-int4-20261002.tar.gz
cd qwen25-vl3b-int4
sudo apt update
sudo apt install -y libopencv-dev libssl-dev
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'transformers==4.51.3' 'torch==2.5.1'
python verify_models.py "$MODEL_DIR"
ldd ./main_axcl_aarch64
```

`MODEL_DIR` 沿用前文的下载目录。校验应输出 `Verified 56 model files`；`ldd` 不应出现 `not found`。若已有 PyAXEngine 虚拟环境使用其他路径，替换激活路径。推理由原生 AXCL 程序执行，Python 服务负责分词和解码。

当前运行包采用内置贪心解码。此版本的 `post_config_path` 参数未传入运行器，不能用它调整采样策略；包内配置与内置默认值一致。

## 运行图片问答

在第一个终端启动图片分词服务，并保留运行：

```bash
cd ~/edgeaccel/qwen25-vl3b-int4
source ~/edgeaccel/python-env/bin/activate
python tokenizer_image.py --host 127.0.0.1 --port 8511
```

在连接算力卡的第二个终端执行；若新终端没有 `MODEL_DIR`，先设置为前文的下载目录：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-vl-3b-instruct-gptq-int4/3cccf4c9262c
cd ~/edgeaccel/qwen25-vl3b-int4
export EDGEACCEL_QWEN_BINARY="$PWD/main_axcl_aarch64"
export EDGEACCEL_QWEN_WEIGHTS="$MODEL_DIR/Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4"
export EDGEACCEL_TOKENIZER_URL=http://127.0.0.1:8511
bash run_single_candidate.sh image "$MODEL_DIR/image/ssd_horse.jpg" \
  '请用中文描述图片中的主要对象。'
bash run_single_candidate.sh image "$MODEL_DIR/image/ssd_car.jpg" \
  'Describe the main objects visible in the image.'
```

每条命令重新加载模型，输出回答后退出并释放算力卡资源。实际回答见下方效果展示。日志中的 `hit eos` 为原程序通用结束提示，不能单独作为自然结束的证明；同时检查退出码、回答完整性和设备空闲状态。

## 运行视频帧问答

在第一个终端按 `Ctrl+C` 停止图片分词服务，切换为视频分词服务：

```bash
python tokenizer_video.py --host 127.0.0.1 --port 8511
```

在保留上述环境变量的第二个终端执行：

```bash
export EDGEACCEL_VIDEO_FPS=1
bash run_single_candidate.sh video "$MODEL_DIR/video" \
  '请用中文描述视频画面中的主要对象及其变化。'
```

本例读取官方 `video` 目录内按文件名排序的 8 张 JPEG，按 1 fps 输入，视觉编码器每两帧执行一次。该设定用于这组帧序列，不代表原视频真实帧率；原始视频解码、抽帧和实时输入仍需另行接入。

运行结束后检查 `axcl-smi`，确认测试进程已退出。模型也可放在已校验的只读挂载目录；本页实测采用主机网络挂载，耗时包含文件读取和模型加载，不能用作本地 SSD 的速度基准。


## 查看部署效果

**部署效果待验证**

配套运行程序正在更新，本页旧结果暂不作为部署验收依据。待同条件复测后更新运行包与效果。

当前没有可展示的成功运行结果。

- 使用已知内容的单张图片提问，回答应包含可核对的图像细节。
- 再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/Qwen2.5-VL-3B-Instruct_vision_image_392.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/Qwen2.5-VL-3B-Instruct_vision_image_392.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/Qwen2.5-VL-3B-Instruct-AX650-c128_p1536-ctx2047-int4/qwen2_5_vl_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/config.json) | 运行配置 |
| [`run_qwen2_5_vl_image.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/run_qwen2_5_vl_image.sh) | 启动或构建脚本 |
| [`run_qwen2_5_vl_video.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/run_qwen2_5_vl_video.sh) | 启动或构建脚本 |

仓库提交：`3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/tree/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/tree/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-3B-Instruct-GPTQ-Int4/blob/3cccf4c9262c3c656ae1c84a19e2e91d8f3b0c9e/README.md)。
- [配套项目：AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera](https://github.com/AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera)。

返回[完整模型目录](../catalog.mdx)。
