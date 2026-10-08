---
title: "Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp 部署指南"
sidebar_label: "Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp"
description: "Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp 部署指南

Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp 用于文本生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp` 的固定版本。下面下载本页选用的 77 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-gptq-int4-tmp/af30672a4213
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp \
  --include "Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/*" "Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2k-prefill-1500/*" "Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2k-prefill-1k/*" "README.md" "model.embed_tokens.weight.bfloat16.bin" \
  --revision af30672a4213bc1bb689781928f3d15760da3efa \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套运行程序

本仓库提供三组权重和共用 embedding，不包含完整运行程序。以下步骤使用官方 [Qwen2.5-0.5B-Instruct-GPTQ-Int4 固定版本](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4/tree/10db075dd5e99796adcec79452fcae0ec03ddded)的程序与分词器。两个仓库分别保存，沿用前文下载模型时的 `MODEL_DIR`。

在连接算力卡的 RK3576 主机执行：

```bash
RUNTIME_DIR=~/edgeaccel/runtime/qwen25-05b/10db075dd5e9
mkdir -p "$RUNTIME_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4 \
  --include 'main_axcl_aarch64' 'post_config.json' 'qwen2.5_tokenizer_uid.py' \
    'qwen2.5_tokenizer/*' 'run_qwen2.5_0.5b_gptq_int4_axcl_aarch64.sh' 'README.md' \
  --revision 10db075dd5e99796adcec79452fcae0ec03ddded \
  --local-dir "$RUNTIME_DIR"
cd "$RUNTIME_DIR"
printf '%s  %s\n' \
  1f9f1a1ca329b47f70840e8b6d104ce8248a82326aa2402bccb31144590a8fb2 \
  main_axcl_aarch64 | sha256sum -c -
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

程序校验须显示 `OK`，动态库检查不得出现 `not found`。三组模型合计约 1.56GB，运行程序及分词文件约 13.2MB；本例放在主机内部存储。

## 启动分词服务

```bash
python3 -m venv ~/edgeaccel/qwen05-tmp-env
source ~/edgeaccel/qwen05-tmp-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4' 'jinja2==3.1.6'
cd "$RUNTIME_DIR"
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
export TOKENIZERS_PARALLELISM=false
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

保持这个终端运行。分词服务在主机执行，模型推理由 AXCL 程序在算力卡上完成。

## 选择规格并运行问答

另开主机终端，设置模型和运行程序目录。`VARIANT` 对应仓库中的目录后缀，可选 `context-2500-prefill-2k`、`context-2k-prefill-1500` 或 `context-2k-prefill-1k`。下面默认使用第一组：

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-0-5b-instruct-gptq-int4-tmp/af30672a4213
RUNTIME_DIR=~/edgeaccel/runtime/qwen25-05b/10db075dd5e9
VARIANT=context-2500-prefill-2k
WEIGHTS="$MODEL_DIR/Qwen2.5-0.5B-Instruct-GPTQ-Int4-$VARIANT"
PROMPT='What is 2 + 3? Reply with only the number.'
cd "$RUNTIME_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
set -o pipefail
printf '%s\n' "$PROMPT" q | ./main_axcl_aarch64 \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 24 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$MODEL_DIR/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 896 \
  --use_mmap_load_embed 0 --live_print 0 --devices 0
```

程序应完成 24 层和 post 模型初始化，输出回答并在收到 `q` 后退出。修改 `VARIANT` 后可用同一命令运行其余两组；修改 `PROMPT` 后可复现中文问答与 JSON 示例：

```text
请用一句中文说明 PCIe 的用途。
Return only a JSON object with apple equal to 3 and pear equal to 2.
```

每次运行结束后用 `axcl-smi` 确认推理进程已退出。短输入结果不能代表长上下文和连续对话已经验证，三组的具体输出分别见下方效果展示。


## 查看部署效果

### context-2k-prefill-1k

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

数值正确，并按要求只输出数字。

程序内部首 token 耗时：377.57 ms；含模型加载的完整进程：14.788 s。内部计时不等同于客户端端到端首字延迟。

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

未遵循“一句中文”的要求；关于路由器、打印机、扫描仪及服务器直接连接的说明不准确，不能作为接口用途的技术说明。

程序内部首 token 耗时：316.18 ms；含模型加载的完整进程：44.878 s。内部计时不等同于客户端端到端首字延迟。

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

输出未包含要求的 apple 和 pear 字段，内容不正确；额外的 Markdown 代码围栏也不符合“只输出 JSON”的要求。

程序内部首 token 耗时：299.00 ms；含模型加载的完整进程：15.741 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 本结果仅确认加载、推理和解码完成，不代表回答质量通过。中文事实与指令遵循、JSON字段和格式仍需复核。
- 仅实测16GB卡上的三条独立短输入；实际8GB容量、长上下文、连续对话、并发和持续运行需单独验证。目录名称表示上游规格，本次未测最大可用上下文。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### context-2k-prefill-1500

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

数值正确，并按要求只输出数字。

程序内部首 token 耗时：296.74 ms；含模型加载的完整进程：18.161 s。内部计时不等同于客户端端到端首字延迟。

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

