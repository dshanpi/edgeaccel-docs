---
title: "immich 部署指南"
sidebar_label: "immich"
description: "immich 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# immich 部署指南

immich 用于图文匹配。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。

### 准备本模型的输入

本提交可核对的样本：`asset/axcl-status.png`、`asset/deduplication.png`、`asset/immich-logo.png`、`asset/login.png`、`asset/mission-01.png`、`asset/rpi5-with-m.2-card.png`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/immich` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/immich/81c75d735f40
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/immich \
  --revision 81c75d735f4087a4359ff152646436da1685af1c \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 检查向量维度、有限数值及是否需要归一化；文本与图片使用配套编码器。
- 用匹配对、不匹配对比较相似度排序，再建立小型索引；更换模型后重建索引。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/immich/blob/81c75d735f4087a4359ff152646436da1685af1c/config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/immich/blob/81c75d735f4087a4359ff152646436da1685af1c/requirements.txt) | Python 依赖清单 |

仓库提交：`81c75d735f4087a4359ff152646436da1685af1c`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/immich/tree/81c75d735f4087a4359ff152646436da1685af1c)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 该提交未直接列出 .axmodel 文件；先核对模型卡指向的实际权重或程序仓库，不能将该目录直接交给 axcl_run_model。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/immich/tree/81c75d735f4087a4359ff152646436da1685af1c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/immich/blob/81c75d735f4087a4359ff152646436da1685af1c/README.md)。
- [配套项目：AXERA-TECH/immich](https://github.com/AXERA-TECH/immich)。
- [配套项目：AXERA-TECH/immich](https://github.com/AXERA-TECH/immich/tree/ax650-v2.7.5)。
- [配套项目：AXERA-TECH/pyaxengine](https://github.com/AXERA-TECH/pyaxengine)。

返回[完整模型目录](../catalog.mdx)。
