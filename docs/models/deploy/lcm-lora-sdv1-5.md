---
title: "lcm-lora-sdv1-5 部署指南"
sidebar_label: "lcm-lora-sdv1-5"
description: "lcm-lora-sdv1-5 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# lcm-lora-sdv1-5 部署指南

lcm-lora-sdv1-5 用于图像生成。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/lcm-lora-sdv1-5` 的固定版本。下面下载本页选用的 18 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/lcm-lora-sdv1-5/4ba40db7f8fd
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/lcm-lora-sdv1-5 \
  --include "models/*" "Disclaimer.md" "LICENSE" "README.md" "config.json" "launcher.py" "requirements.txt" \
  --revision 4ba40db7f8fddbf3e4f86edacf7fb255bb45d339 \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 安装图像生成依赖

本例使用 RK3576 + AX8850 **16GB M.2 算力卡**，调用固定版本仓库的 `launcher.py`，通过 `AXCLRTExecutionProvider` 执行文本编码、去噪和图像解码。本页验证范围为 512×512 文生图和图生图。模型文件约 1.23GB，首次安装 Python 依赖还需额外预留空间。

激活已安装 [PyAXEngine](../../usage/python.md) 的主机虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'torch==2.5.1' 'transformers==4.51.3' \
  'diffusers==0.35.2' 'numpy==1.26.4' 'Pillow==11.3.0' \
  'onnxruntime==1.20.1'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。这组版本已在本次环境实测；无需安装原仓库用于转换、训练的全部依赖。

下载[算力卡运行脚本](../../../static/examples/lcm_card.py)，保存为 `~/edgeaccel/lcm_card.py`；下载[固定文件校验清单](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/download-manifest.json)，保存为 `$MODEL_DIR/download-manifest.json`。若在 Windows 浏览器下载，将这两个文件复制到 Linux 主机的对应位置。

本页下载 `models/` 目录的 512×512 权重。输出目录须尚不存在。

## 输入文字生成图片

沿用下载步骤设置的 `MODEL_DIR`，在同一主机终端执行：

```bash
python ~/edgeaccel/lcm_card.py \
  --model-dir "$MODEL_DIR" --variant 512 \
  --prompt 'a cat wearing sunglasses' --seed 0 \
  --output ~/edgeaccel/results/lcm-cat-01
```

运行成功后，`lcm-cat-01/output.png` 为本次生成图片，`deployment-result.json` 中 `completed` 为 `true`。文生图使用官方固定的 4 步时间序列 `[999, 759, 499, 259]`。

更换提示词和输出目录即可生成其他画面，例如：

```bash
python ~/edgeaccel/lcm_card.py \
  --model-dir "$MODEL_DIR" --variant 512 \
  --prompt 'a peaceful mountain lake at sunrise, pine trees, reflection in the water, landscape photography' \
  --seed 0 --output ~/edgeaccel/results/lcm-lake-01
```

本例验证的是英文短提示词。入口按模型 tokenizer 检查长度，超过 77 个 token 时停止执行；修改为更短的提示词后重新运行。

## 使用输入图片生成新画面

使用上方已下载的 `models/` 权重及官方输入样例：

```bash
python ~/edgeaccel/lcm_card.py \
  --model-dir "$MODEL_DIR" --variant 512 \
  --init-image "$MODEL_DIR/models/img2img-init.png" \
  --prompt 'Astronauts in a jungle, cold color palette, muted colors, detailed, 8k' \
  --seed 0 --output ~/edgeaccel/results/lcm-img2img-01
```

输入会转为 RGB 并缩放到 512×512，使用官方 2 步时间序列 `[499, 259]`。查看 `output.png` 和 `output_grid.png`，后者从左到右显示输入图与生成图。提示词中的 `8k` 是文字描述，本例实际输出仍为 512×512。

## 检查生成结果

```bash
python - <<'PY'
import json
from pathlib import Path
r = json.loads(Path.home().joinpath(
    'edgeaccel/results/lcm-cat-01/deployment-result.json').read_text())
