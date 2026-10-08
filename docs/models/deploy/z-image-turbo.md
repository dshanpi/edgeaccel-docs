---
title: "Z-Image-Turbo 部署指南"
sidebar_label: "Z-Image-Turbo"
description: "Z-Image-Turbo 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Z-Image-Turbo 部署指南

Z-Image-Turbo 用于文本生成图片。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[安装 PyAXEngine](../../usage/python.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 准备出图示例

本例在 RK3576 + AX8850 16GB M.2 算力卡上运行，使用 Python 3.12、AXCL 3.16.0 和 PyAXEngine 0.1.3.rc3。输入为两条固定的中英文提示词，输出为 512×512 图片。8GB 卡尚未完成本模型的回归验证。

下载[配套示例包](/examples/zimage-axcl-example-20261003.tar.gz)，保存到连接算力卡的 RK3576 主机 `~/edgeaccel/`。在主机终端校验并解压：

```bash
cd ~/edgeaccel
echo '863c6151e25f4683c31ce0d080e0190f860a43cf4f54afc4c7be1a450fdae8f3  zimage-axcl-example-20261003.tar.gz' | sha256sum -c -
tar -xzf zimage-axcl-example-20261003.tar.gz
cd zimage-axcl-example
```

校验应输出 `OK`。按 [Python 接口](../../usage/python.md#安装已核对的-pyaxengine-版本)下载并校验官方 wheel，保存到 `~/axcl-setup`，然后创建独立环境：

```bash
python3 -m venv ~/edgeaccel/zimage-env
source ~/edgeaccel/zimage-env/bin/activate
python -m pip install \
  ~/axcl-setup/axengine-0.1.3-py3-none-any.whl \
  -r requirements.txt 'opencv-python-headless==4.11.0.86'
python -m pip check
export PATH=/usr/bin/axcl:$PATH
axcl-smi
```

确认依赖无冲突，设备 0 可用且没有其他推理任务。示例明确选择 `AXCLRTExecutionProvider`，固定使用 `diffusers==0.32.1`，不要直接升级其他模型共用的 Python 环境。

## 下载模型文件

模型目录需要存放 102 个文件，约 11.65 GiB；建议至少预留 15 GiB。板载空间不足时，将 `MODEL_DIR` 改为已挂载的存储卡或 SSD 目录。

```bash
MODEL_DIR=~/edgeaccel/models/z-image-turbo/117d8586d5c5
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
python download_models.py --model-dir "$MODEL_DIR"
```

程序从官方仓库下载固定提交 `117d8586d5c50de6f4c6e0a7058e934c207407be`，逐一核对 SHA256。结束时应输出 `Verified 102 model files`。无需下载仅供 CPU 参考计算的三份 safetensors 权重。需要代理时，先在当前终端设置实际可用的 `http_proxy` 和 `https_proxy`，方法见[模型下载](../../usage/download-models.md)。

## 运行中英文出图

先检查示例包、依赖和模型文件。此命令不启动推理：

```bash
python run_examples.py --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/zimage-example --check-only
```

确认 `verifiedModelFiles` 为 `102` 后运行：

```bash
python run_examples.py --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/zimage-example
```

输出目录必须为新目录。程序依次执行文本编码、9 步去噪和 VAE 解码，使用随包提供的 seed 42 初始噪声。每次加载一个子模型，执行后释放其设备资源。去噪使用本轮算力卡生成的文本特征；包内 CPU 参考数组只用于数值核对。

此入口提供两条固定提示词，暂不接受自定义提示词参数。更换提示词需要重新准备对应的分词与 embedding 输入。

完成后应输出两条 `Saved` 信息，得到以下文件：

```text
~/edgeaccel/results/zimage-example/images/sample-1/result.png
~/edgeaccel/results/zimage-example/images/sample-2/result.png
```

打开图片后，结合下方提示词检查主体、颜色、动作和场景。再次执行 `axcl-smi`，确认模型进程已退出、资源已释放。程序报错时保留输出目录；排除原因后换用新的输出目录重试。

本次实测通过主机只读网络目录读取模型，逐个子模型的读取与加载占用较多时间。下方出图耗时包含这部分开销，且不含单独完成的文本编码阶段，不能作为本地 SSD 条件下的纯推理性能。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成中英文两组 512×512 出图，展示实际图片和提示词符合情况。

**英文提示词出图**

提示词：A small red robot watering green plants in a bright greenhouse, sunlight through glass, detailed illustration.

画面出现一大一小两个红色机器人，温室窗格和绿植清晰。红色机器人、温室和植物符合提示词，但额外出现第二个机器人，且未表现出明确的浇水动作。

<div className="model-effect-gallery">

<figure>

[![实际生成图片 1 · 512×512](../../../static/validation/effects/z-image-turbo-20261003/sample-1.png)](../../../static/validation/effects/z-image-turbo-20261003/sample-1.png)

<figcaption>实际生成图片 1 · 512×512</figcaption>
</figure>

</div>

| 本次图像阶段 | 实测值 |
| --- | --- |
| 去噪与解码总耗时（含读取、加载） | 1598.737 s |
| 其中模型加载 | 1367.881 s |
| 其中 AXCL run 调用（含传输） | 92.546 s |
| 参数 | 512×512 / 9 步 / seed 42 固定噪声 |

**中文提示词出图**

提示词：一只橙色小猫坐在蓝色花盆旁，背景是明亮的温室，柔和的自然光。

画面是一只坐着的橙色猫，左侧为蓝色花盆，背景可见温室中的植物与柔和光线。这组的主体、颜色、相邻位置及场景与提示词基本一致。

<div className="model-effect-gallery">

<figure>

[![实际生成图片 2 · 512×512](../../../static/validation/effects/z-image-turbo-20261003/sample-2.png)](../../../static/validation/effects/z-image-turbo-20261003/sample-2.png)

<figcaption>实际生成图片 2 · 512×512</figcaption>
</figure>

</div>

| 本次图像阶段 | 实测值 |
| --- | --- |
| 去噪与解码总耗时（含读取、加载） | 1600.728 s |
| 其中模型加载 | 1370.265 s |
| 其中 AXCL run 调用（含传输） | 92.435 s |
| 参数 | 512×512 / 9 步 / seed 42 固定噪声 |

**使用时注意：**

- 图片已正常生成，但第一组的浇水动作不明确且出现额外机器人；基本运行通过不代表提示词质量全部通过。
- 两张图均有可辨认主体；中文猫与花盆示例基本符合提示词，英文机器人示例的主体数量及浇水动作未完全符合。只完成这两组人工检查，尚不能给出模型整体质量结论。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`117d8586d5c50de6f4c6e0a7058e934c207407be`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | Python 3.12 / PyAXEngine 0.1.3.rc3 / PyTorch 2.5.1 / Diffusers 0.32.1 / AXCLRTExecutionProvider |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 实际输出 | 2 张 512×512 图片 | 每条提示词执行文本编码、9 步去噪与 VAE 解码。 |
| 算力卡执行 | 73 个 AXModel 文件 / 688 次调用 | 37 个文本模型、34 个去噪子图和 2 份内容相同的 VAE 文件均实际执行。 |
| 文本编码阶段 | 两条提示词合计约 324 s | 包含模型读取、加载、执行及参考数值核对；出图表格另列去噪和解码耗时。 |

适用范围：

- 本例使用两条固定提示词，不提供任意提示词输入；文本特征由本轮算力卡生成。尚未完成完整生成网络与浮点模型逐张量对照。
- 实测为 16GB 卡；8GB 卡、其他分辨率、连续多轮及长期稳定性尚未验证。
- 模型通过只读网络目录加载。上述时间包含读取与加载，不代表本地 SSD 条件下的纯 NPU 性能。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`VideoX-Fun/examples/z_image_fun/collect_subgraph_inputs.py`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/z_image_fun/collect_subgraph_inputs.py) | Python 程序 / 前后处理 |
| [`VideoX-Fun/examples/z_image_fun/launcher_axmodel.py`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/z_image_fun/launcher_axmodel.py) | Python 程序 / 前后处理 |
| [`VideoX-Fun/vae_decoder.axmodel`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/vae_decoder.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`text_encoder_axmodel/qwen3_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/text_encoder_axmodel/qwen3_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`text_encoder_axmodel/qwen3_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/text_encoder_axmodel/qwen3_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`text_encoder_axmodel/qwen3_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/text_encoder_axmodel/qwen3_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`text_encoder_axmodel/qwen3_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/text_encoder_axmodel/qwen3_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`VideoX-Fun/comfyui/annotator/zoe/zoedepth/models/base_models/midas_repo/ros/run_talker_listener_test.sh`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/comfyui/annotator/zoe/zoedepth/models/base_models/midas_repo/ros/run_talker_listener_test.sh) | 启动或构建脚本 |
| [`VideoX-Fun/config/zero_stage2_config.json`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/config/zero_stage2_config.json) | 运行配置 |
| [`VideoX-Fun/config/zero_stage3_config.json`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/config/zero_stage3_config.json) | 运行配置 |
| [`VideoX-Fun/examples/cogvideox_fun/post_infer.py`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/cogvideox_fun/post_infer.py) | Python 程序 / 前后处理 |
| [`VideoX-Fun/examples/wan2.1/post_infer.py`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/wan2.1/post_infer.py) | Python 程序 / 前后处理 |
| [`VideoX-Fun/examples/wan2.1_fun/post_infer.py`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/wan2.1_fun/post_infer.py) | Python 程序 / 前后处理 |
| [`VideoX-Fun/examples/wan2.2/post_infer.py`](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/wan2.2/post_infer.py) | Python 程序 / 前后处理 |

仓库提交：`117d8586d5c50de6f4c6e0a7058e934c207407be`。仓库中的 73 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/tree/117d8586d5c50de6f4c6e0a7058e934c207407be)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本页示例只提供两条固定提示词；使用同一初始噪声、512×512 分辨率和 9 步去噪。更换提示词需要重新准备分词和 embedding 输入。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/tree/117d8586d5c50de6f4c6e0a7058e934c207407be)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/README.md)。
- [主要程序入口：VideoX-Fun/examples/z_image_fun/collect_subgraph_inputs.py](https://huggingface.co/AXERA-TECH/Z-Image-Turbo/blob/117d8586d5c50de6f4c6e0a7058e934c207407be/VideoX-Fun/examples/z_image_fun/collect_subgraph_inputs.py)。
- [ModelScope 对应资源](https://modelscope.cn/models/AXERA-TECH/Z-Image-Turbo)。不同平台的 revision 不通用，另行记录版本。

返回[完整模型目录](../catalog.mdx)。
