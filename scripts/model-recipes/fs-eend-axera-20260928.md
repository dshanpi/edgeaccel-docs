## 准备 Python 环境

先按 [Python 接口](../../usage/python.md) 安装 PyAXEngine，在 RK3576 主机执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'librosa==0.11.0' 'scipy==1.17.1' 'soundfile==0.13.1'
python -c "import axengine; print(axengine.get_available_providers())"
```

输出须包含 `AXCLRTExecutionProvider`。本例分别运行 `models/simu/streaming_step.axmodel` 和 `models/ami/streaming_step.axmodel`，输出录音中各个说话人的活动时间段。说话人编号只是当前录音内的匿名标签，不代表真实身份。

## 运行说话人分离

下载 [FS-EEND 算力卡示例](../../../static/examples/fseend_card.py)，保存为 `~/edgeaccel/fseend_card.py`。沿用上方下载步骤的 `MODEL_DIR`：

```bash
python ~/edgeaccel/fseend_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/fseend-01
```

输出目录须尚不存在。程序按顺序运行两套权重，每套处理约 192 秒的官方四人混合录音、重复录音和三秒静音。每次录音开始前重置状态，按 0.1 秒特征帧调用算力卡。

## 查看说话人时间段

输出目录中：

- `input.wav`：实际输入录音。
- `simu-official.rttm`、`ami-official.rttm`：两套权重的说话人分段。
- `reference.rttm`：官方示例的参考标注，仅适用于默认示例。
- `deployment-result.json`：实际分段、活跃说话人数、耗时和模型调用记录。
- `*.npz`：特征与原始预测，供本地复核。

RTTM 每行的第 4、5 列分别为开始时间和持续时间，单位为秒；第 8 列为匿名说话人标签。下方效果展示使用相同颜色对齐匿名说话人，便于观察漏检、误检和说话人混淆。

后处理沿用官方设置：取前四个说话人通道、概率阈值 0.5、11 帧中值滤波。此入口只保留最多四个说话人。前九帧用于状态预热，录音末尾约 0.9 秒未刷新输出。

下方说话人分离错误率（DER）用完整录音评分，包含重叠说话和未输出的尾部；分别给出无边界容差和 0.5 秒容差的结果。0.5 秒容差表示参考边界前后各排除 0.25 秒，匿名标签按全局最优匹配对齐。评分使用 [pyannote.metrics](https://pyannote.github.io/pyannote-metrics/reference.html)，并以独立时间区间积分复核。单段示例分数不能代替完整数据集精度。

`rtf` 为逐帧推理耗时除以录音时长，包含传输、状态更新与校验记录，不含音频特征提取、后处理和模型加载；不等同于麦克风实时端到端延迟。

## 处理自己的录音

```bash
python ~/edgeaccel/fseend_card.py \
  --model-dir "$MODEL_DIR" \
  --audio ~/Music/meeting.wav \
  --output ~/edgeaccel/results/fseend-custom-01
```

本入口接受最长十分钟的音频，建议使用 8 kHz 单声道 WAV。其他采样率由前处理重采样到 8 kHz。自定义录音输出为 `simu-custom.rttm` 和 `ami-custom.rttm`，需要另外提供对应参考标注才能计算 DER；随包的 `reference.rttm` 不适用。
