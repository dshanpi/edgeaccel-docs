---
title: "Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 部署指南"
sidebar_label: "Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047"
description: "Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 部署指南

Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL 专用脚本。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-2b-instruct-gptq-int4-p1536-ctx2047/cf4b904ba59e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047 \
  --revision cf4b904ba59e66fefd17668af196fc9c199ab70f \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 选择 AXCL 启动入口

此包使用旧版专用程序，保留其脚本、分片和 tokenizer 服务组合。不能直接替换成新版 `axllm run`。

| 启动脚本 | 主机 / 模式 |
| --- | --- |
| [`run_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_axcl_aarch64_api.sh) | ARM64，API 模式 |
| [`run_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_axcl_x86_api.sh) | x86_64，API 模式 |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_image_axcl_aarch64.sh) | ARM64 |
| [`run_image_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_image_axcl_x86.sh) | x86_64 |
| [`run_video_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_video_axcl_aarch64.sh) | ARM64，视频模式 |
| [`run_video_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_video_axcl_x86.sh) | x86_64，视频模式 |

本页选择 `run_image_axcl_aarch64.sh`。在 RK3576 上还需用 file 确认程序是 ARM64，并用 ldd 检查 AXCL 依赖。

```bash
cd "$MODEL_DIR"
file main_axcl_aarch64
ldd main_axcl_aarch64
```

依赖中不能出现 `not found`。

## 核对本地分词器

此脚本读取本地 tokenizer 文件：`qwen3_tokenizer.txt`，不启动旧版 HTTP 分词服务。确认这些文件与模型同 revision，保留脚本中的分词器参数名。

## 配置并运行本机脚本

终端 2 在模型目录复制脚本，在副本中设置本机参数：

```bash
cd "$MODEL_DIR"
cp -n run_image_axcl_aarch64.sh run_image_axcl_aarch64.sh.local
sed -n '1,220p' run_image_axcl_aarch64.sh.local
```

- 将 `--devices` 的原值 `0,` 改成实际设备列表；单卡编号为 0 时使用 `0`，保留程序要求的参数格式。
- 核对脚本中的模型目录、embedding、post 模型和输入文件全部存在。不要改变已编译的层数和上下文规格。

确认架构、依赖、文件和附加服务均匹配后，在终端 2 执行：

```bash
cd "$MODEL_DIR"
set -o pipefail
bash run_image_axcl_aarch64.sh.local 2>&1 | tee run.log
```

保存修改后的脚本和日志。设备初始化、tokenizer 连接或模型加载失败时停止，先解决对应依赖。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 使用已知内容的单张图片提问，回答应包含可核对的图像细节。
- 再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`gradio_demo.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/gradio_demo.py) | Python 程序 / 前后处理 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_640x640.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_640x640.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_u8.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/Qwen3-VL-2B-Instruct_vision_u8.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/Qwen3-VL-2B-Instruct-AX650-c128_p1536_ctx2047-int4/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/config.json) | 运行配置 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/images/demo.jpg) | 示例输入 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/post_config.json) | 运行配置 |
| [`run_ax650_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_ax650_api.sh) | 启动或构建脚本 |
| [`run_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_axcl_aarch64_api.sh) | 启动或构建脚本 |
| [`run_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_axcl_x86_api.sh) | 启动或构建脚本 |
| [`run_image_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/run_image_ax650.sh) | 启动或构建脚本 |

仓库提交：`cf4b904ba59e66fefd17668af196fc9c199ab70f`。仓库中的 32 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/tree/cf4b904ba59e66fefd17668af196fc9c199ab70f)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/tree/cf4b904ba59e66fefd17668af196fc9c199ab70f)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/README.md)。
- [主要程序入口：gradio_demo.py](https://huggingface.co/AXERA-TECH/Qwen3-VL-2B-Instruct-GPTQ-Int4-P1536-CTX2047/blob/cf4b904ba59e66fefd17668af196fc9c199ab70f/gradio_demo.py)。
- [配套项目：AXERA-TECH/Qwen3-VL.AXERA](https://github.com/AXERA-TECH/Qwen3-VL.AXERA)。

返回[完整模型目录](../catalog.mdx)。
