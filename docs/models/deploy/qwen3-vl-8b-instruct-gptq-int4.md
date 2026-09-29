---
title: "Qwen3-VL-8B-Instruct-GPTQ-Int4 部署指南"
sidebar_label: "Qwen3-VL-8B-Instruct-GPTQ-Int4"
description: "Qwen3-VL-8B-Instruct-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-8B-Instruct-GPTQ-Int4 部署指南

Qwen3-VL-8B-Instruct-GPTQ-Int4 用于图像与文本理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4` 的固定版本。下面下载本页选用的 76 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-8b-instruct-gptq-int4/e9e73ad656bd
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4 \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/Qwen3-VL-8B-Instruct_vision.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/model.embed_tokens.weight.bfloat16.bin" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l0_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l10_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l11_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l12_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l13_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l14_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l15_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l16_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l17_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l18_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l19_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l1_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l20_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l21_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l22_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l23_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l24_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l25_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l26_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l27_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l28_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l29_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l2_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l30_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l31_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l32_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l33_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l34_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l35_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l3_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l4_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l5_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l6_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l7_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l8_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l9_together.axmodel" \
  "Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_post.axmodel" \
  "README.md" \
  "images/demo.jpg" \
  "images/demo1.jpg" \
  "images/demo_720p.jpg" \
  "images/recoAll_attractions_1.jpg" \
  "images/recoAll_attractions_2.jpg" \
  "images/recoAll_attractions_3.jpg" \
  "images/recoAll_attractions_4.jpg" \
  "images/ssd_car.jpg" \
  "images/ssd_horse.jpg" \
  "main_axcl_aarch64" \
  "post_config.json" \
  "qwen3-vl-tokenizer/README.md" \
  "qwen3-vl-tokenizer/chat_template.json" \
  "qwen3-vl-tokenizer/config.json" \
  "qwen3-vl-tokenizer/configuration.json" \
  "qwen3-vl-tokenizer/generation_config.json" \
  "qwen3-vl-tokenizer/merges.txt" \
  "qwen3-vl-tokenizer/model.safetensors.index.json" \
  "qwen3-vl-tokenizer/preprocessor_config.json" \
  "qwen3-vl-tokenizer/tokenizer.json" \
  "qwen3-vl-tokenizer/tokenizer_config.json" \
  "qwen3-vl-tokenizer/video_preprocessor_config.json" \
  "qwen3-vl-tokenizer/vocab.json" \
  "requirements.txt" \
  "run_image_axcl_aarch64.sh" \
  "run_video_axcl_aarch64.sh" \
  "tokenizer_images.py" \
  "tokenizer_video.py" \
  "video/frame_0000.jpg" \
  "video/frame_0008.jpg" \
  "video/frame_0016.jpg" \
  "video/frame_0024.jpg" \
  "video/frame_0032.jpg" \
  "video/frame_0040.jpg" \
  "video/frame_0048.jpg" \
  "video/frame_0056.jpg" \
  --revision e9e73ad656bd299aedd92c9dad85cf0b308c77fd \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 编译配套 ARM64 程序

本页使用 RK3576、AX8850 **16GB** 和 AXCL 3.16。模型包的预编译程序依赖 OpenCV 4.10；RK3576 的 OpenCV 4.6 环境使用下列固定源码编译。程序采用 AXCL 后端与本地 C++ 分词器。

在 RK3576 主机执行，保留上文的 `MODEL_DIR`：

```bash
sudo apt install -y git build-essential cmake libopencv-dev python3-venv
SOURCE_DIR=~/edgeaccel/src/qwen3-vl-axcl-3be4cc3f
git clone --branch axcl-qwen3-vl --single-branch \
  https://github.com/AXERA-TECH/ax-llm.git "$SOURCE_DIR"
git -C "$SOURCE_DIR" checkout 3be4cc3fee4a4c730ec7c9b8982ff4b398eefac7
git -C "$SOURCE_DIR" submodule update --init --recursive

cmake -S "$SOURCE_DIR" -B "$SOURCE_DIR/build" \
  -DCMAKE_BUILD_TYPE=Release -DTOKENIZER_BUILD_TESTS=OFF \
  -DOpenCV_DIR=/usr/lib/aarch64-linux-gnu/cmake/opencv4
