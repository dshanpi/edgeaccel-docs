---
title: "FastVLM-1.5B 部署指南"
sidebar_label: "FastVLM-1.5B"
description: "FastVLM-1.5B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# FastVLM-1.5B 部署指南

FastVLM-1.5B 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/FastVLM-1.5B` 的固定版本。下面下载本页选用的 38 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/fastvlm-1-5b/d1e86badf01e
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/FastVLM-1.5B \
  "FastVLM_tokenizer.txt" \
  "README.md" \
  "fastvlm_ax650_context_1k_prefill_640/image_encoder_1024x1024.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/image_encoder_512x512.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l0_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l10_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l11_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l12_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l13_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l14_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l15_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l16_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l17_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l18_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l19_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l1_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l20_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l21_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l22_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l23_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l24_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l25_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l26_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l27_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l2_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l3_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l4_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l5_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l6_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l7_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l8_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l9_together.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/llava_qwen2_post.axmodel" \
  "fastvlm_ax650_context_1k_prefill_640/model.embed_tokens.weight.bfloat16.bin" \
  "images/image_1.jpg" \
  "images/ssd_horse.jpg" \
  "post_config.json" \
  "run_axcl_aarch64.sh" \
  --revision d1e86badf01ec701bb6b5f06a005622f3074614f \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 ARM64 运行程序

按 [编译 AXCL 大模型运行时](../llm-runtime.md) 编译固定提交 `8501c22b940f8c5804cb35044c5ffc136918b8f1`，确认 `axllm version` 显示 `backend: AXCL` 和 `Linux aarch64`。RK3576 使用这里编译的 ARM64 程序，并由配置脚本接入本仓库的 W8A16 权重。

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
"$AXLLM" version
```

## 生成本模型的配置

下载 [FastVLM-1.5B 配置脚本](../../../static/examples/fastvlm15_prepare.py)，保存为 `~/edgeaccel/fastvlm15_prepare.py`。保持上文的 `MODEL_DIR` 变量，选择一个尚不存在的运行目录：

```bash
RUNTIME_DIR=~/edgeaccel/runtime/fastvlm15-d1e86bad
export PORT=8512
python3 ~/edgeaccel/fastvlm15_prepare.py \
  --model-dir "$MODEL_DIR" \
  --output "$RUNTIME_DIR" \
  --image-size 1024
```

脚本使用同一提交的 28 个语言模型分片、输出层、1024×1024 图像编码器、1536 维词向量和 FastVLM 分词表。运行目录通过符号链接引用下载文件，不再复制权重；保留 `MODEL_DIR` 才能运行。生成的配置使用设备 0、mmap 加载和 `top_k=1`。

1024 规格使用 256 个视觉 token；512 规格使用 64 个。切换到 512 时，先退出正在运行的服务，再创建另一个运行目录：

```bash
RUNTIME_DIR=~/edgeaccel/runtime/fastvlm15-d1e86bad-512
export PORT=8516
python3 ~/edgeaccel/fastvlm15_prepare.py \
  --model-dir "$MODEL_DIR" \
  --output "$RUNTIME_DIR" \
  --image-size 512
```

两种规格共用语言分片，使用各自的图像编码器；不要同时启动两套服务。下方分别保留两种规格的实际回答。

## 启动图像问答

在当前终端启动服务：

```bash
AXLLM_DEVICES=0 "$AXLLM" serve "$RUNTIME_DIR" --port "$PORT"
```

在 RK3576 的另一个终端设置相同端口并确认服务就绪。1024 规格使用 8512，512 规格使用 8516：

```bash
export PORT=8512  # 512 规格改为 8516
curl --noproxy '*' -fsS "http://127.0.0.1:$PORT/health"
curl --noproxy '*' -fsS "http://127.0.0.1:$PORT/v1/models"
```

模型列表应包含 `AXERA-TECH/FastVLM-1.5B`。在这个新终端重新设置模型目录，然后提交官方熊猫图：

