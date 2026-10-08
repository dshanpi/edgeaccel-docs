## 准备唤醒例程

在 RK3576 主机激活已安装 [PyAXEngine](../../usage/python.md) 的环境，确认算力卡后端可用：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出应包含 `AXCLRTExecutionProvider`。下载 [OpenWakeWord 算力卡例程](../../../static/examples/openwakeword_card.py)，保存为 `~/edgeaccel/openwakeword_card.py`。

本页在主机计算 mel 音频特征，在算力卡上执行特征编码和六组分类器。保留 `config/openwakeword_mel_weights.npz`，不要将其替换为 `melspectrogram.axmodel`；该替换路径未通过本环境的样例触发准确性核对。

## 运行音频唤醒检测

保持下载步骤中的 `MODEL_DIR`，执行：

```bash
python ~/edgeaccel/openwakeword_card.py \
  --model-dir "$MODEL_DIR" \
  --mode wake-word \
  --output ~/edgeaccel/results/openwakeword
```

结果目录需要尚不存在。例程处理三段官方 16kHz、单声道 PCM16 音频，并生成四秒静音作为负例；每份输入从空状态运行两次。

处理窗口为 1280 个采样点，即 80ms。前五个窗口是初始化阶段，分数按官方流程置零；最后不足一窗的音频补零。检测阈值为 `0.5`。

## 查看触发结果

打开 `deployment-result.json`，查看各音频的 `triggeredModels`：

| 输入 | 本次结果 |
| --- | --- |
| `alexa_test.wav` | `alexa_v0.1` |
| `hey_mycroft_test.wav` | `hey_mycroft_v0.1` |
| `hey_jane.wav` | 未触发 |
| `silence-4s.wav` | 未触发 |

每个 `*-input.wav` 是对应的实际输入，`detectionScores` 保存逐窗口触发分数。`completed: true` 表示处理已结束；默认样例还应满足 `functionalChecks` 全部为 `true`，七个子模型均有调用记录，且 `repeatExact` 为 `true`。实际音频和追加的唤醒词效果见下方展示。

timer 是七通道输出。按照[官方类别映射](https://github.com/dscripka/openWakeWord/blob/368c03716d1e92591906a84949bc477f3a834455/openwakeword/__init__.py)，第 1–6 通道分别对应 1、5、10、20、30 分钟和 1 小时计时指令；第 0 通道不作为触发类别。例程的 timer 触发分数取第 1–6 通道最大值，完整七通道值仍保存在 `frame_scores` 中。

`triggeredTimerClasses` 给出实际达到阈值的计时类别编号，`timerClassPeaks` 保存各类别峰值。判断“十分钟计时”时应检查第 3 类，不能只检查 timer 总体是否触发。

## 检测自己的录音

在 RK3576 主机安装 FFmpeg，将录音转换成 16kHz、单声道 PCM16 WAV。下面的 `recording.wav` 替换为自己的输入文件；录音前后各留约 1 秒静音。

```bash
sudo apt install -y ffmpeg
mkdir -p ~/edgeaccel/audio/openwakeword
ffmpeg -i recording.wav -ar 16000 -ac 1 -c:a pcm_s16le \
  ~/edgeaccel/audio/openwakeword/microphone.wav

python ~/edgeaccel/openwakeword_card.py \
  --model-dir "$MODEL_DIR" \
  --audio-dir ~/edgeaccel/audio/openwakeword \
  --mode wake-word \
  --output ~/edgeaccel/results/openwakeword-custom
```

例程会处理目录中的全部 WAV，并额外检查四秒静音。结果目录需尚不存在。将 `triggeredModels`、`triggeredTimerClasses` 与实际说出的指令核对；自备录音没有预设标签，`completed` 和重复输出一致都不能代替识别正确性判断。

下方追加样例采用[官方的合成音频生成方法](https://github.com/AXERA-TECH/openWakeWord.AXERA/blob/517ce5609726680eea98dae0c0a91a771fd7b71a/python/generate_calibration_audio.py)，覆盖 Alexa、Hey Jarvis、Hey Mycroft、Hey Rhasspy、天气查询及六种计时指令。合成音频的触发结果不能替代麦克风、距离、噪声和长时间连续录音测试。
