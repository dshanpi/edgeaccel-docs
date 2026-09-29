---
title: "Qwen2.5-0.5B-Instruct-CTX-Int8 部署指南"
sidebar_label: "Qwen2.5-0.5B-Instruct-CTX-Int8"
description: "Qwen2.5-0.5B-Instruct-CTX-Int8 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-0.5B-Instruct-CTX-Int8 部署指南

Qwen2.5-0.5B-Instruct-CTX-Int8 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8` 的固定版本。下面下载本页选用的 35 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-ctx-int8/2aca5290377e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8 \
  "README.md" \
  "config.json" \
  "post_config.json" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l0_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l10_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l11_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l12_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l13_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l14_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l15_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l16_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l17_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l18_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l19_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l1_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l20_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l21_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l22_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l23_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l2_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l3_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l4_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l5_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l6_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l7_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l8_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l9_together.axmodel" \
  "qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_post.axmodel" \
  "qwen2.5_tokenizer/merges.txt" \
  "qwen2.5_tokenizer/tokenizer.json" \
  "qwen2.5_tokenizer/tokenizer_config.json" \
  "qwen2.5_tokenizer/vocab.json" \
  "qwen2.5_tokenizer_uid.py" \
  "run_qwen2.5_0.5b_gptq_int8_ctx_ax650.sh" \
  --revision 2aca5290377e6fa7ec1f49e37eda6554699ccfd0 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 AXCL 程序

本仓库固定版本提供 AX650 板端入口。M.2 算力卡使用下面已固定版本的官方 AXCL ARM64 程序，权重与 tokenizer 仍来自本页的 CTX Int8 仓库。

在前文设置的 `MODEL_DIR` 中下载程序并校验：

```bash
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4 \
  --revision 10db075dd5e99796adcec79452fcae0ec03ddded \
  --include main_axcl_aarch64 --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
printf '%s  %s\n' \
  1f9f1a1ca329b47f70840e8b6d104ce8248a82326aa2402bccb31144590a8fb2 \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

校验须显示 `OK`，动态库检查不得出现 `not found`。

## 启动分词服务

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
python - <<'PY'
import json
from pathlib import Path
p = Path('post_config.json')
backup = p.with_suffix('.json.upstream')
if not backup.exists():
    backup.write_bytes(p.read_bytes())
config = json.loads(p.read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
p.write_text(json.dumps(config, indent=2) + '\n')
PY
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持分词服务运行。

## 运行文本生成

另开终端，按本页 CTX Int8 权重名称启动程序：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-ctx-int8/2aca5290377e
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --system_prompt 'You are Qwen, created by Alibaba Cloud. You are a helpful assistant.' \
  --template_filename_axmodel 'qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l%d_together.axmodel' \
  --axmodel_num 24 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_post.axmodel \
  --filename_tokens_embed qwen2.5-0.5b-gptq-int8-ctx-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 151936 --tokens_embed_size 896 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0
```

在交互提示下输入问题，等待完整回复。输入 `q` 退出；每次核对新样例时重新启动程序。最后在分词服务终端按 `Ctrl+C` 关闭服务。下方只展示这套固定权重与 AXCL 程序组合的实际结果。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-27 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

复用固定版本官方 AXCL ARM64 程序，完成 CTX Int8 权重的三组单轮输入。算术返回 5；中文回复超过一句，JSON 字段与数值未符合请求。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

精确返回 5，数值与格式正确。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速数据传输接口，广泛应用于计算机、服务器、存储设备和网络设备等设备中。它的主要用途包括：

1. **高速数据传输**：PCIe支持高速数据传输，能够实现数据的高速传输，适用于需要大量数据传输的场景，如高速网络、高速存储设备等。

2. **高带宽**：PCIe的带宽非常大，可以支持更高的数据传输速率，适用于需要大量数据传输的场景，如高速网络、高速存储设备等。

3. **低延迟**：PCIe的延迟非常低，可以实现极低的延迟，适用于需要高实时性的场景，如高速网络、高速存储设备等。

4. **高可靠性**：PCIe设计有高可靠性，可以实现设备的高可靠性和高稳定性，适用于需要高可靠性的场景，如高速网络、高速存储设备等。

5. **兼容性**：PCIe支持多种设备和协议，可以兼容各种设备和协议，适用于需要兼容各种设备和协议的场景，如高速网络、高速存储设备等。

6. **扩展性**：PCIe的扩展性非常强，可以支持更多的设备和协议，适用于需要支持更多设备和协议的场景，如高速网络、高速存储设备等。

PCIe的广泛使用和性能优势使其成为现代计算机和网络设备中不可或缺的接口，广泛应用于各种设备中。
```

返回了多段重复性说明，未遵循一句话要求；其中笼统的性能和兼容性表述未作为技术结论采纳。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

````text
```json
{
  "result": [
    "apple",
    "pear"
  ]
}
```
````

返回了 result 数组，没有要求的 apple=3、pear=2 字段，且附带代码围栏，内容与格式均不符合要求。

**使用时注意：**

- 已确认这套固定 AXCL 程序与 CTX Int8 权重能够加载、生成和退出；回复质量尚待与同版本参考推理对照，不能据此判断为量化或硬件问题。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-27。模型版本：`2aca5290377e6fa7ec1f49e37eda6554699ccfd0`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | aarch64 / RK3576，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 推理程序 | 官方固定提交的 main_axcl_aarch64，AXCL 设备 0；跨仓库复用时另列程序来源与校验值。 |
| 分词服务 | 官方配套 tokenizer；Python 3.12 / Transformers 4.51.3 / Tokenizers 0.21.4 |
| 采样 | top_k=1；关闭 temperature、repetition_penalty、top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例 1 进程耗时 | 18.457 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 55.578 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 20.184 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

适用范围：

- 已确认这套固定 AXCL 程序与 CTX Int8 权重能够加载、生成和退出；回复质量尚待与同版本参考推理对照，不能据此判断为量化或硬件问题。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5-0.5b-gptq-int8-ctx-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_0.5b_gptq_int8_ctx_ax630c.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/run_qwen2.5_0.5b_gptq_int8_ctx_ax630c.sh) | 启动或构建脚本 |
| [`run_qwen2.5_0.5b_gptq_int8_ctx_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/run_qwen2.5_0.5b_gptq_int8_ctx_ax650.sh) | 启动或构建脚本 |

仓库提交：`2aca5290377e6fa7ec1f49e37eda6554699ccfd0`。仓库中的 50 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/tree/2aca5290377e6fa7ec1f49e37eda6554699ccfd0)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/tree/2aca5290377e6fa7ec1f49e37eda6554699ccfd0)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/README.md)。
- [主要程序入口：qwen2.5_tokenizer_uid.py](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-CTX-Int8/blob/2aca5290377e6fa7ec1f49e37eda6554699ccfd0/qwen2.5_tokenizer_uid.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
