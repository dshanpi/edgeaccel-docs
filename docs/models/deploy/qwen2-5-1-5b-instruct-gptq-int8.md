---
title: "Qwen2.5-1.5B-Instruct-GPTQ-Int8 部署指南"
sidebar_label: "Qwen2.5-1.5B-Instruct-GPTQ-Int8"
description: "Qwen2.5-1.5B-Instruct-GPTQ-Int8 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-1.5B-Instruct-GPTQ-Int8 部署指南

Qwen2.5-1.5B-Instruct-GPTQ-Int8 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8` 的固定版本。下面下载本页选用的 39 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct-gptq-int8/a882598b8893
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8 \
  --include "README.md" "main_axcl_aarch64" "post_config.json" "qwen2.5-1.5b-gptq-int8-ax650/*" "qwen2.5_tokenizer.py" "qwen2.5_tokenizer/*" "run_qwen2.5_1.5b_gptq_int8_ax650.sh" \
  --revision a882598b8893f0baec13189cac7f62f57109c835 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备程序与分词服务

以下命令在连接算力卡的 RK3576 主机执行，沿用前文的 `MODEL_DIR`。文件约 2.43GB，另外预留运行和日志空间。本页使用主机内部存储、仓库自带的 `main_axcl_aarch64` 和 `qwen2.5_tokenizer.py` 分词服务。

```bash
python3 -m venv ~/edgeaccel/qwen25-gptq-env
source ~/edgeaccel/qwen25-gptq-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4' 'jinja2==3.1.6'
cd "$MODEL_DIR"
printf '%s  %s\n' \
  bb111fc00c54abb6142a8f44df087bf104c8150a1cefa6be55c6b174b932c4ec \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

程序校验须显示 `OK`，动态库检查不得出现 `not found`。设置固定采样参数，并保留上游配置副本：

```bash
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
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
python qwen2.5_tokenizer.py --host 127.0.0.1 --port 12345
```

保持这个终端运行。Python 服务负责分词，文本生成由 AXCL 程序在算力卡上完成。

## 运行单轮问答

另开主机终端，设置同一内部存储中的模型目录。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-1-5b-instruct-gptq-int8/a882598b8893
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

PROMPT='What is 2 + 3? Reply with only the number.'
WEIGHTS=qwen2.5-1.5b-gptq-int8-ax650
./main_axcl_aarch64 \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --tokenizer_type 2 \
  --filename_tokenizer_model http://127.0.0.1:12345 \
  --bos 0 --eos 0 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --live_print 0 --continue 0 --prompt "$PROMPT"
```

当前设置采用非 mmap 方式加载 embedding，在生成结束后显示完整回答并退出。复现其他单轮输入时，修改 `PROMPT` 后重新运行同一命令：

```text
请用一句中文说明 PCIe 的用途。
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

运行日志应完成 28 层和 post 模型初始化，随后输出回答并出现 `hit eos`。程序结束后运行 `axcl-smi`，确认推理进程已释放资源。该版本未输出首 token 耗时；效果展示保留完整进程耗时，包含模型加载、一次问答和退出。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-29 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

在 RK3576 + AX8850 16GB 上完成三条独立短输入，展示算术回答、中文用途说明和带代码围栏的 JSON 回复。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

返回 5，与 2 + 3 的计算结果一致。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是一种高速扩展总线标准，用于连接计算机的硬件组件，如图形卡、网络卡和存储设备，以提高数据传输速度和系统性能。
```

以一句中文说明 PCIe 用于连接计算机硬件组件，列举了图形卡、网络卡和存储设备。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
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

返回的对象包含 apple=3、pear=2，但带有 Markdown 代码围栏，未满足仅输出 JSON 对象的格式要求。

**使用时注意：**

- 算术示例结果正确，中文用途说明可读；JSON 示例含 Markdown 代码围栏，不能直接作为严格 JSON 解析。三条示例不代表完整问答质量评测通过。
- 本次仅实测16GB卡上的三条独立短输入；实际8GB容量、长文本、并发和持续运行需单独验证。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-29。模型版本：`a882598b8893f0baec13189cac7f62f57109c835`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 程序与分词 | 本仓库固定版本的main_axcl_aarch64与非UID分词服务；Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 / Jinja2 3.1.6 |
| 运行参数 | 主机内部ext4存储；use_mmap_load_embed=0，live_print=0，continue=0，top_k=1；关闭temperature、repetition_penalty及top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1完整进程 | 46.002 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 单轮示例2完整进程 | 53.142 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 单轮示例3完整进程 | 49.363 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |

适用范围：

- 算术示例结果正确，中文用途说明可读；JSON 示例含 Markdown 代码围栏，不能直接作为严格 JSON 解析。三条示例不代表完整问答质量评测通过。
- 本次仅实测16GB卡上的三条独立短输入；实际8GB容量、长文本、并发和持续运行需单独验证。
- 该版本程序未输出首token耗时；保留原生生成速率及含模型加载的完整进程耗时。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5-1.5b-gptq-int8-ax650/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer.py`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5_tokenizer.py) | 旧版分词服务入口 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen2.5_1.5b_gptq_int8_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/run_qwen2.5_1.5b_gptq_int8_ax650.sh) | 启动或构建脚本 |

仓库提交：`a882598b8893f0baec13189cac7f62f57109c835`。仓库中的 29 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/tree/a882598b8893f0baec13189cac7f62f57109c835)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/tree/a882598b8893f0baec13189cac7f62f57109c835)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-1.5B-Instruct-GPTQ-Int8/blob/a882598b8893f0baec13189cac7f62f57109c835/README.md)。

返回[完整模型目录](../catalog.mdx)。
