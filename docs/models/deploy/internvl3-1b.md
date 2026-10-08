---
title: "InternVL3-1B 部署指南"
sidebar_label: "InternVL3-1B"
description: "InternVL3-1B 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# InternVL3-1B 部署指南

InternVL3-1B 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/InternVL3-1B` 的固定版本。下面下载本页选用的 41 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/internvl3-1b/797dd3d7676d
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/InternVL3-1B \
  "README.md" \
  "internvl3_1b_ax650/internvl3_1b_vit.axmodel" \
  "internvl3_1b_ax650/model.embed_tokens.weight.bfloat16.bin" \
  "internvl3_1b_ax650/qwen2_p128_l0_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l10_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l11_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l12_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l13_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l14_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l15_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l16_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l17_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l18_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l19_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l1_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l20_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l21_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l22_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l23_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l2_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l3_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l4_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l5_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l6_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l7_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l8_together.axmodel" \
  "internvl3_1b_ax650/qwen2_p128_l9_together.axmodel" \
  "internvl3_1b_ax650/qwen2_post.axmodel" \
  "internvl3_tokenizer.py" \
  "internvl3_tokenizer/added_tokens.json" \
  "internvl3_tokenizer/config.json" \
  "internvl3_tokenizer/generation_config.json" \
  "internvl3_tokenizer/merges.txt" \
  "internvl3_tokenizer/preprocessor_config.json" \
  "internvl3_tokenizer/special_tokens_map.json" \
  "internvl3_tokenizer/tokenizer.json" \
  "internvl3_tokenizer/tokenizer_config.json" \
  "internvl3_tokenizer/vocab.json" \
  "post_config.json" \
  "run_internvl_3_1b_448_axcl_x86.sh" \
  "ssd_car.jpg" \
  --revision 797dd3d7676d1900815a53906c72015e172bbad1 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 编译 ARM64 推理程序

本页使用 **RK3576 + AX8850 16GB M.2**。固定模型仓库提供的是 x86 AXCL 程序；在 ARM64 主机上从官方源码编译以下版本，不直接运行 `main_axcl_x86`。

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

## 准备分词服务

在下载模型的终端中执行：

```bash
python3 -m venv ~/edgeaccel/internvl3-env
source ~/edgeaccel/internvl3-env/bin/activate
python -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'
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
python internvl3_tokenizer.py --host 127.0.0.1 --port 12345
```

看到 `http://127.0.0.1:12345` 后保持服务运行。配套脚本会按图片数量和编码尺寸插入图像 token；这里每题输入一张图片，编码尺寸为 448×448。样例采用贪心采样，与仓库默认随机采样配置不同。

## 运行图像问答

在另一终端设置目录并定义命令：

```bash
MODEL_DIR=~/edgeaccel/models/internvl3-1b/797dd3d7676d
RUNTIME_DIR=~/edgeaccel/runtime/internvl3-72ada011
cd "$MODEL_DIR"
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"

run_question() {
  printf '%s\n%s\nq\n' "$1" ssd_car.jpg | "$RUNTIME_DIR/build/main" \
    --template_filename_axmodel './internvl3_1b_ax650/qwen2_p128_l%d_together.axmodel' \
    --axmodel_num 24 \
    --filename_image_encoder_axmodedl ./internvl3_1b_ax650/internvl3_1b_vit.axmodel \
    --use_mmap_load_embed 1 --url_tokenizer_model http://127.0.0.1:12345 \
    --filename_post_axmodel ./internvl3_1b_ax650/qwen2_post.axmodel \
    --filename_tokens_embed ./internvl3_1b_ax650/model.embed_tokens.weight.bfloat16.bin \
    --tokens_embed_num 151674 --tokens_embed_size 896 --devices 0 --live_print 0
}

run_question 'Describe the image in one sentence.'
run_question 'What color is the bus? Answer with only the color.'
run_question 'What words are written in the large white advertisement on the bus? Transcribe only the visible text.'
run_question '请用一句中文描述图片中的车辆。'
```

程序从标准输入依次读取问题、图片路径和退出指令 `q`。此版本没有 `--prompt` 或 `--image` 参数。参数 `filename_image_encoder_axmodedl` 的拼写来自官方接口，照原样使用。

每题独立启动，运行结束后退出。`--live_print 0` 在生成结束后显示完整回复；内部首 token 计时不能解释为客户端首次看到文字的等待时间。

## 检查图片与回复

对照原图检查车辆颜色、类型和广告文字，保留模型原文，不能把补充猜测视为图片中的事实。程序应产生回复并出现 `hit eos`；退出后用 `axcl-smi` 确认模型进程已释放。

本页只有一张图片的四次单轮问答，不代表完整 OCR、视频、多图或长上下文评测。结束使用后，在分词服务终端按 `Ctrl+C`；恢复默认采样时，将 `post_config.json.upstream` 复制回 `post_config.json`。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

四次街景问答识别出红色双层公交车及广告主要单词；颜色题附加完整句子，OCR 附加解释，中文题扩展为三句话，均未遵守对应格式要求。本次格式质量未通过。

**示例 1：输入**

