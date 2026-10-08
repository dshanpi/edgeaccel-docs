---
title: "选择图像问答模型"
description: "用画面可核对的问题评估模型，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择图像问答模型

<GuideHero label="多模态模型 · 图像问答" title="用画面可核对的问题评估模型" description="图像问答需要视觉编码器与语言模型共同运行。进入具体部署页，可以下载同一张测试图片，发送问题并对照实际回复。" facts={[["输入","图片与问题；部分支持多帧"],["输出","描述、回答或提取文本"],["先检查","回答与图像是否一致"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 单张图片问答 | SmolVLM2、FastVLM、Qwen 或 InternVL 对应部署页 | 选择有配套编码器与运行配置的具体权重，先测试一张图片。 |
| 读取图片中的文字 | [OCR 与文档模型](extensions.md) | 逐字转录、版面理解和开放问答的验收标准不同。 |
| 视频片段概述 | 明确提供多帧入口的部署配置 | 记录采样帧、顺序与覆盖时间；Video 名称不能代替视频实测。 |
| 实时检测、计数或告警 | [检测](detection.md) + [视频处理](../usage/video.md) | 先明确延迟和输出要求，再决定是否加入问答模型。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [FastVLM-1.5B-GPTQ-Int4](deploy/fastvlm-1-5b-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/fastvlm-1-5b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [SmolVLM2-500M-Video-Instruct](deploy/smolvlm2-500m-video-instruct.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/smolvlm2-500m-video-instruct.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3-VL-2B-Instruct-GPTQ-Int4](deploy/qwen3-vl-2b-instruct-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-vl-2b-instruct-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3.5-0.8B-AX650-GPTQ-Int4-C128-P1152-CTX2047](deploy/qwen3-5-0-8b-ax650-gptq-int4-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-0-8b-ax650-gptq-int4-c128-p1152-ctx2047.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047](deploy/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [InternVL3_5-1B_GPTQ_INT4](deploy/internvl3-5-1b-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/internvl3-5-1b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [InternVL3_5-2B_GPTQ_INT4](deploy/internvl3-5-2b-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/internvl3-5-2b-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [MiniCPM-V-4.6-GPTQ](deploy/minicpm-v-4-6-gptq.md) | 图像与文本理解 | [固定样例已核对](deploy/minicpm-v-4-6-gptq.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [qwenpaw-2b-flash-gptq-int4](deploy/qwenpaw-2b-flash-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwenpaw-2b-flash-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3.5-0.8B-AX650-C128-P1152-CTX2047](deploy/qwen3-5-0-8b-ax650-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-0-8b-ax650-c128-p1152-ctx2047.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3.5-2B-AX650-C128-P1152-CTX2047](deploy/qwen3-5-2b-ax650-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-2b-ax650-c128-p1152-ctx2047.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [Qwen3-VL-4B-Instruct-GPTQ-Int4](deploy/qwen3-vl-4b-instruct-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-vl-4b-instruct-gptq-int4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Qwen3.5-4B-AX650-GPTQ-Int4-C128-P1152-CTX2047](deploy/qwen3-5-4b-ax650-gptq-int4-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-4b-ax650-gptq-int4-c128-p1152-ctx2047.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [FastVLM-0.5B](deploy/fastvlm-0-5b.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/fastvlm-0-5b.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [FastVLM-1.5B](deploy/fastvlm-1-5b.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/fastvlm-1-5b.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 准备对象、数量、文字和空间关系可核对的图片，并为每张图片保存问题与参考答案。
2. 视觉编码器、语言分片、embedding、分词器及配置成套下载，不混用同系列不同上下文版本。
3. 多图或视频先核对输入上限及占用，从单图、短问题逐步扩展；记录实际帧数和抽帧规则。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| 画面一致性 | 核对人数、物体、颜色、文字和位置；流畅描述仍可能包含不存在的细节。 |
| 覆盖与完整性 | 分清模型未看到的帧和理解错误；检查回复是否达到生成上限而截断。 |
| 计时与容量 | 分别记录图像编码、语言生成和完整请求耗时，测试目标输入规模下的峰值。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- 检查回答中的人数、对象和场景细节；流畅的句子也可能包含与画面不符的描述。
- 测试范围因模型而异，以各部署页的输入和结果为准。名称中含 Video 不代表该页面已验证视频。
- 达到 max_tokens 上限的回复会在效果区标注。要求简短回答或调整上限后重新运行，不把截断文本当作完整结果。

## 接入下一步应用

更多量化与上下文变体见[完整模型目录](catalog.mdx)，按具体版本进入部署页。

<GuideNext items={[{"to":"/docs/models/llm-runtime","title":"匹配模型运行时","text":"区分统一 axllm 与旧专用程序。"},{"to":"/docs/usage/api-service","title":"接入多模态请求","text":"按具体部署配置发送图片与问题。"}]} />
