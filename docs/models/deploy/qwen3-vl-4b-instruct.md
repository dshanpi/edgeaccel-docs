---
title: "Qwen3-VL-4B-Instruct 部署指南"
sidebar_label: "Qwen3-VL-4B-Instruct"
description: "Qwen3-VL-4B-Instruct 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-4B-Instruct 部署指南

Qwen3-VL-4B-Instruct 用于图像与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-4B-Instruct` 的固定版本。下面下载本页选用的 48 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-4b-instruct/052d3999478f
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-4B-Instruct \
  --include "*" \
  --revision 052d3999478f8974b736f8663072e9a72aaabbf5 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套程序

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16。模型目录至少预留 8GB 可用空间。程序依赖 OpenCV 4.6，词嵌入读取约占 742 MiB 主机内存；文件校验脚本需要 Python 3.11 或更高版本。

下载[配套运行包](/examples/qwen3-vl4-fixed-20261003.tar.gz)，复制到连接算力卡的 Linux 主机并命名为 `~/edgeaccel/qwen3-vl4-fixed-20261003.tar.gz`。保留前文设置的 `MODEL_DIR`，在该 Linux 主机执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl4-fixed-20261003.tar.gz
chmod +x qwen3-vl4-fixed/main_axcl_aarch64
ldd qwen3-vl4-fixed/main_axcl_aarch64
python3 qwen3-vl4-fixed/verify_models.py "$MODEL_DIR"
```

`ldd` 不应出现 `not found`，校验应输出 `Verified 48 model files`。校验失败时先重新下载对应固定文件。程序使用本模型仓库的原生词表，无需启动分词服务。

视觉编码器、36 个文本层和输出层在算力卡运行；分词、图片预处理和词嵌入读取在主机执行。配套程序固定使用设备 0、贪心解码和独立进程，输入上限为 1152 token。

## 运行图片问答

先使用运行包内的骑乘场景图片：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input ~/edgeaccel/qwen3-vl4-fixed/companion/images/ssd_horse.jpg \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.'
```

`companion` 内的图片和八帧视频来自固定版本的官方 2B 仓库，用于对照同一输入的效果；推理使用本页下载的 4B 权重。再使用 4B 仓库自带的室内图片统计人数：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py image \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/01.jpg" \
  --prompt '画面中有几个人清晰可见？只回答人数。'
```

将问题改为 `请用一句中文描述图片中的主要内容。` 可查看室内描述。街景样例位于 `~/edgeaccel/qwen3-vl4-fixed/companion/images/ssd_car.jpg`。每条命令等待回答完成后再运行下一条。

## 运行视频帧问答

先使用 4B 仓库自带的三张 JPEG 帧：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" \
  --prompt '请用两句中文描述这些视频帧中动物的动作。'
```

程序按文件名顺序、1 fps 解释输入。编码器每两帧组成一组，三帧输入会重复末帧以完成最后一组；重复帧沿用原末帧时间，不表示额外观察了一帧。

再测试运行包内的八帧配套样例：

```bash
python3 ~/edgeaccel/qwen3-vl4-fixed/run_model.py video \
  --model-dir "$MODEL_DIR" \
  --input ~/edgeaccel/qwen3-vl4-fixed/companion/video \
  --prompt 'Describe what the two animals are doing in these video frames. Use two sentences.'