[![输入图片 · ssd_car.jpg](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)

```text
Describe the image in one sentence.
```

**实际回复**

```text
: A woman stands in front of a red double-decker bus on a city street, with a black car nearby.
```

人物、红色双层公交车、旁边的深色车辆及主要相对位置与画面相符；回复开头额外输出了冒号。

图像编码：401.96 ms；程序内部首 token 耗时：1253.91 ms；含模型加载的完整进程：27.505 s。内部计时不等同于客户端端到端首字延迟。

**示例 2：输入**

[![输入图片 · ssd_car.jpg](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)

```text
What color is the bus? Answer with only the color.
```

**实际回复**

```text
The color of the bus is red.
```

颜色 red 与图片一致，但返回了完整英文句子，没有满足“只返回颜色”的要求。

图像编码：458.92 ms；程序内部首 token 耗时：1109.22 ms；含模型加载的完整进程：25.274 s。内部计时不等同于客户端端到端首字延迟。

**示例 3：输入**

[![输入图片 · ssd_car.jpg](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)

```text
What words are written in the large white advertisement on the bus? Transcribe only the visible text.
```

**实际回复**

```text
The words written in the large white advertisement on the bus are: "THINGS GET MORE EXCITING WHEN YOU SAY YES."
```

读出了广告主要单词 THINGS GET MORE EXCITING WHEN YOU SAY YES；仍附带解释，并没有忠实保留原图的引号等排版，不能视为逐字符 OCR 通过。

图像编码：396.39 ms；程序内部首 token 耗时：1319.19 ms；含模型加载的完整进程：28.391 s。内部计时不等同于客户端端到端首字延迟。

**示例 4：输入**

[![输入图片 · ssd_car.jpg](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)](../../../static/validation/effects/internvl3-1b-20260928/ssd_car.jpg)

```text
请用一句中文描述图片中的车辆。
```

**实际回复**

```text
图片中的车辆是一辆红色的双层巴士，车身广告上写着“THINGS GET MORE EXCITING WHEN YOU SAY YES”，旁边还有Virgin Money的标志。在巴士前面，有一位女性站在街道上，她穿着黑色外套，面带微笑。背景中可以看到一些商店和建筑物。
```

红色双层巴士、广告、人物和建筑等主要内容与画面相符；回复扩展成三句话，没有满足“一句中文”的要求。

图像编码：397.00 ms；程序内部首 token 耗时：1194.04 ms；含模型加载的完整进程：32.273 s。内部计时不等同于客户端端到端首字延迟。

**使用时注意：**

- 仅在一张街景图片上测试四个问题；主要内容可辨认，但严格格式及逐字符 OCR 未全部通过，未评估完整数据集。
- 仅在 16GB 算力卡上测试 4 条单轮输入；未验证 8GB、多轮、长上下文、并发或持续运行。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`797dd3d7676d1900815a53906c72015e172bbad1`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 | aarch64 / RK3576，主机内存约 4GB |
| 内核 | 6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 推理程序 | 官方 ax-llm 72ada011e58fc0015578e6b9b5fd6b4674e26429，RK3576 本机 CMake Release 编译，设备 0。 |
| 分词服务 | 官方配套 tokenizer；Python 3.12 / Transformers 4.51.3 / Tokenizers 0.21.4 |
| 采样 | top_k=1；关闭 temperature、repetition_penalty、top_p |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 示例 1 进程耗时 | 27.505 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 2 进程耗时 | 25.274 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 3 进程耗时 | 28.391 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |
| 示例 4 进程耗时 | 32.273 s | 每题独立启动程序；包含权重加载、tokenizer 通信、生成和退出，不是纯推理耗时。 |

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_internvl_3_1b_448_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/run_internvl_3_1b_448_axcl_x86.sh) | 启动或构建脚本 |
| [`internvl3_tokenizer.py`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_tokenizer.py) | 旧版分词服务入口 |
| [`internvl3_1b_ax650/internvl3_1b_vit.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_1b_ax650/internvl3_1b_vit.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_1b_ax650/qwen2_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_1b_ax650/qwen2_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_1b_ax650/qwen2_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_1b_ax650/qwen2_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_1b_ax650/qwen2_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_1b_ax650/qwen2_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`internvl3_1b_ax650/qwen2_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_1b_ax650/qwen2_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/config.json) | 运行配置 |
| [`internvl3_tokenizer/config.json`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_tokenizer/config.json) | 运行配置 |
| [`internvl3_tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_tokenizer/generation_config.json) | 运行配置 |
| [`internvl3_tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_tokenizer/preprocessor_config.json) | 运行配置 |
| [`internvl3_tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_tokenizer/tokenizer_config.json) | 运行配置 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/post_config.json) | 运行配置 |
| [`run_internvl_3_1b_448_api_ax650.sh`](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/run_internvl_3_1b_448_api_ax650.sh) | 启动或构建脚本 |

仓库提交：`797dd3d7676d1900815a53906c72015e172bbad1`。仓库中的 26 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/InternVL3-1B/tree/797dd3d7676d1900815a53906c72015e172bbad1)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 旧 AXCL 脚本含 devices=0,2,4 多设备示例和 tokenizer 地址。单卡部署需改成实际设备并保留相同分词器协议。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/InternVL3-1B/tree/797dd3d7676d1900815a53906c72015e172bbad1)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/README.md)。
- [主要程序入口：internvl3_tokenizer.py](https://huggingface.co/AXERA-TECH/InternVL3-1B/blob/797dd3d7676d1900815a53906c72015e172bbad1/internvl3_tokenizer.py)。
- [配套项目：AXERA-TECH/InternVL3-2B.axera](https://github.com/AXERA-TECH/InternVL3-2B.axera/tree/master/model_convert)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/ax-internvl)。
- [配套项目：AXERA-TECH/ax-llm](https://github.com/AXERA-TECH/ax-llm/tree/axcl-internvl)。

返回[完整模型目录](../catalog.mdx)。
