## 准备运行环境

在 RK3576 的 Linux 终端执行。本例已在 **AX8850 16GB M.2 算力卡、AXCL 3.16.0** 上验证，用文字描述音色并生成中文语音，无需参考录音。

先完成[驱动与设备检查](../../usage/device-check.md)，保持风扇正常运行。运行前执行 `axcl-smi`，确认设备 0 可用。准备至少 4 GiB 可用存储；模型与配套文件约 2.79 GB。

下载[VoiceDesign 配套运行包](/examples/qwen3tts-voicedesign-20261004.tar.gz)，保存到主机的 `~/edgeaccel/`，然后执行：

```bash
cd ~/edgeaccel
tar -xzf qwen3tts-voicedesign-20261004.tar.gz
sudo apt-get install -y libopencv-dev libblas3
chmod +x qwen3tts-voicedesign/bin/axllm
ldd qwen3tts-voicedesign/bin/axllm
```

`ldd` 输出中不能出现 `not found`。包内程序适用于 Linux ARM64，包含本页 1.7B VoiceDesign 的接口和输出尺度适配，请与本页固定权重配套使用。

## 下载并校验模型

设置模型目录。存储不足时，将 `MODEL_DIR` 改为已挂载存储设备上的目录，后续命令继续使用同一个变量：

```bash
MODEL_DIR=~/edgeaccel/models/qwen3tts-voicedesign
mkdir -p "$MODEL_DIR"
df -h "$MODEL_DIR"
python3 ~/edgeaccel/qwen3tts-voicedesign/setup_models.py \
  --model-dir "$MODEL_DIR"
```

下载工具使用 Python 3.11 或更新版本的标准库，逐个核对文件大小和 SHA-256。输出 `Verified 87 runtime files` 后继续。已有且校验一致的文件会跳过；下载失败后可重新执行同一命令。

若 Hugging Face 无法直连，在运行下载命令前设置可用代理。以下地址仅为局域网示例，需替换为主机可访问的地址：

```bash
export http_proxy="http://192.168.1.38:7897"
export https_proxy="$http_proxy"
```

文件由三部分组成：

| 内容 | 固定来源 | 运行位置 |
| --- | --- | --- |
| VoiceDesign 1.7B 权重与嵌入 | AXERA-TECH/Qwen3-TTS-12Hz-1.7B-VoiceDesign-AX650，`3d4e2e701313` | 50 个 AXModel 在算力卡运行 |
| 公用语音解码器与词表 | AXERA-TECH/Qwen3-TTS-12Hz-0.6B-Base-AX650，`3b3fde9cb90b` | 11 个解码 AXModel 在算力卡运行 |
| 文本投影、预测器解码投影、Talker 归一化 | Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign，`5ecdb67327fd` | 使用原始权重在 RK3576 CPU 运行，已随运行包提供 |

使用公用解码器不会替换 1.7B 的文本与语音码生成模型。完整文件来源、版本和校验值见包内 `runtime-files.json`。

## 运行语音生成

下面的输入、音色描述和参数与本页实测一致：

```bash
python3 ~/edgeaccel/qwen3tts-voicedesign/setup_models.py \
  --model-dir "$MODEL_DIR" --verify-only
mkdir -p ~/edgeaccel/results/qwen3tts-voicedesign
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  ~/edgeaccel/qwen3tts-voicedesign/bin/axllm tts_voice_design "$MODEL_DIR" \
  --text '你好，欢迎使用算力卡语音合成。' \
  --instruct '用温柔清晰的女声朗读，语速适中。' \
  --language Chinese --seed 1234 --max_new_tokens 160 \
  --non_streaming_mode \
  --output ~/edgeaccel/results/qwen3tts-voicedesign/generated.wav
```

`--text` 指定朗读内容，`--instruct` 描述音色和语速。程序完成后输出 `voice design wav saved`，生成 24 kHz、单声道 WAV。此次样例生成 43 帧语音码后自然结束，音频为 3.44 秒。

用桌面音频播放器打开文件，或在主机已配置音频输出时执行：

```bash
aplay ~/edgeaccel/results/qwen3tts-voicedesign/generated.wav
```

本页只验证上述中文短句。配套解码器的单次容量为 128 帧；先使用短句，长文本按句拆分。达到生成上限、出现容量错误或输出头范围错误时，保留提示并停止，不能将被截断的音频视为完整结果。

<details>
<summary>需要重新编译运行程序时展开</summary>

包内 `source.tar.gz` 为本次实际使用的完整源码，已包含固定版本子模块及适配。AX-LLM 基础提交为 `a51df2d43b3ec1c49b30792bbe4fad5a964231ea`。

```bash
sudo apt-get install -y build-essential cmake libopencv-dev libblas3
cd ~/edgeaccel/qwen3tts-voicedesign
mkdir -p source
tar -xzf source.tar.gz -C source
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON
cmake --build build --target axllm -j1
```

编译后，将运行命令中的 `bin/axllm` 换成 `build/axllm`。编译时须已安装 AXCL 的头文件和库。

</details>
