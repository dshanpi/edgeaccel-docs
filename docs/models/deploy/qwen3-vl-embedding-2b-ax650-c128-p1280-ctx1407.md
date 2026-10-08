---
title: "Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 部署指南"
sidebar_label: "Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407"
description: "Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 部署指南

Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 用于文本或图像向量。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。

## 下载模型与样例

本页使用 `AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407` 的固定版本。下面下载本页选用的 33 个文件。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407/97ecf827ecfc
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407 \
  --include "*.axmodel" "config.json" "model.embed_tokens.weight.bfloat16.bin" "qwen3_tokenizer.txt" \
  --revision 97ecf827ecfc3b07d35b74b852981d3415d14a1a \
  --local-dir "$MODEL_DIR"
cd "$MODEL_DIR"
```

保留当前终端中的 `MODEL_DIR` 变量，后续命令沿用此目录。下载受阻或需要离线复制时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备图文检索运行程序

本例在 RK3576 主机通过 AXCL 使用 AX8850 16GB M.2 算力卡，将图片和文本转换成 2048 维向量，再用余弦相似度检索图片。使用 Linux ARM64、AXCL 3.16.0，以及本页固定版本的 2B 权重。

下载[配套运行包](/examples/qwen3-vl-embedding-20261001.tar.gz)，保存到主机的 `~/edgeaccel`。包内包含运行程序、固定源码与适配文件、三张样图、检索示例和模型校验工具。保留前文下载模型后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3-vl-embedding-20261001.tar.gz
sudo apt-get install -y libopencv-dev
chmod +x qwen3-vl-embedding/bin/axllm
ldd qwen3-vl-embedding/bin/axllm
python3 qwen3-vl-embedding/verify_models.py --model-dir "$MODEL_DIR"
```

`ldd` 应找到全部动态库，模型校验应输出 `Verified 33 model files`。模型及配套文件约 3.3 GB，可把 `MODEL_DIR` 指向已挂载的存储卡。运行程序基于官方 AX-LLM 提交 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`，包含 AXCL 设备与两组形状 K/V 缓冲区适配。

## 启动图文向量服务

```bash
cd ~/edgeaccel
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ./qwen3-vl-embedding/bin/axllm serve "$MODEL_DIR" --port 3611
```

保持该终端运行。在 RK3576 的另一个终端检查接口：

```bash
curl --noproxy '*' --fail http://127.0.0.1:3611/health
curl --noproxy '*' --fail http://127.0.0.1:3611/v1/models
```

模型列表应包含 `AXERA-TECH/Qwen3-VL-Embedding-2B`。首次启动需要加载模型；出现服务就绪信息后再发送请求。使用结束后，在服务终端按 `Ctrl+C` 释放模型。

## 运行中英文图片检索

以下命令在运行服务的同一台 RK3576 上执行。图片路径由服务端读取，应使用主机上存在的文件。

```bash
cd ~/edgeaccel
python3 qwen3-vl-embedding/retrieval_demo.py \
  --images "$HOME/edgeaccel/qwen3-vl-embedding/images" \
  --api http://127.0.0.1:3611 \
  --output "$HOME/edgeaccel/results/qwen3-vl-embedding/retrieval-result.json"
```

程序依次编码鸟、猫、狗三张图片，再发送 `a bird`、`a cat`、`a dog`、`一只鸟`、`一只猫`、`一只狗` 六个查询。终端按相似度从高到低列出图片，JSON 保存原始输入、2048 维向量、请求耗时和排序。

该示例使用 `messages` 接口，每次编码一个输入，统一指令为 `Represent the user's input.`。分词器使用仓库内的 `qwen3_tokenizer.txt`；运行程序在序列末尾添加 EOS，取最后一个位置的特征并作 L2 归一化。余弦相似度用于比较相关性，不是分类概率。

使用自己的图片时，修改示例中的图片文件名与查询文本，保持图片和文本的指令一致。图文联合输入可在同一条用户消息的 `content` 中同时放入 `image_url` 和 `text`。同一图片的后续请求可能使用视觉特征缓存，不能直接与首次编码耗时比较。

<details>
<summary>重新编译运行程序</summary>

若系统动态库与预编译程序不匹配，使用包内固定源码重新编译：

