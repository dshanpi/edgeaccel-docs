## 准备 Python 环境

本例在 RK3576 主机完成音频读取、特征提取和解码控制；通过 AXCL 在 M.2 算力卡上运行 FSMN-VAD、语音编码器及解码器。

按 [Python 接口](../../usage/python.md) 建好环境后，安装本例用到的依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'soundfile==0.13.1' 'kaldiio==2.18.1' 'kaldi-native-fbank==1.22.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本入口使用官方 NumPy 推理代码，无需安装训练用的 Torch 和 Torchaudio。

## 运行语音识别

下载 [FireRedASR 算力卡示例](../../../static/examples/firered_card.py)，保存为 `~/edgeaccel/firered_card.py`。沿用上方下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/firered_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/firered-01
```

输出目录须尚不存在。程序依次识别四段官方音频，再重复第一段，并检查三秒静音。每段音频按 10 秒分块；VAD 检出的语音不足 1 秒时，该块不进入语音识别。

每块最多生成 128 个 token。结果中的 `chunks[].hitEos` 为 `true` 才表示该块正常结束；达到上限时应检查是否截断。

## 查看转写和耗时

结果保存在输出目录：

- `input-*.wav`：本次实际输入，可播放核对。
- `deployment-result.json`：原始转写、官方参考文本、VAD 区间、逐块 token 和运行耗时。
- `reference-text.txt`：官方样例参考文本。
- `raw-*.npz`：用于复核的特征、VAD 分数和解码 logits。

`processSeconds` 包含文件读取、特征提取、传输、推理、解码及记录校验值的开销，不含模型加载和结果文件保存。`rtf` 等于处理时间除以输入音频时长；小于 1 才表示这次处理快于音频播放速度。

参考文本用于比较这几段样例，不能代表所有语音的识别准确率。模型可能漏字、错字；保留原始转写后再做业务侧处理。

## 使用自己的音频

```bash
python ~/edgeaccel/firered_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/example.wav \
  --output ~/edgeaccel/results/firered-custom-01
```

示例接受不超过 60 秒的音频，并重复该文件及检查静音。优先使用 16 kHz、单声道 PCM16 WAV；其他采样率会按官方代码插值到 16 kHz，多声道会平均混为单声道。该入口处理已有音频文件，未包含麦克风采集或实时流式服务。
