---
title: "FastVLM-0.5B 部署指南"
sidebar_label: "FastVLM-0.5B"
description: "FastVLM-0.5B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# FastVLM-0.5B 部署指南

FastVLM-0.5B 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/FastVLM-0.5B` 的固定版本。下面下载本页选用的 33 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/fastvlm-0-5b/8182c1f3eda4
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/FastVLM-0.5B \
  "FastVLM_tokenizer.txt" \
  "README.md" \
  "embeds/model.embed_tokens.weight.bfloat16.bin" \
  "fastvlm_C128_CTX1024_P640_ax650/image_encoder_512x512_0.5b_ax650.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l0_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l10_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l11_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l12_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l13_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l14_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l15_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l16_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l17_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l18_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l19_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l1_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l20_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l21_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l22_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l23_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l2_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l3_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l4_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l5_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l6_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l7_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l8_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l9_together.axmodel" \
  "fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_post.axmodel" \
  "images/image_1.jpg" \
  "images/ssd_horse.jpg" \
  "post_config.json" \
  "run_axcl_x86.sh" \
  --revision 8182c1f3eda4239c7b663cfd04605a02967784ce \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 ARM64 运行程序

按 [编译 AXCL 大模型运行时](../llm-runtime.md) 编译固定提交 `8501c22b940f8c5804cb35044c5ffc136918b8f1`，确认 `axllm version` 显示 `backend: AXCL` 和 `Linux aarch64`。本模型仓库的 `main_axcl_x86` 用于 x86 主机，RK3576 使用这里编译的 ARM64 程序。

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
"$AXLLM" version
```

## 生成本模型的配置

下载 [FastVLM-0.5B 配置脚本](../../../static/examples/fastvlm05_prepare.py)，保存为 `~/edgeaccel/fastvlm05_prepare.py`。保持上文的 `MODEL_DIR` 变量，选择一个尚不存在的运行目录：

```bash
RUNTIME_DIR=~/edgeaccel/runtime/fastvlm05-8182c1f3
python3 ~/edgeaccel/fastvlm05_prepare.py \
  --model-dir "$MODEL_DIR" \
  --output "$RUNTIME_DIR"
```

脚本使用同一提交的 24 个语言模型分片、输出层、512×512 图像编码器、896 维词向量和 FastVLM 分词表。运行目录通过符号链接引用下载文件，不再复制权重；保留 `MODEL_DIR` 才能运行。生成的配置使用设备 0、mmap 加载和 `top_k=1`。

## 启动图像问答

在当前终端启动服务：

```bash
AXLLM_DEVICES=0 "$AXLLM" serve "$RUNTIME_DIR" --port 8512
```

在 RK3576 的另一个终端确认服务就绪：

```bash
curl --noproxy '*' -fsS http://127.0.0.1:8512/health
curl --noproxy '*' -fsS http://127.0.0.1:8512/v1/models
```

模型列表应包含 `AXERA-TECH/FastVLM-0.5B`。在这个新终端重新设置模型目录，然后提交官方熊猫图：

```bash
export MODEL_DIR=~/edgeaccel/models/fastvlm-0-5b/8182c1f3eda4
python3 - <<'PY'
import base64, json, os, urllib.request
from pathlib import Path

image = Path(os.environ['MODEL_DIR']) / 'images/image_1.jpg'
question = 'Describe the image in one sentence.'
uri = 'data:image/jpeg;base64,' + base64.b64encode(image.read_bytes()).decode()
payload = {
    'model': 'AXERA-TECH/FastVLM-0.5B',
    'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': question},
        {'type': 'image_url', 'image_url': {'url': uri}},
    ]}],
    'max_tokens': 96, 'temperature': 0, 'stream': True,
}
request = urllib.request.Request(
    'http://127.0.0.1:8512/v1/chat/completions',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'},
)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(request, timeout=150) as response:
    for raw in response:
        line = raw.decode().strip()
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            break
        event = json.loads(data)
        if 'error' in event:
            raise RuntimeError(event['error'])
        for choice in event.get('choices', []):
            print(choice.get('delta', {}).get('content') or '', end='', flush=True)
print()
PY
```

模型应返回描述熊猫的文字。将图片改为 `images/ssd_horse.jpg`、问题改为 `Name the two animals in the foreground.`，可继续检查马和狗的识别。中文可使用 `请用一句中文描述图片的主要内容。`，但需人工核对细节，实际错误示例见下方。

