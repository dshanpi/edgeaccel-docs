---
title: "frigate-resource 资源使用"
sidebar_label: "frigate-resource"
description: "frigate-resource 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# frigate-resource 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

先完成 Frigate 使用的主机视频输入与检测后端，再选择匹配的模型、标签与预处理配置。

继续阅读[对应操作指南](../../usage/video.md)。本仓库固定参考提交为 `805a98b0c77d03135fd6da5986375bcb457156e0`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/frigate-resource/blob/805a98b0c77d03135fd6da5986375bcb457156e0/config.json) | 运行配置 |

仓库提交：`805a98b0c77d03135fd6da5986375bcb457156e0`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/frigate-resource/tree/805a98b0c77d03135fd6da5986375bcb457156e0)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/frigate-resource/tree/805a98b0c77d03135fd6da5986375bcb457156e0)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/frigate-resource/blob/805a98b0c77d03135fd6da5986375bcb457156e0/README.md)。

返回[完整模型目录](../catalog.mdx)。
