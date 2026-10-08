---
title: "Qwen3-VL-8B 部署与使用"
sidebar_label: "Qwen3-VL-8B 部署与使用"
slug: /ax650n/applications/qwen3-vl/usage
description: "复现 RK3576 与 AX8850 16GB 的旧版 Qwen3-VL-8B 本地图文和视频帧问答。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# AX8850 16GB：Qwen3-VL-8B 本地使用

<GuideHero label="历史部署 · Qwen3-VL-8B" title="复现已交付的本地图文问答入口" description="使用原测试环境中的专用程序与配套文件，运行单图、文字和视频帧问答。" facts={[["主机", "RK3576 · aarch64"], ["算力卡", "AX8850 16GB"], ["适用范围", "原交付配置"]]} />

本页适用于已准备好旧版交付目录的环境，模型为 `Qwen3-VL-8B-Instruct-GPTQ-Int4`。历史结果不作为 8GB 卡的容量依据，也不替代其他版本的检查。

**首次下载和重新部署**请使用[该模型独立部署指南](/docs/models/deploy/qwen3-vl-8b-instruct-gptq-int4)；比较其他型号见[图像问答选型](/docs/models/vision-language)。本页的 `run_local.sh` 是旧交付入口，与统一 `axllm` 的命令、配置分别使用。

## 确认现有目录

在 RK3576 主机核对下方“部署文件”表中的启动脚本、运行程序、分词器和权重目录，并完成[设备检查](/docs/usage/device-check)。缺少文件时先按独立指南准备，不将本页的启动命令作为完整安装流程。

## 启动图像与文字问答

通过 SSH 登录开发板，执行：

```bash
cd ~/Qwen3-VL-8B/Qwen3-VL-8B-Instruct-GPTQ-Int4
./run_local.sh image
```

本机每次启动加载模型约需 2～3 分钟。等待出现 `prompt >>` 后输入问题。例如：

```text
prompt >> 请用一句中文描述图片中的主要内容。
image >> images/ssd_car.jpg
```

`image >>` 可以输入 JPG/PNG 图片的绝对路径。仅文字问答时，在这里直接按回车。

回答结束后可以继续提问。在 `prompt >>` 输入 `q` 退出并释放模型内存；生成过程中按 `Ctrl+C` 可以中断当前回答。

启动脚本已配置模型路径、设备 0 和本地分词器。正常运行无需联网、无需启动 Python 分词服务，也无需使用 `sudo`。

## 运行视频理解示例

先退出图像模式，再运行：

```bash
./run_local.sh video
```

按提示输入问题和示例帧目录：

```text
prompt >> 请用两句中文描述这段视频的主要内容。
video >> video
```

该程序接收按文件名排序的图片帧目录，不直接读取 MP4 或 RTSP。仓库自带的 `video` 目录包含 8 帧示例。

测试自己的 MP4 时，先抽取帧。下面两个路径分别替换为实际视频路径和一个尚不存在的输出目录：

```bash
./prepare_video.sh /home/baiwen/ax-pipeline/video/traffic.mp4 /home/baiwen/Qwen3-VL-8B/traffic_frames
```

脚本按每秒 1 帧抽取最多 8 帧，用于观察视频开头约 8 秒的内容。随后在 `video >>` 输入输出目录的绝对路径。目录中只放本次抽取的图片。

旧交付目录中还包含道路交通示例 `deployment/traffic_frames`。该目录存在时可直接输入；重新部署环境需自行准备相应帧文件。

这是抽帧后的多模态问答，不是逐帧实时检测，也没有读取视频音频。

## 检查回复与运行状态

先用页面提供的图片和短问题复现输出，再替换自己的输入。回答后检查对象、数量和场景细节，并确认回复完整。历史样例、计时范围和文件版本见[样例结果与版本](validation.md)。

另开一个 SSH 终端：

```bash
watch -n 1 /usr/bin/axcl/axcl-smi
```

模型加载后，进程列表应出现 `deployment/bin/main_axcl_aarch64`，CMM 占用明显增加。程序输出中的 `ttft` 表示本轮记录的首 token 耗时，`token/s` 表示生成速度；图像编码耗时会单独打印。

测试日志保存在模型目录的 `deployment/logs/`，部署版本信息在 `deployment/manifest.json`，模型 SHA256 校验结果在 `deployment/model-integrity.json`。

## 核对部署文件

| 文件／目录 | 用途 |
|---|---|
| `run_local.sh` | 图像、文字与视频帧问答的统一启动入口 |
| `prepare_video.sh` | 将 MP4 抽取为最多 8 张 JPEG 帧 |
| `deployment/bin/main_axcl_aarch64` | 在当前主机编译、与系统 OpenCV 4.6 匹配的运行程序 |
| `deployment/qwen3_tokenizer.txt` | 与当前运行程序配套的 C++ 分词词表 |
| `deployment/src/ax-llm` | 实际使用的爱芯单卡分支源码 |
| `Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/` | 36 层语言模型、视觉编码器、输出层与 embedding 权重 |
| `.venv/` | 分词对照与自动测试的独立 Python 环境，正常启动不依赖它 |

视觉与语言模型由 AX8850 执行，主机负责图片预处理、分词、调度和显示文字结果。

根目录原始 `main_axcl_aarch64` 及官方脚本保留原样。该预编译文件要求 OpenCV 4.10，本机安装的是 4.6，因此请使用本次提供的 `run_local.sh`。

## 处理常见情况

- **提示已有会话运行**：返回旧终端，在问题提示处输入 `q`；再开启新会话。
- **找不到图片**：使用已存在的 JPG/PNG 文件绝对路径。不要将 MP4 文件填入图片路径。
- **加载失败或内存不足**：先用 `axcl-smi` 查看是否有其他模型或视频程序占用算力卡，退出这些任务后重试。
- **输入过长**：本次运行报告最大输入为 1152 token，KV 容量为 2047 token。图片／视频占位 token 和提示词也计入输入长度。先使用短问题、单张图片或上述 8 帧示例，不按原始 Hugging Face 模型宣称的最大上下文长度直接使用。
- **重启后使用**：重新执行 `./run_local.sh image` 即可，无需重新下载模型或安装环境。

当前交付是本地命令行推理入口；未设置常驻服务或开机自启。

<GuideNext items={[{to: '/docs/ax650n/applications/qwen3-vl/validation', title: '对照历史样例结果', text: '核对 16GB 环境、输入与计时范围。'}, {to: '/docs/models/deploy/qwen3-vl-8b-instruct-gptq-int4', title: '进入独立部署指南', text: '重新下载、部署时使用完整操作步骤。'}]} />

## 参考资料

- [AXCL 官方 LLM 指南](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_npu_samples.html#llm)
- [爱芯 Qwen3-VL-8B 模型仓库](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4)
- [爱芯 AXCL Qwen3-VL 单卡源码分支](https://github.com/AXERA-TECH/ax-llm/tree/axcl-qwen3-vl)
