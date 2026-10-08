---
title: "MiniCPM5-2B-GPTQ-Int4 部署指南"
sidebar_label: "MiniCPM5-2B-GPTQ-Int4"
description: "MiniCPM5-2B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM5-2B-GPTQ-Int4 部署指南

MiniCPM5-2B-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。量化源权重，选择编译版本。

## 准备运行环境

本仓库提供 GPTQ 量化源权重，固定版本不含 `.axmodel`。在 M.2 算力卡上运行时，选择下表中的官方编译版本，并完成[驱动与设备检查](../../usage/device-check.md)和[AXCL 大模型运行时安装](../llm-runtime.md)。

## 选择并下载编译版本

进入所选版本的独立部署页，按其中的固定提交下载模型、分词器和配置。不同规格使用各自的完整文件，不混用目录。

| 编译版本 / 部署入口 | 固定提交 | 该版本实测范围 |
| --- | --- | --- |
| [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K](./minicpm5-2b-gptq-int4-ax650-c128-p1k-ctx2k.md) | `2c7c6ffc0a1ed07d7ffec83368cbc752606dc407` | RK3576 DshanPi A1 + AX8850 8GB M.2；通过（结果正确性） |
| [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P4K-CTX6K](./minicpm5-2b-gptq-int4-ax650-c128-p4k-ctx6k.md) | `df71361ffdcad3fca0c9e1cf461faffd322df6f4` | RK3576 + AX8850 16GB M.2；通过（结果正确性） |

## 运行文本生成

在所选部署页完成下载后，沿用该页的模型目录、运行时版本和配置启动服务，再执行页面给出的文本请求。收到完整回复后，核对回答内容及结束状态。

量化源权重不能直接交给 `axcl_run_model`。需要自行转换模型时，另按[自定义模型接入](../custom-model.md)准备工具链，转换产物需单独验证。

## 查看部署效果

以下入口展示对应编译版本的实际请求、完整回复和耗时。源权重仓库本身尚无独立的算力卡运行记录，编译版本的结果仅适用于各页列出的硬件、模型提交和测试输入。

- [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K 的部署效果](./minicpm5-2b-gptq-int4-ax650-c128-p1k-ctx2k.md#查看部署效果)：三组文本样例已核对：算术题返回 5；中文简述 PCIe；按要求输出含 apple=3、pear=2 的裸 JSON。
- [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P4K-CTX6K 的部署效果](./minicpm5-2b-gptq-int4-ax650-c128-p4k-ctx6k.md#查看部署效果)：在 16GB 卡上完成三次文本生成：算术仅返回 5，中文说明符合 PCIe 的用途，JSON 的键名、数值和输出格式均符合要求。

## 核对版本来源

量化源权重固定提交为 `eb062da85bfa5c839905da40911967263988dd6d`。两个编译仓库的模型卡均将本仓库列为转换来源；编译版本的提交与源权重提交独立管理。

- [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K 的固定版本模型卡](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K/blob/2c7c6ffc0a1ed07d7ffec83368cbc752606dc407/README.md)。
- [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P4K-CTX6K 的固定版本模型卡](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4-AX650-C128-P4K-CTX6K/blob/df71361ffdcad3fca0c9e1cf461faffd322df6f4/README.md)。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/tree/eb062da85bfa5c839905da40911967263988dd6d)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM5-2B-GPTQ-Int4/blob/eb062da85bfa5c839905da40911967263988dd6d/README.md)。

返回[完整模型目录](../catalog.mdx)。
