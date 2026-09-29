---
title: "六路推流：启动、观看与录制"
sidebar_label: "开发版：启动与观看"
slug: /ax650n/applications/six-streams/usage
pagination_prev: projects/six-streams
pagination_next: ax650n/applications/six-streams/local-preview
---

# 启动、观看与录制六路视频

适用于已部署 `~/ax-pipeline/six` 的 RK3576 主机。项目功能及两套部署的区别见[项目总览](/docs/projects/six-streams)；使用 `~/ax8850-multistream-demo` 的主机请按[演示版服务管理](/docs/usage/services)操作。

项目源码与新部署说明见 [GitHub 仓库](https://github.com/dshanpi/ax8850-multistream-demo)；本文中的原部署路径与记录按下述环境使用。

## 1. 确认环境并启动

在运行推流程序的开发板终端执行：

```bash
cd ~/ax-pipeline/six
test -x ./bin/six_app && test -f ./config.json && test -f ./start.sh
sudo /usr/bin/axcl/axcl-smi
```

确认目录、程序和配置存在，SMI 能识别设备。模型、输入视频与插件路径须与 `config.json` 一致；缺少文件时先补齐项目环境。启动前停止其他占用同一卡或 `8554`、`8850` 端口的演示服务。

```bash
./start.sh
sudo journalctl -u ax-six-rtsp -n 20 -o cat
```

`start.sh` 启动 `ax-six-rtsp` 和本地预览服务 `ax-six-local-preview`，也会停止开发版原有的 `ax-pipeline-pcd` 服务。日志中的 `decoded`、`rendered`、`inferred`、`encoded` 应持续增加；`mux_errors`、`submit_errors` 应为 0。出现模型加载、输入文件或端口错误时，先排查再播放。

## 2. 观看六宫格

将下面的 `BOARD_IP` 替换为开发板实际局域网 IP。在另一台电脑的 VLC 中选择 **媒体 → 打开网络串流**，输入：

```text
rtsp://BOARD_IP:8554/overview
```

六宫格为 **1920×1080，3 列 × 2 行**。

![六路总览](/resources/ax650n/aarch64/AX8850%E5%85%AD%E8%B7%AFAI%E6%8E%A8%E6%B5%81/images/overview-no-filenames.jpg)

开发板自带 VLC 使用本地 HTTP 地址：

```text
http://127.0.0.1:8850/overview.ts
```

这里的 `127.0.0.1` 指开发板自身。该预览服务仅监听本机，其他电脑使用 RTSP 地址。详见[本地预览与输入视频](/docs/ax650n/applications/six-streams/local-preview)。

## 3. 观看单路并检查结果

将下表路径接到 `rtsp://BOARD_IP:8554` 后，例如第四路为 `rtsp://BOARD_IP:8554/driving`。

| 通道 | 输入视频 | 模型与显示结果 | 路径 |
|---|---|---|---|
| 1 | `traffic.mp4` | PCD：人、车、骑行者检测与跟踪 | `/pcd` |
| 2 | `traffic4.mp4` | YOLOv8s：道路目标检测 | `/vehicle` |
| 3 | `traffic3_slow_0p5x.mp4` | YOLO26n-Seg：实例分割与检测框 | `/seg` |
| 4 | `traffic7_slow_0p5x.mp4` | YOLO26n + ByteTrack：检测与跟踪 ID | `/driving` |
| 5 | `traffic5.mp4` | YOLO26n-Depth：相对深度热力图 | `/depth` |
| 6 | `traffic6.mp4` | YOLOv8s + ByteTrack：跟踪与过线计数 | `/count` |

第三、四路使用 0.5 倍速视频，分辨率为 1920×1080，输出帧率分别为 30、29.97 FPS。输入变慢用于观察模型结果，不代表推理速度翻倍。

检查各路画面更新、检测框、分割掩码、跟踪 ID、深度热力图与计数是否符合输入：

- 第四路保留有效检测框，轨迹确认后显示 `#ID`；不提供车道线或可行驶区域分割。
- 第五路亮色表示相对更近，不是经过校准的米制距离。
- 第六路同一 ID 只计一次；视频循环时重置跟踪并保留总计数，重启程序后清零。移动视角的过线次数不等同于固定路口流量。

## 4. 查看帧率与录制视频

启动约 25 秒后，在开发板终端执行：

```bash
cd ~/ax-pipeline/six
sudo ./fps.py
```

`New video` 表示新画面更新率，`AI` 表示推理结果更新率，`Encode` 表示编码输出率。视频与推理独立更新，标注可能稍滞后于快速运动的画面。原 16GB 测试环境的数据见[实测结果](/docs/ax650n/applications/six-streams/validation)与[推理性能优化](/docs/ax650n/applications/six-streams/inference)。

录制一分钟六宫格：

```bash
cd ~/ax-pipeline/six
./record-overview.sh 60
```

MP4 保存在 `~/ax-pipeline/six/recordings/`，直接保存算力卡编码输出，不进行软件重编码。打开新生成的文件，确认时长、画面和标注。

[已保存的优化版录像](/resources/ax650n/aarch64/AX8850%E5%85%AD%E8%B7%AFAI%E6%8E%A8%E6%B5%81/%E5%85%AD%E8%B7%AFAI%E6%80%BB%E8%A7%88_%E5%B8%A7%E7%8E%87%E4%BC%98%E5%8C%96%E7%89%88_1080p30.mp4)使用替换前的第四路 `traffic2`，用于对照当次验证；`traffic7` 请查看实际部署的预览画面。

## 5. 停止与修改配置

停止推流与本地预览：

```bash
cd ~/ax-pipeline/six
./stop.sh
```

修改前备份 `config.json`。输入路径、模型、插件、源帧率等参数见[模型配置与构建](/docs/ax650n/applications/six-streams/implementation)。修改后执行 `./start.sh`，重新检查日志和各路输出。

本开发版使用脚本创建运行期服务，主机重启后按本页重新启动。需要管理演示版开机自启时，使用其[专用说明](/docs/usage/services)。播放中断时见[VLC 播放排查](/docs/ax650n/applications/six-streams/vlc-troubleshooting)。