```bash
export MODEL_DIR=~/edgeaccel/models/fastvlm-1-5b/d1e86badf01e
python3 - <<'PY'
import base64, json, os, urllib.request
from pathlib import Path

image = Path(os.environ['MODEL_DIR']) / 'images/image_1.jpg'
question = 'Describe the image in one sentence.'
uri = 'data:image/jpeg;base64,' + base64.b64encode(image.read_bytes()).decode()
payload = {
    'model': 'AXERA-TECH/FastVLM-1.5B',
    'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': question},
        {'type': 'image_url', 'image_url': {'url': uri}},
    ]}],
    'max_tokens': 96, 'temperature': 0, 'stream': True,
}
request = urllib.request.Request(
    'http://127.0.0.1:' + os.environ['PORT'] + '/v1/chat/completions',
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

模型应返回描述熊猫的文字。将图片改为 `images/ssd_horse.jpg`、问题改为 `Name the two animals in the foreground.`，可继续检查马和狗的识别。中文可使用 `请用一句中文描述图片的主要内容。`，需人工核对细节；两种规格的实际回复见下方。

本包上下文上限为 1024 token、预填充上限为 640 token；先使用单张图片和简短问题。每次请求独立发送图片和问题，不将前一次回复自动加入新请求。退出时在服务终端按 `Ctrl+C`，再用 `axcl-smi` 确认推理进程已释放。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

1024 与 512 两种规格各完成六次问答，马和狗识别正确，各自重复回复一致；1024 规格把两名清晰人物答为 1，512 规格答为 2。不能因一种规格计数正确就判定整个模型质量通过，本次 1024 规格计数未通过。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/fastvlm-1-5b-20260928/image_1.jpg)](../../../static/validation/effects/fastvlm-1-5b-20260928/image_1.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/fastvlm-1-5b-20260928/ssd_horse.jpg)](../../../static/validation/effects/fastvlm-1-5b-20260928/ssd_horse.jpg)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
1024×1024 规格
图片：image_1.jpg
问题：Describe the image in one sentence.
```

**实际回复**

```text
A panda bear is sitting in a bamboo forest.
```

正确识别熊猫和周围竹叶；不能仅凭局部画面确认属于森林环境。

客户端首段文字：1.853 s；完整流式请求：3.881 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 2：输入**

```text
1024×1024 规格
图片：image_1.jpg
问题：请用一句中文描述图片的主要内容。
```

**实际回复**

```text
一只熊猫正坐在竹林里。
```

正确识别坐着的熊猫和周围竹叶；“竹林”作为概括，未核验场地类型。

客户端首段文字：2.256 s；完整流式请求：4.339 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 3：输入**

