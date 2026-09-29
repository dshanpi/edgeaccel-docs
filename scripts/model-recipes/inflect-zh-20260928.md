## 准备语音合成环境

本例在 **RK3576 + AX8850 16GB M.2** 上运行中文男声、女声合成。文本转声学特征由主机 CPU 完成，BigVGAN 声码器通过 AXCL 调用算力卡。

在已安装 PyAXEngine 的 AXCL Python 环境中执行：

```bash
python -m pip install 'numpy==1.26.4' 'onnxruntime==1.20.1' \
  'soundfile==0.13.1' 'pypinyin==0.55.0'
python -c "import axengine; print(axengine.get_available_providers())"
axcl-smi
```

提供者列表应包含 `AXCLRTExecutionProvider`，且设备 0 可用。本页使用 PyAXEngine `0.1.3.rc3`；安装方法见前面的主机环境步骤。

下载 [Inflect 中文语音运行示例](../../../static/examples/inflect_zh_card.py)，保存为 `~/edgeaccel/inflect_zh_card.py`。前面的模型下载命令包含男、女声 ONNX、各自的外置 `.data` 权重、NPU 声码器和官方前端代码，约 101 MB。保留目录结构和文件名。

例程在结果目录内建立 ONNX 外置权重的文件别名，并核对固定版本哈希，无需手动重命名模型。官方中文前端、mel 后处理和声码器分块流程保持不变。

## 运行男声与女声合成

保持下载步骤中的 `MODEL_DIR`，指定一个尚不存在的结果目录：

```bash
python ~/edgeaccel/inflect_zh_card.py \
  --model-dir "$MODEL_DIR" \
  --output ~/edgeaccel/results/inflect-zh-01
```

程序依次合成两句女声和两句男声，使用 `noise_scale=0`、随机种子 `0`。声码器只加载一次，同一音色的声学模型复用于对应短句；切换音色时重新加载声学模型。

合成自己的短句：

```bash
python ~/edgeaccel/inflect_zh_card.py \
  --model-dir "$MODEL_DIR" \
  --voice female \
  --text '您好，欢迎体验语音合成。' \
  --output ~/edgeaccel/results/inflect-zh-custom-01
```

`--voice` 可设为 `female` 或 `male`。例程检查分句后的输入长度，超过声学模型支持的长度时停止，避免静默截断。先使用简短中文句子，再根据业务需要评估长文本和数字、英文混读。

## 播放并检查音频

| 文件 | 内容 |
| --- | --- |
| `01-female.wav`、`02-female.wav` | 两段女声，24 kHz 单声道 PCM16 |
| `03-male.wav`、`04-male.wav` | 两段男声，24 kHz 单声道 PCM16 |
| `*-raw.wav` | 归一化前的浮点音频 |
| `deployment-result.json` | 输入、后端、模型加载与生成耗时、逐次调用及音频校验值 |

运行成功后，JSON 中 `completed` 应为 `true`，各模型调用的 `allFinite` 应为 `true`，四个 WAV 均存在且时长大于零。进程退出后用 `axcl-smi` 确认模型已释放。下方播放器展示本次实际生成的音频，可逐句对照输入文本。

页面中的生成耗时包含 CPU 声学推理、AXCL 声码器、主机后处理和调用记录开销，不包含模型加载和 WAV 写入；模型加载另行记录。RTF 为生成耗时除以音频时长，不代表首包延迟或纯 NPU 性能。

本次四段原始音频均只有 32 个幅度取值，女声波形出现平顶段。同一 mel 输入与官方 CPU 声码器比较，原始音频 SNR 为 2.65–6.93 dB，存在明显输出差异。当前仅确认流程可以运行，音质尚未通过验收；峰值归一化不会恢复已经损失的波形细节。

下方保留本次实际音频。有限值和非静音检查不能代替发音准确度、音色和听感评测；长文本、分块边界和真实 8GB 卡仍需另行验证。
