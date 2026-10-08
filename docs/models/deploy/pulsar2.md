---
title: "Pulsar2 资源使用"
sidebar_label: "Pulsar2"
description: "Pulsar2 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Pulsar2 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

用于在转换环境中将原始网络编译为 .axmodel。按模型转换章节配置容器、量化样本和芯片目标，生成后再复制到算力卡主机验证。

继续阅读[对应操作指南](../../models/custom-model.md)。本仓库固定参考提交为 `f3be38bdab5ac6f86628bf871e518bdef69c745b`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Pulsar2/blob/f3be38bdab5ac6f86628bf871e518bdef69c745b/config.json) | 运行配置 |

仓库提交：`f3be38bdab5ac6f86628bf871e518bdef69c745b`。该提交没有预编译 `.axmodel` 文件。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Pulsar2/tree/f3be38bdab5ac6f86628bf871e518bdef69c745b)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Pulsar2/tree/f3be38bdab5ac6f86628bf871e518bdef69c745b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Pulsar2/blob/f3be38bdab5ac6f86628bf871e518bdef69c745b/README.md)。

返回[完整模型目录](../catalog.mdx)。