assert r['completed']
assert all(s['providerActual'] == 'AXCLRTExecutionProvider' for s in r['sessions'])
print('输出尺寸：', r['width'], 'x', r['height'])
print('算力卡调用合计：', round(r['npuCallTotalMilliseconds'], 2), 'ms')
print('生成流程：', round(r['pipelineSecondsIncludingLoadAndHash'], 2), 's')
PY
```

算力卡调用合计包含输入输出传输及各次 `run()` 的执行时间；生成流程另含权重校验、模型加载和图片保存，不包含 Python 启动及依赖导入。两者均不代表常驻服务的吞吐率。

相同输入、种子、版本和运行环境用于复现；更换依赖或运行平台后应重新核对。生成图片仍可能出现手部、细节或构图偏差，下方保留实际输出。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成 512×512 文生图与图生图，以下展示本次真实生成图片。

**512×512 文生图：戴墨镜的猫**

提示词：`a cat wearing sunglasses`。随机种子为 0，4 步。画面为佩戴深色圆形墨镜的灰白猫，主体与提示词一致。

<div className="model-effect-gallery">

<figure>

[![本次算力卡生成结果](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-cat512-a.png)](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-cat512-a.png)

<figcaption>本次算力卡生成结果</figcaption>
</figure>

</div>

| 实际输出 | 算力卡调用合计 | 生成流程（含校验与加载） |
| --- | --- | --- |
| 512×512 | 2.685 s | 25.333 s |

**512×512 文生图：山湖风景**

提示词：`a peaceful mountain lake at sunrise, pine trees, reflection in the water, landscape photography`。随机种子为 0，4 步。可见山峰、松林、晨光和水面倒影。

<div className="model-effect-gallery">

<figure>

[![本次算力卡生成结果](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-lake512-a.png)](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-lake512-a.png)

<figcaption>本次算力卡生成结果</figcaption>
</figure>

</div>

| 实际输出 | 算力卡调用合计 | 生成流程（含校验与加载） |
| --- | --- | --- |
| 512×512 | 2.703 s | 25.218 s |

**512×512 图生图：宇航员与丛林**

提示词：`Astronauts in a jungle, cold color palette, muted colors, detailed, 8k`。随机种子为 0，2 步。保留三个宇航员的大致布局，加入丛林植被；手部和服装细节仍带有生成画面的变形。

<div className="model-effect-gallery">

<figure>

[![输入：官方宇航员摆件样例](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-img512-a-input.png)](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-img512-a-input.png)

<figcaption>输入：官方宇航员摆件样例</figcaption>
</figure>

<figure>

[![本次算力卡生成结果](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-img512-a.png)](../../../static/validation/effects/lcm-lora-sdv1-5-20260930/lcm-img512-a.png)

<figcaption>本次算力卡生成结果</figcaption>
</figure>

</div>

| 实际输出 | 算力卡调用合计 | 生成流程（含校验与加载） |
| --- | --- | --- |
| 512×512 | 2.275 s | 26.225 s |

**固定种子复现**

512×512 的猫图片以相同提示词和种子 0 在两个独立进程中生成，6 次模型调用的输出张量和最终图片像素均逐字节一致。保持种子 0、改为山湖提示词后，初始噪声相同，生成结果随提示词变化。此检查仅覆盖当前版本与样例。

**使用时注意：**

- 本次为 16GB 卡的短样例部署验证，未完成真实 8GB 容量、并发和长时间稳定性回归。
- 英文短提示词、固定种子与步数；未评估中文、文字渲染、复杂构图或数据集级生成质量。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`4ba40db7f8fddbf3e4f86edacf7fb255bb45d339`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| Python 推理 | Python 3.12 / PyAXEngine 0.1.3.rc3 / NumPy 1.26.4 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 生成规格 | 512×512 | 文生图 4 步；图生图仅 512×512、2 步。 |
| 编译权重 | 512×512 所需 4 个子模型实际执行 | 文本编码器、UNet、VAE 编码器和解码器。 |
| 基本验证 | 4 次生成 / 23 次算力卡调用 | 含一次 512×512 同种子独立进程复现。 |

适用范围：

- 1024×768 的完整生成尚未验证通过，不在本页已验证范围内。
- 算力卡调用计时含 run() 和传输；生成流程另含校验及加载，不代表常驻服务吞吐。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`launcher.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/launcher.py) | Python 程序 / 前后处理 |
| [`models/text_encoder/sd15_text_encoder_sim.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/text_encoder/sd15_text_encoder_sim.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/unet.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/unet.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/vae_decoder.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/vae_decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models/vae_encoder.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/vae_encoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`models_1024x768/text_encoder/sd15_text_encoder_sim.axmodel`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models_1024x768/text_encoder/sd15_text_encoder_sim.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`assets/gradio_demo.png`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/assets/gradio_demo.png) | 示例输入 |
| [`config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/config.json) | 运行配置 |
| [`models/text_encoder/config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/text_encoder/config.json) | 运行配置 |
| [`models/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models/tokenizer/tokenizer_config.json) | 运行配置 |
| [`models_1024x768/text_encoder/config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models_1024x768/text_encoder/config.json) | 运行配置 |
| [`models_1024x768/tokenizer/tokenizer_config.json`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/models_1024x768/tokenizer/tokenizer_config.json) | 运行配置 |
| [`requirements.txt`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/requirements.txt) | Python 依赖清单 |
| [`run_img2img_axe_infer.py`](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/run_img2img_axe_infer.py) | Python 程序 / 前后处理 |

仓库提交：`4ba40db7f8fddbf3e4f86edacf7fb255bb45d339`。仓库中的 7 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/tree/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 文本编码器、去噪网络和 VAE 需要同一套分辨率规格。512×512 与 1024×768 编译包分别部署；固定随机种子比较输出。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/tree/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/README.md)。
- [主要程序入口：launcher.py](https://huggingface.co/AXERA-TECH/lcm-lora-sdv1-5/blob/4ba40db7f8fddbf3e4f86edacf7fb255bb45d339/launcher.py)。

返回[完整模型目录](../catalog.mdx)。
