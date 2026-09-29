---
title: "lcm-lora-sdv1-5 部署指南"
sidebar_label: "lcm-lora-sdv1-5"
description: "lcm-lora-sdv1-5 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# lcm-lora-sdv1-5 部署指南

lcm-lora-sdv1-5 用于图像生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。需确认 AXCL 适配。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 确认算力卡接入条件

该提交的模型文件或示例已收录，尚未核对到可直接用于此 M.2 卡的完整 AXCL 组合。下面给出此模型的接入文件与待完成项目，当前不作为已可运行教程。

### 核对本模型的程序入口

| 程序入口 | 接入条件 |
| --- | --- |
| [`launcher.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/launcher.py) | 使用 PyAXEngine，需显式选择 AXCL 并核对配套输入 |

修改前备份程序；只切换执行后端，保留本模型的输入处理、输出解码和资源释放。修改后保存源码版本或补丁。

### 准备本模型的输入

本提交可核对的样本：`assets/img2img-init.png`、`assets/lcm_lora_sdv1_5_axmodel.png`、`assets/txt2img_1024x768_sample_0.png`、`assets/txt2img_1024x768_sample_1.png`、`assets/txt2img_1024x768_sample_2.png`、`assets/txt2img_1024x768_sample_3.png`。结合模型卡选择输入，结果图片不作为原始输入。

### 完成接入后再运行

1. 确认实际权重编译目标为本卡，检查输入输出的 shape、dtype、布局与批次。
2. Python 路径使用 `AXCLRTExecutionProvider`；C++ 路径使用 AXCL 设备初始化和内存接口。依赖 `/soc/lib` 或芯片板端 runtime 的程序需移植或另行编译。
3. 先用固定输入打通模型加载、执行与输出解码，再检查下节所列效果。

共用步骤见[Python 接口](../../usage/python.md)与[自定义模型接入](../custom-model.md)。配套入口确认后，再使用对应程序的参数运行。
## 下载模型与样例

本页使用 `AXERA-TECH/lcm-lora-sdv1-5` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/lcm-lora-sdv1-5/4ba40db7f8fd
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/lcm-lora-sdv1-5 \
  --revision 4ba40db7f8fddbf3e4f86edacf7fb255bb45d339 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 固定提示词、随机种子、步数和分辨率，检查图像内容和明显伪影。
- 分别记录首图耗时、后续耗时与峰值内存，验证各阶段输出接口一致。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`launcher.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/launcher.py) | Python 程序 / 前后处理 |
| [`models/text_encoder/sd15_text_encoder_sim.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/text_encoder/sd15_text_encoder_sim.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/unet.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/unet.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/vae_decoder.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/vae_decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/vae_encoder.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/vae_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models_1024x768/text_encoder/sd15_text_encoder_sim.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models_1024x768/text_encoder/sd15_text_encoder_sim.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/gradio_demo.png`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/assets/gradio_demo.png) | 示例输入 |
| [`config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/config.json) | 运行配置 |
| [`models/text_encoder/config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/text_encoder/config.json) | 运行配置 |
| [`models/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/tokenizer/tokenizer_config.json) | 运行配置 |
| [`models_1024x768/text_encoder/config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models_1024x768/text_encoder/config.json) | 运行配置 |
| [`models_1024x768/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models_1024x768/tokenizer/tokenizer_config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/requirements.txt) | Python 依赖清单 |
| [`run_img2img_axe_infer.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/run_img2img_axe_infer.py) | Python 程序 / 前后处理 |

仓库提交：`4ba40db7f8fddbf3e4f86edacf7fb255bb45d339`。仓库中的 7 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/tree/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 文本编码器、去噪网络和 VAE 需要同一套分辨率规格。512×512 与 1024×768 编译包分别部署；固定随机种子比较输出。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/tree/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/README.md)。
- [主要程序入口：launcher.py](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/launcher.py)。

返回[完整模型目录](../catalog.mdx)。
