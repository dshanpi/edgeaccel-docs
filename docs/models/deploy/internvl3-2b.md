---
title: "InternVL3-2B 部署指南"
sidebar_label: "InternVL3-2B"
description: "InternVL3-2B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# InternVL3-2B 部署指南

InternVL3-2B 用于视觉问答。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/InternVL3-2B` 的固定版本。下面下载本页选用的 55 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/internvl3-2b/48bb181aa119
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/InternVL3-2B \
  "README.md" \
  "examples/image_0.jpg" \
  "examples/image_1.jpg" \
  "examples/image_2.png" \
  "examples/image_3.png" \
  "examples/red-panda.mp4" \
  "internvl3_2b_axmodel/model.embed_tokens.weight.bfloat16.bin" \
  "internvl3_2b_axmodel/qwen2_p128_l0_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l10_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l11_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l12_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l13_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l14_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l15_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l16_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l17_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l18_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l19_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l1_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l20_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l21_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l22_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l23_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l24_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l25_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l26_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l27_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l2_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l3_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l4_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l5_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l6_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l7_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l8_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_p128_l9_together.axmodel" \
  "internvl3_2b_axmodel/qwen2_post.axmodel" \
  "internvl3_2b_tokenizer/added_tokens.json" \
  "internvl3_2b_tokenizer/config.json" \
  "internvl3_2b_tokenizer/configuration_intern_vit.py" \
  "internvl3_2b_tokenizer/configuration_internvl_chat.py" \
  "internvl3_2b_tokenizer/conversation.py" \
  "internvl3_2b_tokenizer/generation_config.json" \
  "internvl3_2b_tokenizer/merges.txt" \
  "internvl3_2b_tokenizer/modeling_intern_vit.py" \
  "internvl3_2b_tokenizer/modeling_internvl_chat.py" \
  "internvl3_2b_tokenizer/preprocessor_config.json" \
  "internvl3_2b_tokenizer/special_tokens_map.json" \
  "internvl3_2b_tokenizer/tokenizer.json" \
  "internvl3_2b_tokenizer/tokenizer_config.json" \
  "internvl3_2b_tokenizer/vocab.json" \
  "internvl3_tokenizer.py" \
  "main_axcl_aarch64" \
  "post_config.json" \
  "run_internvl_3_2b_448_axcl_aarch64.sh" \
  "vit_axmodel/internvl3_2b_vit_slim.axmodel" \
  --revision 48bb181aa11917fea8309a6304c570152f9b5903 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 编译 ARM64 推理程序

本页使用 **RK3576 + AX8850 16GB M.2**。仓库自带的 ARM64 程序依赖 OpenCV 4.5，本页系统使用 OpenCV 4.6.0，因此从官方源码编译兼容本机库的程序。

在 RK3576 主机终端执行。首次构建使用一个新的源码目录：

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git libopencv-dev libspdlog-dev
RUNTIME_DIR=~/edgeaccel/runtime/internvl3-72ada011
git clone --filter=blob:none --no-checkout https://github.com/AXERA-TECH/ax-llm.git "$RUNTIME_DIR"
git -C "$RUNTIME_DIR" checkout --detach 72ada011e58fc0015578e6b9b5fd6b4674e26429
cmake -S "$RUNTIME_DIR" -B "$RUNTIME_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_WITH_YOLOV5_TEST=OFF
cmake --build "$RUNTIME_DIR/build" --target main -j1
ldd "$RUNTIME_DIR/build/main"
"$RUNTIME_DIR/build/main" --help
```

编译产物为 `build/main`，依赖检查不能出现 `not found`。此版本使用 HTTP 分词服务，参数名为 `--url_tokenizer_model`。后续提交已更改分词方式，复现本页结果时保留上述提交号。

本页构建环境使用 OpenCV 4.6.0。若找不到 AXCL 头文件或库，先完成驱动与开发包安装，再重新配置 CMake。

实际语言权重位于 internvl3_2b_axmodel/，图像编码器位于 vit_axmodel/internvl3_2b_vit_slim.axmodel；以下命令已修正仓库脚本中的旧目录。

## 配置分词与采样

在 RK3576 的模型目录执行：

