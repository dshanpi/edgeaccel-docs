---
title: "六路推流：VLC 播放排查"
sidebar_label: "VLC 播放排查"
slug: /ax650n/applications/six-streams/vlc-troubleshooting
---

# 排查 VLC 播放中断

适用于 `~/ax-pipeline/six` 开发版。先区分推流程序停止、网络连接中断与播放器停止；演示版使用不同服务名，需按[项目总览](/docs/projects/six-streams)核对。

## 1. 检查推流程序

画面停止时先记录时间，在开发板终端查看最近日志：

```bash
sudo journalctl -u ax-six-rtsp -u ax-six-local-preview --since '10 minutes ago' -o short-iso
```

- 若解码、推理、编码计数仍在增加，继续检查播放连接。
- 若程序退出或计数停止，先按日志检查输入、模型和设备；需要时参阅[通用故障处理](/docs/usage/troubleshooting)。
- `interleaved send timeout/failed` 表示服务端向客户端发送失败或超时，单凭此日志不能确定是播放器主动退出、接收阻塞还是显示线程异常。

## 2. 核对播放地址

| 播放位置 | 地址 |
|---|---|
| 开发板自带 VLC | `http://127.0.0.1:8850/overview.ts` |
| 局域网另一台电脑 | `rtsp://BOARD_IP:8554/overview`，替换 `BOARD_IP` 为开发板实际 IP |

原开发板 VLC 未启用 live555，使用本地 HTTP 转封装服务播放。其他电脑使用 RTSP。详见[本地预览说明](local-preview.md)。

## 3. 保存播放器日志后重试

先保存故障时的播放器状态和日志，再完整退出 VLC。在开发板桌面终端运行：

```bash
cd ~/ax-pipeline/six
./preview-debug.sh
```

该脚本打开新的 VLC 进程，日志保存在 `~/ax-pipeline/six/logs/vlc/`，不改变模型、输入视频或显示后端。再次断流时，将同一时段的 VLC 日志与服务日志对照，判断哪一端先停止读取或关闭连接。

恢复播放后持续观察画面和计数。短时恢复不等于根因已修复，`axcl-smi` 正常也不能单独证明推流或播放器正常。

<details>
<summary>2026-09-18 排查记录与已知限制</summary>

原 RK3576 + AX8850 16GB 部署曾出现本地 VLC 停止、推流程序仍持续运行的情况。重启 VLC 后约 5 分钟未复现，尚未确认最初断流的根因。

## 已确认的证据

- 六路进程自 9 月 16 日 19:28 持续运行，检查时已约 40 小时；六路计数和六宫格编码计数继续增加，各路 `mux_errors`、`submit_errors` 为 0。
- 9 月 18 日 10:46:55、10:57:56，RTSP 服务记录 `interleaved send timeout/failed, dropping session send loop`。对应本地预览连接于 10:47:12、10:58:13 关闭。
- 服务端代码对 TCP 发送设置了 2 秒超时。上述日志表明向播放客户端发送失败或超时，单凭这条日志不能区分客户端主动关闭、接收阻塞与显示线程异常。
- 主机检查时可用内存约 2.5 GiB，磁盘空余约 20 GiB；本轮检查未发现内存耗尽的证据。

本地播放路径：算力卡 H.264 输出 → RTSP `8554` → FFmpeg 仅转封装 → HTTP `8850` → 开发板 VLC 解码显示。

## 对照测试

| 测试 | 结果 |
|---|---|
| FFmpeg 直接拉 RTSP，保持压缩码流 | 380 秒媒体时长，正常结束，无错误日志 |
| FFmpeg 拉本地 HTTP，保持压缩码流 | 380 秒媒体时长，正常结束，无错误日志 |
| VLC 解码但使用 dummy 显示输出 | 约 392 秒，显示计数增至 11701，丢帧计数 0 |
| 完整重启桌面 VLC，保留默认显示方式 | 连续约 5 分钟未复现断流；日志保存在下述目录 |

桌面 VLC 默认显示路径的 CPU 占用约 260%（100% 为一个核心），日志有 VA-API 初始化失败及少量显示延迟。它是进一步排查的线索，**不是已证实的断流根因**。

另测试了 X11 输出和两线程软件解码，CPU 降至约 149%，但约一半显示帧被丢弃，故已放弃该设置并恢复默认显示路径。该实验没有修改六路推流配置。

证据位于原主机 `~/ax-pipeline/six/evidence/vlc-disconnect-20260918/`，包含 `vlc-restored.log`；网站副本见[原始附件目录](/docs/reference/original-files)中同名目录。

</details>
