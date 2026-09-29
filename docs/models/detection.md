---
title: "选择目标检测模型"
---

# 选择目标检测模型

目标检测输出目标类别、置信度和矩形框。通用场景可从 YOLO11 或 yolo26 开始；行业场景选择对应类别的专用模型。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [YOLO11](deploy/yolo11.md) | 目标检测 | [固定样例已核对](deploy/yolo11.md#查看部署效果) |
| [yolo26](deploy/yolo26.md) | 目标检测 | [固定样例已核对](deploy/yolo26.md#查看部署效果) |
| [YOLOv5](deploy/yolov5.md) | 目标检测 | [固定样例已核对](deploy/yolov5.md#查看部署效果) |
| [YOLOv8](deploy/yolov8.md) | 目标检测 | [已运行，效果仍需评估](deploy/yolov8.md#查看部署效果) |
| [RT-DETR](deploy/rt-detr.md) | 目标检测 | [已运行，效果仍需评估](deploy/rt-detr.md#查看部署效果) |
| [E_bike-axera](deploy/e-bike-axera.md) | 目标检测 | [固定样例已核对](deploy/e-bike-axera.md#查看部署效果) |
| [Helmet-axera](deploy/helmet-axera.md) | 目标检测 | [固定样例已核对](deploy/helmet-axera.md#查看部署效果) |
| [Person_car-axera](deploy/person-car-axera.md) | 目标检测 | [固定样例已核对](deploy/person-car-axera.md#查看部署效果) |
| [Fall-axera](deploy/fall-axera.md) | 目标检测 | [固定样例已核对](deploy/fall-axera.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- 行业权重只识别其训练类别，安全帽、车辆和跌倒模型不能互换。
- 静态图片中的 fall 标签不等于已经实现视频跌倒告警；视频业务还需要连续帧规则。

需要处理摄像头或文件视频时，先完成单张图片推理，再进入[视频处理](../usage/video.md)。
