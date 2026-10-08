---
title: "选择目标检测模型"
description: "先匹配目标类别，再比较检测效果，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择目标检测模型

<GuideHero label="视觉模型 · 目标检测" title="先匹配目标类别，再比较检测效果" description="目标检测输出目标类别、置信度和矩形框。通用场景可从 YOLO11 或 yolo26 开始；行业场景选择对应类别的专用模型。" facts={[["输入","单张图片 / 视频帧"],["输出","类别、置信度、检测框"],["先检查","漏检、误检与框的位置"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 人、车与常见物体 | YOLO11、yolo26、YOLOv5、YOLOv8 | 核对训练类别表；型号更新不等于对当前场景更准确。 |
| 安全帽、电动车等专用类别 | 对应行业检测模型 | 检查类别含义和拍摄角度；先用真实业务图片评估。 |
| 需要像素轮廓或人体关节 | [分割](segmentation.md) / [姿态](pose.md) | 检测框只表示范围，不提供物体边缘或关节坐标。 |
| 用文本指定新目标 | [开放词汇检测](open-vocabulary.md) | 文本特征与词表需要配套，另测不含目标的图片。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [YOLO11](deploy/yolo11.md) | 目标检测 | [已运行，效果仍需评估](deploy/yolo11.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [yolo26](deploy/yolo26.md) | 目标检测 | [已运行，效果仍需评估](deploy/yolo26.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [YOLOv5](deploy/yolov5.md) | 目标检测 | [固定样例已核对](deploy/yolov5.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [YOLOv8](deploy/yolov8.md) | 目标检测 | [已运行，效果仍需评估](deploy/yolov8.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [RT-DETR](deploy/rt-detr.md) | 目标检测 | [已运行，效果仍需评估](deploy/rt-detr.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [E_bike-axera](deploy/e-bike-axera.md) | 目标检测 | [固定样例已核对](deploy/e-bike-axera.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [Helmet-axera](deploy/helmet-axera.md) | 目标检测 | [固定样例已核对](deploy/helmet-axera.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [Person_car-axera](deploy/person-car-axera.md) | 目标检测 | [固定样例已核对](deploy/person-car-axera.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [Fall-axera](deploy/fall-axera.md) | 目标检测 | [固定样例已核对](deploy/fall-axera.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 准备包含目标、不含目标、遮挡和小目标的图片，并标出预期类别与位置。
2. 沿用部署页的输入尺寸、颜色顺序、缩放补边和后处理配置；替换权重时同步核对输出布局。
3. 记录置信度阈值与 NMS 设置。比较不同模型时固定输入和判断标准。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| 类别与位置 | 检测框是否覆盖目标，类别是否符合标注，有无同一目标重复框。 |
| 误检与漏检 | 分别查看背景、远处目标、遮挡和光照变化，不能只使用一张清晰正样本。 |
| 视频接入 | 记录解码、前处理、推理、后处理的总延迟；计数和告警另测跟踪、去重与连续帧规则。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- 行业权重只识别其训练类别，安全帽、车辆和跌倒模型不能互换。
- 静态图片中的 fall 标签不等于已经实现视频跌倒告警；视频业务还需要连续帧规则。

## 接入下一步应用

需要处理摄像头或文件视频时，先完成单张图片推理，再进入[视频处理](../usage/video.md)。

<GuideNext items={[{"to":"/docs/usage/video","title":"接入视频处理","text":"从单图结果扩展到文件视频与摄像头。"},{"to":"/docs/models/segmentation","title":"需要更精细的轮廓","text":"比较检测框与分割掩码的适用场景。"}]} />