```bash
python3 -m venv ~/edgeaccel/internvl3-2b-env
source ~/edgeaccel/internvl3-2b-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
cd "$MODEL_DIR"
python - <<'PY'
import json
from pathlib import Path
t = Path('internvl3_tokenizer.py')
original = t.read_text()
old = 'prompt += "<|im_end|>\\n<|im_start|>assistant"'
new = 'prompt += "<|im_end|>\\n<|im_start|>assistant\\n"'
if old in original:
    assert original.count(old) == 1
    t.with_suffix('.py.upstream').write_text(original)
    t.write_text(original.replace(old, new))
else:
    assert new in original, '请确认使用本页固定版本的分词脚本'
p = Path('post_config.json')
backup = p.with_suffix('.json.upstream')
if not backup.exists():
    backup.write_bytes(p.read_bytes())
config = json.loads(p.read_text())
config.update(enable_temperature=False, enable_repetition_penalty=False,
              enable_top_p_sampling=False, enable_top_k_sampling=True, top_k=1)
p.write_text(json.dumps(config, indent=2) + '\n')
PY
python internvl3_tokenizer.py --host 127.0.0.1 --port 12345
```

保持服务运行。脚本加载配套的 `internvl3_2b_tokenizer/` 词表；每张 448×448 图片对应 256 个图像 token。上方补齐 `assistant` 后的换行，使提示模板与同版本官方 `llm.py` 一致。样例采用贪心采样，与仓库默认随机采样不同。

## 运行四张图片

在另一终端设置目录，定义每次只运行一题的命令：

```bash
MODEL_DIR=~/edgeaccel/models/internvl3-2b/48bb181aa119
RUNTIME_DIR=~/edgeaccel/runtime/internvl3-72ada011
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

run_question() {
  printf '%s\n%s\nq\n' "$2" "$1" | "$RUNTIME_DIR/build/main" \
    --template_filename_axmodel './internvl3_2b_axmodel/qwen2_p128_l%d_together.axmodel' \
    --axmodel_num 28 \
    --filename_image_encoder_axmodedl ./vit_axmodel/internvl3_2b_vit_slim.axmodel \
    --use_mmap_load_embed 1 --url_tokenizer_model http://127.0.0.1:12345 \
    --filename_post_axmodel ./internvl3_2b_axmodel/qwen2_post.axmodel \
    --filename_tokens_embed ./internvl3_2b_axmodel/model.embed_tokens.weight.bfloat16.bin \
    --tokens_embed_num 151674 --tokens_embed_size 1536 --devices 0 --live_print 0
}

run_question examples/image_0.jpg 'What animal is in the image? Answer in one short sentence.'
run_question examples/image_1.jpg '请用一句中文描述图片中的动物。'
run_question examples/image_2.png 'How many people are in the image? Reply with only the number.'
run_question examples/image_3.png 'Describe the hair color and background in one sentence.'
```

程序依次读取问题、图片路径和 `q`；完成生成后退出。`--live_print 0` 在生成结束后显示完整文本。`filename_image_encoder_axmodedl` 是此版本的实际参数拼写，照原样使用。

## 对照图片检查输出

四张图片分别包含小熊猫、大熊猫、三名穿宇航服的人物，以及海边人物肖像。对照下方原图与模型原文，分别检查类别、数量、颜色、场景细节和要求的输出格式。

正常运行应产生文字并显示 `hit eos`。进程退出后，用 `axcl-smi` 确认已释放模型。内部首 token 耗时不包含模型加载，也不等同于终端首次显示回复的等待时间。

本页展示四次独立的单图问答，尚未覆盖视频、多图比较、多轮或完整评测集。结束使用后，在分词服务终端按 `Ctrl+C`；需要恢复默认采样时，将 `post_config.json.upstream` 复制回 `post_config.json`。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

四张图片分别识别出小熊猫、大熊猫、三名人物和银发海边肖像；人数题返回完整句子，没有遵守只输出数字的要求。本次指定格式未通过。

**示例 1：输入**

[![输入图片 · image_0.jpg](../../../static/validation/effects/internvl3-2b-20260928/image_0.jpg)](../../../static/validation/effects/internvl3-2b-20260928/image_0.jpg)

```text
What animal is in the image? Answer in one short sentence.
```

**实际回复**

```text
The animal in the image is a red panda.
```

red panda 与图中的小熊猫一致，回复为一个简短英文句子。

图像编码：413.49 ms；程序内部首 token 耗时：2101.26 ms；含模型加载的完整进程：70.436 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

[![输入图片 · image_1.jpg](../../../static/validation/effects/internvl3-2b-20260928/image_1.jpg)](../../../static/validation/effects/internvl3-2b-20260928/image_1.jpg)

```text
请用一句中文描述图片中的动物。
```

