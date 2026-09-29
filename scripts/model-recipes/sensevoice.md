## 安装文件转写依赖

本例使用非流式模型处理仓库内的五段短音频。音频解码、FBank 和文字后处理在主机执行，模型推理使用 M.2 卡。

```bash
source ~/edgeaccel/python-env/bin/activate
python -m pip install numpy==1.26.4 torch==2.5.1 librosa==0.9.1 \
  kaldi-native-fbank==1.22.3 soundfile==0.14.0
```

下载 [sensevoice_file.py](../../../static/examples/sensevoice_file.py)，通过 scp 或 SFTP 复制到 Linux 主机的 `$MODEL_DIR/sensevoice_file.py`。

## 指定 AXCL 后端

在模型目录执行以下修改。脚本保留原文件；重新下载上游源码后需要再次执行。

```bash
cd "$MODEL_DIR"
python - <<'PY'
from pathlib import Path
p = Path("python/SenseVoiceAx.py")
s = p.read_text(encoding="utf-8")
old = "axe.InferenceSession(model_path)"
new = 'axe.InferenceSession(model_path, providers=["AXCLRTExecutionProvider"])'
if old in s:
    backup = p.with_suffix(".py.upstream")
    if not backup.exists():
        backup.write_text(s, encoding="utf-8")
    p.write_text(s.replace(old, new), encoding="utf-8")
else:
    assert new in s, "源码与本页固定版本不匹配"
PY
```

## 转写样例音频

```bash
cd "$MODEL_DIR"
test -s sensevoice_file.py
set -o pipefail
python sensevoice_file.py --model-dir . \
  --languages zh en yue ja ko \
  --out sensevoice-result.json 2>&1 | tee run.log
```

日志中的 provider 应为 `AXCLRTExecutionProvider`。结果文件按音频记录实际转写、时长与端到端耗时；只测试中文时将参数改为 `--languages zh`。

`wallRTF` 是本脚本一次文件转写耗时除以音频时长，包含音频加载和前后处理，不是纯 NPU 延迟。第一次运行可能包含音频库初始化。非流式短文件结果不代表已经验证麦克风采集、流式识别或长录音分段。
