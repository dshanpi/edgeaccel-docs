## 准备 AXCL 运行程序

本例适用于 RK3576 + AX8850 16GB M.2 算力卡、Ubuntu 24.04 ARM64、Python 3.12 和 AXCL 3.16。使用官方标准版 W8A16 权重，图片输入为 448×448，视频帧输入为 308×308。模型文件约 5.95 GB，建议预留至少 8 GB 存储空间。

下载[配套运行包](/examples/qwen25-vl3b-standard-20261002.tar.gz)，保存到连接算力卡的 Linux 主机 `~/edgeaccel/`。包内包含已测试的 ARM64 程序、分词服务、配置及适配源码。

```bash
cd ~/edgeaccel
tar -xzf qwen25-vl3b-standard-20261002.tar.gz
cd qwen25-vl3b-standard
sudo apt update
sudo apt install -y libopencv-dev libssl-dev
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'transformers==4.51.3' 'torch==2.5.1'
python verify_models.py "$MODEL_DIR"
ldd ./main_axcl_aarch64
```

`MODEL_DIR` 沿用前文的下载目录。校验应输出 `Verified 80 model files`；`ldd` 不应出现 `not found`。若已有 Python 虚拟环境使用其他路径，替换激活路径。Python 服务负责分词和解码，原生 AXCL 程序执行推理。

## 运行图片问答

在第一个终端启动图片分词服务，并保留运行：

```bash
cd ~/edgeaccel/qwen25-vl3b-standard
source ~/edgeaccel/python-env/bin/activate
python tokenizer_image.py --host 127.0.0.1 --port 8511
```

在连接算力卡的第二个终端执行：

```bash
cd ~/edgeaccel/qwen25-vl3b-standard
source ~/edgeaccel/python-env/bin/activate
MODEL_DIR=~/edgeaccel/models/qwen2-5-vl-3b-instruct/d967363ac68e
python run_model.py image --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/image/ssd_car.jpg" \
  --prompt 'Describe the main vehicle and its color in this image.'
python run_model.py image --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/image/ssd_horse.jpg" \
  --prompt '请用两句中文描述画面前景中的动物和人物。'
python run_model.py image --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/image/ssd_horse.jpg" \
  --prompt 'How many dogs are visible in the foreground? Reply with only the number.'
```

每条命令重新加载模型，输出回答后退出并释放资源。实际回答见下方效果展示。启动日志应出现 `load config:`。问答结束时确认 `termination_reason=eos last_token=151645`、进程退出码为 0，并检查回答内容和设备空闲状态。

## 运行视频帧问答

在第一个终端按 `Ctrl+C` 停止图片分词服务，切换为视频分词服务：

```bash
python tokenizer_video.py --host 127.0.0.1 --port 8511
```

在保留 `MODEL_DIR` 的第二个终端执行：

```bash
python run_model.py video --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" --prompt '描述这个视频的内容'
python run_model.py video --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/video" --prompt 'Describe this video.'
```

本例读取官方 `video` 目录内按文件名排序的 8 张 JPEG，按 1 fps 输入，视觉编码器每两帧执行一次。此配置的输入长度上限为 512 token，8 帧及上述问题共占用 509 token；不要直接增加帧数或改成长问题。1 fps 用于这组帧序列，不代表原视频真实帧率。原始视频解码、抽帧和实时输入需另行接入。

运行结束后检查 `axcl-smi`，确认测试进程已退出。本页实测使用经校验的主机只读网络挂载目录；进程耗时包含文件读取、模型加载和推理，不能用作本地 SSD 的速度基准。
