## 安装音频依赖与运行脚本

本例比较 ECAPA-TDNN 和 ERes2NetV2 两套模型。音频前处理在 RK3576 上执行，`.axmodel` 推理明确使用 AXCL；CPU ONNX 仅用于核对量化前后的向量。

在已安装 PyAXEngine 的 Python 环境执行：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install numpy==1.26.4 torch==2.5.1 torchaudio==2.5.1 \
  onnxruntime==1.20.1 soundfile==0.14.0
```

下载本站的 [speaker_compare.py](../../../static/examples/speaker_compare.py)，通过 scp 或 SFTP 将它复制到 Linux 主机的 `$MODEL_DIR/speaker_compare.py`。

该脚本采用配套 [FBank 前端参数](https://github.com/modelscope/3D-Speaker/blob/065629c313eaf1a01c65c640c46d77e61e9607b4/speakerlab/process/processor.py)：16 kHz、80 维、dither=0、均值归一化。超过模型帧数时截取前部；不足时仅在尾部补零，保留已有语音。它同时解决原始入口缺少 `processor.py`、板端 provider 和短音频处理问题。

## 提取声纹并比较录音

在模型根目录执行：

```bash
cd "$MODEL_DIR"
test -s speaker_compare.py
set -o pipefail
python speaker_compare.py --model-dir . --reference \
  --out speaker-result.json 2>&1 | tee run.log
```

`--reference` 使用本包同提交的两个 `.onnx` 模型做 CPU 对照。只需要卡端声纹时可省略该参数；示例音频和 `.axmodel` 仍须完整保留。

运行后检查日志中的实际 provider 为 `AXCLRTExecutionProvider`，并查看 `speaker-result.json`：

- `sameSpeaker`：speaker1 的两段录音之间的余弦相似度。
- `differentSpeaker`：speaker1 与 speaker2 录音之间的余弦相似度。
- `onnxComparison.embeddingCosine`：每段录音的卡端向量与 CPU ONNX 向量之间的相似度。

先比较本页样例的排序，再使用自己的录音标定业务阈值。相似度不是百分比准确率，也不能直接生成语音转写或说话人时间轴。
