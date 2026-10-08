---
title: "处理视频与接入视频流"
description: "用 YOLOv8n 处理固定交通视频，生成检测结果，并验证 HTTP 视频输入与服务停止。"
mdx:
  format: mdx
---

import useBaseUrl from '@docusaurus/useBaseUrl';

# 处理视频与接入视频流

将已跑通的图片推理扩展到视频：读取交通视频前 10 秒，每秒抽取一帧，在算力卡上检测，再生成带检测框的 MP4。随后用 HTTP 地址读取同一视频，检查网络输入的结果。

本页固定使用 **RK3576 DShanPi-A1 + AX8850 16GB、AXCL 3.16.0、YOLOv8n NPU3**。视频解码、抽帧和编码由主机 FFmpeg 完成，模型推理由 `AXCLRTExecutionProvider` 完成。该流程用于理解应用接入，不作为实时吞吐或硬件视频加速的性能示例。

## 准备模型与工具

先完成[Python 图片推理](python.md)，保留该页下载的模型、`ax_infer.py` 与虚拟环境。本页沿用相同的 `EDGEACCEL_WORK` 设置，另外预留约 150 MB 空间。

```bash
sudo apt-get install -y ffmpeg curl
APP_ROOT=${EDGEACCEL_WORK:-$HOME/edgeaccel/application-guides}
source "$APP_ROOT/python/env/bin/activate"
mkdir -p "$APP_ROOT/video"
cd "$APP_ROOT/video"
/usr/bin/axcl/axcl-smi
ffmpeg -version
```

本次主机使用系统 FFmpeg，输出编码器为 `libx264`。不将系统 `/usr/bin/ffmpeg` 与 AXCL SDK 中的 `/usr/bin/axcl/ffmpeg` 混用。

## 下载固定输入视频

