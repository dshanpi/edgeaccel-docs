---
title: "选择 OCR、检索与图像增强模型"
description: "按应用需要的结果选择处理链路，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择 OCR、检索与图像增强模型

<GuideHero label="扩展模型 · 文字、检索与决策" title="按应用需要的结果选择处理链路" description="根据应用需要的最终输出选择模型：文字、向量、放大图像或局部特征。各页给出独立步骤与对应效果。" facts={[["输入","图片、文本或结构化状态"],["输出","文字 / 向量 / 图像 / 类别"],["先检查","结果含义与配套处理"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 读取文字与牌照 | PPOCR、PaddleOCR-VL、Plate 对应部署页 | 区分文字检测、识别、版面理解与牌照字符解码。 |
| 文本或图文检索 | Qwen3-Embedding、CLIP、MobileCLIP | 核对编码器、归一化和相似度；检索与回答生成分别配置。 |
| 图像放大与增强 | Real-ESRGAN 等图像处理模型 | 比较原图细节和输出尺寸，注意伪影与内容变化。 |
| 局部特征与细分类别 | superpoint、Bird-Species-Classification | 特征点还需匹配几何处理；分类输出需匹配标签表。 |
| 固定动作决策与交互展示 | Laya | 把状态转换为模型输入，核对候选动作与分数，再驱动界面。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [PPOCR_v5](deploy/ppocr-v5.md) | 文字检测与识别 | [已运行，效果仍需评估](deploy/ppocr-v5.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [PPOCR_v6](deploy/ppocr-v6.md) | 文字检测与识别 | [已运行，效果仍需评估](deploy/ppocr-v6.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [PaddleOCR-VL-1.5](deploy/paddleocr-vl-1-5.md) | 文字检测与识别 | [固定样例已核对](deploy/paddleocr-vl-1-5.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [Plate-axera](deploy/plate-axera.md) | 目标检测 | [固定样例已核对](deploy/plate-axera.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [Qwen3-Embedding-0.6B](deploy/qwen3-embedding-0-6b.md) | 文本或图像向量 | [固定样例已核对](deploy/qwen3-embedding-0-6b.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [clip](deploy/clip.md) | 文本或图像向量 | [固定样例已核对](deploy/clip.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [MobileCLIP](deploy/mobileclip.md) | 图文相似度比较 | [已运行，效果仍需评估](deploy/mobileclip.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [Real-ESRGAN](deploy/real-esrgan.md) | 图像增强与修复 | [固定样例已核对](deploy/real-esrgan.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [superpoint](deploy/superpoint.md) | 图像特征提取 | [已运行，效果仍需评估](deploy/superpoint.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Bird-Species-Classification](deploy/bird-species-classification.md) | 图像分类 | [已运行，效果仍需评估](deploy/bird-species-classification.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [Laya](deploy/laya.md) | 结构化决策与文本分类 | [固定样例已核对](deploy/laya.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 明确输出类型，准备带参考文字、检索标签、原图或正确类别的业务样本。
2. 记录字典、类别表、特征维度、归一化及距离定义；这些文件或设置改变时重新检查结果。
3. 组合应用先分别验证各模型，再保存完整输入、处理中间结果和最终输出。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| OCR 与检索 | OCR 同时核对框和文字；检索对比相关与不相关候选，检查排序而非单个分数。 |
| 图像与特征 | 检查尺寸、细节、伪影和坐标；更大图片或更多特征点不等于更准确。 |
| 类别与决策 | 核对标签顺序、错误输入与低分情况；界面动作与实际模型输出一一对应。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- OCR 需要同时检查文字框和识别文本；向量检索需要比较匹配与不匹配输入的相似度。
- 图像增强应比较实际输出尺寸和细节；生成更大图片不等于新增了真实细节。
- 更换向量模型、归一化或预处理后，需要重新生成索引。

## 接入下一步应用

没有配套 AXCL 程序时，按[自定义模型接入](custom-model.md)完成前后处理。

<GuideNext items={[{"to":"/docs/projects/laya-games","title":"体验 Laya 交互项目","text":"将模型决策放到可见的游戏场景中。"},{"to":"/docs/models/custom-model","title":"适配自己的模型","text":"固定输入输出，完成转换与主机集成。"}]} />