```text
1024×1024 规格
图片：ssd_horse.jpg
问题：Name the two animals in the foreground.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

前景两只动物为马和狗，回答与画面一致。

客户端首段文字：1.967 s；完整流式请求：4.479 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 4：输入**

```text
1024×1024 规格
图片：ssd_horse.jpg
问题：How many people are clearly visible in the image?
```

**实际回复**

```text
There is one person clearly visible in the image.
```

回答为 1 人；图中清晰可辨的是骑马者和右侧红衣人物，共 2 人，计数未通过。

客户端首段文字：1.930 s；完整流式请求：3.872 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 5：输入**

```text
1024×1024 规格
图片：image_1.jpg
问题：Describe the image in one sentence.
```

**实际回复**

```text
A panda bear is sitting in a bamboo forest.
```

切换图片后重复提问，与本规格第一次回复逐字一致。

客户端首段文字：1.996 s；完整流式请求：4.095 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 6：输入**

```text
1024×1024 规格
图片：ssd_horse.jpg
问题：请用一句中文描述图片的主要内容。
```

**实际回复**

```text
一个男人骑着一匹棕色的马，旁边是一只棕色的狗，背景中有一辆卡车和一些人。
```

识别出骑马者、棕马、棕狗、车辆及背景人物；不依据图片核验人物身份或性别。

客户端首段文字：1.948 s；完整流式请求：7.398 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 7：输入**

```text
512×512 规格
图片：image_1.jpg
问题：Describe the image in one sentence.
```

**实际回复**

```text
A panda is sitting in a grassy area with bamboo.
```

正确识别熊猫和竹叶；画面地面为泥土、落叶和竹枝，“grassy area”不够准确。

客户端首段文字：0.951 s；完整流式请求：3.657 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 8：输入**

```text
512×512 规格
图片：image_1.jpg
问题：请用一句中文描述图片的主要内容。
```

**实际回复**

```text
一只熊猫正坐在竹林里。
```

正确识别坐着的熊猫和周围竹叶；“竹林”作为概括，未核验场地类型。

客户端首段文字：0.844 s；完整流式请求：2.384 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 9：输入**

```text
512×512 规格
图片：ssd_horse.jpg
问题：Name the two animals in the foreground.
```

**实际回复**

```text
The two animals in the foreground are a horse and a dog.
```

前景两只动物为马和狗，回答与画面一致。

客户端首段文字：0.821 s；完整流式请求：3.421 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 10：输入**

```text
512×512 规格
图片：ssd_horse.jpg
问题：How many people are clearly visible in the image?
```

**实际回复**

```text
There are two people clearly visible in the image. One person is sitting on the horse, and the other person is standing in the background.
```

回答为 2 人，并区分骑马者与背景站立人物，与清晰可见对象一致。

客户端首段文字：0.948 s；完整流式请求：6.396 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 11：输入**

```text
512×512 规格
图片：image_1.jpg
问题：Describe the image in one sentence.
```

**实际回复**

```text
A panda is sitting in a grassy area with bamboo.
```

切换图片后重复提问，与本规格第一次回复逐字一致。

客户端首段文字：0.901 s；完整流式请求：3.143 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**示例 12：输入**

```text
512×512 规格
图片：ssd_horse.jpg
问题：请用一句中文描述图片的主要内容。
```

**实际回复**

```text
一个男人骑着一匹棕色的马，旁边有一只狗看着他。
```

识别出骑马者、马、狗及周边场景；不依据图片核验人物身份或性别。

客户端首段文字：0.791 s；完整流式请求：4.104 s。首段指首个非空文字事件；两项均为主机 HTTP 墙钟，包含输入传输与处理，不含模型加载，不是纯 NPU 耗时。

**使用时注意：**

- 每种图像规格仅测试两张图片、五种图文问题和一次重复；未测试视频、OCR、复杂计数、多轮长上下文或并发。
- 1024 规格人数回答未通过人工核对，512 规格地面描述不够准确；基本运行通过不代表所有回答正确。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`d1e86badf01ec701bb6b5f06a005622f3074614f`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行时 | AX-LLM 8501c22b940f / AXCL / Linux aarch64 / GCC 13.3 |
| 采样 | top_k=1，temperature=0，每题最多 96 token；单张图片、独立请求 |
| 图像与权重 | 1024×1024 与 512×512 图像编码器，28 个语言分片，1536 维词向量，AX650 W8A16 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 1024 规格加载至服务就绪 | 67.194 s | 模型加载独立于下列请求计时。 |
| 512 规格加载至服务就绪 | 65.681 s | 模型加载独立于下列请求计时。 |
| 1024 规格首段文字 / 完整回复范围 | 1.853–2.256 s / 3.872–7.398 s | 六次同主机 HTTP 请求墙钟；包含图片处理、预填充和生成，不是独立 NPU 时间。 |
| 512 规格首段文字 / 完整回复范围 | 0.791–0.951 s / 2.384–6.396 s | 六次同主机 HTTP 请求墙钟；包含图片处理、预填充和生成，不是独立 NPU 时间。 |

适用范围：

- 该测试未导出逐层原始张量，因此不作全张量有限性或逐层数值精度结论。
- 仅在 16GB 卡验证，8GB 容量回归待完成。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/run_axcl_aarch64.sh) | 启动或构建脚本 |
| [`infer_axmodel.py`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/infer_axmodel.py) | Python 程序 / 前后处理 |
| [`fastvlm_ax650_context_1k_prefill_640/image_encoder_1024x1024.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_ax650_context_1k_prefill_640/image_encoder_1024x1024.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_ax650_context_1k_prefill_640/image_encoder_512x512.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_ax650_context_1k_prefill_640/image_encoder_512x512.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_ax650_context_1k_prefill_640/llava_qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/config.json) | 运行配置 |
| [`fastvlm_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_tokenizer/config.json) | 运行配置 |
| [`fastvlm_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_tokenizer/generation_config.json) | 运行配置 |
| [`fastvlm_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/fastvlm_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/post_config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/requirements.txt) | Python 依赖清单 |
| [`run_ax650_1024.sh`](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/run_ax650_1024.sh) | 启动或构建脚本 |

仓库提交：`d1e86badf01ec701bb6b5f06a005622f3074614f`。仓库中的 31 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/tree/d1e86badf01ec701bb6b5f06a005622f3074614f)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/tree/d1e86badf01ec701bb6b5f06a005622f3074614f)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/README.md)。
- [主要程序入口：infer_axmodel.py](https://huggingface.co/AXERA-TECH/FastVLM-1.5B/blob/d1e86badf01ec701bb6b5f06a005622f3074614f/infer_axmodel.py)。

返回[完整模型目录](../catalog.mdx)。
