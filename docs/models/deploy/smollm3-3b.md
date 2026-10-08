---
title: "SmolLM3-3B 部署指南"
sidebar_label: "SmolLM3-3B"
description: "SmolLM3-3B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SmolLM3-3B 部署指南

SmolLM3-3B 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/SmolLM3-3B` 的固定版本。下面下载本页选用的 53 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/smollm3-3b/a00aaa540d2c
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SmolLM3-3B \
  --include ".gitignore" "README.md" "config.json" "infer_axmodel.py" "smollm3_axmodel/*" "smolvlm3_tokenizer/*" "utils/*" \
  --revision a00aaa540d2c0dcb911dbaa64e499254a6671a30 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备文本生成程序

本例在 RK3576 + AX8850 16GB M.2 算力卡上运行固定版本的 SmolLM3-3B。36 个解码层和输出层通过 `AXCLRTExecutionProvider` 执行，分词、词嵌入读取和 token 选择在主机 CPU 完成。

下载[配套运行包](/examples/smollm3-20261001.tar.gz)，保存到 `~/edgeaccel/smollm3-20261001.tar.gz`。在连接算力卡的 Linux 主机执行，沿用前文的 `MODEL_DIR`：

```bash
cd ~/edgeaccel
tar -xzf smollm3-20261001.tar.gz
cd smollm3-card
source ~/edgeaccel/python-env/bin/activate
python -m pip install -r requirements.txt
python verify_models.py --model-dir "$MODEL_DIR"
```

使用 Python 3.12 和已安装 PyAXEngine 的虚拟环境；路径不同则替换激活命令。校验应输出 `Verified 53 model files`。模型及配套文件约 5 GB，保留原目录结构，分词器目录名称为 `smolvlm3_tokenizer`。

程序沿用固定仓库中的 `utils/infer_func.py`，显式选择 AXCL 后端。约 1 GB 的 FP32 词嵌入以只读内存映射访问，保持原始数值。运行包保留输入、回答、自然结束状态及每次调用的检查记录，耗时包含这些检查。

## 运行短文本问答

输出目录必须尚不存在。以下命令依次运行算术、中文问答和 JSON 生成，每个问题重置上下文：

```bash
cd ~/edgeaccel/smollm3-card
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
python smollm3_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/smollm3-basic \
  --max-new-tokens 256
```

默认按官方示例添加 `/no_think` 系统指令。运行结束后，终端打印各问题的 `SAMPLE_RESULT`；输出目录中的 `deployment-result.json` 应为 `completed: true`，每个样本应为 `naturalEos: true`。回答内容见各样本的 `response` 字段。

更换问题时，使用 `--question` 并指定新的输出目录：

```bash
python smollm3_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/smollm3-custom \
  --question '请用一句话说明 PCIe 的用途。' \
  --max-new-tokens 256
```

`--think` 可取消 `/no_think` 指令。思考过程也占用生成 token，需要为推理过程和最终回答预留长度。达到生成上限仍未输出结束 token 时，脚本报告失败并保留已有结果，不将截断回答标记为完整输出。

本版本缓存上限为 2559 token，输入与生成预算之和须小于该值。固定示例均为短输入；对于分词长度恰好为 128 倍数的输入，脚本会停止并提示官方分块边界问题。更长上下文和多轮对话需另行验证。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 SmolLM3-3B 三组短输入生成，原始回答见本页。

**短文本问答与结构化输出**

以下为相互独立的三个输入与原始回答，均使用 /no_think。是否完成生成与是否遵循格式分别列出；每个问题均由模型输出结束 token。

**示例 1：输入**

```text
2+3等于多少？只输出数字。
```

**实际回复**

```text
5
```

回答为 5，满足本题的数值和“只输出数字”要求。

**示例 2：输入**

```text
请用一句话说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高性能的扩展接口标准，用于连接处理器、存储器、显卡等外围设备，提高系统的处理速度和扩展性。
```

回答说明了连接外围设备的用途。“提高系统的处理速度”是模型的概括表述，本例没有进行系统性能测试。

**示例 3：输入**

```text
有3个苹果和2个梨。只输出JSON对象，键为apple和pear，值为数量，不要解释或代码块。
```

**实际回复**

````text
```json
{
  "apple": 3,
  "pear": 2
}
```
````

apple 和 pear 的数值正确，但原始回答带有 Markdown 代码块，未满足“只输出 JSON、不要代码块”的要求。此项严格格式检查未通过；上方保留原文。

| 输入类型 | 输入 token | 生成 token（含结束） | 首 token / s | 生成流程 / s |
| --- | --- | --- | --- | --- |
| 算术 | 79 | 2 | 1.890 | 4.336 |
| 中文问答 | 78 | 47 | 1.361 | 70.112 |
| JSON | 99 | 21 | 1.508 | 30.816 |

**使用时注意：**

- 当前为 16GB 卡上的短输入基本运行；8GB 容量、长上下文、连续服务和多轮对话尚未验证。
- JSON 数值正确，但带有代码块，严格格式要求未通过。三个样本不能代表通用正确率。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`a00aaa540d2c0dcb911dbaa64e499254a6671a30`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际执行 | 37 个 AXModel | 36 个解码层与输出层，共 2,590 次调用。 |
| 输入覆盖 | 算术 / 中文 / JSON | 三个独立短输入，使用 /no_think；各自记录完整回答及自然结束。 |
| 模型加载 | 208.396 s | 首 token 与生成流程另列；包含主机处理、PCIe 传输和输出校验，不作为吞吐基准。 |

适用范围：

- 该示例保持官方贪心 token 选择，并加入文件校验、逐次输出检查和自然结束判定。
- 模型权重与程序已固定版本；词嵌入通过主机只读内存映射访问，分词和 token 选择也使用主机 CPU。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`smollm3_axmodel/smollm3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smollm3_axmodel/smollm3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm3_axmodel/smollm3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smollm3_axmodel/smollm3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm3_axmodel/smollm3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smollm3_axmodel/smollm3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm3_axmodel/smollm3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smollm3_axmodel/smollm3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm3_axmodel/smollm3_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smollm3_axmodel/smollm3_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/config.json) | 运行配置 |
| [`smolvlm3_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smolvlm3_tokenizer/config.json) | 运行配置 |
| [`smolvlm3_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smolvlm3_tokenizer/generation_config.json) | 运行配置 |
| [`smolvlm3_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/smolvlm3_tokenizer/tokenizer_config.json) | 运行配置 |

仓库提交：`a00aaa540d2c0dcb911dbaa64e499254a6671a30`。仓库中的 37 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SmolLM3-3B/tree/a00aaa540d2c0dcb911dbaa64e499254a6671a30)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SmolLM3-3B/tree/a00aaa540d2c0dcb911dbaa64e499254a6671a30)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/README.md)。
- [主要程序入口：infer_axmodel.py](https://huggingface.co/AXERA-TECH/SmolLM3-3B/blob/a00aaa540d2c0dcb911dbaa64e499254a6671a30/infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
