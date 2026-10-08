## 下载固定版本模型

模型文件约 3.74 GiB。首次下载前，确认目标分区至少有 6 GiB 可用空间；板载空间不足时，将 `MODEL_DIR` 改为已挂载的 SSD 或存储卡目录。

```bash
MODEL_DIR=~/edgeaccel/models/qwen3-4b-instruct-2507-gptq-int4/ff1d40a1ca77
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen3-4B-Instruct-2507-GPTQ-Int4 \
  --revision ff1d40a1ca779b69146e883ef9e7f5b0c7af3213 \
  --local-dir "$MODEL_DIR"
```

保留同一终端中的 `MODEL_DIR`。下载受阻或需要使用代理时，见[下载方式与文件校验](../../usage/download-models.md)。

## 准备配套运行程序

本页使用固定 Int4 权重和配套 ARM64 程序，在 RK3576 + AX8850 16GB 上完成单轮问答。每次启动加载 36 个文本层及输出层，使用原生分词器。输入上限为 3584 个 token，包含系统提示词与对话模板。

下载[本页配套程序与源码](/examples/qwen3-instruct-int4-native-20261004.tar.gz)，将文件命名为 `qwen3-instruct-int4-native-20261004.tar.gz`，复制到 RK3576 的 `~/Downloads`。该包在 Ubuntu 24.04 ARM64 上编译；依赖 AXCL 3.16、OpenCV 4.6、PCRE2 和 ICU 74。

```bash
cd ~/Downloads
echo '54a5fa4364f13102570b9dc4229fd1a66a4691609a4ab8610cb7f5ce7a8c1965  qwen3-instruct-int4-native-20261004.tar.gz' | sha256sum -c -
mkdir -p ~/edgeaccel/runtimes
tar -xzf qwen3-instruct-int4-native-20261004.tar.gz -C ~/edgeaccel/runtimes
RUNTIME_DIR=~/edgeaccel/runtimes/qwen3-instruct-int4-native-20261004/runtime
chmod +x "$RUNTIME_DIR/main_axcl_aarch64"
file "$RUNTIME_DIR/main_axcl_aarch64"
ldd "$RUNTIME_DIR/main_axcl_aarch64"
python3 "$RUNTIME_DIR/../verify_models.py" "$MODEL_DIR"
```

程序包校验应显示 `OK`，模型校验应显示 `Verified 53 model files`，程序架构应为 ARM aarch64，依赖中不能出现 `not found`。其他系统按包内 `README.md` 从源码编译。

## 运行单轮问答

在同一终端执行，`MODEL_DIR` 使用前文下载目录。程序使用设备 0，自动添加与官方入口一致的系统提示词和 `/no_think` 后缀。

```bash
mkdir -p ~/edgeaccel/results/qwen3-instruct-int4
RESULT_DIR=~/edgeaccel/results/qwen3-instruct-int4
printf '%s' 'What is 2 + 3? Reply with only the number.' > "$RESULT_DIR/prompt.txt"
set -o pipefail
bash "$RUNTIME_DIR/run.sh" "$MODEL_DIR" \
  "$RESULT_DIR/prompt.txt" "$RESULT_DIR/answer.json" 2>&1 | tee "$RESULT_DIR/run.log"
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["output"]); print("hitEos:",r["hitEos"])' "$RESULT_DIR/answer.json"
```

程序正常退出，日志包含 `termination_reason=eos last_token=151645`，结果文件中的 `hitEos` 为 `True`。下方保留本机实际输入和回复。

替换 `prompt.txt` 可运行中文或 JSON 问答。每次调用独立加载模型，不保留上一轮对话；`answer.json` 同时保存原始回复、token 和耗时。完整进程计时包含模型加载，本轮网络读取的耗时不能直接用作本地磁盘部署的性能指标。
