## 下载固定版本模型

本页使用 `Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k` 的固定提交，模型文件约 11.2 GiB。下载分区建议至少有 16 GiB 可用空间。板载空间不足时，将 `MODEL_DIR` 改为已挂载的 SSD 或存储卡目录。

在连接算力卡的 RK3576 终端执行：

```bash
MODEL_DIR=~/edgeaccel/models/qwen35-4b-ctx32k/4222f23a3459
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3.5-4B-AX650-GPTQ-Int4-C512-P30k-CTX32k \
  --revision 4222f23a3459751d20239a51621df62538cfd409 \
  --local-dir "$MODEL_DIR"
```

本目录应包含 32 个文本层、输出层、视觉编码器、embedding、分词器及配置。保留完整目录；名称相近的 C128、C256 和 C512 版本不能混用文件。代理设置见[下载方式与文件校验](../../usage/download-models.md)。

## 准备 ARM64 运行程序

本页使用官方 AXCL ARM64 程序，版本报告源码提交 `b704e2f3dc4e`、分词器提交 `a08af3838d76`。本轮硬件为 RK3576 + AX8850 16GB；实际 8GB 卡另行验证。

下载[固定运行程序与输入样例](/examples/qwen35-4b-20261003.tar.gz)，将文件命名为 `qwen35-4b-20261003.tar.gz`，复制到 RK3576 的 `~/Downloads`。模型校验脚本需要 Python 3.11 或更高版本。在同一终端执行：

```bash
cd ~/Downloads
echo 'afcdb99892184b742afffdfb0d0db79eab35e90f162714d8634d4e6020b3cb8c  qwen35-4b-20261003.tar.gz' | sha256sum -c -
mkdir -p ~/edgeaccel/runtimes
tar -xzf qwen35-4b-20261003.tar.gz -C ~/edgeaccel/runtimes
RUNTIME_DIR=~/edgeaccel/runtimes/qwen35-4b-20261003
chmod +x "$RUNTIME_DIR/axllm"
"$RUNTIME_DIR/axllm" version
ldd "$RUNTIME_DIR/axllm"
python3 "$RUNTIME_DIR/verify_models.py" "$MODEL_DIR"
```

程序版本应显示 `backend : AXCL` 和 `Linux aarch64`，依赖中不能出现 `not found`，模型校验应显示 `Verified 40 model files`。

## 启动模型服务

终端 1 执行，保持进程运行：

```bash
AXLLM_DEVICES=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  "$RUNTIME_DIR/axllm" serve "$MODEL_DIR" --port 8000
```

使用原始 `config.json` 和 `post_config.json`。运行时会加载混合注意力模型，并保留内存预检。出现模型加载或内存预检错误时，先处理错误，再发送请求。

## 发送文字、图片和视频请求

终端 2 设置前文的程序目录后，先确认服务就绪：

```bash
RUNTIME_DIR=~/edgeaccel/runtimes/qwen35-4b-20261003
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/v1/models
```

程序包内的 `request.py` 客户端接受 `--prompt`、`--image` 或 `--video`。保持 `enable_thinking=false`、`temperature=0` 和 128 个生成 token，与实测请求一致。

```bash
python3 "$RUNTIME_DIR/request.py" --prompt 'What is 2 + 3? Reply with only the number.'
python3 "$RUNTIME_DIR/request.py" \
  --prompt 'Name the two animals in the foreground. Reply in one sentence.' \
  --image "$RUNTIME_DIR/fixtures/images/horse-dog.jpg"
python3 "$RUNTIME_DIR/request.py" \
  --prompt 'Describe the main action across these video frames in one short sentence.' \
  --video "$RUNTIME_DIR/fixtures/video8"
```

图片和帧目录路径必须能被服务进程访问。替换提问文字即可复现下方其他问题。样例视频由 8 张有序图片组成，按配置的 1 fps 解释；不代表原始视频的采集时间。下方展示本机实际回答与请求耗时。

完成后，在终端 1 按 `Ctrl+C` 退出，再运行 `axcl-smi` 确认模型资源已释放。本轮仅检查短输入；名称中的 32K 不代表本页已经验证长上下文能力。
