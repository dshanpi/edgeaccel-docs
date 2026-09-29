## 准备音频增强例程

在 RK3576 主机准备 FFmpeg，并激活已安装 [PyAXEngine](../../usage/python.md) 的环境：

```bash
sudo apt install ffmpeg
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。下载 [FastEnhancer 算力卡例程](../../../static/examples/fastenhancer_card.py)，保存为 `~/edgeaccel/fastenhancer_card.py`。

本例保留官方 NumPy 流式前后处理：主机执行 STFT、幅度压缩、解压和 ISTFT，算力卡执行神经网络核心。两种采样率分别使用自己的模型配置、窗函数与循环状态，不能混用。

## 运行 16kHz 和 48kHz 模型

保持下载步骤中的 `MODEL_DIR`。按顺序执行，等待上一条结束后再继续：

```bash
python ~/edgeaccel/fastenhancer_card.py \
  --model-dir "$MODEL_DIR" --rate 16k \
  --output ~/edgeaccel/results/fastenhancer-16k

python ~/edgeaccel/fastenhancer_card.py \
  --model-dir "$MODEL_DIR" --rate 48k \
  --output ~/edgeaccel/results/fastenhancer-48k
```

结果目录需要尚不存在。官方输入 `p232_013_original.wav` 是 48kHz 单声道 PCM16：16kHz 模型先通过 FFmpeg 重采样，48kHz 模型直接使用原音频。每个规格还处理两秒静音；各输入均从初始状态运行两次。

## 试听本次增强结果

在桌面音频播放器中分别打开各结果目录中的文件：

| 文件 | 内容 |
| --- | --- |
| `official-input.wav` | 实际送入该采样率流程的语音 |
| `official-output.wav` | 本次算力卡处理结果 |
| `silence-input.wav`、`silence-output.wav` | 静音输入与输出 |
| `*-raw.npz` | 本次浮点输入与输出数组 |
| `deployment-result.json` | 样本数、耗时、RTF、RMS 与重复一致性 |

完成标志为 `completed: true`，输入与输出样本数相等，重复输出一致且数值有限。本次静音也经过了神经网络处理，并未跳过算力卡调用。

RTF 是完整处理耗时除以音频时长。下方记录包含主机前后处理和 AXCL 调用，不包含模型加载、重采样和文件保存。RTF 小于 1 仅说明这段样例处理耗时少于音频时长；持续麦克风链路还需要单独验证。

试听时同时比较背景噪声、语音清晰度和失真。RMS 下降只是整体幅度变化，不能直接当作音质或降噪准确性指标。
