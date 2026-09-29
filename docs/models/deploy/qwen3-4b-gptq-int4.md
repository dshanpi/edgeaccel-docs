---
title: "Qwen3-4B-GPTQ-Int4 部署指南"
sidebar_label: "Qwen3-4B-GPTQ-Int4"
description: "Qwen3-4B-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-4B-GPTQ-Int4 部署指南

Qwen3-4B-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 DshanPi A1 + AX8850 8GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[编译 AXCL 大模型运行时](../llm-runtime.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-4B-GPTQ-Int4` 的固定版本。下面下载本页选用的 41 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-4b-gptq-int4/582922aeace5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-4B-GPTQ-Int4 \
  "config.json" \
  "qwen3_p128_l0_together.axmodel" \
  "qwen3_p128_l1_together.axmodel" \
  "qwen3_p128_l2_together.axmodel" \
  "qwen3_p128_l3_together.axmodel" \
  "qwen3_p128_l4_together.axmodel" \
  "qwen3_p128_l5_together.axmodel" \
  "qwen3_p128_l6_together.axmodel" \
  "qwen3_p128_l7_together.axmodel" \
  "qwen3_p128_l8_together.axmodel" \
  "qwen3_p128_l9_together.axmodel" \
  "qwen3_p128_l10_together.axmodel" \
  "qwen3_p128_l11_together.axmodel" \
  "qwen3_p128_l12_together.axmodel" \
  "qwen3_p128_l13_together.axmodel" \
  "qwen3_p128_l14_together.axmodel" \
  "qwen3_p128_l15_together.axmodel" \
  "qwen3_p128_l16_together.axmodel" \
  "qwen3_p128_l17_together.axmodel" \
  "qwen3_p128_l18_together.axmodel" \
  "qwen3_p128_l19_together.axmodel" \
  "qwen3_p128_l20_together.axmodel" \
  "qwen3_p128_l21_together.axmodel" \
  "qwen3_p128_l22_together.axmodel" \
  "qwen3_p128_l23_together.axmodel" \
  "qwen3_p128_l24_together.axmodel" \
  "qwen3_p128_l25_together.axmodel" \
  "qwen3_p128_l26_together.axmodel" \
  "qwen3_p128_l27_together.axmodel" \
  "qwen3_p128_l28_together.axmodel" \
  "qwen3_p128_l29_together.axmodel" \
  "qwen3_p128_l30_together.axmodel" \
  "qwen3_p128_l31_together.axmodel" \
  "qwen3_p128_l32_together.axmodel" \
  "qwen3_p128_l33_together.axmodel" \
  "qwen3_p128_l34_together.axmodel" \
  "qwen3_p128_l35_together.axmodel" \
  "qwen3_post.axmodel" \
  "model.embed_tokens.weight.bfloat16.bin" \
  "qwen3_tokenizer.txt" \
  "post_config.json" \
  --revision 582922aeace55d1369c17b837abd3b83a5f050e2 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。
## 核对运行配置

配置文件：`config.json`。

| 项目 | 当前配置 |
| --- | --- |
| 运行时模型名称 | `AXERA-TECH/Qwen3-4B-GPTQ-Int4` |
| 分词器类型（tokenizer_type） | `Qwen3` |
| 多模态类型（vlm_type） | 不启用 |
| Transformer 层数 | 36 |
| 分片命名模板 | `qwen3_p128_l%d_together.axmodel` |
| Embedding 模式 | 否 |

| 配置字段 | 文件路径 | 同提交文件表 |
| --- | --- | --- |
| `filename_post_axmodel` | `qwen3_post.axmodel` | 已找到 |
| `filename_tokens_embed` | `model.embed_tokens.weight.bfloat16.bin` | 已找到 |
| `url_tokenizer_model` | `qwen3_tokenizer.txt` | 已找到 |
| `post_config_path` | `post_config.json` | 已找到 |

逐层核对 36 个分片，不能用同系列其他版本补缺。文件名检查只能证明文件布局一致，实际张量和后端兼容性仍需加载验证。

## 检查完整模型包

在模型根目录执行文件检查：

```bash
cd "$MODEL_DIR"
python3 - <<'PY'
import json
from pathlib import Path
p = Path(".")
c = json.loads((p / "config.json").read_text())
files = [c["template_filename_axmodel"] % i for i in range(c["axmodel_num"])]
files += [c[k] for k in ["filename_post_axmodel","filename_tokens_embed","url_tokenizer_model","post_config_path"] if c.get(k)]
missing = [str(p / f) for f in files if not (p / f).is_file()]
assert not missing, missing
print("模型配套文件齐全")
PY
```

此包按新 `axllm` 配置接口核对。使用[本站编译的 AXCL 程序](../llm-runtime.md)，包内 `bin/axllm` 可能是 AX650 板端程序，不能仅因同为 ARM64 就直接使用。

## 启动单卡服务

终端 1 执行，保持服务前台运行：

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
"$AXLLM" version
AXLLM_DEVICES=0 "$AXLLM" serve "$MODEL_DIR" --port 8000
```

版本输出必须显示 AXCL 后端。保留内存预检；若提示 CMM 不足，先缩小模型或使用较短上下文的独立编译包，不关闭内存预检强制运行。

## 发送文本请求

在同一主机终端 2 执行。先从 `/v1/models` 获取实际模型名称。

```bash
python3 - <<'PY'
import json, urllib.request
base = "http://127.0.0.1:8000"
with urllib.request.urlopen(base + "/v1/models", timeout=30) as r:
    model = json.load(r)["data"][0]["id"]
payload = {"model": model, "messages": [{"role": "user", "content": "请用一句话说明 PCIe 的用途。"}], "max_tokens": 128, "temperature": 0}
endpoint = "/v1/chat/completions"
payload.update(enable_thinking=False, stream=False)
request = urllib.request.Request(base + endpoint,
    data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as r:
    result = json.load(r)
print(result["choices"][0]["message"]["content"])
PY
```

检查 choices 中的回复是否完整且与输入相关。替换 messages 中的提问文字，可复现下方其他问题；保持其余输入和生成参数一致。回复达到 max_tokens 上限时可能被截断，可先要求简短回答。HTTP 请求成功只说明接口可用，仍需按下节核对效果。

运行时依据：[固定源码版本](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)、[配置接口](https://github.com/AXERA-TECH/ax-llm/blob/8501c22b940f8c5804cb35044c5ffc136918b8f1/docs/configuration.md)。

## 查看部署效果

**固定样例已核对** · 2026-09-23 · RK3576 DshanPi A1 + AX8850 8GB M.2。以下输入与输出来自本页固定版本的实际运行。

三组固定短样例已核对：算术题只返回 5；中文说明 PCIe 是连接显卡、固态硬盘等设备的高速串行扩展总线；第三次返回可直接解析的 JSON，apple=3、pear=2。本结论仅覆盖这三个问题与本页固定版本。

**示例 1：输入**

```text
What is 2 + 3? Answer with only the number.
```

**实际回复**

```text
5
```

**示例 2：输入**

```text
请用一句话说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速串行计算机扩展总线标准，用于连接计算机内部的高速设备，如显卡、固态硬盘和网络接口卡等。
```

**示例 3：输入**

```text
只输出 JSON：把苹果的数量 3 和梨的数量 2 写成一个对象，键名分别为 apple 和 pear。
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

**使用时注意：**

- 本页的正确性结论只覆盖三组短样例，不能推断复杂推理、知识准确率或任意 JSON 任务都能通过。
- 单 token 算术回复未返回 decode_tps；两条较长回复分别约 2.316 与 2.421 token/s，不作为统一性能基准。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 DshanPi A1 + AX8850 8GB M.2。日期：2026-09-23。模型版本：`582922aeace55d1369c17b837abd3b83a5f050e2`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机系统 | Ubuntu 24.04 / Armbian 25.11.0-trunk，aarch64 |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0；CMM 总量 7040 MiB，空闲基线占用 18 MiB |
| AX-LLM 提交 | 8501c22b940f8c5804cb35044c5ffc136918b8f1；Release / AXCL / Linux aarch64 |
| 大模型测试方式 | 单卡串行运行，3 次独立请求；temperature=0、enable_thinking=false、stream=false、max_tokens=128 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 完整生成请求 | 3 | 仅 /v1/chat/completions；另有 health 与模型列表两项接口检查 |
| 三次 HTTP 耗时 | 1.908 / 18.200 / 5.942 s | 按本页展示顺序；客户端从请求到完整回复，不包含服务启动 |
| 三次首 token 延迟 | 1522.421 / 1358.189 / 1392.288 ms | 运行时返回的 usage 字段；单 token 回复可能没有 decode_tps，不估算缺失值。TTFT 非客户端流式到达时间 |
| 三次生成速率 | 未返回 / 2.316 / 2.421 token/s | 运行时返回的 usage 字段；单 token 回复可能没有 decode_tps，不估算缺失值。TTFT 非客户端流式到达时间 |
| 服务就绪等待 | 74.52 s | 进程启动至 /health 返回成功，含模型加载与轮询等待 |

适用范围：

- 本页的正确性结论只覆盖三组短样例，不能推断复杂推理、知识准确率或任意 JSON 任务都能通过。
- 单 token 算术回复未返回 decode_tps；两条较长回复分别约 2.316 与 2.421 token/s，不作为统一性能基准。
- 仅执行本页列出的短请求，未测试长期稳定性、并发或最大上下文；上游板端性能不作为本机结果。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/config.json) | 运行配置 |
| [`qwen3_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/post_config.json) | 运行配置 |
| [`qwen3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/qwen3_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`582922aeace55d1369c17b837abd3b83a5f050e2`。仓库中的 37 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/tree/582922aeace55d1369c17b837abd3b83a5f050e2)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/tree/582922aeace55d1369c17b837abd3b83a5f050e2)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-4B-GPTQ-Int4/blob/582922aeace55d1369c17b837abd3b83a5f050e2/README.md)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen3-4B-GPTQ-Int4)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
