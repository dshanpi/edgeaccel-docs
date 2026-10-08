## 安装依赖与运行包

本例面向 RK3576 主机和 AX8850 16GB M.2 算力卡，使用 AXCL 3.16.0，应用和配套权重均保存于板载文件系统。语音应用约 471MB，配套 Qwen 权重约 2.46GB，建议预留至少 5GB 存储空间。退出其他推理应用，用 `axcl-smi` 确认设备 0 可用。启动服务前，用 `grep MemAvailable /proc/meminfo` 确认主机至少有 2400MiB 可用内存；主机内存与算力卡 CMM 分开计算。

在已安装 PyAXEngine 的 Python 环境中执行：

```bash
sudo apt-get install -y espeak-ng libespeak-ng1
python -m pip install torch==2.5.1 torchaudio==2.5.1 numpy==1.26.4 \
  transformers==4.51.3 tokenizers==0.21.4 onnxruntime==1.20.1 \
  funasr==1.2.7 kaldi-native-fbank==1.22.3 cn2an==0.5.24 \
  pypinyin==0.55.0 phonemizer==3.3.0 num2words==0.5.14 \
  soundfile==0.13.1 librosa==0.11.0 sentencepiece==0.2.1
python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。使用以上配套依赖，避免直接执行仓库中要求另一版 Torch 的安装列表。

## 下载配套 Qwen 模型

保留前文的 `MODEL_DIR`。语音应用调用同一主机上的 Qwen API，另外下载该 API 配套的上下文模型：

```bash
QWEN_DIR=~/edgeaccel/models/qwen2.5-1.5b-speech/eaa03390b75f
~/edgeaccel/hf-env/bin/hf download AXERA-TECH/Qwen2.5-1.5B-Instruct \
  --revision eaa03390b75ff42286b46ad492d007ce536b303d \
  --include 'qwen2.5-1.5b-ctx-ax650/*' \
  --local-dir "$QWEN_DIR"
```

模型目录需包含 28 个文本层、`qwen2_post.axmodel` 和 BF16 词嵌入。不能替换为同仓库中的 Int4 分片。

## 启动分词与问答服务

使用三个终端，并在每个终端激活同一 Python 环境，设置相同的 `MODEL_DIR` 和 `QWEN_DIR`。

每个终端先设置本机服务绕过下载代理，并限制主机计算线程：

```bash
export NO_PROXY=127.0.0.1,localhost
export no_proxy="$NO_PROXY"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1
```

终端一启动分词服务：

```bash
cd "$MODEL_DIR/libaxllm"
python qwen2.5_tokenizer_uid.py --host 127.0.0.1 --port 12345
```

终端二启动 ARM64 算力卡 API：

```bash
cd "$MODEL_DIR/libaxllm"
chmod +x main_api_axcl_aarch64
WEIGHTS="$QWEN_DIR/qwen2.5-1.5b-ctx-ax650"
./main_api_axcl_aarch64 \
  --system_prompt 'You are a helpful assistant.' \
  --template_filename_axmodel "$WEIGHTS/qwen2_p128_l%d_together.axmodel" \
  --axmodel_num 28 --url_tokenizer_model http://127.0.0.1:12345 \
  --filename_post_axmodel "$WEIGHTS/qwen2_post.axmodel" \
  --filename_tokens_embed "$WEIGHTS/model.embed_tokens.weight.bfloat16.bin" \
  --tokens_embed_num 151936 --tokens_embed_size 1536 \
  --use_mmap_load_embed 0 --devices 0
```

等待模型加载和 API 监听完成。应用通过 `http://127.0.0.1:8000` 访问本机服务。

## 运行语音问答

下载[配套运行包](/examples/spoken-communication-20261001-v2.tar.gz)，将下载文件重命名为 `spoken-communication-20261001-v2.tar.gz`，放到 `~/edgeaccel/`。终端三执行：

```bash
cd ~/edgeaccel
tar -xzf spoken-communication-20261001-v2.tar.gz
python spoken-communication/verify_models.py \
  --app-dir "$MODEL_DIR" --companion-dir "$QWEN_DIR"
python spoken-communication/run.py --app-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input_question/Q1.wav" --output "$HOME/edgeaccel/output/spoken-q1"
```

校验应分别确认 122 个应用文件和 30 个配套权重文件。处理完成后，输出目录中应生成 `result.json` 和 `synthesized.wav`；前者包含识别文本、回答及处理耗时，后者为本次合成音频。

保持两个服务运行，再处理另外两条问题：

```bash
python spoken-communication/run.py --app-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input_question/Q2.wav" --output "$HOME/edgeaccel/output/spoken-q2"
python spoken-communication/run.py --app-dir "$MODEL_DIR" \
  --audio "$MODEL_DIR/input_question/Q3.wav" --output "$HOME/edgeaccel/output/spoken-q3"
```

每次运行会重置对话，将识别出的语音问题交给本机 Qwen 服务回答，并要求回答限制在 100 个字以内。输出目录必须尚不存在；复测时换一个目录名。处理自己的录音时，将 `--audio` 改为音频文件的绝对路径。

VAD、SenseVoice 和 MeloTTS 解码器在算力卡运行；Qwen 的 29 个 AXModel 由本机 API 服务调用。音频预处理、分词和 MeloTTS 的 ONNX 编码器在 RK3576 主机执行。当前使用 `ZH_MIX_EN` 合成流程，不切换到仓库中的独立英文解码器。

## 检查回答与合成音频

逐项对照输入音频、识别文本、回答和生成音频。回答启用了采样，复测措辞可能不同，需检查是否回应问题，而不是要求逐字一致。生成回答与音频质量正确属于不同检查项。可将 WAV 下载到桌面播放，也可在已配置声卡的 Linux 主机执行：

```bash
aplay "$HOME/edgeaccel/output/spoken-q1/synthesized.wav"
```

处理程序退出码应为 `0`，文本不能为空，音频应能播放。测试结束后，在 API 和分词服务终端分别按 `Ctrl+C`。两个服务均退出后，校验并释放模型文件的主机缓存，再检查设备状态：

```bash
python spoken-communication/release_cache.py \
  --app-dir "$MODEL_DIR" --companion-dir "$QWEN_DIR"
axcl-smi
```

缓存释放程序应确认 152 个文件校验通过；该操作保留磁盘文件，复用模型时无需重新下载。`axcl-smi` 应显示设备 0，且不再有本次推理进程。