cmake --build "$SOURCE_DIR/build" --target main --parallel 2
ldd "$SOURCE_DIR/build/main"
"$SOURCE_DIR/build/main" --help
```

使用尚不存在的源码目录。依赖检查中不能出现 `not found`；帮助信息应包含 `--devices` 和 `--video`。本页固定的 tokenizer 子模块提交为 `0eed4120c6e1b5ea1e51b51c576924faddc8b2a1`，不另行切换分支。

## 导出分词表并生成启动脚本

创建独立 Python 环境，用本包的分词文件导出 C++ 词表。Python 仅用于导出，后续运行不需要分词服务。

```bash
python3 -m venv ~/edgeaccel/qwen3-vl-env
PYTHON=~/edgeaccel/qwen3-vl-env/bin/python
"$PYTHON" -m pip install 'transformers==4.51.3' 'tokenizers==0.21.4'

TOKENIZER=~/edgeaccel/qwen3-vl-8b-tokenizer.txt
"$PYTHON" "$SOURCE_DIR/third_party/tokenizer.axera/tests/convert_tokenizer.py" \
  --tokenizer_path "$MODEL_DIR/qwen3-vl-tokenizer" \
  --dst_path "$TOKENIZER"
sha256sum "$TOKENIZER"
```

本次导出词表的 SHA256 为 `7119de4966cc6a8ae87d7f083e65b315282d06c3122fdd41ce783fdd2d3c1ca2`。这里读取本包的 Qwen2 分词文件，不使用 Python 加载 Qwen3-VL 网络权重。

下载[启动配置脚本](../../../static/examples/qwenvl8_prepare.py)，保存为 `~/edgeaccel/qwenvl8_prepare.py`。选择尚不存在的运行目录：

```bash
RUNTIME_DIR=~/edgeaccel/runtime/qwenvl8-int4-e9e73ad6
python3 ~/edgeaccel/qwenvl8_prepare.py \
  --model-dir "$MODEL_DIR" \
  --binary "$SOURCE_DIR/build/main" \
  --tokenizer "$TOKENIZER" \
  --output "$RUNTIME_DIR"
```

脚本配置 36 个语言分片、384×384 视觉编码器、4096 维词向量、设备 0 和 `top_k=1`，并启用 embedding 的 mmap 加载。运行目录链接原模型文件，保留模型、源码编译目录和分词表即可继续使用。

## 运行图片问答

```bash
bash "$RUNTIME_DIR/run_image.sh"
```

等待出现 `prompt >>`，依次输入问题和图片路径。程序在完整回答生成后显示文字：

```text
prompt >> 请用一句中文说出图片前景中的两种动物。
image >> images/ssd_horse.jpg
```

可继续输入下面的问题，检查人物计数；每次都填写对应图片路径：

```text
prompt >> 画面中有几个人清晰可见？只回答人数。
image >> images/ssd_horse.jpg
```

街景示例使用 `images/ssd_car.jpg` 和问题 `请用一句中文描述图片中的主要内容。`。文件名虽含 `car`，图片同时包含公交车、汽车和前景人物，应按实际画面核对回答。

在 `prompt >>` 输入 `q` 退出。确认 `axcl-smi` 中本次进程已释放，再启动视频模式。

## 运行视频帧问答

```bash
bash "$RUNTIME_DIR/run_video.sh"
```

输入简短问题及官方示例帧目录：

```text
prompt >> 请用两句中文描述这些视频帧中动物的动作。
video >> video
```

`video` 是包含 8 张 JPEG 的目录，程序按文件名排序后读取；此入口不直接接收 MP4 或 RTSP，也不处理音频。使用自己的视频时，先安装 `ffmpeg` 并抽帧，输出目录只存本次帧：

```bash
sudo apt install -y ffmpeg
INPUT_VIDEO="$HOME/Videos/example.mp4"
FRAME_DIR=~/edgeaccel/inputs/example-frames
mkdir -p "$(dirname "$FRAME_DIR")"
mkdir "$FRAME_DIR"
ffmpeg -i "$INPUT_VIDEO" -vf fps=1 -frames:v 8 \
  "$FRAME_DIR/frame_%04d.jpg"
