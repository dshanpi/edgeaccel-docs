---
title: "AXERA_Benchmark 资源使用"
sidebar_label: "AXERA_Benchmark"
description: "AXERA_Benchmark 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# AXERA_Benchmark 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

选择与卡目标和运行时一致的测试文件，固定输入、重复次数和计时范围，再保存设备内存与延迟。

继续阅读[对应操作指南](../../usage/performance.md)。本仓库固定参考提交为 `552cff9460e063cfe8b2704dc5abb798dc162418`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/config.json) | 运行配置 |
| [`deit_t_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/deit_t_onnx/config.json) | 运行配置 |
| [`depth_anything_v2_vits/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/depth_anything_v2_vits/config.json) | 运行配置 |
| [`inception_v1_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/inception_v1_onnx/config.json) | 运行配置 |
| [`inception_v3_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/inception_v3_onnx/config.json) | 运行配置 |
| [`mobilenet_v1_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/mobilenet_v1_onnx/config.json) | 运行配置 |
| [`mobilenet_v2_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/mobilenet_v2_onnx/config.json) | 运行配置 |
| [`resnet18_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/resnet18_onnx/config.json) | 运行配置 |
| [`resnet50_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/resnet50_onnx/config.json) | 运行配置 |
| [`squeezenet11_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/squeezenet11_onnx/config.json) | 运行配置 |
| [`swin_t_onnx/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/swin_t_onnx/config.json) | 运行配置 |
| [`yolov10s/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/yolov10s/config.json) | 运行配置 |
| [`yolov11s/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/yolov11s/config.json) | 运行配置 |
| [`yolov26s/config.json`](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/yolov26s/config.json) | 运行配置 |

仓库提交：`552cff9460e063cfe8b2704dc5abb798dc162418`。仓库中的 0 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/tree/552cff9460e063cfe8b2704dc5abb798dc162418)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/tree/552cff9460e063cfe8b2704dc5abb798dc162418)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/AXERA_Benchmark/blob/552cff9460e063cfe8b2704dc5abb798dc162418/README.md)。

返回[完整模型目录](../catalog.mdx)。
