---
title: "MiniCPM4-0.5B 部署指南"
sidebar_label: "MiniCPM4-0.5B"
description: "MiniCPM4-0.5B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# MiniCPM4-0.5B 部署指南

MiniCPM4-0.5B 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，固定样例已核对。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/MiniCPM4-0.5B` 的固定版本。下面下载本页选用的 39 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/minicpm4-0-5b/40672934396f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/MiniCPM4-0.5B \
  "README.md" \
  "config.json" \
  "main_axcl_aarch64" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l0_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l10_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l11_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l12_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l13_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l14_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l15_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l16_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l17_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l18_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l19_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l1_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l20_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l21_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l22_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l23_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l2_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l3_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l4_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l5_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l6_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l7_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l8_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l9_together.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_post.axmodel" \
  "minicpm4-0.5b-int8-ctx-ax650/model.embed_tokens.weight.bfloat16.bin" \
  "minicpm4_tokenizer/added_tokens.json" \
  "minicpm4_tokenizer/config.json" \
  "minicpm4_tokenizer/generation_config.json" \
  "minicpm4_tokenizer/special_tokens_map.json" \
  "minicpm4_tokenizer/tokenizer.json" \
  "minicpm4_tokenizer/tokenizer.model" \
  "minicpm4_tokenizer/tokenizer_config.json" \
  "minicpm4_tokenizer_uid.py" \
  "post_config.json" \
  "run_minicpm4_0.5b_int8_ctx_axcl_aarch64.sh" \
  --revision 40672934396f0171cce4aa72487dc1b934c0c9e1 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词服务

本例使用官方 `main_axcl_aarch64` 通过 AXCL 在 M.2 算力卡上推理，Python 服务负责分词。以下版本已在 RK3576 主机上测试：

```bash
python3 -m venv ~/edgeaccel/legacy-text-env
source ~/edgeaccel/legacy-text-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

确认依赖检查没有 `not found`，再启动服务。

## 运行文本生成

在模型目录设置与本页效果一致的贪心采样，并保留原配置：

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
python minicpm4_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持服务终端运行。另开终端，进入同一模型目录：

```bash
MODEL_DIR=~/edgeaccel/models/minicpm4-0-5b/40672934396f
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
./main_axcl_aarch64 \
  --system_prompt 'You are MiniCPM4, created by ModelBest. You are a helpful assistant.' \
  --template_filename_axmodel 'minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l%d_together.axmodel' \
  --axmodel_num 24 \
  --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_post.axmodel \
  --filename_tokens_embed minicpm4-0.5b-int8-ctx-ax650/model.embed_tokens.weight.bfloat16.bin \
  --tokens_embed_num 73448 --tokens_embed_size 1024 \
  --use_mmap_load_embed 1 --live_print 0 --devices 0
```

在交互提示下输入 `What is 2 + 3? Reply with only the number.`，等待完整回复。`--live_print 0` 表示生成完成后显示回复。本次该问题返回 `5`。

输入 `q` 退出程序；测试下一条问题时重新启动，避免沿用对话历史。运行结束后，在分词服务终端按 `Ctrl+C` 关闭服务。下方展示三条独立输入的实际结果和进程耗时。


## 查看部署效果

**固定样例已核对** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

官方 AXCL ARM64 程序完成三组单轮输入：算术返回 5，中文说明符合 PCIe 的基本用途，JSON 字段、数值和格式均符合请求。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

精确返回 5，没有附加解释，数值与格式均符合要求。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe（Peripheral Component Interconnect Express）是用于连接计算机外围设备的高速串行总线标准。
```

用一句中文说明了连接计算机外围设备的用途，以及高速串行互连的基本性质。

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

原始回复可直接解析为 JSON，且对象精确等于 {"apple":3,"pear":2}，没有附加说明。

**使用时注意：**

- 这里只核对了展示的三条固定输入，不能据此推断通用知识准确率、复杂推理能力或其他问题的格式遵循率。
- 仅在 16GB 算力卡上测试三条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`40672934396f0171cce4aa72487dc1b934c0c9e1`。

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
| 示例 1 进程耗时 | 16.756 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 19.655 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 18.662 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_minicpm4_0.5b_int8_ctx_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/run_minicpm4_0.5b_int8_ctx_axcl_aarch64.sh) | 启动或构建脚本 |
| [`minicpm4_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4_tokenizer_uid.py) | 旧版分词服务入口 |
| [`minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4-0.5b-int8-ctx-ax650/MiniCPMForCausalLM_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/config.json) | 运行配置 |
| [`minicpm4_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4_tokenizer/config.json) | 运行配置 |
| [`minicpm4_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4_tokenizer/generation_config.json) | 运行配置 |
| [`minicpm4_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/post_config.json) | 运行配置 |
| [`run_minicpm4_0.5b_int8_ctx_ax630c.sh`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/run_minicpm4_0.5b_int8_ctx_ax630c.sh) | 启动或构建脚本 |
| [`run_minicpm4_0.5b_int8_ctx_ax650.sh`](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/run_minicpm4_0.5b_int8_ctx_ax650.sh) | 启动或构建脚本 |

仓库提交：`40672934396f0171cce4aa72487dc1b934c0c9e1`。仓库中的 50 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/tree/40672934396f0171cce4aa72487dc1b934c0c9e1)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/tree/40672934396f0171cce4aa72487dc1b934c0c9e1)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/README.md)。
- [主要程序入口：minicpm4_tokenizer_uid.py](https://huggingface.co/AXERA-TECH/MiniCPM4-0.5B/blob/40672934396f0171cce4aa72487dc1b934c0c9e1/minicpm4_tokenizer_uid.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
