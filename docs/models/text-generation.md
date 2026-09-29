---
title: "选择文本对话模型"
---

# 选择文本对话模型

独立部署页提供准备环境、下载配套文件、启动服务和实际回复。短问答可从 Qwen3-0.6B 开始；需要翻译时可对照 HY-MT 页面的中英文样例。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [Qwen3-0.6B](deploy/qwen3-0-6b.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-0-6b.md#查看部署效果) |
| [Qwen3-0.6B-GPTQ-Int4](deploy/qwen3-0-6b-gptq-int4.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-0-6b-gptq-int4.md#查看部署效果) |
| [Qwen3-1.7B](deploy/qwen3-1-7b.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-1-7b.md#查看部署效果) |
| [Qwen3-1.7B-GPTQ-Int4](deploy/qwen3-1-7b-gptq-int4.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-1-7b-gptq-int4.md#查看部署效果) |
| [Qwen3-4B-GPTQ-Int4](deploy/qwen3-4b-gptq-int4.md) | 文本生成 | [固定样例已核对](deploy/qwen3-4b-gptq-int4.md#查看部署效果) |
| [Qwen3-4B](deploy/qwen3-4b.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-4b.md#查看部署效果) |
| [Qwen2.5-7B-Instruct-GPTQ-Int4](deploy/qwen2-5-7b-instruct-gptq-int4.md) | 文本生成 | [本次运行未通过](deploy/qwen2-5-7b-instruct-gptq-int4.md#查看部署效果) |
| [gemma-3-270m-it](deploy/gemma-3-270m-it.md) | 文本生成 | [已运行，效果仍需评估](deploy/gemma-3-270m-it.md#查看部署效果) |
| [Gemma-3-1B-it-AX650](deploy/gemma-3-1b-it-ax650.md) | 文本生成 | [已运行，效果仍需评估](deploy/gemma-3-1b-it-ax650.md#查看部署效果) |
| [MiniCPM5-1B](deploy/minicpm5-1b.md) | 文本生成 | [已运行，效果仍需评估](deploy/minicpm5-1b.md#查看部署效果) |
| [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K](deploy/minicpm5-2b-gptq-int4-ax650-c128-p1k-ctx2k.md) | 文本生成 | [固定样例已核对](deploy/minicpm5-2b-gptq-int4-ax650-c128-p1k-ctx2k.md#查看部署效果) |
| [HY-MT1.5-1.8B_GPTQ_INT4](deploy/hy-mt1-5-1-8b-gptq-int4.md) | 文本翻译 | [已运行，效果仍需评估](deploy/hy-mt1-5-1-8b-gptq-int4.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- 增加参数量、上下文或并发之前，用 axcl-smi 检查空闲 CMM；保留运行时的内存预检。
- 同一系列的量化、上下文规格和旧版脚本可能不同，配置、分词器与模型分片需要成套使用。
- 先检查实际回答再选型：算术错误、异常分词字符和 JSON 代码围栏均保留在各页，基本运行不表示内容或格式正确。

公共编译步骤见[AXCL 大模型运行时](llm-runtime.md)，应用调用见[服务接口](../usage/api-service.md)。
