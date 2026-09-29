---
title: "Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4 部署指南"
sidebar_label: "Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4"
description: "Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4 部署指南

Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需多卡配置。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

这是张量并行模型包。先按模型卡确认设备数量、设备编号顺序和各设备可用内存，单卡不能直接沿用多卡配置。

### 准备本模型的输入

本提交可核对的样本：`image.png`。结合模型卡选择输入，结果图片不作为原始输入。

核对分片到各卡的分配、主机到设备的数据传输及卡间依赖。先逐卡检查设备状态，不能仅将 devices 字段缩成一个编号。
## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-8b-instruct-gptq-int4-ax650-c128-p1152-ctx2047-tp4/d2e3e2ea2083
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4 \
  --revision d2e3e2ea2083dc1b73b6b2297c04340740aceda3 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 使用已知内容的单张图片提问，回答应包含可核对的图像细节。
- 再测试多轮图片或短视频，记录抽帧和缩放规则；纯文本回复正确不能代替视觉编码器验证。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/Qwen3-VL-8B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/blob/d2e3e2ea2083dc1b73b6b2297c04340740aceda3/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/Qwen3-VL-8B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/blob/d2e3e2ea2083dc1b73b6b2297c04340740aceda3/post_config.json) | 运行配置 |
| [`run_qwen3_vl_8b_tp.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/blob/d2e3e2ea2083dc1b73b6b2297c04340740aceda3/run_qwen3_vl_8b_tp.sh) | 启动或构建脚本 |

仓库提交：`d2e3e2ea2083dc1b73b6b2297c04340740aceda3`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/tree/d2e3e2ea2083dc1b73b6b2297c04340740aceda3)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- TP4 包需要对应四路张量并行配置。单卡不能按普通 8B 目录直接加载。
- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。
- 此提交没有 README.md。已核对文件清单；运行参数和验收数据不能仅根据仓库名称补写。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4-AX650-C128-P1152-CTX2047-TP4/tree/d2e3e2ea2083dc1b73b6b2297c04340740aceda3)。

返回[完整模型目录](../catalog.mdx)。
