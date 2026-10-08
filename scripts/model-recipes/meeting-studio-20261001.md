## 安装 AXCL 会议转录组件

本例在连接算力卡的 ARM64 Linux 主机上处理 PCM WAV 文件，输出说话人编号、时间段和转录文本。SenseVoice 与 FireRed/Punc 使用各自的识别模型；会议总结还需要单独运行大模型服务。

以下命令沿用下载步骤中的 `MODEL_DIR`。在 Python 环境中安装固定版本的 AXCL wheel：

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'sentencepiece==0.2.1' \
  'scipy==1.17.1' 'scikit-learn==1.9.1' setuptools wheel
python -m pip install --no-deps --no-build-isolation 'fastcluster==1.2.6'
python -m pip install --no-deps \
  "$MODEL_DIR/wheel/ax_meeting_studio-0.3.0+axcl-py3-none-linux_aarch64.whl"
export AXMEETING_AXCL_DEVICE=0
python - <<'PY'
import ax_meeting_studio
import ax_meeting_studio._core as core
assert core._native_backend().decode().lower() == 'axcl'
assert ax_meeting_studio.ax_runtime_available()
print('AXCL 原生运行时可用。')
PY
```

使用文件名含 `+axcl` 的 wheel。安装后应输出 `AXCL 原生运行时可用。`；若出现动态库版本错误，先核对 Linux 主机的 AXCL 安装和系统版本。本例使用 Python 3.12、glibc 2.39。

## 使用 SenseVoice 转录会议

```bash
mkdir -p ~/edgeaccel/results/meeting-studio
python -m ax_meeting_studio.cli \
  --wav "$MODEL_DIR/wav/vad_example.wav" \
  --model-dir "$MODEL_DIR/models" \
  --task meeting \
  --asr-backend sensevoice \
  --output ~/edgeaccel/results/meeting-studio/sensevoice.json
```

输入为完整样例录音。程序依次执行语音分段、说话人处理和转录，结果保存在 `sensevoice.json`。

## 使用 FireRed/Punc 转录同一录音

上一条命令结束后，再执行：

```bash
python -m ax_meeting_studio.cli \
  --wav "$MODEL_DIR/wav/vad_example.wav" \
  --model-dir "$MODEL_DIR/models" \
  --task meeting \
  --asr-backend firered_punc \
  --output ~/edgeaccel/results/meeting-studio/firered_punc.raw.json
```

两种后端分别保存结果，便于对照同一录音检查识别文本、标点及说话人边界。一次运行一种后端，避免并行占用同一张卡。

本次 FireRed/Punc 样例的原始末段结束时间比录音长约 79 毫秒。保留原文件，并将转录结束时间限制在输入音频范围内，文本不作修改：

```bash
export MODEL_DIR
python - <<'PY'
import json, os, wave
from pathlib import Path
root = Path.home() / 'edgeaccel/results/meeting-studio'
model = Path(os.environ['MODEL_DIR'])
with wave.open(str(model / 'wav/vad_example.wav'), 'rb') as wav:
    end_ms = round(wav.getnframes() * 1000 / wav.getframerate())
result = json.loads((root / 'firered_punc.raw.json').read_text())
for segment in result['meeting']['transcripts']:
    assert 0 <= segment['start_ms'] <= segment['end_ms']
    assert segment['start_ms'] <= end_ms
    if segment['end_ms'] > end_ms:
        assert segment['end_ms'] - end_ms <= 100, '时间超出较多，请先核对输入与原始结果'
        segment['end_ms'] = end_ms
(root / 'firered_punc.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
```

更换录音时，同步修改此处 WAV 路径。`firered_punc.raw.json` 保留原始输出，`firered_punc.json` 用于查看和后续处理。

## 查看分段文本

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path.home() / 'edgeaccel/results/meeting-studio'
for backend in ['sensevoice', 'firered_punc']:
    result = json.loads((root / (backend + '.json')).read_text())
    assert result['task'] == 'meeting' and result['asr_backend'] == backend
    segments = result['meeting']['transcripts']
    assert segments and any(segment['text'].strip() for segment in segments)
    print('\n' + backend)
    for segment in segments:
        print(f"[{segment['start_ms'] / 1000:.3f}, {segment['end_ms'] / 1000:.3f}] "
              f"Speaker_{segment['speaker']}: {segment['text']}")
PY
```

对照原始录音检查文本、时间段和说话人切换。说话人编号是本段录音的聚类标签，不表示经过确认的真实身份。

## 更换会议录音

将 `--wav` 改为自己的未压缩 PCM WAV 文件，并为 `--output` 指定新文件名。建议先使用单声道、16 kHz 输入；其他采样率会由官方 CLI 重采样。

本节覆盖离线文件转录。Web 页面、麦克风实时输入、大模型总结和长期连续运行需要分别验证；不从离线结果推断这些功能的效果。
