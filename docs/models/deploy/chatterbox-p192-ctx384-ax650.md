---
title: "chatterbox-p192-ctx384-ax650 部署指南"
sidebar_label: "chatterbox-p192-ctx384-ax650"
description: "chatterbox-p192-ctx384-ax650 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# chatterbox-p192-ctx384-ax650 部署指南

chatterbox-p192-ctx384-ax650 用于语音合成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/chatterbox-p192-ctx384-ax650` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/chatterbox-p192-ctx384-ax650/f37f2a4bd733
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/chatterbox-p192-ctx384-ax650 \
  --revision f37f2a4bd7331fbf511e089a6741f5685d58c2c0 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 回放生成音频，检查文字是否完整、读音、音色、停顿和尾部截断。
- 记录采样率、音频时长、生成时间与 RTF；长文本、参考音色和多语言分别验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`llama_p64_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`llama_p64_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/llama_p64_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`f37f2a4bd7331fbf511e089a6741f5685d58c2c0`。仓库中的 32 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/tree/f37f2a4bd7331fbf511e089a6741f5685d58c2c0)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/tree/f37f2a4bd7331fbf511e089a6741f5685d58c2c0)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/chatterbox-p192-ctx384-ax650/blob/f37f2a4bd7331fbf511e089a6741f5685d58c2c0/README.md)。

返回[完整模型目录](../catalog.mdx)。
