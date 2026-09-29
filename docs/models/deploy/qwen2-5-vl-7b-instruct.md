---
title: "Qwen2.5-VL-7B-Instruct 部署指南"
sidebar_label: "Qwen2.5-VL-7B-Instruct"
description: "Qwen2.5-VL-7B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-VL-7B-Instruct 部署指南

Qwen2.5-VL-7B-Instruct 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL 专用脚本。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-VL-7B-Instruct` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-vl-7b-instruct/d6ded77c295c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-VL-7B-Instruct \
  --revision d6ded77c295c220efe50d4894ff0d5820f01b3b1 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 选择 AXCL 启动入口

此包使用旧版专用程序，保留其脚本、分片和 tokenizer 服务组合。不能直接替换成新版 `axllm run`。

| 启动脚本 | 主机 / 模式 |
| --- | --- |
| [`run_qwen2_5vl_image_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/run_qwen2_5vl_image_axcl_x86.sh) | x86_64 |
| [`run_qwen2_5vl_video_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/run_qwen2_5vl_video_axcl_x86.sh) | x86_64，视频模式 |

本页选择 `run_qwen2_5vl_image_axcl_x86.sh`。该入口是 x86_64；RK3576 不能直接运行此二进制，需从同版本源码构建 ARM64 AXCL 程序。

```bash
cd "$MODEL_DIR"
file main_axcl_x86
ldd main_axcl_x86
```

依赖中不能出现 `not found`。

## 启动配套分词服务

在终端 1 激活安装本仓库依赖的 Python 环境，在模型根目录启动 `qwen2_tokenizer_images.py`：

```bash
cd "$MODEL_DIR"
python3 qwen2_tokenizer_images.py --host 127.0.0.1 --port 8091
```

保持该终端运行，在另一个终端用 `ss -ltnp` 确认端口 8091 已监听。首次启动可能还需模型卡指定的 tokenizer 资源；不能用同系列另一个服务脚本替代。

## 配置并运行本机脚本

终端 2 在模型目录复制脚本，在副本中设置本机参数：

```bash
cd "$MODEL_DIR"
cp -n run_qwen2_5vl_image_axcl_x86.sh run_qwen2_5vl_image_axcl_x86.sh.local
sed -n '1,220p' run_qwen2_5vl_image_axcl_x86.sh.local
```

- 将 `--devices` 的原值 `0,1,2,3,4,5,6,7` 改成实际设备列表；单卡编号为 0 时使用 `0`，保留程序要求的参数格式。
- 将 tokenizer URL 改为本机服务地址，并保留与服务一致的端口。地址 `0.0.0.0` 用于监听，不作为客户端目标，客户端改用 `127.0.0.1`。
- 核对脚本中的模型目录、embedding、post 模型和输入文件全部存在。不要改变已编译的层数和上下文规格。

确认架构、依赖、文件和附加服务均匹配后，在终端 2 执行：

```bash
cd "$MODEL_DIR"
set -o pipefail
bash run_qwen2_5vl_image_axcl_x86.sh.local 2>&1 | tee run.log
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
| [`run_qwen2_5vl_image_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/run_qwen2_5vl_image_axcl_x86.sh) | 启动或构建脚本 |
| [`qwen2_tokenizer_images.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/qwen2_tokenizer_images.py) | 旧版分词服务入口 |
| [`qwen2_tokenizer_video_308.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/qwen2_tokenizer_video_308.py) | 旧版分词服务入口 |
| [`Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/Qwen2.5-VL-7B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/Qwen2.5-VL-7B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/Qwen2.5-VL-7B-Instruct_vision_video.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/Qwen2.5-VL-7B-Instruct_vision_video.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/qwen2_5_vl_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/qwen2_5_vl_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/qwen2_5_vl_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/qwen2_5_vl_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/qwen2_5_vl_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/Qwen2.5-VL-7B-Instruct-AX650-chunk_prefill_1280/qwen2_5_vl_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/config.json) | 运行配置 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/images/demo.jpg) | 示例输入 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/post_config.json) | 运行配置 |
| [`qwen2_5_vl_7b_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/qwen2_5_vl_7b_tokenizer/config.json) | 运行配置 |
| [`qwen2_5_vl_7b_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/qwen2_5_vl_7b_tokenizer/generation_config.json) | 运行配置 |
| [`qwen2_5_vl_7b_tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/qwen2_5_vl_7b_tokenizer/preprocessor_config.json) | 运行配置 |

仓库提交：`d6ded77c295c220efe50d4894ff0d5820f01b3b1`。仓库中的 31 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/tree/d6ded77c295c220efe50d4894ff0d5820f01b3b1)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/tree/d6ded77c295c220efe50d4894ff0d5820f01b3b1)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/README.md)。
- [主要程序入口：qwen2_tokenizer_images.py](https://huggingface.co/AXERA-TECH/Qwen2.5-VL-7B-Instruct/blob/d6ded77c295c220efe50d4894ff0d5820f01b3b1/qwen2_tokenizer_images.py)。
- [配套项目：AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera](https://github.com/AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera/tree/axcl)。
- [配套项目：AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera](https://github.com/AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera/tree/main)。

返回[完整模型目录](../catalog.mdx)。