本包上下文上限为 1024 token、预填充上限为 640 token；先使用单张图片和简短问题。每次请求独立发送图片和问题，不将前一次回复自动加入新请求。退出时在服务终端按 `Ctrl+C`，再用 `axcl-smi` 确认推理进程已释放。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两张官方图片完成六次图像问答，能识别熊猫、马和狗，重复提问输出一致；中文细节和人数计数存在错误，下方保留全部实际回复。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/fastvlm-0-5b-20260928/image_1.jpg)](../../../static/validation/effects/fastvlm-0-5b-20260928/image_1.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/fastvlm-0-5b-20260928/ssd_horse.jpg)](../../../static/validation/effects/fastvlm-0-5b-20260928/ssd_horse.jpg)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
图片：image_1.jpg
问题：Describe the image in one sentence.
```

**实际回复**

```text
A panda bear is sitting in a forest, surrounded by bamboo and trees.
```

正确识别熊猫和周围竹木；画面不足以确认拍摄环境属于野外森林，该表述不作为地点判断。

**示例 2：输入**

```text
图片：image_1.jpg
问题：请用一句中文描述图片的主要内容。
```

**实际回复**

```text
图片中的熊猫是黑白相间的，它正坐在一棵树上，周围是绿色的植物和岩石。
```

正确识别黑白熊猫和绿色植物，但“坐在一棵树上”与图片不符，中文细节存在幻觉。

**示例 3：输入**

```text
图片：ssd_horse.jpg
问题：Name the two animals in the foreground.
```

**实际回复**

```text
The two animals in the foreground are a brown horse and a brown dog.
```

前景两只动物为棕色马和棕色狗，回答与画面一致。

**示例 4：输入**

```text
图片：ssd_horse.jpg
问题：How many people are clearly visible in the image?
```

**实际回复**

```text
There are three people clearly visible in the image.
```

回答为 3 人；图中清晰可辨的是骑马者和右侧红衣人物，未核对到第三名清晰人物，计数未通过。

**示例 5：输入**

```text
图片：image_1.jpg
问题：Describe the image in one sentence.
```

**实际回复**

```text
A panda bear is sitting in a forest, surrounded by bamboo and trees.
```

切换至骑马图后，再提交相同熊猫图与英文问题，文字与第一次逐字一致。

**示例 6：输入**

```text
图片：ssd_horse.jpg
问题：请用一句中文描述图片的主要内容。
```

**实际回复**

```text
这幅图片描绘了一个男人骑在马上的场景，旁边有一只狗和一辆卡车。
```

识别出骑马场景、狗和左侧车辆；仅核对这些可见对象，不据图片判断人物身份。

**使用时注意：**

- 仅测试两张图片、五种图文问题和一次重复；未测试视频、OCR、复杂计数、多轮长上下文或并发。
- 中文熊猫描述包含错误位置关系，人数回答未通过人工核对；基本运行通过不代表所有回答正确。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`8182c1f3eda4239c7b663cfd04605a02967784ce`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行时 | AX-LLM 8501c22b940f / AXCL / Linux aarch64 / GCC 13.3 |
| 采样 | top_k=1，temperature=0，每题最多 96 token；单张图片、独立请求 |
| 图像与权重 | 512×512 图像编码器，24 个语言分片，896 维词向量，AX650 W8A16 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 首次加载至服务就绪 | 38.106 s | 包含分词表、语言分片和图像编码器加载，独立于下列请求。 |
| 请求 1 首段文字 / 完整回复 | 0.532 s / 2.563 s | 同主机 HTTP 客户端墙钟，包含图片传输与处理、预填充和生成；首段为首个非空 content 事件，不是独立 NPU 时间。 |
| 请求 2 首段文字 / 完整回复 | 0.783 s / 3.571 s | 同主机 HTTP 客户端墙钟，包含图片传输与处理、预填充和生成；首段为首个非空 content 事件，不是独立 NPU 时间。 |
| 请求 3 首段文字 / 完整回复 | 0.601 s / 2.304 s | 同主机 HTTP 客户端墙钟，包含图片传输与处理、预填充和生成；首段为首个非空 content 事件，不是独立 NPU 时间。 |
| 请求 4 首段文字 / 完整回复 | 0.605 s / 2.003 s | 同主机 HTTP 客户端墙钟，包含图片传输与处理、预填充和生成；首段为首个非空 content 事件，不是独立 NPU 时间。 |
| 请求 5 首段文字 / 完整回复 | 0.653 s / 2.937 s | 同主机 HTTP 客户端墙钟，包含图片传输与处理、预填充和生成；首段为首个非空 content 事件，不是独立 NPU 时间。 |
| 请求 6 首段文字 / 完整回复 | 0.599 s / 3.338 s | 同主机 HTTP 客户端墙钟，包含图片传输与处理、预填充和生成；首段为首个非空 content 事件，不是独立 NPU 时间。 |

适用范围：

- 仅测试两张图片、五种图文问题和一次重复；未测试视频、OCR、复杂计数、多轮长上下文或并发。
- 中文熊猫描述包含错误位置关系，人数回答未通过人工核对；基本运行通过不代表所有回答正确。
- 该测试未导出逐层原始张量，因此不作全张量有限性或逐层数值精度结论。
- 仅在 16GB 卡验证，8GB 容量回归待完成。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/run_axcl_x86.sh) | 启动或构建脚本 |
| [`infer_axmodel_620e.py`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/infer_axmodel_620e.py) | Python 程序 / 前后处理 |
| [`infer_axmodel_650.py`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/infer_axmodel_650.py) | Python 程序 / 前后处理 |
| [`fastvlm_C128_CTX1024_P640_ax650/image_encoder_512x512_0.5b_ax650.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_C128_CTX1024_P640_ax650/image_encoder_512x512_0.5b_ax650.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_C128_CTX1024_P640_ax650/llava_qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/config.json) | 运行配置 |
| [`fastvlm_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_tokenizer/config.json) | 运行配置 |
| [`fastvlm_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_tokenizer/generation_config.json) | 运行配置 |
| [`fastvlm_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/fastvlm_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/post_config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/requirements.txt) | Python 依赖清单 |

仓库提交：`8182c1f3eda4239c7b663cfd04605a02967784ce`。仓库中的 52 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/tree/8182c1f3eda4239c7b663cfd04605a02967784ce)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/tree/8182c1f3eda4239c7b663cfd04605a02967784ce)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/README.md)。
- [主要程序入口：infer_axmodel_620e.py](https://huggingface.co/AXERA-TECH/FastVLM-0.5B/blob/8182c1f3eda4239c7b663cfd04605a02967784ce/infer_axmodel_620e.py)。

返回[完整模型目录](../catalog.mdx)。
