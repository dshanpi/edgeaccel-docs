## 安装例程依赖

在 RK3576 主机激活已安装 PyAXEngine 的虚拟环境：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'opencv-python-headless==4.11.0.86' 'pillow==11.3.0'
```

下载 [vision_card.py](../../../static/examples/vision_card.py)，保存到 `$MODEL_DIR`。例程指定 `AXCLRTExecutionProvider`，使用本页固定版本的权重和样例，并保存本次输出。

## 准备语音分块例程

下载固定版本的上游 Python SDK，只提取源码，不安装其板端依赖：

```bash
cd "$MODEL_DIR"
python -m pip download --no-deps --dest sdk-download 'silero-vad-axera==0.1.2'
python -m zipfile -e sdk-download/silero_vad_axera-0.1.2-py3-none-any.whl silero_sdk
```

本页从 SDK 复用 `SileroAx` 的状态与上下文处理，显式传入本仓库的 `models/silero_vad_ax650.axmodel`，不使用 SDK 自带权重。

## 检测语音片段

```bash
python vision_card.py --model-dir . --task silero-vad --variant audio60 \
  --output results/vad
```

输入 `demo.wav` 为 16 kHz、单声道、PCM16。每帧 512 个采样点（32 ms），语音阈值 0.5，最短语音 250 ms，连续静音达到 200 ms 后结束片段。末尾不足一帧时补零，输出片段按原音频范围截取。

`results/vad/segment-*.wav` 为语音片段；`deployment-result.json` 保存逐帧概率和以秒为单位的起止时间。可逐段播放核对是否漏掉首尾。这里的分段规则由本例程实现，与上游 `StreamVAD` 的时间戳和尾段处理不同，不做语音转写或说话人识别。
