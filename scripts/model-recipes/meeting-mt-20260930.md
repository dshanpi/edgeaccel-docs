## 准备会议转录依赖

本例在 RK3576 主机与 AX8850 **16GB M.2 算力卡**上运行离线会议转录：检测语音、提取说话人特征、聚类，再输出带说话人标签和时间段的文本。模型与配套文件约 277MB，另需预留 Python 依赖和结果空间。

在已安装 [PyAXEngine](../../usage/python.md) 的主机虚拟环境中执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'scipy==1.17.1' \
  'scikit-learn==1.9.1' 'soundfile==0.13.1' 'torch==2.5.1' \
  'kaldi-native-fbank==1.22.3' 'sentencepiece==0.2.1' \
  'jieba==0.42.1' 'PyYAML==6.0.3' 'loguru==0.7.3' setuptools wheel
```

本次使用 Python 3.12。ARM64 环境中的 `fastcluster 1.2.6` 需要源码编译。在主机安装编译工具，然后回到虚拟环境执行安装：

```bash
sudo apt-get install -y build-essential python3-dev
python -m pip install --no-deps --no-build-isolation 'fastcluster==1.2.6'
python -c "import axengine, fastcluster; print(axengine.get_available_providers()); print(fastcluster.__version__)"
```

输出应包含 `AXCLRTExecutionProvider` 和版本 `1.2.6`。如果虚拟环境使用了自行安装的 Python，开发头文件也须匹配该 Python 版本。

下载[运行脚本](../../../static/examples/meeting_mt_card.py)，保存为 `~/edgeaccel/meeting_mt_card.py`。将[文件校验清单](../../../static/validation/effects/3d-speaker-mt-axera-20260930/download-manifest.json)保存为 `$MODEL_DIR/.validation-download.json`。

## 运行会议音频转录

在连接算力卡的 Linux 主机执行：

```bash
python ~/edgeaccel/meeting_mt_card.py \
  --model-dir "$MODEL_DIR" \
  --audio wav/vad_example.wav \
  --output ~/edgeaccel/results/meeting-01
```

`--audio` 是模型目录内的相对路径，输出目录须尚不存在。程序调用固定版本的官方离线处理流程，将 VAD、CAMPPlus 和 SenseVoice 三个模型明确交给 AXCL 执行。

完成后生成 `transcript.txt`、`deployment-result.json` 和逐次调用记录 `calls.jsonl`。

## 查看说话人和转录文本

```bash
cat ~/edgeaccel/results/meeting-01/transcript.txt
python - <<'PY'
import json
from pathlib import Path
r = json.loads((Path.home() / 'edgeaccel/results/meeting-01/deployment-result.json').read_text())
assert r['completed'] and len(r['sessions']) == 3
assert all(s['calls'] > 0 and s['provider'] == 'AXCLRTExecutionProvider'
           for s in r['sessions'])
print('音频时长：', round(r['audio']['durationSeconds'], 3), 's')
print('说话人标签数：', r['speakerCount'])
print('文件处理流程：', round(r['elapsedSeconds'], 3), 's')
PY
```

输出格式为 `Speaker_编号: [开始秒数 结束秒数] 转录文本`。标签只区分本次录音中的聚类结果，不代表说话人的真实身份。

播放原始音频，检查切换说话人的位置、漏字、错字和重复。本页下方保留本次实际输出，包括识别错误及未清除的特殊标记。

## 替换输入音频

将自己的 WAV 或 MP3 放入 `$MODEL_DIR/wav/`，再更换输入路径和输出目录。程序沿用官方处理方式：多声道取均值，必要时重采样到 16kHz。本次样例均为 16kHz，不据此评价其他采样率的处理效果。

```bash
python ~/edgeaccel/meeting_mt_card.py \
  --model-dir "$MODEL_DIR" \
  --audio wav/002.mp3 \
  --output ~/edgeaccel/results/meeting-02
```

当前已验证离线文件转录。浏览器麦克风、实时 WebSocket、多人长会议及大模型纪要总结仍需单独验证；本页命令不会调用外部总结服务。

流程计时包含官方模块导入、模型加载、音频处理、推理和运行后校验，不含 Python 启动及运行前校验。逐次 AXCL 调用计时包含 PCIe 传输，不能等同于常驻服务吞吐。
