## 准备运行环境

本页部署仓库中的本地媒体功能：语音转文字、文字转语音、图片问答和视频问答。实测环境为 **RK3576 + AX8850 16GB M.2 算力卡、AXCL 3.16**。QQ 账号接入和 OpenClaw 对话调度尚未验证，不能将下面的本地结果视为 QQ 机器人完整部署通过。

先完成[驱动与设备检查](../../usage/device-check.md)，确认 `axcl-smi` 能识别算力卡。板端需要 Python 3.11 或更新版本；安装音视频工具和只读挂载工具：

```bash
sudo apt update
sudo apt install -y python3 ffmpeg rclone fuse3
python3 --version
```

模型可存放在 PC，通过 SSH 只读挂载供板端加载。以下步骤采用该方式；PC 需要保持开机，并安装 Python 3.11 或更新版本。模型推理在 M.2 算力卡执行。

## 下载部署包与模型

在 PC 下载并解压[本地媒体 AXCL 部署包](/examples/openclaw-media-axcl-20261004.zip)。进入解压后的 `openclaw-media-axcl` 目录，在 PowerShell 执行：

```powershell
# 根据实际网络修改代理地址；可直接访问 Hugging Face 时省略这两行。
$env:http_proxy = 'http://192.168.1.38:7897'
$env:https_proxy = 'http://192.168.1.38:7897'
python download_models.py --models-dir .\models
python verify_models.py --models-dir .\models
```

看到 `verifiedFiles: 874` 表示本页所需的 43 个 `.axmodel` 及分词器、字典、ONNX 组件等配套文件均已核对。下载脚本固定仓库提交，并逐文件检查 SHA-256；中断后可重跑，已校验的文件会跳过。不要混用仓库内的 SoC 运行程序与本页 AXCL 程序。

将部署包的 `board` 目录复制到 RK3576。下方以 `baiwen@192.168.1.44` 为例，按实际用户名与地址修改：

```powershell
ssh baiwen@192.168.1.44 "mkdir -p ~/openclaw-media-axcl"
scp -r .\board baiwen@192.168.1.44:~/openclaw-media-axcl/
```

PC 终端一启动只读文件服务，并保持运行：

```powershell
python serve_models.py --models-dir .\models --port 18867
```

PC 终端二建立 SSH 转发，并保持连接：

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -R 127.0.0.1:18868:127.0.0.1:18867 baiwen@192.168.1.44
```

在 RK3576 终端以普通用户挂载模型，不加 `sudo`：

```bash
mkdir -p ~/openclaw-media-axcl/models
rclone mount :http: ~/openclaw-media-axcl/models \
  --http-url http://127.0.0.1:18868/ \
  --read-only --vfs-cache-mode off --buffer-size 0 \
  --vfs-read-chunk-size 8M --vfs-read-chunk-size-limit 32M \
  --config /dev/null --daemon

cd ~/openclaw-media-axcl/board
export MODELS="$HOME/openclaw-media-axcl/models"
python3 run_media.py --models-dir "$MODELS" check
```

确认输出包含 `verifiedModelFiles: 874`，并显示算力卡信息。如果读取失败，先检查两个 PC 终端和 SSH 连接。板端已有足够存储时，也可将 `models` 完整复制到板端，再将 `MODELS` 指向该目录。

## 运行语音识别

在 RK3576 终端识别仓库随附的中文录音：

```bash
python3 run_media.py --models-dir "$MODELS" asr \
  "$MODELS/media/SenseVoiceSmall-axmodel/test_wavs/zh.wav" --language zh
```

终端输出实际转写文字。换用 `en.wav` 并指定 `--language en` 可识别英文样例。自有录音使用绝对路径；`--language auto` 开启自动语言识别。超过 10 秒的音频由脚本先做语音活动检测，再分段识别。

## 运行语音合成

在 RK3576 终端生成 WAV 文件：

```bash
python3 run_media.py --models-dir "$MODELS" tts \
  "$PWD/kokoro-v1_0.wav" '你好，欢迎使用算力卡。' --version 1_0

python3 run_media.py --models-dir "$MODELS" tts \
  "$PWD/kokoro-v1_1.wav" '你好，欢迎使用算力卡。' --version 1_1

ffprobe -v error -show_entries stream=sample_rate,channels kokoro-v1_0.wav
```

输出应为 24 kHz、单声道音频。默认使用音色编号 1、正常语速。Kokoro 的 6 个 AXModel 阶段在卡端运行，时长预测及声码器尾部使用配套 ONNX；发音和文本完整性需结合试听检查。

在 PC 下载录音后播放：

```powershell
scp baiwen@192.168.1.44:~/openclaw-media-axcl/board/kokoro-v1_0.wav .
scp baiwen@192.168.1.44:~/openclaw-media-axcl/board/kokoro-v1_1.wav .
```

## 运行图片与视频问答

语音命令结束后，在 RK3576 终端一启动视觉语言服务：

```bash
cd ~/openclaw-media-axcl/board
export MODELS="$HOME/openclaw-media-axcl/models"
python3 run_media.py --models-dir "$MODELS" serve
```

等待模型加载完成。RK3576 终端二检查服务，再提交仓库随附图片：

```bash
cd ~/openclaw-media-axcl/board
export MODELS="$HOME/openclaw-media-axcl/models"
curl --noproxy '*' --fail http://127.0.0.1:8120/health

python3 run_media.py --models-dir "$MODELS" image \
  "$MODELS/media/vlm/Qwen3-VL-2B-Instruct-GPTQ-Int4/image.png"
```

服务返回图片描述。也可在图片路径后添加问题，例如 `'图中有几位宇航员？请只回答数量。'`。

下载下方的[实测视频片段](/validation/effects/openclaw-ax8850-qqbot-media-20261004/stone-mill-10s.mp4)，将文件名改为 `stone-mill-10s.mp4`，复制到 RK3576 的 `~/openclaw-media-axcl/board/`，再执行：

```bash
python3 run_media.py --models-dir "$MODELS" video "$PWD/stone-mill-10s.mp4"
```

默认均匀采样 8 帧，再间隔选取 4 帧，以原生视频输入提交；默认最多生成 512 token。下方保留原始问题的实际回复。该示例存在字幕与动作描述偏差，不能据此判断完整视频内容准确性。

若需要聚焦问题，可在视频路径后添加一句具体提问。不要通过不断增加帧数来处理长视频；修改采样和生成参数后需重新检查模型容量与结果。

## 停止服务

在视觉语言服务终端按 `Ctrl+C`，等待进程退出后检查 `axcl-smi`。同一部署目录会限制同时加载模型；如需继续语音处理，先退出视觉语言服务。

全部测试结束后，在 RK3576 终端执行：

```bash
fusermount3 -u ~/openclaw-media-axcl/models
```

再结束 PC 上的 SSH 转发和文件服务。原始模型仍保存在 PC，可供下一次使用。
