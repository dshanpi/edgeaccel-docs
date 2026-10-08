## 准备运行环境

本例将一段会议录音转换为带说话人标签的文本，再生成会议总结。已验证的组合为 RK3576（约 4GB 主机内存）、AX8850 16GB M.2 算力卡和 AXCL V3.16.0。40 个神经网络模型均通过 AXCL 在算力卡上执行。

模型与样例约 5.32GB，保存在 Windows 主机。RK3576 通过 SSH 只读访问这些文件；Windows 负责提供文件，不执行模型推理。运行期间需要保持网络连接。此页展示这一实际验证过的部署方式。

在 RK3576 上完成[驱动与设备检查](../../usage/device-check.md)和[安装 PyAXEngine](../../usage/python.md)，然后执行：

```bash
axcl-smi
sudo apt-get install -y rclone fuse3 build-essential python3-dev
source ~/edgeaccel/python-env/bin/activate
python -m pip install 'numpy==1.26.4' 'torch==2.5.1' \
  'torchaudio==2.5.1' 'transformers==4.51.3' 'funasr==1.2.7' \
  'librosa==0.11.0' 'soundfile==0.13.1' 'hdbscan==0.8.44' \
  'kaldi-native-fbank==1.22.3' 'ml_dtypes==0.5.3' \
  'sentencepiece==0.2.1' 'scipy==1.17.1' 'scikit-learn==1.9.1' \
  'umap-learn==0.5.12' 'jieba==0.42.1' 'PyYAML==6.0.3' \
  'loguru==0.7.3' setuptools wheel
python -m pip install --no-deps --no-build-isolation 'fastcluster==1.2.6'
python -c "import axengine, funasr, hdbscan, fastcluster; print(axengine.get_available_providers())"
```

Python 环境使用 3.12；最后一条命令应输出 `AXCLRTExecutionProvider`。模型运行前停止其他推理程序，保持散热风扇运行，并为输出文件预留空间。

## 下载模型与配套程序

在 Windows 下载[会议总结部署包](../../../static/examples/meeting-summary-deployment-20261004.zip)，解压到独立目录。部署包包含运行脚本、文件校验清单、只读文件服务和嵌入表校验数据，不包含模型权重。

在解压目录打开 PowerShell。Windows 需安装 Python 3.12 和 OpenSSH 客户端，并预留至少 6GB 模型存储空间：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install huggingface_hub
.\.venv\Scripts\python.exe .\download_models.py --models-dir .\models
```

下载固定版本 `b55d044e8eb419c779dc15c4b3e486dfe531f67e`，完成后输出 `Verified 86 fixed model and support files`。需要代理时，在此 PowerShell 窗口设置 `HTTP_PROXY` 和 `HTTPS_PROXY`，具体设置见[下载方式与文件校验](../../usage/download-models.md)。

将下面的用户名和 IP 替换为实际 RK3576 的 SSH 登录信息，复制运行文件：

```powershell
$Board = "baiwen@192.168.1.44"
ssh $Board 'mkdir -p ~/edgeaccel/meeting-summary'
scp .\meeting_summary_card.py .\embedding-row-sha256.bin "${Board}:edgeaccel/meeting-summary/"
.\.venv\Scripts\python.exe .\serve_models.py --models-dir .\models --port 18869
```

看到 `"ready": true` 后保持此窗口运行。在同一目录另开一个 PowerShell 窗口，建立 SSH 转发：

```powershell
$Board = "baiwen@192.168.1.44"
ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -N `
  -R 127.0.0.1:18869:127.0.0.1:18869 $Board
```

登录后命令会持续运行，保持窗口开启。文件服务仅监听本机回环地址，RK3576 通过这条 SSH 连接读取文件。

## 挂载模型并运行

在 RK3576 的另一个 SSH 终端执行：

```bash
mkdir -p ~/edgeaccel/meeting-summary/models
env http_proxy= https_proxy= HTTP_PROXY= HTTPS_PROXY= ALL_PROXY= all_proxy= \
  rclone mount :http: ~/edgeaccel/meeting-summary/models \
  --http-url http://127.0.0.1:18869/ --read-only \
  --vfs-cache-mode off --buffer-size 0 \
  --vfs-read-chunk-size 8M --vfs-read-chunk-size-limit 32M \
  --config /dev/null --daemon --daemon-wait 20s
MODEL_DIR=~/edgeaccel/meeting-summary/models/3D-Speaker-Meeting-Summary
test -f "$MODEL_DIR/.validation-download.json" && echo '模型目录已就绪'
source ~/edgeaccel/python-env/bin/activate
python ~/edgeaccel/meeting-summary/meeting_summary_card.py \
  --model-dir "$MODEL_DIR" --audio wav/vad_example.wav \
  --embedding-oracle ~/edgeaccel/meeting-summary/embedding-row-sha256.bin \
  --embedding-oracle-sha256 aa2ca3f481fa7bf2bc8bb26355515af94d6e46cf7c19a20cc0e672b969032a63 \
  --max-new-tokens 1024 --output ~/edgeaccel/results/meeting-summary-01
```

输出目录须尚不存在。脚本依次完成文件校验、语音活动检测、说话人聚类、语音识别和 Qwen3 总结，最后再次校验文件。本样例约 70.47 秒，实测完整流程约 41.7 分钟；耗时包含文件读取、校验、模型加载及结果记录，不能作为常驻服务的吞吐指标。

## 检查转录与总结

```bash
cat ~/edgeaccel/results/meeting-summary-01/vad_example.wav.txt
cat ~/edgeaccel/results/meeting-summary-01/vad_example.wav_summary.md
python - <<'PY'
import json
from pathlib import Path
r = json.loads((Path.home() / 'edgeaccel/results/meeting-summary-01/deployment-result.json').read_text())
assert r['completed'] and r['endedWithEos']
assert len(r['sessions']) == 40 and len(r['filesAfter']) == 86
assert all(s['calls'] > 0 and s['provider'] == 'AXCLRTExecutionProvider'
           for s in r['sessions'])
print('完整流程结束，已生成转录和总结。')
PY
```

先对照录音检查转录，再核对总结是否保留原文信息。`Speaker_0` 等编号是当前录音中的聚类标签。识别错字、人物归属和模型补充的解释需要人工复核，不能直接当作正式会议纪要。

程序未生成结束标记、文件校验不一致或网络断开时，不能把已有部分输出视为完整结果。保留输出目录，修复连接后使用新的输出目录重试。

完成处理后，先在 RK3576 卸载模型目录，再在 Windows 的两个运行窗口按 `Ctrl+C` 关闭转发和文件服务：

```bash
cd ~
fusermount3 -u ~/edgeaccel/meeting-summary/models
```

下方展示本次原始音频、完整转录和模型总结。其他音频、实时麦克风、并发和真实 8GB 卡尚需分别验证。
