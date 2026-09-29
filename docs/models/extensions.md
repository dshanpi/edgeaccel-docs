---
title: "选择 OCR、检索与图像增强模型"
---

# 选择 OCR、检索与图像增强模型

根据应用需要的最终输出选择模型：文字、向量、放大图像或局部特征。各页给出独立步骤与对应效果。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [PPOCR_v5](deploy/ppocr-v5.md) | 文字检测与识别 | [固定样例已核对](deploy/ppocr-v5.md#查看部署效果) |
| [PPOCR_v6](deploy/ppocr-v6.md) | 文字检测与识别 | [固定样例已核对](deploy/ppocr-v6.md#查看部署效果) |
| [PaddleOCR-VL-1.5](deploy/paddleocr-vl-1-5.md) | 文字检测与识别 | [固定样例已核对](deploy/paddleocr-vl-1-5.md#查看部署效果) |
| [Plate-axera](deploy/plate-axera.md) | 目标检测 | [固定样例已核对](deploy/plate-axera.md#查看部署效果) |
| [Qwen3-Embedding-0.6B](deploy/qwen3-embedding-0-6b.md) | 文本或图像向量 | [固定样例已核对](deploy/qwen3-embedding-0-6b.md#查看部署效果) |
| [clip](deploy/clip.md) | 文本或图像向量 | [固定样例已核对](deploy/clip.md#查看部署效果) |
| [MobileCLIP](deploy/mobileclip.md) | 图文相似度比较 | [已运行，效果仍需评估](deploy/mobileclip.md#查看部署效果) |
| [Real-ESRGAN](deploy/real-esrgan.md) | 图像增强与修复 | [已运行，效果仍需评估](deploy/real-esrgan.md#查看部署效果) |
| [superpoint](deploy/superpoint.md) | 图像特征提取 | [已运行，效果仍需评估](deploy/superpoint.md#查看部署效果) |
| [Bird-Species-Classification](deploy/bird-species-classification.md) | 图像分类 | [已运行，效果仍需评估](deploy/bird-species-classification.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- OCR 需要同时检查文字框和识别文本；向量检索需要比较匹配与不匹配输入的相似度。
- 图像增强应比较实际输出尺寸和细节；生成更大图片不等于新增了真实细节。
- 更换向量模型、归一化或预处理后，需要重新生成索引。

没有配套 AXCL 程序时，按[自定义模型接入](custom-model.md)完成前后处理。
