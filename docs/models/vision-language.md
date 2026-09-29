---
title: "选择图像问答模型"
---

# 选择图像问答模型

图像问答需要视觉编码器与语言模型共同运行。进入具体部署页，可以下载同一张测试图片，发送问题并对照实际回复。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [FastVLM-1.5B-GPTQ-Int4](deploy/fastvlm-1-5b-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/fastvlm-1-5b-gptq-int4.md#查看部署效果) |
| [SmolVLM2-500M-Video-Instruct](deploy/smolvlm2-500m-video-instruct.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/smolvlm2-500m-video-instruct.md#查看部署效果) |
| [Qwen3-VL-2B-Instruct-GPTQ-Int4](deploy/qwen3-vl-2b-instruct-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-vl-2b-instruct-gptq-int4.md#查看部署效果) |
| [Qwen3.5-0.8B-AX650-GPTQ-Int4-C128-P1152-CTX2047](deploy/qwen3-5-0-8b-ax650-gptq-int4-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-0-8b-ax650-gptq-int4-c128-p1152-ctx2047.md#查看部署效果) |
| [Qwen3.5-2B-AX650N-GPTQ-Int4-C128-P1152-CTX2047](deploy/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-2b-ax650n-gptq-int4-c128-p1152-ctx2047.md#查看部署效果) |
| [InternVL3_5-1B_GPTQ_INT4](deploy/internvl3-5-1b-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/internvl3-5-1b-gptq-int4.md#查看部署效果) |
| [InternVL3_5-2B_GPTQ_INT4](deploy/internvl3-5-2b-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/internvl3-5-2b-gptq-int4.md#查看部署效果) |
| [MiniCPM-V-4.6-GPTQ](deploy/minicpm-v-4-6-gptq.md) | 图像与文本理解 | [固定样例已核对](deploy/minicpm-v-4-6-gptq.md#查看部署效果) |
| [qwenpaw-2b-flash-gptq-int4](deploy/qwenpaw-2b-flash-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwenpaw-2b-flash-gptq-int4.md#查看部署效果) |
| [Qwen3.5-0.8B-AX650-C128-P1152-CTX2047](deploy/qwen3-5-0-8b-ax650-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-0-8b-ax650-c128-p1152-ctx2047.md#查看部署效果) |
| [Qwen3.5-2B-AX650-C128-P1152-CTX2047](deploy/qwen3-5-2b-ax650-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-2b-ax650-c128-p1152-ctx2047.md#查看部署效果) |
| [Qwen3-VL-4B-Instruct-GPTQ-Int4](deploy/qwen3-vl-4b-instruct-gptq-int4.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-vl-4b-instruct-gptq-int4.md#查看部署效果) |
| [Qwen3.5-4B-AX650-GPTQ-Int4-C128-P1152-CTX2047](deploy/qwen3-5-4b-ax650-gptq-int4-c128-p1152-ctx2047.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/qwen3-5-4b-ax650-gptq-int4-c128-p1152-ctx2047.md#查看部署效果) |
| [FastVLM-0.5B](deploy/fastvlm-0-5b.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/fastvlm-0-5b.md#查看部署效果) |
| [FastVLM-1.5B](deploy/fastvlm-1-5b.md) | 图像与文本理解 | [已运行，效果仍需评估](deploy/fastvlm-1-5b.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- 检查回答中的人数、对象和场景细节；流畅的句子也可能包含与画面不符的描述。
- 测试范围因模型而异，以各部署页的输入和结果为准。名称中含 Video 不代表该页面已验证视频。
- 达到 max_tokens 上限的回复会在效果区标注。要求简短回答或调整上限后重新运行，不把截断文本当作完整结果。

更多量化与上下文变体见[完整模型目录](catalog.mdx)，按具体版本进入部署页。
