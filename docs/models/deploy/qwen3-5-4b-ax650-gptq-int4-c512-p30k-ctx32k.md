---
title: "Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k 部署指南"
sidebar_label: "Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k"
description: "Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k 部署指南

Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 下载固定版本模型

本页使用 `Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k` 的固定提交，模型文件约 11.2 GiB。下载分区建议至少有 16 GiB 可用空间。板载空间不足时，将 `MODEL_DIR` 改为已挂载的 SSD 或存储卡目录。

在连接算力卡的 RK3576 终端执行：

```bash
MODEL_DIR=~/edgeaccel/models/qwen35-4b-ctx32k/4222f23a3459
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k \
  --revision 4222f23a3459751d20239a51621df62538cfd409 \
  --local-dir "$MODEL_DIR"
```

本目录应包含 32 个文本层、输出层、视觉编码器、embedding、分词器及配置。保留完整目录；名称相近的 C128、C256 和 C512 版本不能混用文件。代理设置见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 ARM64 运行程序

本页使用官方 AXCL ARM64 程序，版本报告源码提交 `b704e2f3dc4e`、分词器提交 `a08af3838d76`。本轮硬件为 RK3576 + AX8850 16GB；实际 8GB 卡另行验证。

下载[固定运行程序与输入样例](/examples/qwen35-4b-20261003.tar.gz)，将文件命名为 `qwen35-4b-20261003.tar.gz`，复制到 RK3576 的 `~/Downloads`。模型校验脚本需要 Python 3.11 或更高版本。在同一终端执行：

```bash
cd ~/Downloads
echo 'afcdb99892184b742afffdfb0d0db79eab35e90f162714d8634d4e6020b3cb8c  qwen35-4b-20261003.tar.gz' | sha256sum -c -
mkdir -p ~/edgeaccel/runtimes
tar -xzf qwen35-4b-20261003.tar.gz -C ~/edgeaccel/runtimes
RUNTIME_DIR=~/edgeaccel/runtimes/qwen35-4b-20261003
chmod +x "$RUNTIME_DIR/axllm"
"$RUNTIME_DIR/axllm" version
ldd "$RUNTIME_DIR/axllm"
python3 "$RUNTIME_DIR/verify_models.py" "$MODEL_DIR"
```

程序版本应显示 `backend : AXCL` 和 `Linux aarch64`，依赖中不能出现 `not found`，模型校验应显示 `Verified 40 model files`。

## 启动模型服务

终端 1 执行，保持进程运行：

```bash
AXLLM_DEVICES=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  "$RUNTIME_DIR/axllm" serve "$MODEL_DIR" --port 8000
```

使用原始 `config.json` 和 `post_config.json`。运行时会加载混合注意力模型，并保留内存预检。出现模型加载或内存预检错误时，先处理错误，再发送请求。

## 发送文字、图片和视频请求

终端 2 设置前文的程序目录后，先确认服务就绪：

```bash
RUNTIME_DIR=~/edgeaccel/runtimes/qwen35-4b-20261003
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/v1/models
```

程序包内的 `request.py` 客户端接受 `--prompt`、`--image` 或 `--video`。保持 `enable_thinking=false`、`temperature=0` 和 128 个生成 token，与实测请求一致。

```bash
python3 "$RUNTIME_DIR/request.py" --prompt 'What is 2 + 3? Reply with only the number.'
python3 "$RUNTIME_DIR/request.py" \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.' \
  --image "$RUNTIME_DIR/fixtures/images/horse-dog.jpg"
python3 "$RUNTIME_DIR/request.py" \
  --prompt 'Describe the main action across these video frames in one short sentence.' \
  --video "$RUNTIME_DIR/fixtures/video8"
```

图片和帧目录路径必须能被服务进程访问。替换提问文字即可复现下方其他问题。样例视频由 8 张有序图片组成，按配置的 1 fps 解释；不代表原始视频的采集时间。下方展示本机实际回答与请求耗时。

完成后，在终端 1 按 `Ctrl+C` 退出，再运行 `axcl-smi` 确认模型资源已释放。本轮仅检查短输入；名称中的 32K 不代表本页已经验证长上下文能力。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成文字、图片和视频共 10 条请求，包含 8 种输入及两次重复检查。算术、JSON 格式、马犬识别和室内人数符合本轮要求；两次重复回答一致。下方保留实际回复及尚需复核的细节。

以下请求均在模型加载完成后发出。耗时包含客户端启动、请求处理与响应传输，不含模型加载；重复图片可能命中缓存，不能将这些数值视为纯 NPU 性能。

**示例 1：输入**

```text
What is 2 + 3? Reply with only the number.
```

**实际回复**

```text
5
```

结果为 5，仅输出所要求的数字；完整测试末尾再次提问得到相同答案。

完整请求耗时：16.056 s。

**示例 2：输入**

```text
用一句中文解释 PCIe 的作用。
```

**实际回复**

```text
PCIe 是一种高速计算机内部总线标准，用于连接中央处理器与各种硬件设备（如显卡、硬盘和网卡），以提供比传统标准（如 SATA 或 USB）更高的数据传输速率。
```

说明了 PCIe 连接硬件设备的用途；与 SATA、USB 的速度比较缺少版本、通道数和负载条件，不能作为通用性能结论。

完整请求耗时：38.319 s。

**示例 3：输入**

