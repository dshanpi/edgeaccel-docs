---
title: "BoardImages 资源使用"
sidebar_label: "BoardImages"
description: "BoardImages 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# BoardImages 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

先核对镜像对应的开发板。开发板系统镜像不是 M.2 卡的 PAC，也不是 RK3576 主机系统安装包。

继续阅读[对应操作指南](../../getting-started/prepare.md)。本仓库固定参考提交为 `4ef074332ce220fc2eec2fc873d96a9cccbb210c`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/BoardImages/blob/4ef074332ce220fc2eec2fc873d96a9cccbb210c/config.json) | 运行配置 |

仓库提交：`4ef074332ce220fc2eec2fc873d96a9cccbb210c`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/BoardImages/tree/4ef074332ce220fc2eec2fc873d96a9cccbb210c)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/BoardImages/tree/4ef074332ce220fc2eec2fc873d96a9cccbb210c)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/BoardImages/blob/4ef074332ce220fc2eec2fc873d96a9cccbb210c/README.md)。

返回[完整模型目录](../catalog.mdx)。
