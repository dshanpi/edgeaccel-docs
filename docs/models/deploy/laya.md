---
title: "Laya 部署指南"
sidebar_label: "Laya"
description: "Laya 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Laya 部署指南

Laya 用于结构化决策与文本分类。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Laya` 的固定版本。下面下载本页选用的 19 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/laya/4f02f411fb9b
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Laya \
  "english/config.json" \
  "english/model.axmodel" \
  "english/sample_output.json" \
  "english/sample_request.json" \
  "english/tokenizer/tokenizer.json" \
  "english/tokenizer/tokenizer_config.json" \
  "multilingual/config.json" \
  "multilingual/model.axmodel" \
  "multilingual/sample_output.json" \
  "multilingual/sample_request.json" \
  "multilingual/tokenizer/tokenizer.json" \
  "multilingual/tokenizer/tokenizer_config.json" \
  "python/ax650/infer.py" \
  "typed-decisions/config.json" \
  "typed-decisions/model.axmodel" \
  "typed-decisions/sample_output.json" \
  "typed-decisions/sample_request.json" \
  "typed-decisions/tokenizer/tokenizer.json" \
  "typed-decisions/tokenizer/tokenizer_config.json" \
  --revision 4f02f411fb9b9b09b4a4842b4486177b9594ba9e \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装独立运行环境

Laya 接收文字或 JSON 状态，按给定问题输出类别、分值或判断概率。它不生成聊天回复。仓库包含 `english`、`multilingual`、`typed-decisions` 三个检查点，需要分别选择模型目录。

在 RK3576 主机执行。先按[PyAXEngine 安装说明](../../usage/python.md)下载并校验官方 wheel，再创建 Laya 专用环境：

```bash
python3 -m venv ~/edgeaccel/laya-env
source ~/edgeaccel/laya-env/bin/activate
python -m pip install \
  ~/axcl-setup/axengine-0.1.3-py3-none-any.whl \
  'numpy==2.5.3' 'transformers==5.17.0' \
  'tokenizers==0.23.2' 'ml-dtypes==0.6.0'
python -m pip check
```

本例采用仓库要求的 NumPy、Transformers 和 Tokenizers 版本；独立环境避免改变其他模型的依赖。

## 指定算力卡后端

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path('python/ax650/infer.py')
s = p.read_text()
old = 'provider = "AxEngineExecutionProvider"'
new = 'provider = "AXCLRTExecutionProvider"'
if old in s:
    backup = p.with_suffix('.py.upstream')
    if not backup.exists():
        backup.write_text(s)
    p.write_text(s.replace(old, new))
else:
    assert new in s, '源码与固定版本不匹配'
PY
```

只改变推理后端，保留官方分词、问题编码和分值后处理。

## 运行中文决策样例

```bash
cd "$MODEL_DIR"
python python/ax650/infer.py multilingual \
  --input multilingual/sample_request.json
```

日志应显示 `AXCLRTExecutionProvider`，随后输出包含 4 个问题的 `answers` 对象。中文样例询问重复扣款工单的处理部门、紧急程度、是否要求退款、是否表示取消服务。

## 运行英文与工作流样例

```bash
cd "$MODEL_DIR"
python python/ax650/infer.py english \
  --input english/sample_request.json
python python/ax650/infer.py typed-decisions \
  --input typed-decisions/sample_request.json
```

`choice` 返回选中的类别，`score` 按本题给出的等级计算期望分值，`noul` 返回命题为真的概率值。`score` 不是百分比；同一个数值在不同等级定义下含义不同。下方展示三个检查点的实际输出。

## 制作桌面演示

需要在桌面观察决策过程时，可继续部署 [Laya 智能温室](../../projects/laya-greenhouse.md)。项目提供环境滑块、中文观察输入、动作概率与温室动画，使用同一 multilingual 检查点和 AXCL 后端。

也可体验 [Laya 游戏实验室](../../projects/laya-games.md)：包含打方块、Flappy Bird、俄罗斯方块与贪吃蛇，支持观察模型决策和手动落点评分。


## 查看部署效果

**固定样例已核对** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

English、Multilingual、Typed-decisions 三个检查点各完成 4 个问题。类别与数值输出均复现同版本配套样例，最大数值差小于 1×10⁻⁶；部分问题仍有较低置信度。

三个检查点分别运行同版本的 sample_request.json，每份输入包含 4 个问题。下表按实际数值展示，未将概率自动转换为业务动作。

**english：输入状态**

```text
{
  "body": "Invoice 4411 was charged twice. Please refund the duplicate today or we will cancel our plan."
}
```

