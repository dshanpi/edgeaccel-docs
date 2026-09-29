---
title: "M.2 算力卡使用指南"
slug: /
---

# 使用 M.2 算力卡

本指南面向通过 PCIe 连接主机的 AX650 系列 M.2 算力卡，覆盖 AX8850 产品资料中的 8GB、16GB 配置。具体型号、容量、供电和配套 PAC 以随卡资料为准。RK3576 是主机，模型由算力卡上的 NPU 执行。

## 按顺序完成首次运行

1. [确认硬件与软件版本](getting-started/prepare.md)，选择主机安装指南：[ARM64](ax650n/quick-start/arm64.md)、[Linux x86_64](ax650n/quick-start/linux-x86.md) 或 [Windows](ax650n/quick-start/windows.md)。
2. Linux 主机进入[完成首次推理](usage/first-inference.md)，选择脚本运行或手动操作，完成 YOLO11 图片推理并查看结果；Windows 按对应平台指南操作。

首次运行完成后，再从[模型目录](models/catalog.mdx)选择其他任务，按[输出检查方法](reference/validation.md)核对自己的输入与输出。

“完成首次推理”目录中的第一篇介绍脚本运行，后三篇介绍手动检查设备、下载模型与编译示例。两种方式任选其一；使用脚本时，手动文档可按需用于排查问题。

## 选择应用

| 任务 | 阅读入口 | 完成后检查 |
|---|---|---|
| 图片检测与分析 | [检测](models/detection.md)、[分割](models/segmentation.md)、[姿态](models/pose.md)、[深度](models/depth.md) | 输出图片与输入内容一致 |
| 文本对话 | [部署 AXCL 大模型运行时](models/llm-runtime.md)、[运行文本模型](models/text-generation.md) | 短问答和多轮上下文正确 |
| 图片、视频理解 | [多模态问答](models/vision-language.md) | 能回答图像细节，能按采样帧解释视频 |
| 语音输入与输出 | [语音识别](models/speech-recognition.md)、[语音合成](models/speech-synthesis.md) | 识别文本、生成音频可核对 |
| OCR、检索与行业模型 | [扩展应用](models/extensions.md) | 输出结构与业务标注相符 |
| 视频流与应用接入 | [视频处理](usage/video.md)、[服务接口](usage/api-service.md)、[Python](usage/python.md) | 推理使用 AXCL，应用持续运行 |

## 区分文档与实测状态

各模型页按“准备、下载、运行、查看部署效果”组织。已实测模型展示对应 8GB 或 16GB 环境的真实输出；具体容量、版本和测试范围以该页记录为准。尚未实测的模型单独标注。环境与耗时可在效果区下方展开查看。

[接入应用与维护](usage/application-guide.md)按 Python、HTTP、视频和运行维护提供入口；完整多路演示见[AX8850 六路 AI 视频推流](projects/six-streams.md)。项目操作先区分部署版本，实测性能以记录中的环境为准。

[Qwen3-VL-8B 的 16GB 部署记录](ax650n/applications/qwen3-vl/usage.md)保留其原运行时与验证范围。参考资料与核对版本见[来源说明](reference/sources.md)。不熟悉 AXCL、PAC、CMM 等名称时，可查阅[常用术语](reference/glossary.md)。
