---
title: "Qwen2.5-1.5B-Instruct-python 部署指南"
sidebar_label: "Qwen2.5-1.5B-Instruct-python"
description: "Qwen2.5-1.5B-Instruct-python 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-1.5B-Instruct-python 部署指南

Qwen2.5-1.5B-Instruct-python 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-1.5B-Instruct-python` 的固定版本。下面下载本页选用的 43 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct-python/aa999d91e778
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-1.5B-Instruct-python \
  --include "Qwen2.5-1.5B-Instruct-GPTQ-Int8/LICENSE" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/README.md" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/config.json" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/generation_config.json" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/merges.txt" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/tokenizer.json" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/tokenizer_config.json" "Qwen2.5-1.5B-Instruct-GPTQ-Int8/vocab.json" "README.md" "chat.py" "infer.py" "infer_torch.py" "utils/infer_func.py" "Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/*" \
  --revision aa999d91e7789a80a00bb910cfed4ca8de2b38a2 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 Python 环境

以下命令在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`。本页选用的文件约 2.79GB，放在主机内部存储，并另外预留运行与输出空间。

在已安装 PyAXEngine 的 Python 环境中安装依赖：

```bash
python -m pip install 'torch==2.5.1' 'torchvision==0.20.1' \
  'transformers==4.51.3' 'tokenizers==0.21.4' 'jinja2==3.1.6' \
  'numpy==1.26.4' 'ml_dtypes==0.5.3' 'tqdm' 'pillow'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

确认提供者列表包含 `AXCLRTExecutionProvider`，且算力卡没有其他推理任务。本次使用 PyAXEngine `0.1.3`。Torch 用于主机端数据处理；28 个主模型和 post 模型通过 AXCL 在算力卡上执行。

## 运行文本问答

下载 [Python 算力卡示例包](../../../static/examples/qwen15b-python-card-example.zip)，解压到 `~/edgeaccel/`，得到 `~/edgeaccel/qwen15b-python-example/`。示例沿用官方 `infer.py` 的分词、prefill、decode 和 `top_k=1` 采样，接受命令行输入，指定 AXCL 后端，并保存完整 token 解码结果。

在同一 Python 环境中执行，输出目录使用一个尚不存在的路径：

```bash
EXAMPLE_DIR=~/edgeaccel/qwen15b-python-example
python "$EXAMPLE_DIR/qwen_python_card.py" \
  --model-dir "$MODEL_DIR" \
  --candidate "$EXAMPLE_DIR/infer_axcl.py" \
  --manifest "$EXAMPLE_DIR/download-manifest.json" \
  --output ~/edgeaccel/results/qwen15b-python-01
```

默认依次运行算术、中文用途说明和 JSON 输出三条独立输入，每条重新加载模型。运行结束后查看结果：

```bash
python -m json.tool ~/edgeaccel/results/qwen15b-python-01/result.json
axcl-smi
```

`completed` 为 `true`、各条 `exitCode` 为 `0` 且 `eosReached` 为 `true`，表示这些输入已完成生成。`output` 保留完整回答，`processSeconds` 包含模型加载、一次问答和进程退出，不是首 token 延迟。

指定自己的问题时增加 `--question`，并更换输出目录：

```bash
python "$EXAMPLE_DIR/qwen_python_card.py" \
  --model-dir "$MODEL_DIR" \
  --candidate "$EXAMPLE_DIR/infer_axcl.py" \
  --manifest "$EXAMPLE_DIR/download-manifest.json" \
  --question '请用一句中文说明 PCIe 的用途。' \
  --output ~/edgeaccel/results/qwen15b-python-02
```

本例为单轮问答。上游示例包含固定角色和日期背景，不应把其中的日期或天气当作实时信息。连续对话、接近上下文上限的长输入和实际 8GB 容量需要分别核对。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-29 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

在 RK3576 + AX8850 16GB 上通过 Python 调用 AXCL，完成算术、中文问答和 JSON 输出三条独立输入。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

返回 5，与计算结果一致。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速扩展插槽标准，用于连接计算机的外部设备，如显卡、声卡、网卡等，提高了计算机的性能和灵活性。
```

列举了显卡、声卡、网卡等扩展设备的用途；“外部设备”的措辞不够严谨，不能据此认定技术问答质量已通过。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

```text
{
  "apple": 3,
  "pear": 2
}
```

返回可直接解析的 JSON 对象，apple 为 3、pear 为 2，没有额外代码围栏。

**使用时注意：**

- 算术和本条 JSON 示例符合输入要求，中文回答仍有术语表述问题。三条短输入仅证明本页基础运行，不代表完整问答质量评测通过。
- 本次仅实测16GB卡上的三条独立短输入；连续对话、长上下文、并发、持续运行和实际8GB容量需要单独验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-29。模型版本：`aa999d91e7789a80a00bb910cfed4ca8de2b38a2`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| Python 依赖 | torch 2.5.1; torchvision 0.20.1; axengine 0.1.3; numpy 1.26.4; ml_dtypes 0.5.3; transformers 4.51.3; tokenizers 0.21.4 |
| 执行配置 | 主机内部ext4存储；AXCLRTExecutionProvider；官方Python prefill/decode；top_k=1、top_p=0.9、temperature=0.6；三条独立进程 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1完整进程 | 57.178 s | 包含模型加载、一次问答和退出，不是首token延迟。 |
| 单轮示例2完整进程 | 78.866 s | 包含模型加载、一次问答和退出，不是首token延迟。 |
| 单轮示例3完整进程 | 67.504 s | 包含模型加载、一次问答和退出，不是首token延迟。 |

适用范围：

- 算术和本条 JSON 示例符合输入要求，中文回答仍有术语表述问题。三条短输入仅证明本页基础运行，不代表完整问答质量评测通过。
- 本次仅实测16GB卡上的三条独立短输入；连续对话、长上下文、并发、持续运行和实际8GB容量需要单独验证。
- 上游逐token终端打印与完整字符串可能不同；本页展示完整token序列的实际解码结果。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/infer.py) | Python 程序 / 前后处理 |
| [`chat.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/chat.py) | Python 程序 / 前后处理 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8_axmodel/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8/config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8/config.json) | 运行配置 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8/generation_config.json) | 运行配置 |
| [`Qwen2.5-1.5B-Instruct-GPTQ-Int8/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/Qwen2.5-1.5B-Instruct-GPTQ-Int8/tokenizer_config.json) | 运行配置 |

仓库提交：`aa999d91e7789a80a00bb910cfed4ca8de2b38a2`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/tree/aa999d91e7789a80a00bb910cfed4ca8de2b38a2)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/tree/aa999d91e7789a80a00bb910cfed4ca8de2b38a2)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/README.md)。
- [主要程序入口：infer.py](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-python/blob/aa999d91e7789a80a00bb910cfed4ca8de2b38a2/infer.py)。

返回[完整模型目录](../catalog.mdx)。
