---
title: "QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408 部署指南"
sidebar_label: "QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408"
description: "QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408 部署指南

QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408` 的固定版本。下面下载本页选用的 31 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408/cf9b102777b5
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408 \
  --include "*.axmodel" "config.json" "post_config.json" "model.embed_tokens.weight.bfloat16.bin" "qwen3_5_tokenizer.txt" "qwen3_tokenizer.txt" \
  --revision cf9b102777b59d552bd9820afeb996224f36732c \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备问答运行程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0，运行本页固定版本的 QwenPaw 文本与图片问答。配套程序为 Linux ARM64 版本。

下载[配套运行包](/examples/qwenpaw-20261001.tar.gz)，保存为主机上的 `~/edgeaccel/qwenpaw-20261001.tar.gz`。包内包含原生程序、固定源码与适配文件、三张样图、请求示例和模型文件校验工具。保留前文下载模型后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwenpaw-20261001.tar.gz
sudo apt-get install -y libopencv-dev
chmod +x qwenpaw/bin/axllm
ldd qwenpaw/bin/axllm
python3 qwenpaw/verify_models.py --model-dir "$MODEL_DIR"
```

`ldd` 应找到所有动态库，校验工具应输出 `Verified 31 model files`。模型及配套文件约 3.75 GB，存储空间不足时将 `MODEL_DIR` 指向已挂载的存储卡。

程序基于官方 AX-LLM 提交 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`，包含 AXCL 设备与 K/V 缓冲区适配。保留仓库原始的 `config.json`、`post_config.json` 和 `qwen3_5_tokenizer.txt`；不要用其他 Qwen 模型的配置替换。

## 启动问答服务

```bash
cd ~/edgeaccel
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ./qwenpaw/bin/axllm serve "$MODEL_DIR" --port 3612
```

保持该终端运行，在同一 RK3576 的另一个终端检查：

```bash
curl --noproxy '*' --fail http://127.0.0.1:3612/health
curl --noproxy '*' --fail http://127.0.0.1:3612/v1/models
```

仓库配置的接口模型名为 `AXERA-TECH/Qwen3.5-2B`，请求中的 `model` 使用这个名称；实际加载的仍是前文下载的 QwenPaw 固定权重。出现服务就绪信息后继续。

## 发送文本和图片

在 RK3576 的第二个终端执行：

```bash
cd ~/edgeaccel
python3 qwenpaw/chat.py \
  --text '用一句中文解释 PCIe 的作用。' \
  --output results/qwenpaw/text.json

python3 qwenpaw/chat.py \
  --image "$HOME/edgeaccel/qwenpaw/images/cat.jpg" \
  --text 'Name the main animal in this image and briefly describe its appearance in one sentence.' \
  --output results/qwenpaw/image.json
```

终端显示最终回答，JSON 保存完整请求、原始响应和耗时。若响应带有 `<think>…</think>`，终端只显示结束标记后的内容，原文仍完整保存在 JSON 中；思考片段未闭合时，示例报告回答不完整。示例通过 `/v1/chat/completions` 发送请求，使用 `temperature=0`、`top_p=1`、`max_tokens=512` 和非流式输出。图片路径由服务进程读取，应使用该主机上存在的文件。

回答为空、出现报错文字或内容截断时，检查服务终端输出，不能仅凭 HTTP 200 判断完成。`max_tokens` 是生成上限；该版本接口的 `finish_reason` 不能单独证明自然结束。长回答需要另行验证生成长度和输出完整性。

## 发送两轮对话

```bash
cd ~/edgeaccel
python3 qwenpaw/chat.py \
  --text 'Remember this code: BLUE-47. Reply with only OK.' \
  --output results/qwenpaw/turn1.json
python3 qwenpaw/chat.py \
  --history results/qwenpaw/turn1.json \
  --text 'What code did I ask you to remember? Reply with only the code.' \
  --output results/qwenpaw/turn2.json