```

当前入口接受三帧或八帧 JPEG 目录，目录内不应混入其他文件。1 fps 是本页的输入配置，未核实原视频时基；本页未覆盖 MP4 解码、实时视频或多轮问答。

## 检查运行结果

日志应出现 `termination_reason=eos last_token=151645`，随后输出完整回答并退出。每条命令完成后执行：

```bash
echo $?
axcl-smi
```

退出码应为 `0`，设备列表不应继续显示该推理进程。`context-limit` 表示输出触及上限，不能当作完整回答结束。对照原图检查人数、文字和场景，对照视频帧检查可见动作；实际回答及偏差见下方效果展示。

本轮进程耗时包含网络读取模型、加载和推理，不代表本地存储性能。结果来自 16GB 卡；实际 8GB 卡、更多输入和连续运行需独立验证。

## 查看配套源码

运行包包含固定源码、原生词表来源、配套图片来源、编译信息和文件校验值。程序基于 AXERA 的 AX-LLM 提交 `3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7`，使用本页提供的配套版本。请保持程序、词表和模型版本一致。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成图片、官方三帧及配套八帧视频问答，展示原始输出与核对结果。

**五组图片问答**

以下展示固定输入和原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![输入 ssd_horse.jpg：骑乘者、马和狗](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/ssd_horse.jpg)

<figcaption>输入 ssd_horse.jpg：骑乘者、马和狗</figcaption>
</figure>

<figure>

[![官方输入 01.jpg：室内场景](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/01.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/01.jpg)

<figcaption>官方输入 01.jpg：室内场景</figcaption>
</figure>

<figure>

[![输入 ssd_car.jpg：双层巴士与街道](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/ssd_car.jpg)

<figcaption>输入 ssd_car.jpg：双层巴士与街道</figcaption>
</figure>

</div>

**示例 1：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
In the foreground, a woman is riding a brown horse while a brown dog stands beside them.
```

输入：ssd_horse.jpg。正确识别前景的马和狗；骑乘者性别未作独立标注。

**示例 2：输入**

```text
画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
1
```

输入：01.jpg。回答 1，与室内图中清晰可见的一人相符。

**示例 3：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在伦敦街头，身后是一辆红色的双层巴士，巴士上写着“Things get more exciting when you say ‘yes’”的广告语。
```

输入：ssd_car.jpg。人物、红色双层巴士及所引英文广告与图片基本相符；“伦敦”地名未独立核实，此题未测试广告翻译。

**示例 4：输入**

```text
请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
这是一张温馨的客厅与餐厅结合的室内照片，黄色墙壁、木质地板和绿色装饰墙营造出明亮舒适的氛围，一位女士站在厨房区域，前景的圆桌上摆放着一束粉红色的花。
```

输入：01.jpg。黄色墙壁、木地板、厨房区域和一人等主要内容与图片相符；前景花瓶清晰可见的是一枝花，“一束粉红色的花”不够准确。

**示例 5：输入**

```text
Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
In the foreground, a woman is riding a brown horse while a brown dog stands beside them.
```

输入：ssd_horse.jpg。与首次英文回答完全一致；仅说明此固定输入重复两次一致。

| 问题 | 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- | --- |
| 动物识别（英文） | ssd_horse.jpg | 191.942 | 777 |
| 室内人数 | 01.jpg | 184.608 | 111 |
| 街景描述 | ssd_car.jpg | 198.715 | 1332 |
| 室内描述 | 01.jpg | 202.983 | 1813 |
| 重复动物识别 | ssd_horse.jpg | 190.942 | 777 |

**官方三帧视频问答**

以下展示固定输入和原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![官方三帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0000.jpg)

<figcaption>官方三帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![官方三帧输入：第 2 帧](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0008.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0008.jpg)

<figcaption>官方三帧输入：第 2 帧</figcaption>
</figure>

<figure>

[![官方三帧输入：第 3 帧](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0016.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0016.jpg)

<figcaption>官方三帧输入：第 3 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只松鼠在岩石上面对面，前爪互相搭着，似乎在进行一场友好的“拳击”对决。背景是壮丽的山峦，阳光明媚，画面充满自然野趣。
```

