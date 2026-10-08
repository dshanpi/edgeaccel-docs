---
title: "选择分割与去背景模型"
description: "先区分实例、语义与透明前景，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择分割与去背景模型

<GuideHero label="视觉模型 · 分割与去背景" title="先区分实例、语义与透明前景" description="实例分割为每个目标生成掩码；语义分割按像素分配类别；去背景则保留前景并输出透明通道。按需要的输出选择模型。" facts={[["输入","图片；部分模型还需提示"],["输出","实例掩码 / 类别图 / Alpha"],["先检查","边缘、遮挡与小结构"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 分别选中每个物体 | YOLO11-Seg、yolo26-seg、YOLOv8-Seg | 同类物体应有独立实例，逐个核对掩码与检测框。 |
| 按像素区分类别 | DeepLabv3Plus | 确认类别表、背景标签和颜色映射。 |
| 抠图或替换背景 | RMBG-1.4 | 需要透明通道；重点检查头发、半透明和近似背景色。 |
| 用点或框选出区域 | MobileSAM | 提示方式、图像编码与掩码解码按部署页组合。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [YOLO11-Seg](deploy/yolo11-seg.md) | 图像分割 | [已运行，效果仍需评估](deploy/yolo11-seg.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [yolo26-seg](deploy/yolo26-seg.md) | 图像分割 | [已运行，效果仍需评估](deploy/yolo26-seg.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [YOLOv8-Seg](deploy/yolov8-seg.md) | 图像分割 | [已运行，效果仍需评估](deploy/yolov8-seg.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [DeepLabv3Plus](deploy/deeplabv3plus.md) | 图像分割 | [固定样例已核对](deploy/deeplabv3plus.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [RMBG-1.4](deploy/rmbg-1-4.md) | 图像分割 | [固定样例已核对](deploy/rmbg-1-4.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [MobileSAM](deploy/mobilesam.md) | 图像分割 | [已运行，效果仍需评估](deploy/mobilesam.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 保留原图分辨率，并准备边缘、遮挡、多个同类目标等样本。
2. 区分类别 ID 图、彩色可视化和透明 PNG；保存业务需要的原始输出格式。
3. 带提示的模型需保存点或框坐标，并核对输入缩放后的坐标映射。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| 区域一致性 | 对照原图检查前景完整性、背景渗漏和相邻实例粘连。 |
| 边缘与输出格式 | 放大查看细小结构；确认掩码尺寸、插值方法及 Alpha 通道。 |
| 应用叠加 | 还原到原图坐标后再叠加；视频使用时另外检查跨帧闪烁。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- 检测框正确不能代替掩码检查，重点比较物体边缘、遮挡和细小结构。
- RMBG 输出的透明 PNG 与彩色分割标签含义不同；集成时保留 Alpha 通道。

## 接入下一步应用

各模型的下载命令、程序入口和实际结果图均在对应部署页。

<GuideNext items={[{"to":"/docs/usage/python","title":"读取并处理掩码","text":"接入 AXCL Python 前后处理流程。"},{"to":"/docs/usage/video","title":"扩展到连续帧","text":"检查原图映射、延迟和跨帧表现。"}]} />
