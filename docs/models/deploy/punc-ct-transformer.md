---
title: "punc-ct-transformer 部署指南"
sidebar_label: "punc-ct-transformer"
description: "punc-ct-transformer 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# punc-ct-transformer 部署指南

punc-ct-transformer 用于文本标点恢复。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/punc-ct-transformer` 的固定版本。下面下载本页选用的 8 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/punc-ct-transformer/2e4fdf033e79
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/punc-ct-transformer \
  "model.axmodel" \
  "python/example.py" \
  "python/sherpa_punct_sdk/__init__.py" \
  "python/sherpa_punct_sdk/inference.py" \
  "python/sherpa_punct_sdk/pipeline.py" \
  "python/sherpa_punct_sdk/postprocess.py" \
  "python/sherpa_punct_sdk/preprocess.py" \
  "tokens.json" \
  --revision 2e4fdf033e79f8eabd21453f0902a8ee3b547f29 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备标点恢复环境

在 RK3576 主机使用已安装 PyAXEngine 的虚拟环境，模型、字典和 SDK 必须来自前一节的同一提交。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip check
cd "$MODEL_DIR"
test -s model.axmodel && test -s tokens.json
```

## 恢复文本标点

本模型接收无标点文字，输出补入标点的文字，不提供聊天或翻译接口。推理使用 M.2 卡，字典编码和文本拼接在主机执行。

```bash
cd "$MODEL_DIR"
PYTHONPATH="$MODEL_DIR/python" python - <<'PY'
from sherpa_punct_sdk import PunctuationPipeline
model = PunctuationPipeline(
    'model.axmodel', 'tokens.json', provider='AXCLRTExecutionProvider')
texts = [
    '今天天气真不错我们出去走走吧',
    '这个方案有三个优点第一成本低第二效率高第三维护简单',
    '人工智能技术正在改变我们的生活方式明天下午三点在公司会议室开会请准时参加他是一名优秀的工程师工作认真负责北京是中国的首都拥有悠久的历史文化随着科技的发展人们的生活越来越便利',
]
for text in texts:
    print('输入：', text)
    print('输出：', model(text))
PY
```

日志应显示 `AXCLRTExecutionProvider`。逐句检查输出是否保留原文，句号、逗号是否放在合理位置。第三段输入超过单窗口长度，经过 SDK 的滑动窗口处理；下方保留本次实际断句，仍存在句末逗号和错误停顿。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

三段中文去除输出标点后均与输入一致，没有丢失原文；前两段以逗号结尾，长段落存在“拥有悠久。的历史文化”等错误断句，标点质量尚未通过核对。

**示例 1：无标点输入**

```text
今天天气真不错我们出去走走吧
```

**实际恢复结果**

```text
今天天气真不错，我们出去走走吧，
```

**示例 2：无标点输入**

```text
这个方案有三个优点第一成本低第二效率高第三维护简单
```

**实际恢复结果**

```text
这个方案有三个优点，第一，成本低，第二效率高。第三，维护简单，
```

**示例 3：无标点输入**

```text
人工智能技术正在改变我们的生活方式明天下午三点在公司会议室开会请准时参加他是一名优秀的工程师工作认真负责北京是中国的首都拥有悠久的历史文化随着科技的发展人们的生活越来越便利
```

**实际恢复结果**

```text
人工智能技术正在改变我们的生活方式。明天下午三点在公司会议室开会，请准时参加。他是一名优秀的工程师，工作，认真负责。北京是中国的首都，拥有悠久。的历史文化，随着科技的发展，人们的生活越来越便利。
```

以上保留原始标点；句末逗号和不合理断句没有人工修正。

**使用时注意：**

- 部分逗号和句号位置不合理；当前只确认模型与窗口处理能够执行。
- 仅测试三段中文，尚未覆盖数字、英文、专有名词或完整标点评测集。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`2e4fdf033e79f8eabd21453f0902a8ee3b547f29`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 15232MiB |
| Python / PyAXEngine | Python 3.12；官方 0.1.3.rc3 wheel（包版本 0.1.3）；AXCLRTExecutionProvider |
| NumPy / Pillow | 1.26.4 / 11.3.0 |
| ml-dtypes / OpenCV | 0.5.3 / opencv-python-headless 4.11.0.86 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 三次 Python 调用耗时 | 4.847808 / 0.004457 / 0.008721 s | 按展示顺序；包含 SDK 调用的前后处理，标点模型第一次包含延迟加载；不作为纯 NPU 延迟 |

适用范围：

- 本页使用 AX8850 16GB M.2 卡；未验证 8GB 容量、并发或长期连续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`python/example.py`](https://huggingface.co/AXERA-TECH/punc-ct-transformer/blob/2e4fdf033e79f8eabd21453f0902a8ee3b547f29/python/example.py) | Python 程序 / 前后处理 |
| [`model.axmodel`](https://huggingface.co/AXERA-TECH/punc-ct-transformer/blob/2e4fdf033e79f8eabd21453f0902a8ee3b547f29/model.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`python/requirements.txt`](https://huggingface.co/AXERA-TECH/punc-ct-transformer/blob/2e4fdf033e79f8eabd21453f0902a8ee3b547f29/python/requirements.txt) | Python 依赖清单 |

仓库提交：`2e4fdf033e79f8eabd21453f0902a8ee3b547f29`。仓库中的 1 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/punc-ct-transformer/tree/2e4fdf033e79f8eabd21453f0902a8ee3b547f29)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 这是文本标点恢复模型，输入为无标点文本，输出标点标签或恢复后的句子；不提供自由对话。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/punc-ct-transformer/tree/2e4fdf033e79f8eabd21453f0902a8ee3b547f29)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/punc-ct-transformer/blob/2e4fdf033e79f8eabd21453f0902a8ee3b547f29/README.md)。
- [主要程序入口：python/example.py](https://huggingface.co/AXERA-TECH/punc-ct-transformer/blob/2e4fdf033e79f8eabd21453f0902a8ee3b547f29/python/example.py)。

返回[完整模型目录](../catalog.mdx)。
