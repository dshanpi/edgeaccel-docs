## 准备 Python 环境

按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，并使用以下依赖：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' 'torchaudio==2.5.1' 'soundfile==0.13.1'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本例通过 AXCL 调用 M.2 算力卡，使用官方 Python 特征提取流程。模型目录应保留 `models/`、`python/campplus_sdk/` 和 `samples/`。

## 提取特征并比较音频

下载 [CAM++ 算力卡示例](../../../static/examples/campplus_card.py)，保存为 `~/edgeaccel/campplus_card.py`。沿用前面下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/campplus_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/campplus-01
```

输出目录须尚不存在。程序对三段官方音频分别执行单次特征提取和滑窗提取，再重复第一段；最后计算三组余弦相似度。

单次提取使用前 360 帧特征，约对应开头 3.6 秒。短输入按官方流程循环补齐。滑窗模式以 1.5 秒为窗口、0.75 秒为步长，每个窗口单独补齐后推理，实际区间写入结果。

## 查看相似度和分块结果

打开输出目录中的 `deployment-result.json`：

- `pairs`：三组实际余弦相似度。
- `samples`：输入音频、单次或滑窗模式、窗口区间、输出维度及耗时。
- `sessions`：实际 AXCL 调用次数、模型输入输出校验值。

`raw-*.npz` 保存特征与 192 维向量，便于本地复核；`input-*.wav` 是实际输入。`processSeconds` 包含特征处理、传输、推理和记录校验值的时间，不含音频加载和结果保存。

相似度越高表示这两段样例的特征越接近。它不是概率，也没有通用的同人判定阈值；需要使用自己的有标注数据评估误接受率和误拒绝率。本入口不执行说话人聚类或身份检索。

## 比较自己的两段音频

准备 16 kHz 单声道 WAV，每段建议 1.5–60 秒：

```bash
python ~/edgeaccel/campplus_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/a.wav \
  --audio ~/Music/b.wav \
  --output ~/edgeaccel/results/campplus-custom-01
```

程序依次处理两段音频并重复第一段；使用新的输出目录保留每次结果。长录音应检查滑窗区间，不要把单次提取结果当作整段音频的完整表示。
