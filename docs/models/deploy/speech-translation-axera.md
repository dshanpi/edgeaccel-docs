---
title: "Speech-Translation.axera 部署指南"
sidebar_label: "Speech-Translation.axera"
description: "Speech-Translation.axera 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Speech-Translation.axera 部署指南

Speech-Translation.axera 用于多阶段应用。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL 专用脚本。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Speech-Translation.axera` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/speech-translation-axera/f3672ca715ee
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Speech-Translation.axera \
  --revision f3672ca715ee6380317eb2c87ed8fd049e51d691 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 选择 AXCL 启动入口

此包使用旧版专用程序，保留其脚本、分片和 tokenizer 服务组合。不能直接替换成新版 `axllm run`。

| 启动脚本 | 主机 / 模式 |
| --- | --- |
| [`libaxllm/run_qwen2.5_1.5b_ctx_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/run_qwen2.5_1.5b_ctx_axcl_aarch64_api.sh) | ARM64，API 模式 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh) | x86_64，API 模式 |

现有脚本仅覆盖服务或组合应用入口。先核对其全部服务依赖与参数，不在本文拼接一个未经核对的单模型命令。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 分别验证每个模型阶段的真实输入、输出和后端，再启动完整应用。
- 检查服务地址、错误传播、超时与资源释放；某个子模型运行不代表整条链路完成。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`ax_speech_translate_demo_qwen_api.py`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/ax_speech_translate_demo_qwen_api.py) | Python 程序 / 前后处理 |
| [`ax_speech_translate_demo_qwen_api_realtime.py`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/ax_speech_translate_demo_qwen_api_realtime.py) | Python 程序 / 前后处理 |
| [`ax_model/sensevoice.axmodel`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/ax_model/sensevoice.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`ax_model/vad.axmodel`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/ax_model/vad.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`libmelotts/models/decoder-en.axmodel`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libmelotts/models/decoder-en.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`libmelotts/models/decoder-zh.axmodel`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libmelotts/models/decoder-zh.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/config.json) | 运行配置 |
| [`libaxllm/post_config.json`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/post_config.json) | 运行配置 |
| [`libaxllm/qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`libaxllm/qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_ax650_api.sh`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/run_qwen2.5_1.5b_ctx_ax650_api.sh) | 启动或构建脚本 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_axcl_aarch64_api.sh`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/run_qwen2.5_1.5b_ctx_axcl_aarch64_api.sh) | 启动或构建脚本 |
| [`libaxllm/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libaxllm/run_qwen2.5_1.5b_ctx_axcl_x86_api.sh) | 启动或构建脚本 |
| [`libmelotts/models/lexicon.txt`](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/libmelotts/models/lexicon.txt) | 分词器 / 字典，必须配套 |

仓库提交：`f3672ca715ee6380317eb2c87ed8fd049e51d691`。仓库中的 4 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/tree/f3672ca715ee6380317eb2c87ed8fd049e51d691)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/tree/f3672ca715ee6380317eb2c87ed8fd049e51d691)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/README.md)。
- [主要程序入口：ax_speech_translate_demo_qwen_api.py](https://huggingface.co/AXERA-TECH/Speech-Translation.axera/blob/f3672ca715ee6380317eb2c87ed8fd049e51d691/ax_speech_translate_demo_qwen_api.py)。
- [配套项目：AXERA-TECH/3D-Speaker-MT.axera](https://github.com/AXERA-TECH/3D-Speaker-MT.axera/tree/main)。
- [配套项目：AXERA-TECH/3D-Speaker-MT.axera](https://github.com/AXERA-TECH/3D-Speaker-MT.axera/tree/main/model_convert)。
- [配套项目：AXERA-TECH/3D-Speaker.axera](https://github.com/AXERA-TECH/3D-Speaker.axera/tree/master)。

返回[完整模型目录](../catalog.mdx)。
