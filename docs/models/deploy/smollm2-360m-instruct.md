---
title: "SmolLM2-360M-Instruct 部署指南"
sidebar_label: "SmolLM2-360M-Instruct"
description: "SmolLM2-360M-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# SmolLM2-360M-Instruct 部署指南

SmolLM2-360M-Instruct 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/SmolLM2-360M-Instruct` 的固定版本。下面下载本页选用的 47 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/smollm2-360m-instruct/17a64761eff9
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/SmolLM2-360M-Instruct \
  "README.md" \
  "config.json" \
  "main_axcl_aarch64" \
  "post_config.json" \
  "run_smollm2_360m_axcl_aarch64.sh" \
  "smollm2-360m-ax650/llama_p128_l0_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l10_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l11_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l12_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l13_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l14_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l15_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l16_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l17_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l18_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l19_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l1_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l20_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l21_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l22_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l23_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l24_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l25_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l26_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l27_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l28_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l29_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l2_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l30_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l31_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l3_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l4_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l5_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l6_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l7_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l8_together.axmodel" \
  "smollm2-360m-ax650/llama_p128_l9_together.axmodel" \
  "smollm2-360m-ax650/llama_post.axmodel" \
  "smollm2-360m-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "smollm2_tokenizer.py" \
  "smollm2_tokenizer/chat_template.jinja" \
  "smollm2_tokenizer/merges.txt" \
  "smollm2_tokenizer/special_tokens_map.json" \
  "smollm2_tokenizer/tokenizer.json" \
  "smollm2_tokenizer/tokenizer_config.json" \
  "smollm2_tokenizer/vocab.json" \
  "smollm2_tokenizer_uid.py" \
  --revision 17a64761eff9cee7817f368f7a398e91635a055b \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词服务

模型使用官方 `main_axcl_aarch64` 通过 AXCL 在设备 0 推理。Python 分词服务在 RK3576 主机运行，安装已测试版本：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。本页使用 `smollm2-360m-ax650` 权重；仓库中的空 `config.json` 不作为新版 AX-LLM 服务配置。

## 运行文本生成

设置与下方效果一致的采样参数，然后启动 UID 分词服务：

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
python smollm2_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持该终端运行。在另一终端执行以下命令。显式指定配套 tokenizer 的系统提示词；`--live_print 0` 在完整解码后输出，避免中文字符被流式 token 分块截开。

```bash
MODEL_DIR=~/edgeaccel/models/smollm2-360m-instruct/17a64761eff9
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --template_filename_axmodel 'smollm2-360m-ax650/llama_p128_l%d_together.axmodel' \
  --axmodel_num 32 \
  --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel smollm2-360m-ax650/llama_post.axmodel \
  --filename_tokens_embed smollm2-360m-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 49152 --tokens_embed_size 960 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0 \
  --system_prompt 'You are a AI assistant, created by HuggingfaceTB'
```

输入问题并等待回复，输入 `q` 退出。本页三个样例分别重新启动推理程序，使用独立对话。结束使用后，在分词服务终端按 `Ctrl+C`。

先输入 `Return only a JSON object with apple equal to 3 and pear equal to 2.`，检查回复是否能直接解析为 JSON，再核对字段与数值。其他输入仍需按业务要求评估。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-27 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

使用配套 SmolLM2 系统提示词完成三组输入。JSON 内容和格式符合要求；算术数值正确但格式不符，中文说明存在重复与不准确表述。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
2 + 3 = 5.
```

算术数值正确，但附带算式和句号，没有遵循只输出数字的要求。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 的用途是为了提供硬盘和硬件的连接，允许计算机进行硬盘和硬件的连接，并且可以使用PCIe 的硬盘和硬件进行连接。
```

回复为一句话，但内容重复，没有清楚解释 PCIe 的用途，不能作为技术说明。

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

原始回复可直接解析为 JSON，apple=3、pear=2，字段、数值和格式均符合本题要求。

**使用时注意：**

- 只核对三个固定问题。算术格式和中文说明未通过；尚未使用同版本未量化模型比较，不能将这些问题归因于硬件。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-27。模型版本：`17a64761eff9cee7817f368f7a398e91635a055b`。

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
| 示例 1 进程耗时 | 20.531 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 33.520 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 21.217 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

适用范围：

- 只核对三个固定问题。算术格式和中文说明未通过；尚未使用同版本未量化模型比较，不能将这些问题归因于硬件。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_smollm2_360m_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/run_smollm2_360m_axcl_aarch64.sh) | 启动或构建脚本 |
| [`smollm2_tokenizer.py`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2_tokenizer.py) | 旧版分词服务入口 |
| [`smollm2-360m-ax650/llama_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2-360m-ax650/llama_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm2-360m-ax650/llama_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2-360m-ax650/llama_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm2-360m-ax650/llama_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2-360m-ax650/llama_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm2-360m-ax650/llama_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2-360m-ax650/llama_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`smollm2-360m-ax650/llama_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2-360m-ax650/llama_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/post_config.json) | 运行配置 |
| [`run_smollm2_360m_ax630c.sh`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/run_smollm2_360m_ax630c.sh) | 启动或构建脚本 |
| [`run_smollm2_360m_ax650.sh`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/run_smollm2_360m_ax650.sh) | 启动或构建脚本 |
| [`run_smollm2_360m_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/run_smollm2_360m_axcl_x86.sh) | 启动或构建脚本 |
| [`smollm2_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2_tokenizer/tokenizer_config.json) | 运行配置 |
| [`smollm2_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2_tokenizer_uid.py) | 旧版分词服务入口 |

仓库提交：`17a64761eff9cee7817f368f7a398e91635a055b`。仓库中的 66 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/tree/17a64761eff9cee7817f368f7a398e91635a055b)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/tree/17a64761eff9cee7817f368f7a398e91635a055b)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/README.md)。
- [主要程序入口：smollm2_tokenizer.py](https://huggingface.co/AXERA-TECH/SmolLM2-360M-Instruct/blob/17a64761eff9cee7817f368f7a398e91635a055b/smollm2_tokenizer.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-llm-internvl)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/internvl2)。

返回[完整模型目录](../catalog.mdx)。
