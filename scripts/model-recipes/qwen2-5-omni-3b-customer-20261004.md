## 准备本例依赖

以下命令在 RK3576 主机执行。本例使用固定图片和视频，生成文字与完整语音。图片保留完整画面并缩放为 308 × 308，视频使用官方 `videos/1.mp4`。

配套程序使用 `AXCLRTExecutionProvider` 在设备 0 执行编译模型；两个 ONNX 投影模型在主机 CPU 运行。

| 项目 | 本例环境 |
| --- | --- |
| 主机 | RK3576，ARM64 Linux，4GB 内存 |
| 算力卡 | AX8850，16GB |
| AXCL / 固件 | 3.16.0 |
| Python | 3.12 |
| 模型文件 | 105 个部署文件，约 8.11GB |

准备至少 12GB 可用存储空间，用于模型、独立 Python 环境和运行结果。8GB 算力卡不在本页这次实测的范围内。

安装系统依赖：

```bash
sudo apt update
sudo apt install -y python3-venv ffmpeg libsndfile1 libgomp1
axcl-smi
```

## 下载配套程序与模型

下载[单卡 AXCL 配套程序](/examples/qwen2-5-omni-3b-axcl.tar.gz)，将下载文件重命名为 `qwen2-5-omni-3b-axcl.tar.gz`，保存到 RK3576 的 `~/Downloads`。配套包包含运行入口、依赖安装脚本、模型校验表、图片样例和独立的 Omni 处理器源码。下载后先校验压缩包：

```bash
echo "f1c293593c0d09be602d2aa04cb3f644b5e445bc8c224b475d9ee65619bac62e  $HOME/Downloads/qwen2-5-omni-3b-axcl.tar.gz" | sha256sum -c -
```

```bash
mkdir -p ~/edgeaccel/examples
tar -xzf ~/Downloads/qwen2-5-omni-3b-axcl.tar.gz -C ~/edgeaccel/examples
cd ~/edgeaccel/examples/qwen2-5-omni-3b-axcl

python3 -m venv ~/edgeaccel/omni-env
source ~/edgeaccel/omni-env/bin/activate
python -m pip install --no-cache-dir -r requirements-base.txt
python -m pip check
python install_runtime.py --target ~/edgeaccel/omni-runtime
```

`pip check` 应无依赖冲突。安装脚本校验配套文件，将 Omni 专用处理器和补充依赖放入 `omni-runtime`，完成后输出 `installed: true`。

模型使用固定提交 `38c42b43ece9cca5acf024aeddd8d0a188eca44d`。首次下载先按[下载工具安装](../../usage/download-models.md#使用-hugging-face-下载)准备 `hf`；代理和离线复制方法也见该页。

```bash
MODEL_DIR=~/edgeaccel/models/qwen2-5-omni-3b/38c42b43ece9
mkdir -p "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-Omni-3B \
  --revision 38c42b43ece9cca5acf024aeddd8d0a188eca44d \
  --exclude '*.bfloat16.bin' '*.float32.bin' \
  --local-dir "$MODEL_DIR"
```

保留 `.npy` 形式的 embedding 权重；排除项是本例不读取的两组重复 `.bin` 文件。

## 运行图片与视频示例

在配套程序目录执行，沿用上一步的 `MODEL_DIR`。先检查模型校验值、Python 依赖和运行参数：

```bash
source ~/edgeaccel/omni-env/bin/activate
cd ~/edgeaccel/examples/qwen2-5-omni-3b-axcl
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case chinese-video \
  --output ~/edgeaccel/omni-result-zh \
  --check-only
```

输出应包含 `modelFilesVerified: 105`。该步骤检查文件和 CPU 环境，尚未执行算力卡推理。

运行图片示例。`image-description` 提问为“请用中文简短描述这张图片。”，`image-count` 提问为“图片中有几个人、几只狗？他们在做什么？”：

```bash
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case image-description \
  --output ~/edgeaccel/omni-image-description

python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case image-count \
  --output ~/edgeaccel/omni-image-count
```

运行中文示例，提问为“请简短描述视频中的乐器和声音。”：

```bash
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case chinese-video \
  --output ~/edgeaccel/omni-result-zh
```

运行官方英文示例：

```bash
python run_omni.py \
  --model-dir "$MODEL_DIR" \
  --runtime-dir ~/edgeaccel/omni-runtime \
  --case official-video \
  --output ~/edgeaccel/omni-result-en
```

每次使用一个尚不存在的输出目录。完成后，终端打印文字回答、音频路径和时长；对应目录应包含 `answer.txt`、`output.wav` 和 `result.json`。程序异常退出时先检查错误信息，不将中途生成的文件视为完整结果。

