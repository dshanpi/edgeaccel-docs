---
title: "lite_webui 资源使用"
sidebar_label: "lite_webui"
description: "lite_webui 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# lite_webui 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

先在主机启动并测试模型 API，再配置页面中的服务地址和模型名称。界面启动成功不代表模型已加载。

继续阅读[对应操作指南](../../usage/api-service.md)。本仓库固定参考提交为 `80275904148ab9304a9549fdf3ea87b7933c3619`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/lite_webui/blob/80275904148ab9304a9549fdf3ea87b7933c3619/config.json) | 运行配置 |

仓库提交：`80275904148ab9304a9549fdf3ea87b7933c3619`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/lite_webui/tree/80275904148ab9304a9549fdf3ea87b7933c3619)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/lite_webui/tree/80275904148ab9304a9549fdf3ea87b7933c3619)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/lite_webui/blob/80275904148ab9304a9549fdf3ea87b7933c3619/README.md)。

返回[完整模型目录](../catalog.mdx)。