未遵循“一句中文”的要求；关于路由器、打印机、扫描仪及服务器直接连接的说明不准确，不能作为接口用途的技术说明。

程序内部首 token 耗时：296.82 ms；含模型加载的完整进程：49.095 s。内部计时不等同于客户端端到端首字延迟。

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

输出未包含要求的 apple 和 pear 字段，内容不正确；额外的 Markdown 代码围栏也不符合“只输出 JSON”的要求。

程序内部首 token 耗时：305.64 ms；含模型加载的完整进程：18.999 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 本结果仅确认加载、推理和解码完成，不代表回答质量通过。中文事实与指令遵循、JSON字段和格式仍需复核。
- 仅实测16GB卡上的三条独立短输入；实际8GB容量、长上下文、连续对话、并发和持续运行需单独验证。目录名称表示上游规格，本次未测最大可用上下文。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

### context-2500-prefill-2k

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

数值正确，并按要求只输出数字。

程序内部首 token 耗时：289.59 ms；含模型加载的完整进程：22.424 s。内部计时不等同于客户端端到端首字延迟。

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

未遵循“一句中文”的要求；关于路由器、打印机、扫描仪及服务器直接连接的说明不准确，不能作为接口用途的技术说明。

程序内部首 token 耗时：278.26 ms；含模型加载的完整进程：53.885 s。内部计时不等同于客户端端到端首字延迟。

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

输出未包含要求的 apple 和 pear 字段，内容不正确；额外的 Markdown 代码围栏也不符合“只输出 JSON”的要求。

程序内部首 token 耗时：307.03 ms；含模型加载的完整进程：22.578 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 本结果仅确认加载、推理和解码完成，不代表回答质量通过。中文事实与指令遵循、JSON字段和格式仍需复核。
- 仅实测16GB卡上的三条独立短输入；实际8GB容量、长上下文、连续对话、并发和持续运行需单独验证。目录名称表示上游规格，本次未测最大可用上下文。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

**context-2k-prefill-1k**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`af30672a4213bc1bb689781928f3d15760da3efa`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行程序 | 官方Qwen2.5-0.5B-Instruct-GPTQ-Int4固定版本的ARM64 UID程序与分词器；tmp仓库三组权重分别运行 |
| 分词依赖 | Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 / Jinja2 3.1.6 |
| 加载与采样 | 主机内部ext4存储；use_mmap_load_embed=0，live_print=0，devices=0，top_k=1；关闭temperature、repetition_penalty和top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例1完整进程 | 14.788 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 示例2完整进程 | 44.878 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 示例3完整进程 | 15.741 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |

</details>

**context-2k-prefill-1500**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`af30672a4213bc1bb689781928f3d15760da3efa`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行程序 | 官方Qwen2.5-0.5B-Instruct-GPTQ-Int4固定版本的ARM64 UID程序与分词器；tmp仓库三组权重分别运行 |
| 分词依赖 | Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 / Jinja2 3.1.6 |
| 加载与采样 | 主机内部ext4存储；use_mmap_load_embed=0，live_print=0，devices=0，top_k=1；关闭temperature、repetition_penalty和top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例1完整进程 | 18.161 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 示例2完整进程 | 49.095 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 示例3完整进程 | 18.999 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |

</details>

**context-2500-prefill-2k**

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`af30672a4213bc1bb689781928f3d15760da3efa`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576 ARM64，约4GB主机内存；6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件V3.16.0，CMM总容量15232MiB |
| 运行程序 | 官方Qwen2.5-0.5B-Instruct-GPTQ-Int4固定版本的ARM64 UID程序与分词器；tmp仓库三组权重分别运行 |
| 分词依赖 | Python3.12 / Transformers4.51.3 / Tokenizers0.21.4 / Jinja2 3.1.6 |
| 加载与采样 | 主机内部ext4存储；use_mmap_load_embed=0，live_print=0，devices=0，top_k=1；关闭temperature、repetition_penalty和top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例1完整进程 | 22.424 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 示例2完整进程 | 53.885 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |
| 示例3完整进程 | 22.578 s | 包含模型加载、一次问答和退出，不是单次生成耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/blob/af30672a4213bc1bb689781928f3d15760da3efa/Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/blob/af30672a4213bc1bb689781928f3d15760da3efa/Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/blob/af30672a4213bc1bb689781928f3d15760da3efa/Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/blob/af30672a4213bc1bb689781928f3d15760da3efa/Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/blob/af30672a4213bc1bb689781928f3d15760da3efa/Qwen2.5-0.5B-Instruct-GPTQ-Int4-context-2500-prefill-2k/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`af30672a4213bc1bb689781928f3d15760da3efa`。仓库中的 75 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/tree/af30672a4213bc1bb689781928f3d15760da3efa)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 这是带 tmp 标识的版本，固定本页提交使用，并与非 tmp 仓库分别保存。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/tree/af30672a4213bc1bb689781928f3d15760da3efa)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen2.5-0.5B-Instruct-GPTQ-Int4-tmp/blob/af30672a4213bc1bb689781928f3d15760da3efa/README.md)。

返回[完整模型目录](../catalog.mdx)。