**实际回复**

```text
图片中的动物是一只大熊猫。
```

大熊猫类别与图片一致，回复为一句中文。

图像编码：414.78 ms；程序内部首 token 耗时：2391.96 ms；含模型加载的完整进程：72.065 s。内部计时不等同于客户端端到端首字延迟。

**示例 3：输入**

[![输入图片 · image_2.png](../../../static/validation/effects/internvl3-2b-20260928/image_2.png)](../../../static/validation/effects/internvl3-2b-20260928/image_2.png)

```text
How many people are in the image? Reply with only the number.
```

**实际回复**

```text
There are three people in the image.
```

three 与画面中的三名人物一致；回复带有完整句子，没有满足只返回数字的要求。

图像编码：409.49 ms；程序内部首 token 耗时：2132.72 ms；含模型加载的完整进程：71.735 s。内部计时不等同于客户端端到端首字延迟。

**示例 4：输入**

[![输入图片 · image_3.png](../../../static/validation/effects/internvl3-2b-20260928/image_3.png)](../../../static/validation/effects/internvl3-2b-20260928/image_3.png)

```text
Describe the hair color and background in one sentence.
```

**实际回复**

```text
The character has silver hair adorned with pink flowers and a blue choker, set against a serene beach backdrop.
```

银色头发、粉色花朵、蓝灰色颈饰及海滩背景与画面相符，回复为一个英文句子。

图像编码：417.35 ms；程序内部首 token 耗时：2104.79 ms；含模型加载的完整进程：73.545 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 仅人工核对四张官方样图；人物计数回答未满足严格格式要求，尚无独立数据集精度结论。
- 仅在 16GB 算力卡上测试 4 条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`48bb181aa11917fea8309a6304c570152f9b5903`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | aarch64 / RK3576，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 推理程序 | 官方 ax-llm 72ada011e58fc0015578e6b9b5fd6b4674e26429，RK3576 本机 CMake Release 编译，设备 0。 |
| 分词服务 | 官方配套 tokenizer，按同仓库 Python 入口补齐 assistant 末尾换行；Python 3.12 / Transformers 4.51.3 / Tokenizers 0.21.4。 |
| 采样 | top_k=1；关闭 temperature、repetition_penalty、top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例 1 进程耗时 | 70.436 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 72.065 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 71.735 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 4 进程耗时 | 73.545 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_internvl_3_2b_448_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/run_internvl_3_2b_448_axcl_aarch64.sh) | 启动或构建脚本 |
| [`internvl3_tokenizer.py`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_tokenizer.py) | 旧版分词服务入口 |
| [`gradio_demo_python_api.py`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/gradio_demo_python_api.py) | Python 程序 / 前后处理 |
| [`internvl3_2b_axmodel/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_axmodel/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_2b_axmodel/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_axmodel/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_2b_axmodel/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_axmodel/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_2b_axmodel/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_axmodel/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_2b_axmodel/qwen2_p128_l13_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_axmodel/qwen2_p128_l13_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/config.json) | 运行配置 |
| [`infer.py`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/infer.py) | Python 程序 / 前后处理 |
| [`internvl3_2b_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_tokenizer/config.json) | 运行配置 |
| [`internvl3_2b_tokenizer/configuration_intern_vit.py`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_tokenizer/configuration_intern_vit.py) | 旧版分词服务入口 |
| [`internvl3_2b_tokenizer/configuration_internvl_chat.py`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_tokenizer/configuration_internvl_chat.py) | 旧版分词服务入口 |
| [`internvl3_2b_tokenizer/conversation.py`](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_2b_tokenizer/conversation.py) | 旧版分词服务入口 |

仓库提交：`48bb181aa11917fea8309a6304c570152f9b5903`。仓库中的 30 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/InternVL3-2B/tree/48bb181aa11917fea8309a6304c570152f9b5903)。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/InternVL3-2B/tree/48bb181aa11917fea8309a6304c570152f9b5903)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/README.md)。
- [主要程序入口：internvl3_tokenizer.py](https://huggingface.co/AXERA-TECH/InternVL3-2B/blob/48bb181aa11917fea8309a6304c570152f9b5903/internvl3_tokenizer.py)。
- [配套项目：AXERA-TECH/InternVL3-2B.axera](https://github.com/AXERA-TECH/InternVL3-2B.axera/tree/master/model_convert)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-internvl)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-internvl)。

返回[完整模型目录](../catalog.mdx)。
