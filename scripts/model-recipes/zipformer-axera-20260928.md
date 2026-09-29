## 准备 Python 环境

先按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，再安装本例依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchaudio==2.5.1' 'soundfile==0.13.1' 'kaldi-native-fbank==1.22.3'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本例使用 `inputs/axmodels_650N/` 下的 encoder、decoder 和 joiner，经 AXCL 在 M.2 算力卡上执行。

## 运行音频转写

下载 [Zipformer 算力卡示例](../../../static/examples/zipformer_card.py)，保存为 `~/edgeaccel/zipformer_card.py`。沿用上方下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/zipformer_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/zipformer-01
```

输出目录须尚不存在。默认处理仓库中的十段 WAV/MP3，再重复第一段，并检查三秒静音。每个文件开始前重置编码器缓存。

示例保留固定版本官方代码中的缓存更新和贪心解码。词表直接读取 `tokens.txt`；前处理使用 `kaldi-native-fbank`，并逐文件与 Torchaudio 的 Kaldi FBank 对照，无需为本入口安装 K2 和 Kaldifeat。

## 查看实际转写

输出目录中：

- `input-*`：本次实际音频。
- `deployment-result.json`：原始转写、token、处理耗时、实际模型调用次数，以及前处理对照误差。
- `raw-*.npz`：音频特征、对照特征、编码器输入和 joiner logits，用于本地复核。

`samples[].output` 是原始文本，英文保留模型输出的大小写；`rtf` 为处理耗时除以音频时长。耗时包含音频读取、前处理、传输、推理、解码及记录校验值，不含模型加载、额外前处理对照和结果保存。

本流程按官方设置补 0.3 秒静音尾部，以 103 帧输入、96 帧步长处理；最后不足一块的特征不会单独刷新。句尾文字与短音频需结合原音频核对，不应只检查程序退出码。

## 转写自己的音频

```bash
python ~/edgeaccel/zipformer_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/example.wav \
  --output ~/edgeaccel/results/zipformer-custom-01
```

本入口接受最长 60 秒的文件，优先使用 16 kHz 单声道 WAV。多声道使用第一声道；其他采样率需另外安装 Librosa 完成重采样。程序会重复第一段输入并追加静音测试。本页验证的是文件分块推理，麦克风实时采集、并发服务和更长音频需进一步验证。