```

第二条命令将第一轮的用户消息和模型回答加入 `messages`，再发送新问题。历史保存在客户端结果文件中。替换图片或开始无关任务时，省略 `--history` 创建新的对话。

使用结束后，在服务终端按 `Ctrl+C`，再执行 `axcl-smi` 确认资源已释放。

<details>
<summary>重新编译运行程序</summary>

若系统动态库与配套程序不匹配，使用包内固定源码重新编译：

```bash
sudo apt-get install -y build-essential cmake libopencv-dev
cd ~/edgeaccel/qwenpaw
mkdir source
tar -xzf official-source.tar.gz -C source
cp -r adapted/src/. source/src/
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON
cmake --build build --target axllm -j1
```

后续命令改用 `build/axllm`。固定源码包已包含对应版本子模块。

</details>


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡运行 QwenPaw 文本与图片问答，实际回答和两轮对话见本页。

**文本、图片与两轮对话**

九次请求均得到完整回答。以下展示原始响应中思考结束标记后的最终回答；完整请求与原始响应保存在结果 JSON 中，未改写模型输出。三张图片均识别出主要动物；格式遵循和描述细节仍有偏差，见各条说明。

<div className="model-effect-gallery">

<figure>

[![输入图片：鸟](../../../static/validation/effects/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408-20261001/bird.jpg)](../../../static/validation/effects/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408-20261001/bird.jpg)

<figcaption>输入图片：鸟</figcaption>
</figure>

<figure>

[![输入图片：猫](../../../static/validation/effects/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408-20261001/cat.jpg)](../../../static/validation/effects/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408-20261001/cat.jpg)

<figcaption>输入图片：猫</figcaption>
</figure>

<figure>

[![输入图片：狗](../../../static/validation/effects/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408-20261001/dog-chai.jpeg)](../../../static/validation/effects/qwenpaw-flash-2b-gptq-int4-ax650-c256-p14336-ctx17408-20261001/dog-chai.jpeg)

<figcaption>输入图片：狗</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Calculate 2 + 3. Answer with only the number.
```

**实际回复**

```text
5
```

最终答案为 5；原始响应带有思考片段，不满足“仅数字”的原始文本格式。

**示例 2：输入**

```text
用一句中文解释 PCIe 的作用。
```

**实际回复**

```text
PCI Express（PCIe）是一种高速串行扩展接口标准，用于连接服务器、工作站和服务器机箱中的设备，通过提供高带宽和低延迟实现高效的数据传输，从而支持多设备并行连接和大规模数据处理。
```

完整回答提到高速串行接口、高带宽和低延迟；表述重复，应用范围举例较窄，不能作为术语定义或质量基准。

**示例 3：输入**

