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

每个 `*-input.wav` 是对应的实际输入，`detectionScores` 保存逐窗口触发分数。完成标志为 `completed: true`，七个子模型均有调用记录，重复输出一致。分数图和实际音频见下方效果展示。

timer 是七通道输出。按照[官方类别映射](https://github.com/dscripka/openWakeWord/blob/368c03716d1e92591906a84949bc477f3a834455/openwakeword/__init__.py)，第 1–6 通道分别对应 1、5、10、20、30 分钟和 1 小时计时指令；第 0 通道不作为触发类别。例程的 timer 触发分数取第 1–6 通道最大值，完整七通道值仍保存在 `frame_scores` 中。

这些样例只包含 Alexa、Hey Mycroft 两类正样本。其他分类器需要对应指令、不同说话人和噪声环境的音频才能进一步评估，不要把“未触发”视为该类别识别准确率已验证。
