---
title: "InternVL2_5-1B 部署指南"
sidebar_label: "InternVL2_5-1B"
description: "InternVL2_5-1B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# InternVL2_5-1B 部署指南

InternVL2_5-1B 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/InternVL2_5-1B` 的固定版本。下面下载本页选用的 38 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/internvl2-5-1b/123ee66991d9
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/InternVL2_5-1B \
  "README.md" \
  "internvl2_5_1b_448_ax650/model.embed_tokens.weight.bfloat16.bin" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l0_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l10_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l11_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l12_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l13_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l14_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l15_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l16_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l17_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l18_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l19_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l1_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l20_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l21_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l22_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l23_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l2_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l3_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l4_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l5_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l6_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l7_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l8_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_p320_l9_together.axmodel" \
  "internvl2_5_1b_448_ax650/qwen2_post.axmodel" \
  "internvl2_5_1b_448_ax650/vit_intern_2_5_sim_space2depth_nhwc.axmodel" \
  "internvl2_5_tokenizer/added_tokens.json" \
  "internvl2_5_tokenizer/merges.txt" \
  "internvl2_5_tokenizer/special_tokens_map.json" \
  "internvl2_5_tokenizer/tokenizer_config.json" \
  "internvl2_5_tokenizer/vocab.json" \
  "internvl2_5_tokenizer_448.py" \
  "main_axcl_aarch64" \
  "panda.jpg" \
  "run_internvl2_5_448_axcl_aarch64.sh" \
  "ssd_car.jpg" \
  --revision 123ee66991d912a70487a6d17343982ec67e7444 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备分词服务

本页使用仓库内的原生 AXCL 程序 `main_axcl_aarch64`，配合 `internvl2_5_1b_448_ax650` 权重。图像编码器输入为 448×448；不混用 AX630C 的 364 版本。

在 RK3576 主机执行：

```bash
python3 -m venv ~/edgeaccel/internvl25-env
source ~/edgeaccel/internvl25-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
chmod +x main_axcl_aarch64
ldd ./main_axcl_aarch64
```

依赖检查不能出现 `not found`。使用配套的 `internvl2_5_tokenizer_448.py`；它会为图片插入 256 个图像 token，不适用普通文本模型的 UID 分词接口。

## 配置采样并启动服务

为复现下方样例，在模型目录创建 `post_config.json`，采用 `top_k=1` 的贪心采样。固定版本仓库没有提供该文件；若目录中已有自定义配置，先备份：

```bash
cd "$MODEL_DIR"
python - <<'PY'
import json
from pathlib import Path
p = Path('post_config.json')
if p.exists():
    backup = p.with_suffix('.json.before-guide')
    if not backup.exists():
        backup.write_bytes(p.read_bytes())
config = {
    'enable_temperature': False, 'temperature': 0.9,
    'enable_repetition_penalty': False, 'repetition_penalty': 1.2,
    'penalty_window': 20,
    'enable_top_p_sampling': False, 'top_p': 0.8,
    'enable_top_k_sampling': True, 'top_k': 1
}
p.write_text(json.dumps(config, indent=2) + '\n')
PY
python internvl2_5_tokenizer_448.py --host 127.0.0.1 --port 12345
```

看到 `http://127.0.0.1:12345` 后保持终端运行。服务只监听本机，生成时需要持续可用。

## 运行图像问答

在另一终端设置目录并定义命令。下列拼写 `filename_image_encoder_axmodedl` 与此版本程序一致，不能自行改为 `axmodel`。

```bash
MODEL_DIR=~/edgeaccel/models/internvl2-5-1b/123ee66991d9
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

run_question() {
  ./main_axcl_aarch64 \
    --template_filename_axmodel 'internvl2_5_1b_448_ax650/qwen2_p320_l%d_together.axmodel' \
    --axmodel_num 24 \
    --filename_image_encoder_axmodedl internvl2_5_1b_448_ax650/vit_intern_2_5_sim_space2depth_nhwc.axmodel \
    --tokenizer_type 2 --bos 0 --eos 0 --use_mmap_load_embed 0 \
    --filename_tokenizer_model http://127.0.0.1:12345 \
    --filename_post_axmodel internvl2_5_1b_448_ax650/qwen2_post.axmodel \
    --filename_tokens_embed internvl2_5_1b_448_ax650/model.embed_tokens.weight.bfloat16.bin \
    --tokens_embed_num 151674 --tokens_embed_size 896 \
    --devices 0 --live_print 0 --continue 0 --image "$1" --prompt "$2"
}

run_question ssd_car.jpg 'Describe the image in one sentence.'
run_question ssd_car.jpg 'What color is the bus? Answer with only the color.'
run_question panda.jpg 'What animal is in the image? Answer in one short sentence.'
run_question panda.jpg '请用一句中文描述图片中的动物。'
```

每条命令独立加载模型、生成回复后退出。`--live_print 0` 在生成完成后显示文本；下方程序内部首 token 时间不包含模型加载，不能当作终端首次显示回答的等待时间。

## 检查图片与回复

程序应显示图像编码耗时、生成的文本和结束标记 `hit eos`，退出后用 `axcl-smi` 检查进程已经释放。若图片路径错误，先确认文件可读，再运行问答。

对照下方输入图片查看模型原文，重点检查物体类别、颜色和凭空补充的细节。不要仅凭句子通顺判断视觉内容正确。本页是两张图片的四次单轮问答，未验证多图、视频、OCR、多轮或完整评测集。

