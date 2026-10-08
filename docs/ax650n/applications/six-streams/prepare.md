---
title: "准备六路推流运行环境"
sidebar_label: "1. 准备环境"
pagination_prev: projects/six-streams
pagination_next: ax650n/applications/six-streams/implementation
---

# 准备运行环境

以下命令在 RK3576 的 Linux 终端执行。先完成 [ARM64 主机环境安装](../../quick-start/arm64.md)，连接算力卡并保持散热风扇运行。

## 检查主机与算力卡

```bash
export PATH="/usr/bin/axcl:$PATH"
uname -m
uname -r
lspci -nn
axcl-smi
```

AXCL 工具默认位于 `/usr/bin/axcl`；重新打开终端后如找不到命令，可再次设置上述 `PATH` 或使用工具的绝对路径。

预编译程序用于 `aarch64`。`axcl-smi` 应显示 AX8850、驱动与固件版本，且没有设备通信错误。默认配置使用设备 0；执行期间应停止其他占用该卡的推理任务。

仓库记录的参考环境为 RK3576、Ubuntu 24.04、内核 6.1.115、AXCL 3.16.0、AX8850 16GB 和 OpenCV 4.6。其他系统、SDK 或容量组合需要重新验收，不能直接套用该环境的性能结果。

## 确认散热后再启动

上电后先确认算力卡散热风扇实际转动、进出风口没有遮挡，再执行推流。风扇需要在整个演示期间保持运行，不能仅凭设备被识别就判断散热正常。

启动前记录一次温度，运行后在另一终端观察：

```bash
watch -n 5 /usr/bin/axcl/axcl-smi
```

按 `Ctrl+C` 退出观察。温度持续上升、出现设备告警或推理停止时，先停止推流，再检查风扇供电和散热接触；恢复散热并重新检查设备后再运行。后文的实测温度仅用于说明当次条件，不作为产品工作温度上限。

## 安装依赖

```bash
sudo apt update
sudo apt install -y git git-lfs build-essential cmake pkg-config \
  libopencv-dev python3 ffmpeg util-linux
cmake --version
pkg-config --modversion opencv4
ffmpeg -version
```

源码构建需要 CMake 3.18 及以上、支持 C++17 的编译器和完整 AXCL 开发文件。默认 SDK 路径检查如下：

```bash
test -f /usr/include/axcl/axcl.h && echo 'AXCL headers OK'
test -f /usr/lib/axcl/libaxcl_rt.so && echo 'AXCL runtime OK'
```

需要开发板桌面播放时，再安装 VLC；仅使用电脑播放 RTSP 时可以跳过。

```bash
sudo apt install -y vlc
```

## 预留存储空间

```bash
df -h "$HOME"
free -h
```

模型和视频合计约 1 GB，Git LFS 缓存还会保存一份资源。建议部署位置至少有 **4 GB 可用空间**，录像另行预留。后续默认目录为 `~/ax8850-multistream-demo`；如使用存储卡或 SSD，请在挂载目录克隆，并将后续命令中的项目路径统一替换。运行期间保持存储设备挂载。

## 检查端口与已有服务

```bash
sudo ss -ltnp | grep -E ':(8554|8850)\b' || true
systemctl is-active ax8850-multistream ax8850-local-preview
```

首次安装时服务显示 `inactive` 或未找到属于正常情况。端口 `8554` 用于局域网 RTSP，`8850` 用于开发板本机预览。若已有服务监听，先确认其用途，再按[服务管理](../../../usage/services.md)停止对应演示。启动脚本遇到端口占用会退出。

准备完成后，继续[获取项目与准备程序](implementation.md)。
