---
title: "AXCL 资源使用"
sidebar_label: "AXCL"
description: "AXCL 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# AXCL 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

先确认主机是 ARM64 还是 x86_64，再选择对应的 AXCL 安装包、卡端 PAC 和文档版本。不要将 aarch64 板端程序包当作主机驱动安装。

继续阅读[对应操作指南](../../ax650n/user-guide.md)。本仓库固定参考提交为 `133bc60f1280a5f200921e28bb5777296c0f76df`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/AXCL/blob/133bc60f1280a5f200921e28bb5777296c0f76df/config.json) | 运行配置 |

仓库提交：`133bc60f1280a5f200921e28bb5777296c0f76df`。该提交没有预编译 `.axmodel` 文件。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/AXCL/tree/133bc60f1280a5f200921e28bb5777296c0f76df)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/AXCL/tree/133bc60f1280a5f200921e28bb5777296c0f76df)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/AXCL/blob/133bc60f1280a5f200921e28bb5777296c0f76df/README.md)。

返回[完整模型目录](../catalog.mdx)。
