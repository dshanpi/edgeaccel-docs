---
title: "选择语音合成模型"
---

# 选择语音合成模型

语音合成把文本转换成音频。按需要的语言、音色和参考语音方式选择模型，并使用该页指定的字典、编码器与声码器。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [MeloTTS](deploy/melotts.md) | 语音合成 | [已运行，效果仍需评估](deploy/melotts.md#查看部署效果) |
| [CosyVoice2](deploy/cosyvoice2.md) | 语音合成 | [已运行，效果仍需评估](deploy/cosyvoice2.md#查看部署效果) |
| [CosyVoice3](deploy/cosyvoice3.md) | 语音合成 | [已运行，效果仍需评估](deploy/cosyvoice3.md#查看部署效果) |
| [ZipVoice.AXERA](deploy/zipvoice-axera.md) | 语音合成 | [已运行，效果仍需评估](deploy/zipvoice-axera.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- 不同包的 tokens、lexicon、说话人特征和声码器不能互换。
- 生成 WAV 后需要播放，检查发音、停顿、杂音和尾部截断；文件存在不等于语音质量通过。

MeloTTS 页提供三段中文实测音频，可直接播放并对照输入文本；其他模型按各页状态选择。