```

将 `video >>` 的输入替换为帧目录的绝对路径。默认按每秒 1 帧配置时间位置；抽帧问答不能视为实时视频分析。先限制为 8 帧和短问题，不按原始模型的长上下文规格增加输入。


## 查看部署效果

**已运行，效果仍需评估** · 2026-09-28 · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

两张官方图片与八张视频帧完成七次问答：动物识别、人数问答及重复输出已核对；街景扩展描述和视频细节按下方说明限定，不作为完整精度评测。

点击图片可查看原尺寸。

<div className="model-effect-gallery">

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/images/ssd_horse.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/images/ssd_horse.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/images/ssd_car.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/images/ssd_car.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0000.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0000.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0008.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0008.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0016.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0016.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0024.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0024.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0032.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0032.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0040.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0040.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0048.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0048.jpg)

<figcaption>输入图片</figcaption>
</figure>

<figure>

[![输入图片](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0056.jpg)](../../../static/validation/effects/qwen3-vl-8b-instruct-gptq-int4-20260928/video/frame_0056.jpg)

<figcaption>输入图片</figcaption>
</figure>

</div>

**示例 1：输入**

```text
图片：images/ssd_horse.jpg
问题：请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
前景中有一匹马和一只狗。
```

前景中可见一匹马和一只狗，动物名称与画面一致。

**示例 2：输入**

```text
图片：images/ssd_horse.jpg
问题：Name the two animals in the foreground. Reply in one sentence.
```

**实际回复**

```text
A man is riding a brown horse while a brown dog sits on the ground nearby.
```

识别出马、狗及骑乘关系；本次仅核对这些可见内容，不将人物性别当作验证项。

**示例 3：输入**

```text
图片：images/ssd_horse.jpg
问题：画面中有几个人清晰可见？只回答人数。
```

**实际回复**

```text
2
```

回答为 2，与骑马者和右侧红衣人物这两名清晰人物一致。

**示例 4：输入**

```text
图片：images/ssd_car.jpg
问题：请用一句中文描述图片中的主要内容。
```

**实际回复**

```text
一位女士站在伦敦街头，身后是一辆经典的红色双层巴士，巴士上印有广告语“当你说‘是’时，事情就变得更好了”。
```

正确识别红色双层巴士及其前方人物。画面不能独立确认具体城市；广告的“more exciting”译为“更好了”不够准确，不作为地点或精确 OCR 翻译通过。

**示例 5：输入**

```text
图片：images/ssd_horse.jpg
问题：请用一句中文说出图片前景中的两种动物。
```

**实际回复**

```text
前景中有一匹马和一只狗。
```

切换图片并重新加载进程后，回复与首测“前景中有一匹马和一只狗。”逐字相同。

**示例 6：输入**

```text
视频帧：video/（8 帧，按文件名排序）
问题：请用两句中文描述这些视频帧中动物的动作。
```

**实际回复**

```text
几只松鼠在山间草地上活泼地追逐嬉戏，前爪互相抓握，姿态灵动。它们或跳跃或对视，展现出在自然环境中无忧无虑的天性。
```

片段可见两只动物抬起前爪、互相接触、转身和扑向对方。回复中的“追逐”“无忧无虑的天性”缺少画面依据，“几只松鼠”也未准确限定数量与物种；中文细节未通过。

**示例 7：输入**

```text
视频帧：video/（8 帧，按文件名排序）
问题：Describe what the two animals are doing in these video frames. Use two sentences.
```

**实际回复**

```text
The two marmots are engaged in a playful, almost dance-like interaction, with their paws raised and bodies leaning toward each other. Their synchronized movements and focused gazes suggest a spirited game or social bonding ritual.
```

英文正确描述两只动物抬爪、身体靠近的可见动作；“社交联结仪式”等动机解释无法从帧序列确定，不作行为学或物种识别结论。

**使用时注意：**

- 仅测试两张静态图片、一个八帧片段和一次跨进程重复；未测试长视频、实时摄像头、复杂 OCR、多轮历史或并发。
- 地点、人物身份、精确广告翻译和动物物种没有独立标注，不据自由描述宣称这些能力通过；逐题观察见实际回复。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。日期：2026-09-28。模型版本：`e9e73ad656bd299aedd92c9dad85cf0b308c77fd`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行时 | AX-LLM 3be4cc3f，原样编译 AXCL ARM64，OpenCV 4.6.0，GCC 13.3 |
| 分词器 | tokenizer.axera 0eed4120；同包词表由 Transformers 4.51.3 导出 |
| 模型与输入 | 36 层，4096 维词向量，W4A16；图像 384×384，视频使用 8 帧 |
| 采样与加载 | top_k=1，其余采样关闭；mmap embedding；设备 0；完整生成后显示文字 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 单图首测模式加载至可提问 | 144.691 s | 包含词表、36 个语言分片与视觉编码器加载；独立于单次问答耗时。 |
| 图片复测模式加载至可提问 | 145.512 s | 包含词表、36 个语言分片与视觉编码器加载；独立于单次问答耗时。 |
| 视频帧模式加载至可提问 | 145.400 s | 包含词表、36 个语言分片与视觉编码器加载；独立于单次问答耗时。 |
| 请求 1 完整回复 / 图像编码 / 语言 TTFT | 6.974 s / 320.3 ms / 2111.9 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |
| 请求 2 完整回复 / 图像编码 / 语言 TTFT | 10.265 s / 323.3 ms / 2021.8 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |
| 请求 3 完整回复 / 图像编码 / 语言 TTFT | 3.507 s / 335.3 ms / 2018.6 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |
| 请求 4 完整回复 / 图像编码 / 语言 TTFT | 18.112 s / 378.1 ms / 2300.2 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |
| 请求 5 完整回复 / 图像编码 / 语言 TTFT | 6.908 s / 335.8 ms / 2011.5 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |
| 请求 6 完整回复 / 图像编码 / 语言 TTFT | 24.228 s / 1400.5 ms / 5528.8 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |
| 请求 7 完整回复 / 图像编码 / 语言 TTFT | 24.456 s / 1357.6 ms / 5311.5 ms | 完整回复为主机墙钟、包含前后处理；编码和 TTFT 来自程序分别计时，均不是独立芯片峰值性能。 |

适用范围：

- 仅测试两张静态图片、一个八帧片段和一次跨进程重复；未测试长视频、实时摄像头、复杂 OCR、多轮历史或并发。
- 地点、人物身份、精确广告翻译和动物物种没有独立标注，不据自由描述宣称这些能力通过；逐题观察见实际回复。
- 本次未导出逐层原始张量，不作全张量有限性或数值精度结论。
- 使用 16GB 算力卡；没有据本次结果推定 8GB 可以运行。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/run_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`tokenizer_images.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/tokenizer_images.py) | 旧版分词服务入口 |
| [`tokenizer_video.py`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/tokenizer_video.py) | 旧版分词服务入口 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/Qwen3-VL-8B-Instruct_vision.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/Qwen3-VL-8B-Instruct_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/Qwen3-VL-8B-Instruct-AX650-c128_p1152-int4/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/config.json) | 运行配置 |
| [`images/demo.jpg`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/images/demo.jpg) | 示例输入 |
| [`post_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/post_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/qwen3-vl-tokenizer/config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/generation_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/qwen3-vl-tokenizer/generation_config.json) | 运行配置 |
| [`qwen3-vl-tokenizer/preprocessor_config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/qwen3-vl-tokenizer/preprocessor_config.json) | 运行配置 |

仓库提交：`e9e73ad656bd299aedd92c9dad85cf0b308c77fd`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/tree/e9e73ad656bd299aedd92c9dad85cf0b308c77fd)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/tree/e9e73ad656bd299aedd92c9dad85cf0b308c77fd)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/README.md)。
- [主要程序入口：tokenizer_images.py](https://huggingface.co/AXERA-TECH/Qwen3-VL-8B-Instruct-GPTQ-Int4/blob/e9e73ad656bd299aedd92c9dad85cf0b308c77fd/tokenizer_images.py)。
- [配套项目：AXERA-TECH/Qwen3-VL.AXERA](https://github.com/AXERA-TECH/Qwen3-VL.AXERA)。

返回[完整模型目录](../catalog.mdx)。
