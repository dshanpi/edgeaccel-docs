---
title: "选择深度估计模型"
description: "区分空间层次与实际距离，按输入规格、部署配置与实际效果选择 M.2 算力卡模型。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 选择深度估计模型

<GuideHero label="视觉模型 · 深度估计" title="区分空间层次与实际距离" description="从单张图片生成深度层次图时，可选择 Depth-Anything-V2 或 Depth-Anything-3。各页提供对应程序与实测可视化。" facts={[["输入","单图或配套的左右图"],["输出","深度 / 视差与可视化"],["先检查","尺度定义与近远关系"]]} />

先完成[设备检查](../usage/device-check.md)与[首次推理](../usage/first-inference.md)。还未确定任务或卡容量时，先阅读[选型总览](selection.mdx)。

## 按业务输出选择方案

| 需要完成的任务 | 部署入口或方案 | 选择时确认 |
|---|---|---|
| 单张图片观察空间层次 | Depth-Anything-V2、Depth-Anything-3 | 先查本页权重输出定义；当前展示的相对深度不能直接解释为米。 |
| 双目输入恢复视差 | IGEV-plusplus、RAFT-stereo | 需要对应的左右图、校正与相机参数，不能只提供单张图片。 |
| 距离测量或避障 | 具备尺度依据的完整方案 | 使用已知距离检查误差；深度颜色图本身不是距离验收结果。 |

## 进入模型部署页

以下是本类任务的常用入口。点击模型名称查看“准备 → 下载 → 运行 → 效果展示”；点击状态直接对照实际结果。

| 模型 | 输出或用途 | 最近实测记录 |
|---|---|---|
| [Depth-Anything-V2](deploy/depth-anything-v2.md) | 深度估计 | [固定样例已核对](deploy/depth-anything-v2.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 8GB M.2 |
| [Depth-Anything-3](deploy/depth-anything-3.md) | 深度估计 | [已运行，效果仍需评估](deploy/depth-anything-3.md#查看部署效果)<br />RK3576 DshanPi A1 + AX8850 16GB M.2 |
| [IGEV-plusplus](deploy/igev-plusplus.md) | 深度估计 | [已运行，效果仍需评估](deploy/igev-plusplus.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |
| [RAFT-stereo](deploy/raft-stereo.md) | 深度估计 | [已运行，效果仍需评估](deploy/raft-stereo.md#查看部署效果)<br />RK3576 + AX8850 16GB M.2 |

实测仅覆盖对应日期、环境、权重与输入。“已运行”表示产生了输出，仍需评估业务效果；“固定样例已核对”也不代表全部权重或长期稳定性通过。更多变体见[完整模型目录](catalog.mdx)。

## 准备输入与配套文件

1. 保留原始图片与尺寸；双目样本还应记录左右顺序、同步和标定信息。
2. 固定可视化色表及数值范围，跨样本比较时避免逐图归一化造成误判。
3. 保存数值输出与可视化图，分别用于测量和人工检查。

## 对照效果并完成验收

| 检查环节 | 判断依据 |
|---|---|
| 近远关系 | 对照前后遮挡和场景结构检查层次，留意天空、反光、透明及弱纹理区域。 |
| 数值含义 | 确认输出是深度、逆深度还是视差，再决定如何换算或归一化。 |
| 尺度与误差 | 需要距离时，用标定参数及已知距离验收；单目与双目方案分别评估。 |

先复现部署页提供的输入，再使用自己的业务样本。比较多个模型时固定输入、参数和计时范围，保留原始输出与参考结果。

## 确认使用条件

- 单目页展示的相对深度不能直接解释为米；双目页按视差定义及标定信息处理。
- 需要实际距离时，先确认模型的尺度定义，并使用已知距离或标定数据检查。

## 接入下一步应用

双目、多视图等方案可在[完整模型目录](catalog.mdx)检索；输入数量与相机参数需按其独立指南配置。

<GuideNext items={[{"to":"/docs/models/deploy/depth-anything-3","title":"查看单目部署","text":"对照输入图片、数值输出与深度图。"},{"to":"/docs/models/deploy/igev-plusplus","title":"查看双目部署","text":"确认左右图、视差输出及检查范围。"}]} />
