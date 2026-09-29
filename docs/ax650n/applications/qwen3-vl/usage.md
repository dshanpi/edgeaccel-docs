---
title: "Qwen3-VL-8B 部署与使用"
sidebar_label: "Qwen3-VL-8B 部署与使用"
slug: /ax650n/applications/qwen3-vl/usage
---

> **历史项目 · 16GB**：本页记录旧版 Qwen3-VL-8B 部署，不作为 8GB 卡的容量依据。新运行时见[图片与视频问答](/docs/models/vision-language)。

# AX8850 16GB：Qwen3-VL-8B 本地使用

适用于 原测试环境中的 RK3576 主机与 16GB AX8850。模型为爱芯已转换的 `Qwen3-VL-8B-Instruct-GPTQ-Int4`，通过 AXCL 在算力卡上执行推理。

## 1 启动图像与文字问答

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

## 2 运行视频理解示例

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

本次已提前准备道路交通示例，在 `video >>` 输入 `deployment/traffic_frames` 即可测试。

这是抽帧后的多模态问答，不是逐帧实时检测，也没有读取视频音频。

## 3 查看运行状态

另开一个 SSH 终端：

```bash
watch -n 1 /usr/bin/axcl/axcl-smi
```

模型加载后，进程列表应出现 `deployment/bin/main_axcl_aarch64`，CMM 占用明显增加。程序输出中的 `ttft` 表示本轮记录的首 token 耗时，`token/s` 表示生成速度；图像编码耗时会单独打印。

测试日志保存在模型目录的 `deployment/logs/`，部署版本信息在 `deployment/manifest.json`，模型 SHA256 校验结果在 `deployment/model-integrity.json`。

## 4 了解部署文件

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

## 5 处理常见情况

- **提示已有会话运行**：返回旧终端，在问题提示处输入 `q`；再开启新会话。
- **找不到图片**：使用已存在的 JPG/PNG 文件绝对路径。不要将 MP4 文件填入图片路径。
- **加载失败或内存不足**：先用 `axcl-smi` 查看是否有其他模型或视频程序占用算力卡，退出这些任务后重试。
- **输入过长**：本次运行报告最大输入为 1152 token，KV 容量为 2047 token。图片／视频占位 token 和提示词也计入输入长度。先使用短问题、单张图片或上述 8 帧示例，不按原始 Hugging Face 模型宣称的最大上下文长度直接使用。
- **重启后使用**：重新执行 `./run_local.sh image` 即可，无需重新下载模型或安装环境。

当前交付是本地命令行推理入口；未设置常驻服务或开机自启。

## 参考资料

- [AXCL 官方 LLM 指南](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_npu_samples.html#llm)
- [爱芯 Qwen3-VL-8B 模型仓库](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4)
- [爱芯 AXCL Qwen3-VL 单卡源码分支](https://github.com/AXERA-TECH/ax-llm/tree/axcl-qwen3-vl)
