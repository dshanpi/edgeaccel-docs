---
title: "选择分割与去背景模型"
---

# 选择分割与去背景模型

实例分割为每个目标生成掩码；语义分割按像素分配类别；去背景则保留前景并输出透明通道。按需要的输出选择模型。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [YOLO11-Seg](deploy/yolo11-seg.md) | 图像分割 | [固定样例已核对](deploy/yolo11-seg.md#查看部署效果) |
| [yolo26-seg](deploy/yolo26-seg.md) | 图像分割 | [固定样例已核对](deploy/yolo26-seg.md#查看部署效果) |
| [YOLOv8-Seg](deploy/yolov8-seg.md) | 图像分割 | [固定样例已核对](deploy/yolov8-seg.md#查看部署效果) |
| [DeepLabv3Plus](deploy/deeplabv3plus.md) | 图像分割 | [已运行，效果仍需评估](deploy/deeplabv3plus.md#查看部署效果) |
| [RMBG-1.4](deploy/rmbg-1-4.md) | 图像分割 | [固定样例已核对](deploy/rmbg-1-4.md#查看部署效果) |
| [MobileSAM](deploy/mobilesam.md) | 图像分割 | [已运行，效果仍需评估](deploy/mobilesam.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- 检测框正确不能代替掩码检查，重点比较物体边缘、遮挡和细小结构。
- RMBG 输出的透明 PNG 与彩色分割标签含义不同；集成时保留 Alpha 通道。

各模型的下载命令、程序入口和实际结果图均在对应部署页。
