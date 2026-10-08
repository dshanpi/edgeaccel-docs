---
title: "ppq-xs 资源使用"
sidebar_label: "ppq-xs"
description: "ppq-xs 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# ppq-xs 资源使用

本仓库提供工具或配套资源。

> 工具与配套资源

## 选择适用资源

面向 AX520 / AX513 工具链，不作为本卡默认模型转换工具。AX650 目标按 Pulsar2 流程处理。

继续阅读[对应操作指南](../../models/custom-model.md)。本仓库固定参考提交为 `5311ae8bd583f1442af06a69b2d052812fe7aee4`。


<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`tools/ppq-xs-1.7.6/Helium/myes_demo.py`](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/tools/ppq-xs-1.7.6/Helium/myes_demo.py) | Python 程序 / 前后处理 |
| [`tools/ppq-xs-1.7.6/ppq/samples/Openvino/Example_Benchmark.py`](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/tools/ppq-xs-1.7.6/ppq/samples/Openvino/Example_Benchmark.py) | Python 程序 / 前后处理 |
| [`config.json`](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/config.json) | 运行配置 |
| [`tools/ppq-xs-1.7.6/ppq/samples/TensorRT/trt_infer.py`](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/tools/ppq-xs-1.7.6/ppq/samples/TensorRT/trt_infer.py) | Python 程序 / 前后处理 |
| [`tools/ppq-xs-1.7.6/requirements.txt`](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/tools/ppq-xs-1.7.6/requirements.txt) | Python 依赖清单 |

仓库提交：`5311ae8bd583f1442af06a69b2d052812fe7aee4`。该提交没有预编译 `.axmodel` 文件。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/ppq-xs/tree/5311ae8bd583f1442af06a69b2d052812fe7aee4)。

</details>

## 检查使用结果

记录下载文件名、提交号、主机架构与安装组件版本。安装类资源先检查依赖和设备识别，模型类资源继续验证真实输入输出；界面和工具的启动结果分别记录。

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/ppq-xs/tree/5311ae8bd583f1442af06a69b2d052812fe7aee4)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/README.md)。
- [主要程序入口：tools/ppq-xs-1.7.6/Helium/myes_demo.py](https://huggingface.co/AXERA-TECH/ppq-xs/blob/5311ae8bd583f1442af06a69b2d052812fe7aee4/tools/ppq-xs-1.7.6/Helium/myes_demo.py)。

返回[完整模型目录](../catalog.mdx)。
