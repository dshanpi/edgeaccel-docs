---
title: "Qwen2.5-7B-Instruct-TensorParallel 部署指南"
sidebar_label: "Qwen2.5-7B-Instruct-TensorParallel"
description: "Qwen2.5-7B-Instruct-TensorParallel 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-7B-Instruct-TensorParallel 部署指南

Qwen2.5-7B-Instruct-TensorParallel 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需多卡配置。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

这是张量并行模型包。先按模型卡确认设备数量、设备编号顺序和各设备可用内存，单卡不能直接沿用多卡配置。

核对分片到各卡的分配、主机到设备的数据传输及卡间依赖。先逐卡检查设备状态，不能仅将 devices 字段缩成一个编号。
## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-7b-instruct-tensorparallel/41ea4657159e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel \
  --revision 41ea4657159e37fa1116dd78204c82635bc0e13d \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 先测短问答，再测两轮上下文；翻译模型使用有参考译文的短句。
- 记录首 token 延迟、生成速率和实际上下文长度，确认没有乱码、持续重复或异常提前结束。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/blob/41ea4657159e37fa1116dd78204c82635bc0e13d/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/blob/41ea4657159e37fa1116dd78204c82635bc0e13d/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/blob/41ea4657159e37fa1116dd78204c82635bc0e13d/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/blob/41ea4657159e37fa1116dd78204c82635bc0e13d/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`run_qwen2.5_7B_axcl_context_tp.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/blob/41ea4657159e37fa1116dd78204c82635bc0e13d/run_qwen2.5_7B_axcl_context_tp.sh) | 启动或构建脚本 |
| [`run_qwen2.5_7B_int4_axcl_context_tp.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/blob/41ea4657159e37fa1116dd78204c82635bc0e13d/run_qwen2.5_7B_int4_axcl_context_tp.sh) | 启动或构建脚本 |

仓库提交：`41ea4657159e37fa1116dd78204c82635bc0e13d`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/tree/41ea4657159e37fa1116dd78204c82635bc0e13d)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是 TensorParallel 专用包，需按模型卡准备多卡与分片配置；不作为单张 M.2 卡的默认部署。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。
- 此提交没有 README.md。已核对文件清单；运行参数和验收数据不能仅根据仓库名称补写。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-7B-Instruct-TensorParallel/tree/41ea4657159e37fa1116dd78204c82635bc0e13d)。

返回[完整模型目录](../catalog.mdx)。
