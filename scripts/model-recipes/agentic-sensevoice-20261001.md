## 安装依赖与运行包

本例使用 RK3576 主机、AX8850 16GB M.2 算力卡和 AXCL 3.16.0，运行官方仓库中的整段识别与分块识别程序。仓库名称包含 AgenticRAG，但这里提供的是语音识别流程，不包含检索问答应用。

在已安装 PyAXEngine 的 Python 环境中执行：

```bash
python -m pip install numpy==1.26.4 librosa==0.11.0 soundfile==0.13.1 \
  kaldi-native-fbank==1.22.3 online-fbank==0.0.4
python -c "import axengine; print(axengine.get_available_providers())"
```

提供器列表应包含 `AXCLRTExecutionProvider`。音频解码使用主机 CPU，识别模型使用 M.2 算力卡。

下载[配套运行包](/examples/agentic-sensevoice-20261001.tar.gz)到 `~/edgeaccel`，保留前文设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf agentic-sensevoice-20261001.tar.gz
python agentic-sensevoice/verify_models.py --model-dir "$MODEL_DIR"
mkdir -p sensevoice-results
```

应输出 `Verified 14 model files`。本例使用 `sensevoice_ax650` 目录中的两个不同权重。AX630C 权重不适用于此流程；仓库中的同内容嵌套副本不需要重复下载。

## 识别完整音频

识别仓库中的中文音频：

```bash
python agentic-sensevoice/run.py --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/example/zh.mp3" --language zh \
  --output sensevoice-results/zh.json
```

终端打印识别文字，`zh.json` 保存 `transcript`、音频长度、推理耗时及实时率。实时率为处理耗时除以音频时长，不包含模型加载和音频解码。

识别英文音频：

```bash
python agentic-sensevoice/run.py --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/example/en.mp3" --language en \
  --output sensevoice-results/en.json
```

`--language` 支持 `auto`、`zh`、`en`、`yue`、`ja`、`ko`。替换输入时使用自己的音频文件路径，并选择相应语言。

## 分块识别音频

```bash
python agentic-sensevoice/run.py --model-dir "$MODEL_DIR" \
  --input "$MODEL_DIR/example/zh.mp3" --language zh --streaming \
  --output sensevoice-results/zh-streaming.json
```

程序将音频按 100ms 分块送入官方流式前端，终端依次显示阶段结果；JSON 中的 `streamUpdates` 保留这些文字和时间戳，`transcript` 保存最后一次结果。这是音频文件分块处理，不包含麦克风采集或实时播放节奏。

## 检查结果与设备释放

```bash
echo $?
cat sensevoice-results/zh.json
axcl-smi
```

退出码应为 `0`，JSON 中 `provider` 应为 `AXCLRTExecutionProvider`，并生成非空识别文字。对照实际音频检查人名、数字和专有名词；程序正常退出不等同于文字完全准确。进程结束后，算力卡应释放本次模型占用。