结束使用后，在分词服务终端按 `Ctrl+C`。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两张图片的四次问答中，公交车颜色、小熊猫类别和中文主体描述与图相符；首句把面向镜头的人物写成朝公交车微笑，并推断车辆停放。街景细节质量未通过。

**示例 1：输入**

[![输入图片 · ssd_car.jpg](../../../static/validation/effects/internvl2-5-1b-20260928/ssd_car.jpg)](../../../static/validation/effects/internvl2-5-1b-20260928/ssd_car.jpg)

```text
Describe the image in one sentence.
```

**实际回复**

```text
A woman smiles at a red double-decker bus with an advertisement on its side, parked on a city street with buildings in the background.
```

识别出红色双层公交车、侧面广告、人物与街道建筑；但“朝公交车微笑”与人物朝向不符，“车辆停放”也不能仅凭这张静态图片确认。

图像编码：371.18 ms；程序内部首 token 耗时：594.68 ms；含模型加载的完整进程：34.568 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

[![输入图片 · ssd_car.jpg](../../../static/validation/effects/internvl2-5-1b-20260928/ssd_car.jpg)](../../../static/validation/effects/internvl2-5-1b-20260928/ssd_car.jpg)

```text
What color is the bus? Answer with only the color.
```

**实际回复**

```text
Red
```

仅返回 Red，与输入图中公交车的红色一致，符合只返回颜色的要求。

图像编码：375.76 ms；程序内部首 token 耗时：600.26 ms；含模型加载的完整进程：31.214 s。内部计时不等同于客户端端到端首字延迟。

**示例 3：输入**

[![输入图片 · panda.jpg](../../../static/validation/effects/internvl2-5-1b-20260928/panda.jpg)](../../../static/validation/effects/internvl2-5-1b-20260928/panda.jpg)

```text
What animal is in the image? Answer in one short sentence.
```

**实际回复**

```text
The animal in the image is a red panda.
```

识别为 red panda（小熊猫），与画面一致，回答为一个短句。

图像编码：379.29 ms；程序内部首 token 耗时：631.12 ms；含模型加载的完整进程：33.018 s。内部计时不等同于客户端端到端首字延迟。

**示例 4：输入**

[![输入图片 · panda.jpg](../../../static/validation/effects/internvl2-5-1b-20260928/panda.jpg)](../../../static/validation/effects/internvl2-5-1b-20260928/panda.jpg)

```text
请用一句中文描述图片中的动物。
```

**实际回复**

```text
这是一只红熊猫，它正趴在一块木头上，背景是绿色的树木。
```

回答中的红熊猫指小熊猫；趴在木板上、背景有绿色树木的描述与图片主体相符。

图像编码：371.98 ms；程序内部首 token 耗时：606.12 ms；含模型加载的完整进程：34.347 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 仅测试两张图片的四个短问题；场景细节仍有误述，未完成 OCR、细粒度定位或独立数据集评测。
- 仅在 16GB 算力卡上测试 4 条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`123ee66991d912a70487a6d17343982ec67e7444`。

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
| 示例 1 进程耗时 | 34.568 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 31.214 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 33.018 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 4 进程耗时 | 34.347 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_internvl2_5_448_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/run_internvl2_5_448_axcl_aarch64.sh) | 启动或构建脚本 |
| [`internvl2_5_tokenizer_448.py`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_tokenizer_448.py) | 旧版分词服务入口 |
| [`internvl2_5_tokenizer_364.py`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_tokenizer_364.py) | 旧版分词服务入口 |
| [`internvl2_5_1b_448_ax650/qwen2_p320_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_1b_448_ax650/qwen2_p320_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl2_5_1b_448_ax650/qwen2_p320_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_1b_448_ax650/qwen2_p320_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl2_5_1b_448_ax650/qwen2_p320_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_1b_448_ax650/qwen2_p320_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl2_5_1b_448_ax650/qwen2_p320_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_1b_448_ax650/qwen2_p320_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl2_5_1b_448_ax650/qwen2_p320_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_1b_448_ax650/qwen2_p320_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/config.json) | 运行配置 |
| [`internvl2_5_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_tokenizer/tokenizer_config.json) | 运行配置 |
| [`run_internvl2_5_364_ax630c.sh`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/run_internvl2_5_364_ax630c.sh) | 启动或构建脚本 |
| [`run_internvl2_5_448_ax650.sh`](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/run_internvl2_5_448_ax650.sh) | 启动或构建脚本 |

仓库提交：`123ee66991d912a70487a6d17343982ec67e7444`。仓库中的 52 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/tree/123ee66991d912a70487a6d17343982ec67e7444)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/tree/123ee66991d912a70487a6d17343982ec67e7444)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/README.md)。
- [主要程序入口：internvl2_5_tokenizer_448.py](https://huggingface.co/AXERA-TECH/InternVL2_5-1B/blob/123ee66991d912a70487a6d17343982ec67e7444/internvl2_5_tokenizer_448.py)。
- [配套项目：ZHEQIUSHUI/ax-llm](https://github.com/ZHEQIUSHUI/ax-llm/tree/axcl-intervl2.5-1b-pulsarbuild)。
- [配套项目：ZHEQIUSHUI/ax-llm](https://github.com/ZHEQIUSHUI/ax-llm/tree/intervl2_pulsarbuild)。

返回[完整模型目录](../catalog.mdx)。
