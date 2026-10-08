---
title: "选择语音识别与声纹模型"
description: "分开验证“说了什么”和“谁在说话”，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择语音识别与声纹模型

<GuideHero label="语音模型 · 转写与声纹" title="分开验证“说了什么”和“谁在说话”" description="语音转写输出文字，声纹比对输出说话人特征与相似度。先明确需要的结果，再选择相应模型。" facts={[["输入","规定采样率与声道的音频"],["输出","转写 / 声纹 / 分段"],["先检查","文字、说话人与时间范围"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 把语音转为文字 | Whisper、SenseVoice | 核对支持语言和输入音频规格，再检查转写内容。 |
| 比较录音中的说话人 | 3D-Speaker | 使用匹配的特征模型；相似度阈值需用业务录音确定。 |
| 说话人分段与会议整理 | 3D-Speaker-MT、会议摘要方案 | 分段、转写、翻译和摘要分别检查，再评估完整流程。 |
| 实时录音与交互 | 文件识别 + 录音和分段流程 | 先验证短文件，再加入静音检测、缓冲与流式接入。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [Whisper](deploy/whisper.md) | 语音识别 | [已运行，效果仍需评估](deploy/whisper.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [SenseVoice](deploy/sensevoice.md) | 语音识别 | [已运行，效果仍需评估](deploy/sensevoice.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [3D-Speaker](deploy/3d-speaker.md) | 声纹特征提取与说话人比对 | [已运行，效果仍需评估](deploy/3d-speaker.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [3D-Speaker-MT.Axera](deploy/3d-speaker-mt-axera.md) | 音频理解与记录 | [已运行，效果仍需评估](deploy/3d-speaker-mt-axera.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [3D-Speaker-Meeting-Summary](deploy/3d-speaker-meeting-summary.md) | 多阶段应用 | [已运行，效果仍需评估](deploy/3d-speaker-meeting-summary.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 准备带参考文字的短录音，记录语言、采样率、声道、时长和噪声条件。
2. 按部署页准备编码器、解码器、词表和特征提取配置；旧入口与新模型包不可混搭。
3. 声纹测试同时准备同一人与不同人的录音，避免以一对录音确定通用阈值。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| 转写内容 | 比较漏字、错字、数字、专有名词及顺序；标点与文字分别检查。 |
| 分段与说话人 | 核对说话人切换、重叠语音、短片段与末尾覆盖，不用声纹分数代替转写结果。 |
| 长音频与链路 | 逐步增加时长，检查分段衔接、重复、丢失及端到端延迟。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- Whisper 页面使用当前模型包的 tiny 编码器、解码器与 Python 入口；旧 whisper.axcl 的三段权重不能混用。
- 3D-Speaker 的声纹分数不能代替语音转写或完整会议分段。
- 先处理短文件，再单独接入录音、静音检测、长音频分段和流式识别。

## 接入下一步应用

Whisper 与 SenseVoice 页可播放输入音频并查看实际转写；3D-Speaker 页展示两套声纹模型的录音与相似度。

<GuideNext items={[{"to":"/docs/models/speech-synthesis","title":"补齐语音回复","text":"将识别文本接入问答与语音合成。"},{"to":"/docs/models/catalog","title":"查找会议与语音应用","text":"筛选具体方案，逐项确认模型与依赖。"}]} />
