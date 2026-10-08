---
title: "M.2 算力卡使用指南"
description: "从连接 AX8850 M.2 算力卡、安装 AXCL 到首次推理、模型选择与应用部署的使用入口。"
slug: /
pagination_prev: null
pagination_next: ax650n/roadmap
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# M.2 算力卡使用指南

<GuideHero
  label="AX8850 · 从上手到应用"
  title="接好算力卡，运行模型，查看结果"
  description="通过 PCIe 将 M.2 算力卡连接到主机，使用 AXCL 调用卡上的 NPU。应用、输入准备与结果处理在主机侧完成，模型推理由算力卡执行。"
  facts={[["算力卡配置", "8GB / 16GB，按实际容量选择"], ["主机平台", "ARM64 Linux、x86_64 Linux、Windows x64"], ["部署流程", "准备 → 下载 → 运行 → 效果展示"]]}
/>

本指南围绕算力卡的实际使用展开：先完成环境安装和一次图片推理，再选择视觉、文本、多模态或语音模型，最后将结果接入自己的应用。具体卡型号、供电要求和配套软件以随卡资料及对应安装章节为准。

## 从当前进度开始

<GuideNext items={[
  {to: '/docs/ax650n/user-guide', title: '首次使用：连接与安装', text: '确认卡容量、连接方式和配套文件，按主机平台完成 AXCL 安装与设备检查。'},
  {to: '/docs/usage/first-inference', title: '环境已就绪：完成首次推理', text: '在 Linux 主机运行 YOLO11 图片检测，用一张带检测框的结果图片确认完整流程。'},
  {to: '/docs/models/selection', title: '已跑通样例：选择业务模型', text: '按需要的输出和卡容量筛选模型，进入独立部署页复现样例，再替换自己的输入。'},
  {to: '/docs/usage/application-guide', title: '已有模型：接入应用', text: '选择 Python、HTTP 或视频处理入口，并了解性能测量、运行维护与故障排查。'}
]} />

需要逐步学习时，打开[算力卡上手路线](ax650n/roadmap.mdx)，按阶段完成操作；已有环境或明确型号时，可直接进入相应章节。

## 选择主机安装入口

先阅读[接卡前的准备事项](getting-started/prepare.md)，确认主机接口、供电、散热和卡容量，再选择对应平台。**运行期间保持算力卡散热风扇开启。**

| 连接算力卡的主机 | 安装文档 | 安装后的下一步 |
|---|---|---|
| RK3576 等 ARM64 Linux 主机 | [ARM64 快速上手](ax650n/quick-start/arm64.md) | 检查设备，再完成首次图片推理 |
| Intel / AMD Linux 主机 | [Linux x86_64 快速上手](ax650n/quick-start/linux-x86.md) | 使用 x86_64 运行程序，完成相同的推理流程 |
| Windows x64 主机 | [Windows 快速上手](ax650n/quick-start/windows.md) | 按 Windows 章节检查设备并运行模型工具 |

Linux 主机安装完成后，先确认 `axcl-smi` 能识别设备，再进入[完成首次推理](usage/first-inference.md)。脚本运行与手动操作任选其一，无需重复执行。Windows 的安装包和操作方式以对应章节为准。

## 按需要的结果选择模型

还未确定型号，先看[按任务和容量选择模型](models/selection.mdx)；已有模型名称，直接到[模型目录与独立部署文档](models/catalog.mdx)查找。

| 希望得到的结果 | 适合查阅的文档 |
|---|---|
| 找出人物、车辆或指定物体，输出类别与检测框 | [目标检测](models/detection.md)、[开放词汇检测](models/open-vocabulary.md) |
| 得到物体轮廓、人体关键点或场景远近关系 | [图像分割](models/segmentation.md)、[姿态估计](models/pose.md)、[深度估计](models/depth.md) |
| 生成回答、总结文本或进行多轮对话 | [文本生成](models/text-generation.md)、[AXCL 大模型运行时](models/llm-runtime.md) |
| 描述图片、回答画面问题或理解视频内容 | [视觉与语言模型](models/vision-language.md) |
| 将语音转成文字，或将文字合成为语音 | [语音识别](models/speech-recognition.md)、[语音合成](models/speech-synthesis.md) |
| 识别文字、进行向量检索或使用其他行业模型 | [扩展应用](models/extensions.md) |

进入独立部署页后，按照 **准备 → 下载 → 运行 → 查看部署效果** 操作。先使用页面提供的输入复现结果，再换成自己的图片、音频或提示词。需要接入尚未适配的模型时，查看[自定义模型接入](models/custom-model.md)。

## 从模型走向完整项目

完成单模型运行后，可通过以下项目观察算力卡如何参与视频处理和交互应用。项目页提供各自的环境要求、部署步骤与效果说明。

<GuideNext items={[
  {to: '/docs/projects/six-streams', title: 'AX8850 六路 AI 视频推流', text: '同时展示检测、分割、跟踪、相对深度和过线计数，学习视频推流、本地预览、录像与服务管理。'},
  {to: '/docs/projects/laya-games', title: 'Laya 游戏实验室', text: '在游戏界面观察模型选择动作与评分，通过打方块、Flappy Bird、俄罗斯方块等场景查看决策效果。'}
]} />

开发自己的应用时，从[Python 调用](usage/python.md)、[HTTP 服务](usage/api-service.md)或[视频流接入](usage/video.md)选择合适的方式。增加视频路数、上下文长度或服务并发后，按[性能与稳定性检查](usage/performance.md)重新测量。

## 阅读部署效果与实测说明

模型页中的图片、文字、音频和视频用于对照实际输出。判断是否适合自己的应用时，重点检查以下三项：

- **环境是否一致**：核对卡容量、主机架构、AXCL、模型与运行程序版本。8GB 和 16GB 的记录分别使用。
- **验证到了哪一步**：区分已有部署步骤、产生实际输出和完成样例核对。尚未实测或未通过的配置，以页面标注为准。
- **输出是否满足需求**：样例运行成功后，用自己的业务输入检查准确性、完整性、响应速度和连续运行表现。

具体操作见[输出检查方法](reference/validation.md)。遇到设备识别、模型加载或服务异常，可按[故障现象排查](usage/troubleshooting.md)；术语、配套文件和原厂资料分别见[常用术语](reference/glossary.md)、[资料下载](downloads.md)与[来源说明](reference/sources.md)。