输入：3 帧。面对面和前爪接触与输入帧相符，也按要求输出两句；“松鼠”未作独立物种确认，“友好的拳击”是模型对意图的推测。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
Two marmots are standing on their hind legs, facing each other with their front paws raised in a playful or confrontational gesture. They appear to be engaging in a spirited interaction, possibly a mock fight or social display, set against a backdrop of a rocky mountain landscape.
```

输入：3 帧。后腿站立、抬起前爪和山地背景与画面相符，输出为两句；marmots 的物种称呼及玩耍、对抗、社交展示等意图未独立确认。

| 问题 | 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- | --- |
| 动作描述（中文） | 3 帧 | 202.599 | 1702 |
| 动作描述（英文） | 3 帧 | 220.380 | 2183 |

**配套八帧视频问答**

以下展示固定输入和原始回答。每条问题使用独立进程；进程耗时包含网络读取、加载和推理。

<div className="model-effect-gallery">

<figure>

[![配套八帧输入：第 1 帧](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0000.jpg)

<figcaption>配套八帧输入：第 1 帧</figcaption>
</figure>

<figure>

[![配套八帧输入：第 4 帧](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0024.jpg)

<figcaption>配套八帧输入：第 4 帧</figcaption>
</figure>

<figure>

[![配套八帧输入：第 8 帧](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0056.jpg)](../../../static/validation/effects/qwen3-vl-4b-instruct-20261003/frame_0056.jpg)

<figcaption>配套八帧输入：第 8 帧</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
两只花栗鼠在岩石上互相扑打，动作敏捷而充满活力。它们前爪挥舞，似乎在进行一场有趣的角力，背景是壮丽的山景。
```

输入：8 帧。前爪挥动、相互接触和山地背景与画面相符，输出为两句；“花栗鼠”的物种称呼和“有趣的角力”意图未独立确认。

**示例 2：输入**

```text
Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
Two playful ground squirrels stand on their hind legs, facing each other and gently tapping or “boxing” with their front paws in a friendly manner. Their movements are quick and energetic, suggesting a playful interaction rather than a fight, set against a backdrop of a rocky mountain landscape.
```

输入：8 帧。后腿站立及前爪接触与画面相符，输出为两句；ground squirrels 的物种称呼未独立确认，友好、玩耍而非争斗的判断超出了这些帧能直接证明的内容。

| 问题 | 输入 | 进程耗时 / s | 算力卡调用 |
| --- | --- | --- | --- |
| 动作描述（中文） | 8 帧 | 204.534 | 1628 |
| 动作描述（英文） | 8 帧 | 213.081 | 2330 |

**使用时注意：**

- 室内回答把前景花瓶中的一枝花描述为“一束花”；街景中的“伦敦”地名未独立核实。
- 本轮街景问题为描述任务，未验证广告翻译。人物性别、视频动物的具体物种及玩耍、对抗等意图未独立标注。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`052d3999478f8974b736f8663072e9a72aaabbf5`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 固定 AXCL C++ 配套程序 / AX-LLM 3be4cc3 + 本页修复 / 本地原生分词 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输入覆盖 | 3 张图片 / 3 帧与 8 帧视频 | 5 条图片问题，三帧与八帧各2条视频问题，共9个独立进程。 |
| 算力卡执行 | 38 个 AXModel | 视觉编码器、36个文本层和输出层均执行并释放，共12653次调用。 |
| 视觉输入 | 384 × 384 | 单图1组；三帧视频2组，八帧视频4组视觉执行。 |

适用范围：

- 三帧和八帧的中英文视频回答均为两句；不同帧数下的回答不能单凭文字流畅就视为物种或动作理解正确。
- 图片01.jpg和三帧视频来自4B仓库；马和狗、巴士及八帧样例来自固定2B配套仓库。全部推理使用本页4B权重。
- 视频按文件名排序、1 fps解释；三帧输入末帧重复对齐，沿用原时间。未核实原视频时基，未验证MP4解码或实时视频。
- 9条问题均以 EOS=151645 结束。本次最多643个输入token，程序输入上限1152；未覆盖多轮、长上下文、连续运行及所有中间张量的浮点对照。
- 实际8GB卡仍需独立验证。进程耗时包含网络读取和加载，不代表本地存储性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-4B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/Qwen3-VL-4B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/post_config.json) | 运行配置 |
| [`qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`052d3999478f8974b736f8663072e9a72aaabbf5`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/tree/052d3999478f8974b736f8663072e9a72aaabbf5)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/tree/052d3999478f8974b736f8663072e9a72aaabbf5)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-4B-Instruct/blob/052d3999478f8974b736f8663072e9a72aaabbf5/README.md)。
- [配套项目：AXERA-TECH/Qwen3-VL.AXERA](https://github.com/AXERA-TECH/Qwen3-VL.AXERA)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm)。

返回[完整模型目录](../catalog.mdx)。
