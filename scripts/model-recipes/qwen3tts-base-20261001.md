## 准备语音运行程序

本例在 RK3576 主机通过 AXCL 驱动 M.2 算力卡，使用 Qwen3-TTS 0.6B 的参考音频和文本生成一句中文语音。已验证环境为 AX8850 16GB、AXCL 3.16.0；运行程序为 Linux ARM64 版本。

下载[本页配套运行包](/examples/qwen3tts-base-20261001.tar.gz)，保存为主机上的 `~/edgeaccel/qwen3tts-base-20261001.tar.gz`。包内包含本次使用的程序、固定源码、AXCL 适配文件和文件校验工具。保留前文下载模型后设置的 `MODEL_DIR`，在同一终端执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3tts-base-20261001.tar.gz
sudo apt-get install -y libopencv-dev
chmod +x ~/edgeaccel/qwen3tts-base/bin/axllm
ldd ~/edgeaccel/qwen3tts-base/bin/axllm
~/edgeaccel/qwen3tts-base/bin/axllm tts_voice_clone "$MODEL_DIR" --help
```

`ldd` 应能找到所有动态库，帮助信息应包含 `tts_voice_clone`。程序基于官方 AX-LLM 提交 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`，补齐 AXCL 设备 0 的工作线程初始化与释放、两组形状模型的 K/V 缓冲区绑定。该程序对应本页 0.6B 权重，不直接用于 1.7B VoiceDesign 版本。

## 校验模型文件

确认下载目录保留 `talker`、`code-predictor`、`speech_tokenizer` 和 `assets` 子目录。校验本页固定版本的 91 个文件：

```bash
python3 ~/edgeaccel/qwen3tts-base/verify_models.py --model-dir "$MODEL_DIR"
```

输出 `Verified 91 model files` 后继续。权重与配套文件约 1.9 GB；存储空间不足时，将 `MODEL_DIR` 指向已挂载的存储设备。校验失败时先检查下载文件，不能跳过校验运行。

## 生成中文语音

使用官方自带参考音频，保持参考文本与音频内容一致。下面的参数与本次实测相同：

```bash
mkdir -p ~/edgeaccel/results/qwen3tts-base
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ~/edgeaccel/qwen3tts-base/bin/axllm tts_voice_clone "$MODEL_DIR" \
  --ref_audio "$MODEL_DIR/assets/zero_shot_prompt.wav" \
  --ref_text '希望你以后能够做的比我还好呦。' \
  --text '你好，欢迎使用算力卡语音合成。' \
  --language Chinese --seed 1234 --max_new_tokens 160 \
  --output ~/edgeaccel/results/qwen3tts-base/generated.wav
```

成功后出现 `voice clone wav saved`，结果目录生成 24 kHz、单声道 WAV。用桌面音频播放器打开文件，或在主机已配置音频输出时执行：

```bash
aplay ~/edgeaccel/results/qwen3tts-base/generated.wav
```

`--text` 是待合成文本；`--ref_audio` 与 `--ref_text` 用于参考音色和上下文。换用自己的参考音频时，同时修改对应文本。`--max_new_tokens` 限制生成语音码帧数，本例为 160；达到上限时应检查是否截断，不能仅凭生成文件判断整句已经完成。

<details>
<summary>在其他主机重新编译时展开</summary>


若 ARM64 程序的动态库版本与系统不匹配，可使用包内相同源码和适配文件重新编译。以下步骤使用现有 AXCL 头文件和库：

```bash
sudo apt-get install -y build-essential cmake libopencv-dev
cd ~/edgeaccel/qwen3tts-base
mkdir source
tar -xzf official-source.tar.gz -C source
cp -r adapted/src/. source/src/
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON
cmake --build build --target axllm -j1
```

将前面命令中的 `bin/axllm` 换成 `build/axllm`。固定源码包已包含对应版本的子模块，无需在编译时重新拉取分支。

</details>