| 问题 | 类型 | 实际输出 |
| --- | --- | --- |
| Which team should handle this request? | choice | billing（0.968965） |
| How urgent is this request? | score | 1.392206 / 2；最高概率等级 1 |
| Does the customer explicitly request a refund? | noul | 0.854811 |
| Does the customer threaten to cancel or leave? | noul | 0.844980 |

**multilingual：输入状态**

```text
{
  "body": "发票4411重复扣款，请今天退还多扣的金额，否则我们会取消服务。"
}
```

| 问题 | 类型 | 实际输出 |
| --- | --- | --- |
| 这条请求应由哪个团队处理？ | choice | billing（1.000000） |
| 这条请求有多紧急？ | score | 1.935920 / 2；最高概率等级 2 |
| 用户是否明确要求退款？ | noul | 0.992535 |
| 用户是否表示要取消或离开？ | noul | 0.939950 |

**typed-decisions：输入状态**

```text
{
  "workflow": "security",
  "record": "A production API key was posted in a public issue and is still active; revoke it immediately."
}
```

| 问题 | 类型 | 实际输出 |
| --- | --- | --- |
| What is the next security action? | choice | contain（0.406354） |
| How severe is the incident? | score | 1.737073 / 2；最高概率等级 2 |
| Could customer data be exposed? | noul | 0.480747 |
| Does this require immediate containment? | noul | 0.666736 |

三组类别及数值与同版本仓库配套输出逐项对照，最大数值差小于 1×10⁻⁶。该对照检验运行结果的可复现性；样例本身包含低置信度判断，使用前仍需确定自己的阈值和人工复核规则。

**使用时注意：**

- 每个检查点只使用一份官方输入，未进行完整分类数据集或业务阈值评估。
- 英文紧急程度最高概率为等级 1；工作流样例的类别置信度约 0.068，不能只根据接口完成就自动执行后续业务动作。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`4f02f411fb9b9b09b4a4842b4486177b9594ba9e`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel；AXCLRTExecutionProvider |
| NumPy / ml-dtypes | 2.5.3 / 0.6.0 |
| Transformers / Tokenizers | 5.17.0 / 0.23.2 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| english 四问题耗时 | 0.322634 s | Python predict 调用，包括问题编码、四次推理和后处理，不含模型加载 |
| multilingual 四问题耗时 | 0.152642 s | Python predict 调用，包括问题编码、四次推理和后处理，不含模型加载 |
| typed-decisions 四问题耗时 | 0.324172 s | Python predict 调用，包括问题编码、四次推理和后处理，不含模型加载 |
| 配套样例数值最大差 | 2.379e-08 | 类别、概率、置信度与分值逐项对照；不比较硬件耗时 |

适用范围：

- 使用 16GB 卡与独立 Python 环境；未验证 8GB 容量、并发或长期运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`demo/app.py`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/demo/app.py) | Python 程序 / 前后处理 |
| [`python/ax650/infer.py`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/python/ax650/infer.py) | Python 程序 / 前后处理 |
| [`english/model.axmodel`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/english/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`multilingual/model.axmodel`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/multilingual/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`typed-decisions/model.axmodel`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/typed-decisions/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/config.json) | 运行配置 |
| [`demo/assets/laya_demo.jpg`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/demo/assets/laya_demo.jpg) | 示例输入 |
| [`demo/requirements.txt`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/demo/requirements.txt) | Python 依赖清单 |
| [`english/config.json`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/english/config.json) | 运行配置 |
| [`english/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/english/tokenizer/tokenizer_config.json) | 运行配置 |
| [`multilingual/config.json`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/multilingual/config.json) | 运行配置 |
| [`multilingual/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/multilingual/tokenizer/tokenizer_config.json) | 运行配置 |
| [`python/ax650/requirements.txt`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/python/ax650/requirements.txt) | Python 依赖清单 |
| [`python/pytorch/infer.py`](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/python/pytorch/infer.py) | Python 程序 / 前后处理 |

仓库提交：`4f02f411fb9b9b09b4a4842b4486177b9594ba9e`。仓库中的 3 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Laya/tree/4f02f411fb9b9b09b4a4842b4486177b9594ba9e)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是非自回归结构化决策模型，输入含 state 与 questions，不能按普通聊天模型测试。仓库区分 english、multilingual、typed-decisions 三套权重，配套 bin/axllm 标明 AX650 板端。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Laya/tree/4f02f411fb9b9b09b4a4842b4486177b9594ba9e)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/README.md)。
- [主要程序入口：demo/app.py](https://huggingface.co/AXERA-TECH/Laya/blob/4f02f411fb9b9b09b4a4842b4486177b9594ba9e/demo/app.py)。

返回[完整模型目录](../catalog.mdx)。
