---
title: "DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 部署指南"
sidebar_label: "DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4"
description: "DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 部署指南

DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 本机尚未实测。有 AXCL 专用脚本。

## 准备运行环境

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4` 的固定版本。仓库可能包含多个芯片或模型规格，下载前检查磁盘空间。

```bash
MODEL_DIR=~/edgeaccel/models/deepseek-r1-distill-qwen-7b-gptq-int4/9b903307e1ea
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4 \
  --revision 9b903307e1ea3b216330e88f8e6fe39b6627bb74 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 选择 AXCL 启动入口

此包使用旧版专用程序，保留其脚本、分片和 tokenizer 服务组合。不能直接替换成新版 `axllm run`。

| 启动脚本 | 主机 / 模式 |
| --- | --- |
| [`run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh) | ARM64 |
| [`run_deepseek-r1_7b_gptq_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_axcl_x86.sh) | x86_64 |

本页选择 `run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh`。在 RK3576 上还需用 file 确认程序是 ARM64，并用 ldd 检查 AXCL 依赖。

```bash
cd "$MODEL_DIR"
file main_axcl_aarch64
ldd main_axcl_aarch64
```

依赖中不能出现 `not found`。

## 启动配套分词服务

在终端 1 激活安装本仓库依赖的 Python 环境，在模型根目录启动 `deepseek-r1_tokenizer.py`：

```bash
cd "$MODEL_DIR"
python3 deepseek-r1_tokenizer.py --host 127.0.0.1 --port 12345
```

保持该终端运行，在另一个终端用 `ss -ltnp` 确认端口 12345 已监听。首次启动可能还需模型卡指定的 tokenizer 资源；不能用同系列另一个服务脚本替代。

## 配置并运行本机脚本

终端 2 在模型目录复制脚本，在副本中设置本机参数：

```bash
cd "$MODEL_DIR"
cp -n run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh.local
sed -n '1,220p' run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh.local
```

- 将 tokenizer URL 改为本机服务地址，并保留与服务一致的端口。地址 `0.0.0.0` 用于监听，不作为客户端目标，客户端改用 `127.0.0.1`。
- 核对脚本中的模型目录、embedding、post 模型和输入文件全部存在。不要改变已编译的层数和上下文规格。

确认架构、依赖、文件和附加服务均匹配后，在终端 2 执行：

```bash
cd "$MODEL_DIR"
set -o pipefail
bash run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh.local 2>&1 | tee run.log
```

保存修改后的脚本和日志。设备初始化、tokenizer 连接或模型加载失败时停止，先解决对应依赖。

## 查看部署效果

**本机尚未实测。** 部署后请按以下项目检查输出。

- 先测短问答，再测两轮上下文；翻译模型使用有参考译文的短句。
- 记录首 token 延迟、生成速率和实际上下文长度，确认没有乱码、持续重复或异常提前结束。

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |
| [`deepseek-r1_tokenizer.py`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1_tokenizer.py) | 旧版分词服务入口 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1-7b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/config.json) | 运行配置 |
| [`deepseek-r1_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/post_config.json) | 运行配置 |
| [`run_deepseek-r1_7b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_deepseek-r1_7b_gptq_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/run_deepseek-r1_7b_gptq_int4_axcl_x86.sh) | 启动或构建脚本 |

仓库提交：`9b903307e1ea3b216330e88f8e6fe39b6627bb74`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/tree/9b903307e1ea3b216330e88f8e6fe39b6627bb74)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/tree/9b903307e1ea3b216330e88f8e6fe39b6627bb74)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/README.md)。
- [主要程序入口：deepseek-r1_tokenizer.py](https://huggingface.co/AXERA-TECH/DeepSeek-R1-Distill-Qwen-7B-GPTQ-Int4/blob/9b903307e1ea3b216330e88f8e6fe39b6627bb74/deepseek-r1_tokenizer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