```text
Return only a JSON object with keys apple and pear. There are 3 apples and 2 pears. Do not use Markdown.
```

**实际回复**

```text
{"apple": 3, "pear": 2}
```

返回可直接解析的 JSON 对象，apple=3、pear=2，没有 Markdown 或附加说明。

完整请求耗时：29.443 s。

**示例 4：输入**

[![输入图片 · images/horse-dog.jpg](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/horse-dog.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/horse-dog.jpg)

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
A horse and a dog.
```

正确识别前景中的马和狗。后续重复同一图片与问题，回答一致。

完整请求耗时：27.443 s。

**示例 5：输入**

[![输入图片 · images/bus.jpg](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/bus.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/bus.jpg)

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一名女子站在伦敦街头，背景是一辆红色的双层巴士和古典建筑。
```

描述了前景人物、红色双层巴士和街道建筑；回答中的具体城市是模型推断，本轮未核实。

完整请求耗时：30.352 s。

**示例 6：输入**

[![输入图片 · images/room.jpg](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/room.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/room.jpg)

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
1
```

清晰可见的人数为 1，与输入图片一致。

完整请求耗时：26.064 s。

**示例 7：输入**

[![输入图片 · images/room.jpg](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/room.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/images/room.jpg)

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
这是一张展示现代家居内部的照片，画面中可见客厅和餐厅区域，有电视、餐桌、冰箱等家具，以及一位站在厨房区域的人。
```

电视、餐桌和站立人物与图片相符；“冰箱”不能从该图片可靠确认，应核对后再用于物件清单。

完整请求耗时：34.770 s。

**示例 8：输入**

按输入顺序查看视频帧：

<div className="model-effect-gallery">

<figure>

[![输入帧 1](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0000.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0000.jpg)

<figcaption>输入帧 1</figcaption>
</figure>

<figure>

[![输入帧 2](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0008.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0008.jpg)

<figcaption>输入帧 2</figcaption>
</figure>

<figure>

[![输入帧 3](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0016.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0016.jpg)

<figcaption>输入帧 3</figcaption>
</figure>

<figure>

[![输入帧 4](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0024.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0024.jpg)

<figcaption>输入帧 4</figcaption>
</figure>

<figure>

[![输入帧 5](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0032.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0032.jpg)

<figcaption>输入帧 5</figcaption>
</figure>

<figure>

[![输入帧 6](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0040.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0040.jpg)

<figcaption>输入帧 6</figcaption>
</figure>

<figure>

[![输入帧 7](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0048.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0048.jpg)

<figcaption>输入帧 7</figcaption>
</figure>

<figure>

[![输入帧 8](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0056.jpg)](../../../static/validation/effects/qwen3-5-4b-ax650-gptq-int4-c512-p30k-ctx32k-20261003/inputs/video8/frame_0056.jpg)

<figcaption>输入帧 8</figcaption>
</figure>

</div>

```text
Describe the main action across these video frames in one short sentence.
```

**实际回复**

```text
A group of meerkats are standing on their hind legs and interacting with each other in a mountainous landscape.
```

回答概括了山地背景和动物互动，但未具体说明前爪相触、推挤等动作；画面中主要是两只动物，“meerkats”物种判断未经确认。

完整请求耗时：36.968 s。

**使用时注意：**

- 本轮只覆盖一张 16GB 卡的短输入；未验证实际 8GB 卡、32K 长上下文、多轮对话或持续负载。
- 模型可能补充无法从输入确认的事实或细节；视频描述较笼统，需结合原始图片与帧序列核对。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`4222f23a3459751d20239a51621df62538cfd409`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | RK3576 ARM64，约 4GB 主机内存，Ubuntu 24.04，6.1.115-vendor-rk35xx |
| AXCL / 固件 | AXCL V3.16.0_20260729180218；固件 V3.16.0，CMM 15232 MiB |
| 运行程序 | 官方 AXCL ARM64 axllm，源码 b704e2f3dc4e，分词器 a08af3838d76 |
| 请求配置 | 单卡单并发，temperature=0，enable_thinking=false，max_tokens=128；原始模型配置 |
| 模型读取 | 只读网络模型文件；请求耗时不含模型加载，不能代替本地磁盘性能测试 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 模型服务启动 | 347.189 s | 包含网络读取与模型加载；不作为本地存储性能指标。 |

适用范围：

- 请求使用同一服务进程，重复图片可命中视觉缓存；所列耗时包含客户端与响应处理，不是冷启动或纯 NPU 性能。
- 十条请求均在 128 个生成 token 上限前返回；未独立采集 EOS token ID，不据此宣称所有终止分支已经覆盖。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/config.json) | 运行配置 |
| [`qwen3_5_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_5_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`qwen3_5_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/post_config.json) | 运行配置 |
| [`qwen3_5_text_p512_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_text_p512_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p512_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_text_p512_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p512_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_text_p512_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p512_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_text_p512_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_5_text_p512_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/qwen3_5_text_p512_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`4222f23a3459751d20239a51621df62538cfd409`。仓库中的 34 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/tree/4222f23a3459751d20239a51621df62538cfd409)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/tree/4222f23a3459751d20239a51621df62538cfd409)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k/blob/4222f23a3459751d20239a51621df62538cfd409/README.md)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。
- [配套项目：AXERA-TECH/ax-llm.git](https://github.com/AXERA-TECH/ax-llm.git)。

返回[完整模型目录](../catalog.mdx)。
