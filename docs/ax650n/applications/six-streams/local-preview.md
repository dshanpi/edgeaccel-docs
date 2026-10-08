---
title: "观看与录制六路 AI 视频"
sidebar_label: "4. 观看与录制"
mdx:
  format: mdx
pagination_prev: ax650n/applications/six-streams/usage
pagination_next: ax650n/applications/six-streams/validation
---

# 观看与录制

确认[推流服务已启动](usage.md)。可以在电脑播放局域网 RTSP，也可以在 RK3576 桌面播放本机预览。

## 查看部署效果

下面为 **在 RK3576 + AX8850 16GB 上实测录制**的六宫格结果，使用本指南指定仓库版本、默认模型和视频。画面包含检测框、分割区域、目标跟踪、相对深度与过线计数。

<video className="model-effect-video" controls playsInline preload="metadata" poster="/projects/six-streams-20261008/overview.jpg" src="/projects/six-streams-20261008/overview.mp4" aria-label="RK3576 与 AX8850 六路 AI 视频推流实测录像"></video>

本次请求录制 20 秒，生成 19.700 秒、1920×1080 H.264 视频，完整解码 591 帧通过。播放本段录像可先了解预期效果；观看自己的部署结果，请按下方步骤连接开发板。[实测帧率与验收范围](validation.md#查看本次实测结果)另有说明。

## 在电脑观看 RTSP

在 VLC 中打开“媒体 → 打开网络串流”，将下表的 `BOARD_IP` 替换为开发板实际地址。先打开总览，再按需查看单路结果。

| 画面 | 播放地址 |
|---|---|
| 六宫格总览 | `rtsp://BOARD_IP:8554/overview` |
| 目标检测 | `rtsp://BOARD_IP:8554/pcd` |
| 车辆检测 | `rtsp://BOARD_IP:8554/vehicle` |
| 实例分割 | `rtsp://BOARD_IP:8554/seg` |
| 检测与跟踪 | `rtsp://BOARD_IP:8554/driving` |
| 相对深度 | `rtsp://BOARD_IP:8554/depth` |
| 过线计数 | `rtsp://BOARD_IP:8554/count` |

电脑与开发板应网络互通，防火墙需允许 RTSP 访问。总览分辨率为 1920×1080；网络波动时优先在播放器选择 RTSP over TCP。

## 在开发板桌面观看

在已登录图形桌面的普通用户终端执行，不要使用 `sudo vlc`：

```bash
cd ~/ax8850-multistream-demo
bash preview-local.sh
```

默认播放总览；查看单路时传入对应名称：

```bash
bash preview-local.sh seg
```

脚本播放 `http://127.0.0.1:8850/overview.ts` 等本机地址，HTTP 服务通过 FFmpeg 复制封装码流，不重新编码。该地址只允许开发板本机访问，电脑端应使用 RTSP。播放器仍需解码，桌面播放会增加主机资源占用。

## 录制总览

在开发板终端执行，数字表示请求录制秒数：

```bash
cd ~/ax8850-multistream-demo
bash record-overview.sh 60
```

文件保存在 `recordings/overview-日期时间.mp4`，终端会显示实际路径。下面将 `FILE` 设置为刚生成的文件，再查看参数并完整解码：

```bash
FILE="recordings/overview-实际日期时间.mp4"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height:format=duration \
  -of default=noprint_wrappers=1 "$FILE"
ffmpeg -v error -i "$FILE" -map 0:v:0 -f null -
```

视频应为 H.264、1920×1080，完整解码应正常退出且没有错误输出。复制码流需要等待关键帧，实际文件可能略短于请求时长，应结合关键帧间隔和完整解码结果判断，不以短片必须精确满秒作为唯一标准。

完成播放与录像后，继续[效果与验收](validation.md)。
