---
title: "下载软件、模型与配套资料"
---

# 下载软件、模型与配套资料

先确认主机架构和算力卡容量，再下载对应文件。AXCL 软件、随卡 PAC、模型与应用各自匹配，不按名称相似混用。

## 下载 AXCL 与模型

| 资料 | 入口 | 使用说明 |
|---|---|---|
| AXCL 8GB 基线 | [V3.16.0_8G](https://huggingface.co/AXERA-TECH/AXCL/tree/main/V3.16.0_8G) | 选择主机架构与系统 |
| AXCL 16GB 基线 | [V3.16.0_16G](https://huggingface.co/AXERA-TECH/AXCL/tree/main/V3.16.0_16G) | Windows 组合需供货方确认 |
| 配套 PAC | 随卡资料或供货方 | 匹配容量、硬件和 AXCL，不通用替换 |
| 模型与应用 | [模型目录](models/catalog.mdx) | 按 AXCL 状态选型并记录 revision |
| 验证记录 | [Markdown 模板](pathname:///templates/model-validation.md) | 保存真实结果，不预填性能结论 |

## 查阅本地配套资料

- [六路 AI 视频推流源码](https://github.com/dshanpi/ax8850-multistream-demo)：[项目使用指南](projects/six-streams.md)、演示录像与原环境实测记录。
- [RK3576 内核头资料](ax650n/reference/kernel-headers/install.md)：仅适用于其中明确列出的内核版本，不能替代其他内核的 headers。

下载后按[文件校验步骤](usage/download-models.md)核对。历史安装包和附件按原版本提供，使用前先检查适用环境。