视频取自 [dshanpi/ax8850-multistream-demo 固定提交](https://github.com/dshanpi/ax8850-multistream-demo/tree/2aa772bbf16b8a904ee6ca57877c0e602208bf49)，本页只使用 `traffic4.mp4`。

```bash
curl -fL --retry 2 \
  https://media.githubusercontent.com/media/dshanpi/ax8850-multistream-demo/2aa772bbf16b8a904ee6ca57877c0e602208bf49/videos/traffic4.mp4 \
  -o traffic4.mp4
printf '%s  %s\n' \
  7061eeb147b7d4ee04253ddc062348f92c57b04014e9838319b905c8132846f9 \
  traffic4.mp4 | sha256sum -c -
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of default=nw=1 traffic4.mp4
```

校验必须为 `OK`，视频信息为 H.264、1920 × 1080、25 FPS。下载需要代理时，使用 [Python 页的代理设置](python.md#准备设备与目录)。

## 保存视频处理脚本

在当前目录复制执行。脚本接收输入路径或 HTTP 地址，将前 10 秒抽成 10 张图片；每张图片运行一次同版本官方检测脚本。

```bash
cat > process-video.sh <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
APP_ROOT=${EDGEACCEL_WORK:-$HOME/edgeaccel/application-guides}
SOURCE=${1:?请传入视频文件或HTTP地址}
OUT=${2:?请传入新的结果目录}
[ ! -e "$OUT" ] || { echo "结果目录已存在，请使用新目录" >&2; exit 1; }
mkdir -p "$OUT/frames" "$OUT/results"
ffmpeg -nostdin -hide_banner -loglevel error -y \
  -i "$SOURCE" -t 10 -vf fps=1 -frames:v 10 "$OUT/frames/%03d.jpg"
shopt -s nullglob
FRAMES=("$OUT"/frames/*.jpg)
[ "${#FRAMES[@]}" -eq 10 ] || { echo '抽帧数量不是 10' >&2; exit 1; }
for INPUT in "${FRAMES[@]}"; do
  NAME=$(basename "$INPUT")
  "$APP_ROOT/python/env/bin/python" "$APP_ROOT/python/ax_infer.py" \
    --model-path "$APP_ROOT/python/AX650/yolov8n_640x640_npu3.axmodel" \
    --test-img "$INPUT" --img-save-path "$OUT/results/$NAME" \
    --score-thres 0.25 --nms-thres 0.7 \
    --providers AXCLRTExecutionProvider >"$OUT/results/$NAME.log" 2>&1
  test -s "$OUT/results/$NAME"
done
ffmpeg -nostdin -hide_banner -loglevel error -y \
  -framerate 1 -i "$OUT/results/%03d.jpg" -frames:v 10 \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$OUT/result.mp4"
ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=codec_name,width,height,nb_read_frames:format=duration \
  -of default=nw=1 "$OUT/result.mp4"
ffmpeg -nostdin -v error -i "$OUT/result.mp4" -f null -
echo VIDEO_OK
SH
```

为便于逐步核对，脚本每帧独立加载模型。开发连续视频应用时应复用推理会话，并处理队列、帧丢弃和异常恢复；本页不以这种逐帧进程方式衡量实时性能。

## 处理本地文件

```bash
bash process-video.sh "$PWD/traffic4.mp4" local-output
```

应显示 `nb_read_frames=10`、`duration=10.000000` 和 `VIDEO_OK`。结果在 `local-output/result.mp4`，每帧图片和日志分别在 `frames/` 与 `results/`。重复操作时改用新的输出目录，避免旧结果混入。

## 接入 HTTP 视频源

先启动仅监听本机的示例源，不需要外部摄像头。在同一终端执行：

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory "$PWD" \
  >http-source.log 2>&1 </dev/null &
SOURCE_PID=$!
export no_proxy=localhost,127.0.0.1
curl --noproxy '*' --retry 10 --retry-connrefused --retry-delay 1 \
  -fsS -o /dev/null http://127.0.0.1:8765/
bash process-video.sh http://127.0.0.1:8765/traffic4.mp4 http-output
```

这一步验证 HTTP 视频读取与后续推理。本次使用本机回环网络，没有覆盖摄像头、RTSP 输入、跨设备网络、断线重连或多路实时接入。

核对本地与 HTTP 输入路径的逐帧结果：

```bash
python - <<'PY'
from pathlib import Path
for subdir in ['frames', 'results']:
    files = sorted((Path('local-output') / subdir).glob('*.jpg'))
    assert len(files) == 10
    for file in files:
        assert file.read_bytes() == (Path('http-output') / subdir / file.name).read_bytes()
print('本地与 HTTP 输入、检测图片均为 10/10 一致')
PY
```

## 查看部署效果

以下为本页实际生成的 **10 秒、1 FPS** 检测视频。低帧率来自固定抽帧设置，不能解释为模型只能处理 1 FPS。

<video controls playsInline preload="metadata" style={{width: '100%'}} poster={useBaseUrl('/examples/application-guides/video-frame.jpg')} src={useBaseUrl('/examples/application-guides/video-result.mp4')} aria-label="YOLOv8n 交通视频实际检测结果" />

| 检查项 | 实际结果 |
| --- | --- |
| 本地文件 | 完成 10 帧推理并生成 MP4 |
| HTTP 输入 | 完成 10 帧推理并生成 MP4 |
| 两种输入路径 | 10 张抽帧图片与 10 张检测图片逐文件一致 |
| 输出视频 | H.264，1920 × 1080，10 帧，10 秒 |
| 完整解码检查 | 两份输出视频均通过 |

可见车辆检测框随输入画面变化。检测存在漏检或误检的可能；本页验证应用流程和输出一致性，不报告交通视频检测准确率。

## 停止视频源并检查资源

处理脚本正常结束后自动退出；提前结束前台处理可按 `Ctrl+C`。保留启动 HTTP 源的终端，在该终端执行：

```bash
kill "$SOURCE_PID"
wait "$SOURCE_PID" || true
if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8765/ >/dev/null 2>&1; then
  echo '端口仍可访问，请核对监听进程'
else
  echo 'HTTP 视频源已停止'
fi
deactivate
/usr/bin/axcl/axcl-smi
```

本次停止后 8765 端口不可访问，算力卡无残留推理进程，CMM 回到空闲基线。

## 扩展到多路实时推流

需要硬件解码、检测 / 分割 / 深度叠加、RTSP 输出与桌面预览时，按[AX8850 六路 AI 视频推流](../projects/six-streams.md)的准备、编译、启动和预览顺序部署。该项目统一使用 `dshanpi/ax8850-multistream-demo`，服务启停按项目中的 `start.sh`、`stop.sh` 操作。
