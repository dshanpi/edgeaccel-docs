---
title: "查阅来源与适用版本"
---

# 查阅来源与适用版本

基础资料整理日期：2026-09-22；模型实测日期见各模型页。本站按 M.2 算力卡用户的安装、使用与验证顺序重新组织内容；原厂芯片开发板、板端 SDK 和算力卡 AXCL 的操作分别处理。

## 查阅原厂资料

| 来源 | 本站使用范围 |
|---|---|
| [AXERA Edge Computing Docs](https://awesome-edge-docs.readthedocs.io/zh-cn/latest/) | 模型与项目索引、算力卡使用入口 |
| [AXCL 文档](https://axcl-docs.readthedocs.io/zh-cn/latest/) | 主机安装、设备管理、NPU、Python、FFmpeg 与故障处理；整理基线 V3.16.0 |
| [AXERA-TECH / ModelScope](https://modelscope.cn/organization/AXERA-TECH) | 模型国内下载入口；具体链接依据原厂索引 |
| [AXERA-TECH / Hugging Face](https://huggingface.co/AXERA-TECH) | 模型卡、文件布局、运行依赖和许可证 |

模型目录中的“入口核对”表示资料或源码层面的核对，不表示本机已运行。模型网站和 `latest` 文档会更新，实际部署应固定提交或版本。

## 固定程序基线

| 项目 | 本文核对版本 | 使用范围 |
|---|---|---|
| [axcl-samples](https://github.com/AXERA-TECH/axcl-samples/tree/cbfa4c76891758983ca2b0c99c11d6621d59af39) | `cbfa4c76891758983ca2b0c99c11d6621d59af39` | CV 目标名、参数、输出文件 |
| [ax-llm / axllm](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1) | `8501c22b940f8c5804cb35044c5ffc136918b8f1` | AXCL 构建、run/serve、配置与多模态入口 |
| [PyAXEngine](https://github.com/AXERA-TECH/pyaxengine) | 部署时固定 release 与示例版本 | Python AXCL provider |
| [whisper.axcl](https://github.com/ml-inory/whisper.axcl) | 部署时固定程序与旧三段模型组合 | 社区语音识别示例 |
| [melotts.axcl](https://github.com/ml-inory/melotts.axcl) | 部署时固定程序与下载脚本配套模型 | 社区语音合成示例 |

社区项目单独标明，不称作芯片原厂维护的软件。源码版本已固定不代表模型仓库也固定；部署记录还需填写模型 revision。

## 处理已知差异

- AXCL 示例实际目标使用 `axcl_` 前缀；旧 README 或芯片板端模型卡可能使用 `ax_`。
- 新 `axllm` 与旧 `main_axcl`、独立 tokenizer 服务的启动方式不同。
- Whisper 新旧模型拆分结构不同，应按同一版程序下载配套权重。
- Gemma-4 上游列出 AXCL 后端异常，暂不按可用算力卡模型介绍。
- 历史 Qwen3-VL-8B 项目与新运行时的部署步骤分别记录。8GB、16GB 环境的结果不可互用，模型实测状态以各模型页为准。

## 保留原始资料

原始文档、源码和历史记录见[原始附件目录](original-files.md)。迁移清单保留文件大小与 SHA256，供版本追溯。历史附件中的主机地址与路径仅适用于原测试环境。

使用模型与程序前，请查看对应仓库的许可证。本站不重新分发外部模型权重。
