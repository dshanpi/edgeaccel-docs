---
title: "选择语音识别与声纹模型"
---

# 选择语音识别与声纹模型

语音转写输出文字，声纹比对输出说话人特征与相似度。先明确需要的结果，再选择相应模型。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [Whisper](deploy/whisper.md) | 语音识别 | [已运行，效果仍需评估](deploy/whisper.md#查看部署效果) |
| [SenseVoice](deploy/sensevoice.md) | 语音识别 | [已运行，效果仍需评估](deploy/sensevoice.md#查看部署效果) |
| [3D-Speaker](deploy/3d-speaker.md) | 声纹特征提取与说话人比对 | [已运行，效果仍需评估](deploy/3d-speaker.md#查看部署效果) |
| [3D-Speaker-MT.Axera](deploy/3d-speaker-mt-axera.md) | 音频理解与记录 | [本机尚未实测](deploy/3d-speaker-mt-axera.md#查看部署效果) |
| [3D-Speaker-Meeting-Summary](deploy/3d-speaker-meeting-summary.md) | 多阶段应用 | [本机尚未实测](deploy/3d-speaker-meeting-summary.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- Whisper 页面使用当前模型包的 tiny 编码器、解码器与 Python 入口；旧 whisper.axcl 的三段权重不能混用。
- 3D-Speaker 的声纹分数不能代替语音转写或完整会议分段。
- 先处理短文件，再单独接入录音、静音检测、长音频分段和流式识别。

Whisper 与 SenseVoice 页可播放输入音频并查看实际转写；3D-Speaker 页展示两套声纹模型的录音与相似度。
