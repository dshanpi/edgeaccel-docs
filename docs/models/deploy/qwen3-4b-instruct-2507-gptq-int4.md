---
title: "Qwen3-4B-Instruct-2507-GPTQ-Int4 部署指南"
sidebar_label: "Qwen3-4B-Instruct-2507-GPTQ-Int4"
description: "Qwen3-4B-Instruct-2507-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-4B-Instruct-2507-GPTQ-Int4 部署指南

Qwen3-4B-Instruct-2507-GPTQ-Int4 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 下载固定版本模型

模型文件约 3.74 GiB。首次下载前，确认目标分区至少有 6 GiB 可用空间；板载空间不足时，将 `MODEL_DIR` 改为已挂载的 SSD 或存储卡目录。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-4b-instruct-2507-gptq-int4/ff1d40a1ca77
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4 \
  --revision ff1d40a1ca779b69146e883ef9e7f5b0c7af3213 \
  --local-dir "$MODEL_DIR"
```

保留同一终端中的 `MODEL_DIR`。下载受阻或需要使用代理时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套运行程序

本页使用固定 Int4 权重和配套 ARM64 程序，在 RK3576 + AX8850 16GB 上完成单轮问答。每次启动加载 36 个文本层及输出层，使用原生分词器。输入上限为 3584 个 token，包含系统提示词与对话模板。

下载[本页配套程序与源码](/examples/qwen3-instruct-int4-native-20261004.tar.gz)，将文件命名为 `qwen3-instruct-int4-native-20261004.tar.gz`，复制到 RK3576 的 `~/Downloads`。该包在 Ubuntu 24.04 ARM64 上编译；依赖 AXCL 3.16、OpenCV 4.6、PCRE2 和 ICU 74。

```bash
cd ~/Downloads
echo '54a5fa4364f13102570b9dc4229fd1a66a4691609a4ab8610cb7f5ce7a8c1965  qwen3-instruct-int4-native-20261004.tar.gz' | sha256sum -c -
mkdir -p ~/edgeaccel/runtimes
tar -xzf qwen3-instruct-int4-native-20261004.tar.gz -C ~/edgeaccel/runtimes
RUNTIME_DIR=~/edgeaccel/runtimes/qwen3-instruct-int4-native-20261004/runtime
chmod +x "$RUNTIME_DIR/main_axcl_aarch64"
file "$RUNTIME_DIR/main_axcl_aarch64"
ldd "$RUNTIME_DIR/main_axcl_aarch64"
python3 "$RUNTIME_DIR/../verify_models.py" "$MODEL_DIR"
```

程序包校验应显示 `OK`，模型校验应显示 `Verified 53 model files`，程序架构应为 ARM aarch64，依赖中不能出现 `not found`。其他系统按包内 `README.md` 从源码编译。

## 运行单轮问答

在同一终端执行，`MODEL_DIR` 使用前文下载目录。程序使用设备 0，自动添加与官方入口一致的系统提示词和 `/no_think` 后缀。

```bash
mkdir -p ~/edgeaccel/results/qwen3-instruct-int4
RESULT_DIR=~/edgeaccel/results/qwen3-instruct-int4
printf '%s' 'What is 2 + 3? Reply with only the number.' > "$RESULT_DIR/prompt.txt"
set -o pipefail
bash "$RUNTIME_DIR/run.sh" "$MODEL_DIR" \
  "$RESULT_DIR/prompt.txt" "$RESULT_DIR/answer.json" 2>&1 | tee "$RESULT_DIR/run.log"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["output"]); print("hitEos:",r["hitEos"])' "$RESULT_DIR/answer.json"
```

程序正常退出，日志包含 `termination_reason=eos last_token=151645`，结果文件中的 `hitEos` 为 `True`。下方保留本机实际输入和回复。

替换 `prompt.txt` 可运行中文或 JSON 问答。每次调用独立加载模型，不保留上一轮对话；`answer.json` 同时保存原始回复、token 和耗时。完整进程计时包含模型加载，本轮网络读取的耗时不能直接用作本地磁盘部署的性能指标。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在16GB M.2算力卡完成算术、中文说明和JSON三条独立问答，均正常生成结束标记。下方展示实际输入、原始回复和耗时。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

仅输出数字5，符合本条算术与格式要求。

程序内部首 token 耗时：2075.94 ms；含模型加载的完整进程：117.434 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

```text
请用一句中文说明 PCIe 的用途。
```

**实际回复**

```text
PCIe 用于在计算机中实现高速、可靠的主板与设备间的数据传输。
```

用一句中文说明主板与设备之间的高速数据传输用途。

程序内部首 token 耗时：2068.61 ms；含模型加载的完整进程：121.881 s。内部计时不等同于客户端端到端首字延迟。

**示例 3：输入**

```text
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

返回可直接解析的JSON，apple为3、pear为2，没有附加说明。

程序内部首 token 耗时：2114.27 ms；含模型加载的完整进程：119.685 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 本次三个固定短问题的内容和格式符合要求，尚未进行数据集精度与长时间稳定性测试。
- 本页配套原生运行程序使用固定官方Int4权重；其他入口和采样配置尚未复测。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`ff1d40a1ca779b69146e883ef9e7f5b0c7af3213`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行程序 | 本页配套 ARM64 C++ 程序；原生分词器，单卡、单轮独立问答 |
| 加载与采样 | 只读网络模型文件，embedding 使用 mmap；top_k=1，关闭 temperature、repetition_penalty 和 top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单轮示例1完整进程 | 117.434 s | 包含网络读取、模型加载、一次问答和退出，不是纯推理耗时。 |
| 单轮示例2完整进程 | 121.881 s | 包含网络读取、模型加载、一次问答和退出，不是纯推理耗时。 |
| 单轮示例3完整进程 | 119.685 s | 包含网络读取、模型加载、一次问答和退出，不是纯推理耗时。 |

适用范围：

- 仅实测16GB卡上的三条独立短输入；实际8GB卡、长上下文、多轮及持续运行需单独验证。
- 36个文本层和输出层均有实际AXCL调用记录；未采集中间张量或完成浮点参考对照。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_qwen3_4b_int4_gptq_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/run_qwen3_4b_int4_gptq_axcl_aarch64.sh) | 启动或构建脚本 |
| [`qwen3_tokenizer_uid.py`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/qwen3_tokenizer_uid.py) | 旧版分词服务入口 |
| [`Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/Qwen3-4B-Instruct-2507-GPTQ-Int4-context-4k-prefill-3584/qwen3_p256_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/post_config.json) | 运行配置 |
| [`qwen2.5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/qwen2.5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`qwen3_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/qwen3_tokenizer/config.json) | 运行配置 |
| [`qwen3_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/qwen3_tokenizer/generation_config.json) | 运行配置 |
| [`qwen3_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/qwen3_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_qwen3_4b_int4_gptq_ax650.sh`](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/run_qwen3_4b_int4_gptq_ax650.sh) | 启动或构建脚本 |

仓库提交：`ff1d40a1ca779b69146e883ef9e7f5b0c7af3213`。仓库中的 37 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/tree/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/tree/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/README.md)。
- [主要程序入口：qwen3_tokenizer_uid.py](https://huggingface.co/AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4/blob/ff1d40a1ca779b69146e883ef9e7f5b0c7af3213/qwen3_tokenizer_uid.py)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