```text
Return only a JSON object with keys apple and pear. There are 3 apples and 2 pears. Do not use Markdown.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

原始响应可直接解析为 JSON，apple=3、pear=2，没有 Markdown 包装。

**示例 4：输入**

```text
Name the main animal in this image and briefly describe its appearance in one sentence.（图片：images/bird.jpg）
```

**实际回复**

```text
The main animal is a **macaw** (specifically a Scarlet Macaw). It is depicted in mid-flight with its wings fully spread, showcasing a vibrant blue tail and wings, a bright red chest and belly, and green feathers on its wings.
```

识别出金刚鹦鹉、展翅飞行及主要颜色。图中尾羽也有明显红色，回答描述不全面；具体物种未做标注核对。输出两句，未满足一句话要求。

**示例 5：输入**

```text
Name the main animal in this image and briefly describe its appearance in one sentence.（图片：images/cat.jpg）
```

**实际回复**

```text
The main animal is a young orange and white kitten with large, bright eyes, sitting upright on a rock.
```

识别出橘白小猫、大眼睛及坐在石头上的姿态，最终回答为一句。

**示例 6：输入**

```text
Name the main animal in this image and briefly describe its appearance in one sentence.（图片：images/dog-chai.jpeg）
```

**实际回复**

```text
The main animal in this image is a **dog**, specifically a Shiba Inu. It is a small, medium-sized dog with reddish-brown fur, a white muzzle and chest, and pointed ears, lying down and looking directly at the camera.
```

识别出狗、棕白毛色、尖耳和趴卧姿态。输出两句，且 small, medium-sized 措辞不一致；品种和体型未作为精确分类指标。

**示例 7：输入**

```text
Remember this code: BLUE-47. Reply with only OK.
```

**实际回复**

```text
OK
```

最终回答 OK；原始响应含思考片段，不满足原始文本仅 OK 的格式要求。

**示例 8：输入**

```text
What code did I ask you to remember? Reply with only the code.
```

**实际回复**

```text
BLUE-47
```

最终回答 BLUE-47，与第一轮输入一致；完整原始响应仍带思考片段。

**示例 9：输入**

```text
Calculate 2 + 3. Answer with only the number.
```

**实际回复**

```text
5
```

与首次算术的完整原始响应一致，最终答案为 5。

| 输入 | 首 token / s | 完整请求 / s | 输出层调用数 |
| --- | --- | --- | --- |
| 算术 | 0.716 | 11.209 | 48 |
| 中文解释 | 0.688 | 48.561 | 242 |
| 严格 JSON | 0.645 | 7.914 | 13 |
| 图片：鸟 | 0.669 | 52.591 | 261 |
| 图片：猫 | 0.665 | 59.327 | 313 |
| 图片：狗 | 0.691 | 49.570 | 253 |
| 记忆：第一轮 | 0.708 | 11.002 | 35 |
| 记忆：第二轮 | 0.696 | 13.541 | 72 |
| 重复算术 | 0.645 | 13.558 | 48 |

**使用时注意：**

- 本次为固定 QwenPaw 权重在 16GB 卡上的基本运行；真实 8GB、长上下文、工具调用和长期运行尚未验证。
- 原始文本多数包含思考片段；算术和记忆任务未严格遵循“仅答案”，鸟和狗未遵循“一句话”，鸟的颜色描述不全面、狗的体型措辞不一致。基本运行通过不代表格式遵循或视觉细节质量通过。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`cf9b102777b59d552bd9820afeb996224f36732c`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | AX-LLM a51df2d + AXCL 设备与 K/V 缓冲区适配 / 原生 HTTP 问答接口 / AXCL C API |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际输入 | 9 次请求 | 算术、中文、JSON、三张图片、两轮记忆与重复算术。 |
| 算力卡执行 | 26 个 AXModel | 视觉编码器、24 个文本层及输出层，共 32128 次原生执行。 |
| 运行参数 | temperature=0 / max_tokens=512 | 单输入，非流式 HTTP 接口；首 token 来自运行时日志，完整请求耗时由客户端计时。 |

适用范围：

- 接口返回的结束标记和运行时 hit eos 日志不能单独证明自然结束；保留原始回答及输出层调用次数，不将其写成精确生成 token 数。
- 图像描述仅覆盖三张样图，多轮仅覆盖一组两轮记忆；不能代表完整质量评估。
- 已检查原生调用和最终文本，未捕获全部中间张量，也未与浮点参考模型做精度比较。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/config.json) | 运行配置 |
| [`qwen3_5_text_post.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_5_tokenizer.txt`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`qwen3_5_vision.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/post_config.json) | 运行配置 |
| [`qwen3_5_text_p256_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_text_p256_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p256_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_text_p256_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p256_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_text_p256_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p256_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_text_p256_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p256_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/blob/cf9b102777b59d552bd9820afeb996224f36732c/qwen3_5_text_p256_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`cf9b102777b59d552bd9820afeb996224f36732c`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/tree/cf9b102777b59d552bd9820afeb996224f36732c)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。
- 此提交没有 README.md。已核对文件清单；运行参数和验收数据不能仅根据仓库名称补写。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/QwenPaw-Flash-2B-GPTQ-Int4-AX650-C256-P14336-CTX17408/tree/cf9b102777b59d552bd9820afeb996224f36732c)。

返回[完整模型目录](../catalog.mdx)。
