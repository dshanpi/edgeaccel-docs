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
