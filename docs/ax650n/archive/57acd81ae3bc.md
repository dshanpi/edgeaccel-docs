---
title: "推理优化前_20260916_182855 · 使用说明"
sidebar_label: "推理优化前_20260916_182855 · 使用说明"
slug: /ax650n/archive/57acd81ae3bc
---

> **历史版本**：保留原始操作和验证记录，仅供追溯。缺失的共享图片和文档链接已指向现有资料，可能与该历史版本不同；当前操作请参阅[六路 AI 视频推流](/docs/ax650n/applications/six-streams/usage)。

# AX8850 六路 AI 视频推流

开发板：`192.168.1.44`；程序目录：`~/ax-pipeline/six`。

## 1 查看六宫格

在 VLC 中选择 **媒体 → 打开网络串流**，输入：

```text
rtsp://192.168.1.44:8554/overview
```

总览为 **1920×1080、3 列 × 2 行**，六格按下表排列。

![六路总览](/resources/ax650n/aarch64/AX8850%E5%85%AD%E8%B7%AFAI%E6%8E%A8%E6%B5%81/images/overview-traffic7.jpg)

开发板自带 VLC 请使用 **`http://127.0.0.1:8850/overview.ts`**。第四路本地地址为 **`http://127.0.0.1:8850/driving.ts`**；桌面播放列表 `AX8850-local-preview.m3u` 可直接打开。详见[本地预览说明](/docs/ax650n/applications/six-streams/local-preview)。

## 2 查看单路

下表路径均加在 `rtsp://192.168.1.44:8554` 后面。

| 路数 | 输入视频 | 模型与显示结果 | 路径 |
|---|---|---|---|
| 1 | traffic.mp4 | 原 PCD：人、车、骑行者检测与跟踪 | `/pcd` |
| 2 | traffic4.mp4 | YOLOv8s：道路目标检测 | `/vehicle` |
| 3 | traffic3.mp4 | YOLO26n-Seg：实例分割与检测框 | `/seg` |
| 4 | traffic7.mp4 | YOLO26n + ByteTrack：道路目标检测与跟踪 ID | `/driving` |
| 5 | traffic5.mp4 | YOLO26n-Depth：相对深度热力图 | `/depth` |
| 6 | traffic6.mp4 | YOLOv8s + ByteTrack：车辆跟踪与过线计数 | `/count` |

第四路单独观看：

```text
rtsp://192.168.1.44:8554/driving
```

![第四路检测与跟踪](/resources/ax650n/aarch64/AX8850%E5%85%AD%E8%B7%AFAI%E6%8E%A8%E6%B5%81/images/driving-traffic7.jpg)

第四路保留有效检测框，跟踪确认后显示 `#ID`；尚未形成轨迹的目标也显示检测框。车内人物可能被检出，远处小目标仍可能漏检。这一路不提供车道线或可行驶区域分割。

第五路亮色表示相对更近，不是经过校准的米制距离。第六路统计穿过画面参考线的目标：同一 ID 只计一次，视频循环时重置跟踪并保留总计数，重启程序后清零。移动视角的过线次数不等同于固定路口车流量。

## 3 启动、停止

当前已运行。开发板重启后手动启动：

```bash
cd ~/ax-pipeline/six
./start.sh
```

停止：

```bash
cd ~/ax-pipeline/six
./stop.sh
```

查看日志：

```bash
sudo journalctl -u ax-six-rtsp -n 20 -o cat
```

`decoded`、`rendered`、`inferred`、`encoded` 应持续增加；`mux_errors`、`submit_errors` 应为 0。

## 4 保存合并视频

录制一分钟六宫格：

```bash
cd ~/ax-pipeline/six
./record-overview.sh 60
```

MP4 保存在 `~/ax-pipeline/six/recordings/`，直接保存算力卡编码输出，不进行软件重编码。

之前保存的[帧率优化版总览视频](/resources/ax650n/aarch64/AX8850%E5%85%AD%E8%B7%AFAI%E6%8E%A8%E6%B5%81/%E5%85%AD%E8%B7%AFAI%E6%80%BB%E8%A7%88_%E5%B8%A7%E7%8E%87%E4%BC%98%E5%8C%96%E7%89%88_1080p30.mp4)约一分钟，其中第四路为替换前的 traffic2；最新 traffic7 请看实时预览。[验证结果](/docs/ax650n/applications/six-streams/validation)记录了实测速率。

## 5 修改配置

配置：`~/ax-pipeline/six/config.json`。修改后执行 `./stop.sh`、`./start.sh`。

输入视频位于 `~/ax-pipeline/video/1080p/`，均为 1920×1080 H.264，原始视频仍保留。预处理保留各自源帧率。

第四路使用 `libax_plugin_yolo26.so`；跟踪由六路程序管理，插件中的 `enable_tracking` 保持 `false`，避免重复跟踪。通道上的 `enable_tracking: true` 开启跟踪，`show_unconfirmed_detections: true` 保留未确认轨迹的检测框。

第六路 `line_x: 0.4` 表示参考线位于画面宽度的 40%。更换视频时需重新计算 `source_loop_us`，RTSP 实时源设为 0。

## 查看实时帧率

```bash
cd ~/ax-pipeline/six
sudo ./fps.py
```

启动约 25 秒后可查看。`New video` 是新画面更新率，`AI` 是推理结果更新率，`Encode` 是编码输出率。

六路视频接近源帧率 **12 / 25 / 30 / 30 / 24 / 24 FPS**，总览约 **30 FPS**。推理实测约 **12 / 9 / 6 / 9.6 / 10.6 / 8.5 FPS**，会随画面复杂度变化。

解码、模型执行、图像缩放、标注叠加、六宫格拼接和 H.264 编码在 AX8850 上执行。RK3576 负责后处理、跟踪、计数、小尺寸标注图和 RTSP 服务。

视频与推理独立更新，标注使用最新完成的推理结果，快速运动时可能稍有滞后。详见[帧率优化说明](/docs/ax650n/applications/six-streams/frame-rate)与[验证结果](/docs/ax650n/applications/six-streams/validation)。
