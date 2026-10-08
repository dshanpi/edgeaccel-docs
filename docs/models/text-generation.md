---
title: "选择文本对话模型"
description: "围绕回答质量、上下文和响应时间选型，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择文本对话模型

<GuideHero label="语言模型 · 文本生成" title="围绕回答质量、上下文和响应时间选型" description="独立部署页提供准备环境、下载配套文件、启动服务和实际回复。短问答可从 Qwen3-0.6B 开始；需要翻译时可对照 HY-MT 页面的中英文样例。" facts={[["输入","文本提示与对话历史"],["输出","回复 / 翻译 / 结构化文本"],["先检查","事实、格式与完整性"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 建立短问答基线 | Qwen3-0.6B、Qwen3-1.7B 等较小模型 | 先复现短问题；较小参数量不代表特定任务一定足够。 |
| 增加复杂问答能力 | 较大模型或对应量化版本 | 先匹配卡容量、上下文和运行程序，再对相同问题比较效果。 |
| 中英文翻译 | HY-MT 系列部署页 | 按语言方向检查术语、数字、否定和遗漏。 |
| 知识库问答或固定类别决策 | [向量检索与 Laya](extensions.md) | 先区分检索、生成和类别判断，避免把所有任务都交给对话模型。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [Qwen3-0.6B](deploy/qwen3-0-6b.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-0-6b.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3-0.6B-GPTQ-Int4](deploy/qwen3-0-6b-gptq-int4.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-0-6b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3-1.7B](deploy/qwen3-1-7b.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-1-7b.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3-1.7B-GPTQ-Int4](deploy/qwen3-1-7b-gptq-int4.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-1-7b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3-4B-GPTQ-Int4](deploy/qwen3-4b-gptq-int4.md) | 文本生成 | [固定样例已核对](deploy/qwen3-4b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3-4B](deploy/qwen3-4b.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen3-4b.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [Qwen2.5-7B-Instruct-GPTQ-Int4](deploy/qwen2-5-7b-instruct-gptq-int4.md) | 文本生成 | [已运行，效果仍需评估](deploy/qwen2-5-7b-instruct-gptq-int4.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [gemma-3-270m-it](deploy/gemma-3-270m-it.md) | 文本生成 | [已运行，效果仍需评估](deploy/gemma-3-270m-it.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Gemma-3-1B-it-AX650](deploy/gemma-3-1b-it-ax650.md) | 文本生成 | [已运行，效果仍需评估](deploy/gemma-3-1b-it-ax650.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [MiniCPM5-1B](deploy/minicpm5-1b.md) | 文本生成 | [已运行，效果仍需评估](deploy/minicpm5-1b.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [MiniCPM5-2B-GPTQ-Int4-AX650-C128-P1K-CTX2K](deploy/minicpm5-2b-gptq-int4-ax650-c128-p1k-ctx2k.md) | 文本生成 | [固定样例已核对](deploy/minicpm5-2b-gptq-int4-ax650-c128-p1k-ctx2k.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [HY-MT1.5-1.8B_GPTQ_INT4](deploy/hy-mt1-5-1-8b-gptq-int4.md) | 文本翻译 | [已运行，效果仍需评估](deploy/hy-mt1-5-1-8b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 准备有参考答案的短问题、业务术语及预期输出格式，保留提示词模板。
2. 记录量化、预填充与上下文规格、tokenizer、生成上限和采样参数。上下文还包括历史消息与系统提示。
3. 先单模型、单请求，核对加载与推理的 CMM、主机内存和存储；容量选择见[选型总览](selection.mdx#按实际容量规划部署)。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| 内容正确性 | 检查事实、计算、翻译及拒答行为；能返回文本只是基本运行。 |
| 格式与结束 | 要求 JSON 时实际解析，核对字段；达到生成上限的回复按截断处理。 |
| 响应与资源 | 区分加载耗时、首 token 延迟和生成速度；固定输入长度与计时口径后比较。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- 增加参数量、上下文或并发之前，用 axcl-smi 检查空闲 CMM；保留运行时的内存预检。
- 同一系列的量化、上下文规格和旧版脚本可能不同，配置、分词器与模型分片需要成套使用。
- 先检查实际回答再选型：算术错误、异常分词字符和 JSON 代码围栏均保留在各页，基本运行不表示内容或格式正确。

## 接入下一步应用

公共编译步骤见[AXCL 大模型运行时](llm-runtime.md)，应用调用见[服务接口](../usage/api-service.md)。

<GuideNext items={[{"to":"/docs/models/llm-runtime","title":"准备公共运行时","text":"核对固定版本、AXCL 后端和模型配置。"},{"to":"/docs/usage/api-service","title":"接入 HTTP 服务","text":"查询模型 ID，再发送业务请求。"}]} />