```bash
sudo apt-get install -y build-essential cmake libopencv-dev
cd ~/edgeaccel/qwen3-vl-embedding
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

已在 16GB M.2 算力卡运行 Qwen3-VL-Embedding 2B 图文向量服务，完成中英文图片检索。

**中英文图文检索**

六个中英文查询均将对应图片排在第一位，图片反查文本的首选也匹配。图片和文本各重复两次，返回向量逐元素一致。分数为余弦相似度，不是分类概率。

<div className="model-effect-gallery">

<figure>

[![输入图片：鸟](../../../static/validation/effects/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407-20261001/bird.jpg)](../../../static/validation/effects/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407-20261001/bird.jpg)

<figcaption>输入图片：鸟</figcaption>
</figure>

<figure>

[![输入图片：猫](../../../static/validation/effects/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407-20261001/cat.jpg)](../../../static/validation/effects/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407-20261001/cat.jpg)

<figcaption>输入图片：猫</figcaption>
</figure>

<figure>

[![输入图片：狗](../../../static/validation/effects/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407-20261001/dog-chai.jpeg)](../../../static/validation/effects/qwen3-vl-embedding-2b-ax650-c128-p1280-ctx1407-20261001/dog-chai.jpeg)

<figcaption>输入图片：狗</figcaption>
</figure>

</div>

| 语言 | 查询 | 鸟图片 | 猫图片 | 狗图片 | 首选图片 |
| --- | --- | --- | --- | --- | --- |
| en | a bird | 0.3660 | 0.2537 | 0.1711 | 鸟 |
| en | a cat | 0.2070 | 0.3996 | 0.2427 | 猫 |
| en | a dog | 0.2076 | 0.2863 | 0.3621 | 狗 |
| zh | 一只鸟 | 0.3242 | 0.2558 | 0.1601 | 鸟 |
| zh | 一只猫 | 0.1943 | 0.3770 | 0.2272 | 猫 |
| zh | 一只狗 | 0.1919 | 0.2781 | 0.3068 | 狗 |

| 检查项 | 本次结果 |
| --- | --- |
| 接口请求 | 21 次成功，含 3 次图文联合输入 |
| 向量输出 | 2048 维，有限数值，L2 范数约 1 |
| 算力卡执行 | 30 个 AXModel / 864 次调用 |
| 服务启动 | 120.827 s |
| 完整流程 | 359.175 s（含文件校验） |

**使用时注意：**

- 本次仅验证固定 2B 权重在 16GB 卡上的基本运行；真实 8GB、多用户并发和长期稳定性尚未验证。
- 三张样图用于演示检索流程，不能代表大规模数据集精度；图文联合输入仅核对输出，未做人工相关性评估。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`97ecf827ecfc3b07d35b74b852981d3415d14a1a`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | AX-LLM a51df2d + AXCL 设备与 K/V 缓冲区适配 / 原生 HTTP 图文向量接口 / AXCL C API |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输出向量 | 2048 维 | 图片、文本和图文联合输入均返回有限且归一化的向量。 |
| 实测接口 | 21 次请求 | 三张图片、中英文描述与图文联合输入；图片和文本各重复两次。 |
| 算力卡执行 | 30 个 AXModel | 视觉编码器、28 个文本层和输出层均有实际调用记录。 |

适用范围：

- 请求统一使用单输入 messages 接口；批量 input、视频和长文本未验证。
- 重复图片可命中视觉特征缓存；完整耗时包含加载、校验和记录，不代表在线单次延迟。
- 已核对最终向量及原生调用返回码，未捕获全部中间张量，未与浮点参考模型比较精度。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`config.json`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/config.json) | 运行配置 |
| [`qwen3_vl_text_post.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_post.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`model.embed_tokens.weight.bfloat16.bin`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/model.embed_tokens.weight.bfloat16.bin) | Embedding 权重 |
| [`qwen3_tokenizer.txt`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_tokenizer.txt) | 分词器 / 字典，必须配套 |
| [`Qwen3-VL-Embedding-2B_vision_384x384.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/Qwen3-VL-Embedding-2B_vision_384x384.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`qwen3_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/blob/97ecf827ecfc3b07d35b74b852981d3415d14a1a/qwen3_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |

仓库提交：`97ecf827ecfc3b07d35b74b852981d3415d14a1a`。仓库中的 30 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/tree/97ecf827ecfc3b07d35b74b852981d3415d14a1a)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 名称中的编译规格用于区分上下文与分块版本；不要仅修改 config.json 就视为扩大模型支持的上下文。
- 此提交没有 README.md。已核对文件清单；运行参数和验收数据不能仅根据仓库名称补写。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407/tree/97ecf827ecfc3b07d35b74b852981d3415d14a1a)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Qwen3-VL-Embedding-2B-AX650-C128_P1280_CTX1407)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
