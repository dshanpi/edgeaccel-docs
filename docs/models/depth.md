---
title: "选择深度估计模型"
---

# 选择深度估计模型

从单张图片生成深度层次图时，可选择 Depth-Anything-V2 或 Depth-Anything-3。各页提供对应程序与实测可视化。

## 进入模型部署页

| 模型 | 输出或用途 | 本机效果 |
|---|---|---|
| [Depth-Anything-V2](deploy/depth-anything-v2.md) | 深度估计 | [固定样例已核对](deploy/depth-anything-v2.md#查看部署效果) |
| [Depth-Anything-3](deploy/depth-anything-3.md) | 深度估计 | [固定样例已核对](deploy/depth-anything-3.md#查看部署效果) |

点击模型名称按步骤部署；点击效果状态查看该模型页面的图片、文本或音频输出。状态只适用于页面标明的版本和样例。

## 确认使用条件

- 当前展示的是相对深度，伪彩色和灰度值不能直接解释为米。
- 需要实际距离时，先确认模型的尺度定义，并使用已知距离或标定数据检查。

双目、多视图等方案可在[完整模型目录](catalog.mdx)检索；输入数量与相机参数需按其独立指南配置。
