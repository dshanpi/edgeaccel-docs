---
title: "Qwen2.5-0.5B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen2.5-0.5B-Instruct-GPTQ-Int4"
description: "Qwen2.5-0.5B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-0.5B-Instruct-GPTQ-Int4 部署指南

Qwen2.5-0.5B-Instruct-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4` 的固定版本。下面下载本页选用的 36 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-gptq-int4/10db075dd5e9
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4 \
  "README.md" \
  "config.json" \
  "main_axcl_aarch64" \
  "post_config.json" \
  "qwen2.5-0.5b-gptq-int4-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l14_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l15_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l16_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l17_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l18_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l19_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l1_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l20_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l21_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l22_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l23_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l2_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l3_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l4_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l5_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l6_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l7_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l8_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l9_together.axmodel" \
  "qwen2.5-0.5b-gptq-int4-ax650/qwen2_post.axmodel" \
  "qwen2.5_tokenizer/merges.txt" \
  "qwen2.5_tokenizer/tokenizer.json" \
  "qwen2.5_tokenizer/tokenizer_config.json" \
  "qwen2.5_tokenizer/vocab.json" \
  "qwen2.5_tokenizer_uid.py" \
  "run_qwen2.5_0.5b_gptq_int4_axcl_aarch64.sh" \
  --revision 10db075dd5e99796adcec79452fcae0ec03ddded \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词服务

本例使用仓库中的 `main_axcl_aarch64` 通过 AXCL 在算力卡上推理，Python 只负责分词。使用 Python 3.12 虚拟环境安装已测试版本：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。本仓库的 `config.json` 是模型配置，不是新版 AX-LLM 服务配置；使用下面的专用入口。

## 运行文本生成

先设置与本页效果一致的贪心采样，原配置备份为 `post_config.json.upstream`：

```bash
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

保持该终端运行。另开终端，进入相同模型目录并启动官方 ARM64 算力卡脚本：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-gptq-int4/10db075dd5e9
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
bash run_qwen2.5_0.5b_gptq_int4_axcl_aarch64.sh
```

在交互提示下输入问题，等待完整回复。输入 `q` 退出；本页每条样例均重新启动一次推理程序，未沿用上一题的对话历史。运行结束后，在分词服务终端按 `Ctrl+C` 关闭服务。

先输入 `What is 2 + 3? Reply with only the number.` 核对基础输出，再对照下方中文和 JSON 样例。模型能够生成文字，不代表它能可靠完成事实问答或遵守结构化输出约束。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

固定问答已返回文本，但JSON 回复含代码围栏或额外文字，不能直接解析为指定对象；本次格式要求未通过。 JSON 字段也不符合要求。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

2 + 3 = 5，数值和只输出数字的要求均符合。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCI Express（PCI-E）是一种高速数据传输标准，用于连接计算机的多个设备。它允许设备之间的高速数据传输，使得计算机可以连接到服务器、存储设备和其他设备。PCI Express的用途包括：

1. 数据传输：PCI Express用于连接多个设备，使得数据可以高速传输。例如，可以连接多个存储设备，以实现数据的高速传输。

2. 网络连接：PCI Express可以连接多个网络设备，例如路由器、交换机等，以实现网络的高速连接。

3. 存储设备：PCI Express可以连接多个存储设备，例如硬盘、SSD等，以实现数据的高速传输。

4. 服务器：PCI Express可以连接多个服务器，例如服务器、存储服务器等，以实现服务器的高速连接。

5. 打印机：PCI Express可以连接多个打印机，以实现打印机的高速打印。

6. 打开设备：PCI Express可以连接多个打开设备，例如打印机、扫描仪等，以实现设备的高速扫描。

7. 服务器：PCI Express可以连接多个服务器，例如服务器、存储服务器等，以实现服务器的高速连接。

总之，PCI Express的用途非常广泛，可以用于连接多个设备，实现高速数据传输和连接，使得计算机可以连接到服务器、存储设备和其他设备。
```

没有遵循一句话要求，且多项设备用途表述不可靠；此回复不可作为 PCIe 技术说明。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

````text
```json
{
  "result": "false"
}
```
````

未返回要求的 apple、pear 字段，且附带 Markdown 围栏，内容和格式均不符合请求。

**使用时注意：**

- 本次只确认模型能够加载、生成与退出；中文事实性和结构化输出未通过核对。尚未用同版本未量化模型对照，不能据此归因于量化或硬件。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`10db075dd5e99796adcec79452fcae0ec03ddded`。

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
| 示例 1 进程耗时 | 16.583 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 49.634 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 17.671 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_qwen2.5_0.5b_gptq_int4_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/run_qwen2.5_0.5b_gptq_int4_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen2.5_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5_tokenizer_uid.py) | 旧版分词服务入口 |
| [`qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5-0.5b-gptq-int4-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_0.5b_gptq_int4_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/run_qwen2.5_0.5b_gptq_int4_ax650.sh) | 启动或构建脚本 |
| [`run_qwen2.5_0.5b_gptq_int4_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/run_qwen2.5_0.5b_gptq_int4_axcl_x86.sh) | 启动或构建脚本 |

仓库提交：`10db075dd5e99796adcec79452fcae0ec03ddded`。仓库中的 25 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/tree/10db075dd5e99796adcec79452fcae0ec03ddded)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/tree/10db075dd5e99796adcec79452fcae0ec03ddded)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/blob/10db075dd5e99796adcec79452fcae0ec03ddded/README.md)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
