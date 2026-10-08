---
title: "Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4 部署指南"
sidebar_label: "Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4"
description: "Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4 的 M.2 算力卡部署步骤、配套文件与效果展示。"
---

# Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4 部署指南

Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4 用于图片问答与视频帧理解。本页说明 M.2 算力卡的接入条件、部署步骤与结果检查方法。

> 已实测，效果仍需评估。[查看部署效果](#查看部署效果)。

## 准备运行环境

本页效果展示使用 **RK3576 + AX8850 16GB M.2**；其他容量或平台需重新确认模型能否加载并正确运行。

在连接算力卡的 Linux 主机终端执行，RK3576 使用 ARM64 环境。首次部署先完成[驱动与设备检查](../../usage/device-check.md)、[准备主机环境](../../getting-started/prepare.md)和[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)。已完成这些步骤可直接下载模型。

后文使用设备 0，运行前用 `axcl-smi` 确认设备可用。


## 准备本例环境

本例使用 **RK3576 + AX8850 16GB**。RK3576 运行官方 ARM64 程序，PC 运行分词服务；两端通过 SSH 连接。图片与视频模式需要分别启动对应的分词服务。

| 位置 | 本例配置 |
| --- | --- |
| RK3576 | Ubuntu 24.04 ARM64、AXCL 3.16.0、可用的设备 0 |
| 算力卡 | AX8850 16GB |
| PC | Windows、Python 3.12、OpenSSH 客户端 |
| PC Python 依赖 | Transformers 4.51.3、Tokenizers 0.21.4、Torch 2.6.0 CPU |
| 模型文件 | 固定版本 75 个文件，约 6.99GB |

模型目录建议预留至少 10GB 可用空间；PC 的 Python 环境另需存储空间。下方效果来自 16GB 卡，8GB 容量尚未验证。

在 RK3576 终端检查设备：

```bash
axcl-smi
```

确认设备 0 可用，且无其他模型正在占用。

## 下载模型和配套工具

在 RK3576 终端下载固定版本。也可按[离线下载与文件复制](../../usage/download-models.md)先在 PC 下载，再复制到 RK3576 可访问的目录。

```bash
MODEL_DIR=~/edgeaccel/models/xiaomi-mimo/839273460d34
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4 \
  --revision 839273460d343a02f2e88a0cfe059f8ec78a50ea \
  --local-dir "$MODEL_DIR"
```

下载[运行目录准备工具](../../../static/examples/mimo-axcl-20261004.tar.gz)，将下载文件重命名为 `mimo-axcl-20261004.tar.gz`，保存到 RK3576 的 `~/Downloads`。在 RK3576 终端校验并解压：

```bash
echo "38990441ac608c2c32dcd6eb5f26315f17c9b22f166f3b0c81d4a31489ee9197  $HOME/Downloads/mimo-axcl-20261004.tar.gz" | sha256sum -c -
mkdir -p ~/edgeaccel/examples
tar -xzf ~/Downloads/mimo-axcl-20261004.tar.gz -C ~/edgeaccel/examples
python3 ~/edgeaccel/examples/mimo-axcl/prepare_runtime.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/mimo-runtime
```

输出应包含 `modelFilesVerified: 75`。工具保留模型目录，另建运行目录并放入本例的 `post_config.json` 贪心采样配置。重复准备时选择一个新运行目录。

在 RK3576 安装主机依赖。以下软件包名称适用于本例的 Ubuntu 24.04：

```bash
sudo apt update
sudo apt install -y file curl libopencv-core406t64 libopencv-imgproc406t64 libopencv-imgcodecs406t64
```

检查原版程序依赖：

```bash
cd ~/edgeaccel/mimo-runtime
file main_axcl_aarch64
ldd main_axcl_aarch64
./main_axcl_aarch64 --help
```

程序应为 ARM64，`ldd` 中不能出现 `not found`。本例使用 OpenCV 4.6，三个 OpenCV 库的文件名均以 `.so.406` 结尾。若缺少 `libaxcl_rt.so`，先完成 AXCL 主机运行环境安装；使用其他系统版本时，需安装提供相同库文件的 ARM64 软件包，再继续运行。

## 准备 PC 分词服务

以下命令在 **PC 的 PowerShell 终端 1** 执行。使用 Python 3.12 创建独立环境：

```powershell
$MimoHome = "$HOME\edgeaccel-mimo"
New-Item -ItemType Directory -Force $MimoHome | Out-Null
Set-Location $MimoHome
py -3.12 -m venv env
$Py = "$MimoHome\env\Scripts\python.exe"
& $Py -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
& $Py -m pip install transformers==4.51.3 tokenizers==0.21.4
& $Py -m pip check
& $Py -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4', revision='839273460d343a02f2e88a0cfe059f8ec78a50ea', allow_patterns=['tokenizer/*','tokenizer_image.py','tokenizer_video.py'], local_dir='model')"
```

`pip check` 应无依赖冲突。PC 只下载分词器和服务脚本，无需重复下载全部算力卡权重。下载受阻时，先按[下载方式与代理配置](../../usage/download-models.md)处理网络连接。

在同一终端启动图片分词服务，并保持运行：

```powershell
Set-Location "$MimoHome\model"
& $Py tokenizer_image.py --host 127.0.0.1 --port 8080
```

另开 **PC 的 PowerShell 终端 2**，将 `用户名@开发板IP` 替换为实际 SSH 登录目标，然后建立转发：

```powershell
$BoardTarget = "用户名@开发板IP"
ssh -N -T -o ExitOnForwardFailure=yes -R 127.0.0.1:8080:127.0.0.1:8080 $BoardTarget
```

登录后保持该终端运行。在 RK3576 终端检查分词服务：

```bash
curl --fail http://127.0.0.1:8080/eos_id
```

应返回 `{"eos_id": 151645}`。连接失败时先确认 PC 服务仍在运行、SSH 转发未退出、两端端口 8080 未被其他程序占用。

## 运行图片问答

在 RK3576 终端执行：

```bash
cd ~/edgeaccel/mimo-runtime
bash run_image_axcl_aarch64.sh
```

等待模型加载完成。日志应显示 `load config`，其中 `enable_temperature`、`enable_repetition_penalty`、`enable_top_p_sampling`、`enable_top_k_sampling` 均为 `false`，随后出现 `prompt >>`。

在交互提示中依次输入问题和图片路径：

```text
prompt >> 请用中文简短描述这张图片。
image >> image/ssd_car.jpg
```

等待完整回答和新的 `prompt >>`，输入 `q` 退出。再次启动同一脚本，检查数量和车型：

```text
prompt >> 图片前景中有几位主要人物？旁边的两辆车分别是什么颜色和类型？
image >> image/ssd_car.jpg
```

本页两次图片结果来自分别启动的独立运行。配置或图片打开失败时停止，先处理对应错误。

## 运行视频帧问答

在 RK3576 输入 `q` 退出图片程序。回到 **PC 终端 1**，按 `Ctrl+C` 停止图片分词服务，再启动视频服务；PC 终端 2 的 SSH 转发继续保持：

```powershell
& $Py tokenizer_video.py --host 127.0.0.1 --port 8080
```

在 RK3576 终端启动视频程序：

```bash
cd ~/edgeaccel/mimo-runtime
bash run_video_axcl_aarch64.sh
```

出现交互提示后输入：

```text
prompt >> 请用中文简短描述视频中动物的数量和动作。
image >> video
```

`video` 是仓库提供的八帧图片目录。本例按文件名顺序读取，成对处理为四组视觉输入，不包含音频。不要在此提示中直接输入 MP4 文件路径。

完整回答结束后输入 `q`，再用 `axcl-smi` 确认本次模型进程已退出。程序会同时打印 `<think>...</think>` 和最终回答；下方展示最终回答，并提供包含思考段的完整文本下载。


## 查看部署效果

**已运行，效果仍需评估** · RK3576 + AX8850 16GB M.2。以下输入与输出来自本页固定版本的实际运行。

已在 16GB M.2 算力卡完成图片描述、人数与车辆问答、八帧视频问答。人物和动物数量可对照，车型及动物种类存在识别偏差；以下保留实际输入与原始回答。

**图片中文描述**

使用同一张官方照片的独立运行。 下方展示最终回答；[下载完整原始回复（含思考段）](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/description-full-response.txt)。

<div className="model-effect-gallery">

<figure>

[![输入照片：人物、红色双层巴士与深色车辆](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/ssd_car.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/ssd_car.jpg)

<figcaption>输入照片：人物、红色双层巴士与深色车辆</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用中文简短描述这张图片。
```

**实际回复**

```text
街道上红色双层观光巴士旁停着黑色小车，背景是欧式建筑，有人站在巴士旁。
```

识别出红色双层巴士、深色车辆、人物和街道；单张照片不能确认巴士是否用于观光、车辆是否停着。

| 输出统计 | 本次结果 |
| --- | --- |
| 完整输出 token（含思考段） | 187 |
| 程序报告的生成速度 | 2.33 token/s |
| 程序报告的首 token | 2.625 秒 |

**人数与车辆问答**

使用同一张官方照片的独立运行。 下方展示最终回答；[下载完整原始回复（含思考段）](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/count-full-response.txt)。

<div className="model-effect-gallery">

<figure>

[![输入照片：人物、红色双层巴士与深色车辆](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/ssd_car.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/ssd_car.jpg)

<figcaption>输入照片：人物、红色双层巴士与深色车辆</figcaption>
</figure>

</div>

**示例 1：输入**

```text
图片前景中有几位主要人物？旁边的两辆车分别是什么颜色和类型？
```

**实际回复**

```text
图片前景中有1位主要人物。旁边的两辆车分别是：红色的双层巴士和深蓝色的小轿车。
```

前景中的 1 名主要人物和红色双层巴士判断正确。右侧车辆的车身较高，外观更接近 MPV／面包车型，“小轿车”的分类有偏差。

| 输出统计 | 本次结果 |
| --- | --- |
| 完整输出 token（含思考段） | 172 |
| 程序报告的生成速度 | 2.33 token/s |
| 程序报告的首 token | 2.477 秒 |

**八帧视频问答**

下列八张图片按实际输入顺序排列，不包含音频。 下方展示最终回答；[下载完整原始回复（含思考段）](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/video-full-response.txt)。

<div className="model-effect-gallery">

<figure>

[![官方输入帧 frame_0000.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0000.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0000.jpg)

<figcaption>官方输入帧 frame_0000.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0008.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0008.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0008.jpg)

<figcaption>官方输入帧 frame_0008.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0016.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0016.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0016.jpg)

<figcaption>官方输入帧 frame_0016.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0024.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0024.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0024.jpg)

<figcaption>官方输入帧 frame_0024.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0032.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0032.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0032.jpg)

<figcaption>官方输入帧 frame_0032.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0040.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0040.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0040.jpg)

<figcaption>官方输入帧 frame_0040.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0048.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0048.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0048.jpg)

<figcaption>官方输入帧 frame_0048.jpg</figcaption>
</figure>

<figure>

[![官方输入帧 frame_0056.jpg](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0056.jpg)](../../../static/validation/effects/xiaomi-mimo-vl-miloco-7b-ax650-gptq-int4-20261004/frame_0056.jpg)

<figcaption>官方输入帧 frame_0056.jpg</figcaption>
</figure>

</div>

**示例 1：输入**

```text
请用中文简短描述视频中动物的数量和动作。
```

**实际回复**

```text
视频中有两只羊驼，它们相互靠近、头部接触互动，还呈现站立、移动等姿态。
```

两只动物的数量正确，也提到靠近和移动；画面中的小型动物被误判为羊驼，种类判断不正确。动作描述尚未按逐帧标注评估。

| 输出统计 | 本次结果 |
| --- | --- |
| 完整输出 token（含思考段） | 163 |
| 程序报告的生成速度 | 2.34 token/s |
| 程序报告的首 token | 14.429 秒 |

**使用时注意：**

- 右侧车辆被称为小轿车，视频中的小型动物被称为羊驼；本次基本运行不代表视觉理解准确性通过。
- 生成速度按完整输出统计，包含思考段。表中首 token 与速度来自程序日志，不含首次加载，不是端到端交互延迟或峰值性能。

这些结果用于对照部署后的输出，未覆盖完整数据集精度或长期连续运行。

<details>
<summary>查看样例环境与运行耗时</summary>

环境：RK3576 + AX8850 16GB M.2。模型版本：`839273460d343a02f2e88a0cfe059f8ec78a50ea`。

| 组件 | 版本或配置 |
| --- | --- |
| 主机 / 内核 | RK3576，约 4GB RAM，6.1.115-vendor-rk35xx |
| AXCL / 驱动 | V3.16.0_20260729180218 |
| 固件 / CMM | V3.16.0 / 15232 MiB |
| 运行方式 | 官方 main_axcl_aarch64 / AXCL C API；PC Python 3.12、Transformers 4.51.3、Tokenizers 0.21.4、Torch 2.6.0 CPU 运行原版分词服务。 |

| 指标 | 实测值 | 计时或统计范围 |
| --- | --- | --- |
| 输入覆盖 | 同一照片两问 / 八帧视频一问 | 三次独立加载，38 个编译模型均实际调用，结束后释放。 |
| 执行记录 | 共 19719 次 AXCL 调用 | 图片 6993、6438 次；视频 6288 次，包含每一层预填充与解码。 |

适用范围：

- 实测模型文件由 PC 经只读挂载读取，分词服务在 PC 运行；主机文件读取、SSH 通信和首次加载均会影响等待时间。
- 本次只覆盖 16GB 和所示输入。8GB、新环境全流程安装、更多视频、长期运行与完整数据集质量尚未验收。

</details>

遇到加载、内存或后端错误时，按[常见问题](../../usage/troubleshooting.md)处理。需要更换输入或接入业务时，按[检查输出与记录结果](../../reference/validation.md)保留自己的结果。

<details>
<summary>查看文件用途与版本信息</summary>

| 文件 / 目录内路径 | 用途 |
| --- | --- |
| [`run_image_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/run_image_axcl_aarch64.sh) | 启动或构建脚本 |
| [`tokenizer_video.py`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/tokenizer_video.py) | 旧版分词服务入口 |
| [`Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/Xiaomi-MiMo-VL-Miloco-7B_vision.axmodel`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/Xiaomi-MiMo-VL-Miloco-7B_vision.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l0_together.axmodel`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l0_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l10_together.axmodel`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l10_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l11_together.axmodel`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l11_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l12_together.axmodel`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/Xiaomi-MiMo-VL-Miloco-7B-AX650-c128-p1280-ctx2047-Int4/qwen2_5_vl_text_p128_l12_together.axmodel) | 编译模型；按目录区分芯片和规格 |
| [`config.json`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/config.json) | 运行配置 |
| [`run_image_ax650.sh`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/run_image_ax650.sh) | 启动或构建脚本 |
| [`run_image_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/run_image_axcl_x86.sh) | 启动或构建脚本 |
| [`run_video_ax650.sh`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/run_video_ax650.sh) | 启动或构建脚本 |
| [`run_video_axcl_aarch64.sh`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/run_video_axcl_aarch64.sh) | 启动或构建脚本 |
| [`run_video_axcl_x86.sh`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/run_video_axcl_x86.sh) | 启动或构建脚本 |
| [`tokenizer/config.json`](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/tokenizer/config.json) | 运行配置 |

仓库提交：`839273460d343a02f2e88a0cfe059f8ec78a50ea`。仓库中的 38 个 `.axmodel` 文件可能包括多个芯片、规格和分片。运行时使用本页指定的配套文件，完整列表见[固定版本目录](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/tree/839273460d343a02f2e88a0cfe059f8ec78a50ea)。

</details>

<details>
<summary>补充说明与版本差异</summary>

- 本提交的图片分词脚本实际名为 tokenizer_image.py；模型卡中其他图片脚本名称不在该提交文件表内。视频模式另用 tokenizer_video.py。
- 保留该 GPTQ 量化版本的分片、embedding 和配置，不能与同系列非量化模型混放。
- 较大模型或长上下文需要单独评估峰值 CMM；不承诺当前 8GB 单卡可以加载。

</details>

## 参考资料

- [常用术语](../../reference/glossary.md)：AXCL、CMM、分词器与推理指标。
- [固定版本文件表](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/tree/839273460d343a02f2e88a0cfe059f8ec78a50ea)。
- [模型卡 / 使用说明](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/README.md)。
- [主要程序入口：tokenizer_video.py](https://huggingface.co/AXERA-TECH/Xiaomi-MiMo-VL-Miloco-7B-AX650-GPTQ-Int4/blob/839273460d343a02f2e88a0cfe059f8ec78a50ea/tokenizer_video.py)。
- [配套项目：AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera](https://github.com/AXERA-TECH/Qwen2.5-VL-3B-Instruct.axera)。

返回[完整模型目录](../catalog.mdx)。
