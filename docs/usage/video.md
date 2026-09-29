---
title: "处理视频与接入视频流"
---

# 处理视频与接入视频流

Linux 主机先完成静态图片模型验证。视频应用还包含取流、解码、缩放、前后处理、绘制、编码和输出；单个模型的 NPU 耗时不代表整条链路性能。

## 检查 AXCL FFmpeg

原厂 AXCL FFmpeg 基于 FFmpeg 7.1，提供 `h264_axdec`、`hevc_axdec` 等设备解码器及 `ax_scale` 滤镜。普通发行版的 `/usr/bin/ffmpeg` 不一定包含这些模块。

```bash
test -x /usr/bin/axcl/ffmpeg
export LD_LIBRARY_PATH="/usr/lib/axcl/ffmpeg:${LD_LIBRARY_PATH:-}"
/usr/bin/axcl/ffmpeg -hide_banner -decoders | grep -E 'h264_axdec|hevc_axdec'
/usr/bin/axcl/ffmpeg -hide_banner -filters | grep ax_scale
```

模块缺失时按官方说明安装匹配版本的 FFmpeg 组件。不要通过重命名普通 ffmpeg 假定获得卡端加速。

## 先检查输入视频

使用主机已安装的 `ffprobe` 检查自己的视频文件。

```bash
ffprobe -v error -show_streams -show_format ~/edgeaccel/inputs/clip.mp4
```

记录编码格式、分辨率、帧率、时长和是否含音轨。按 [AXCL FFmpeg 使用说明](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_ffmpeg.html)选择对应解码器和设备输入流程；`ax_scale` 使用设备帧，输出回主机时通常需要 `hwdownload` 与指定像素格式，不能把软件帧直接交给设备滤镜。

## 组成单路 AI 流程

```mermaid
flowchart LR
  A[文件或视频流] --> B[解码与缩放]
  B --> C[模型前处理]
  C --> D[AXCL 推理]
  D --> E[后处理与绘制]
  E --> F[显示 保存 或推流]
```

应用可参考 [ax-pipeline](https://github.com/AXERA-TECH/ax-pipeline) 与 [ax-video-sdk](https://github.com/AXERA-TECH/ax-video-sdk)，选择项目明确支持 AXCL 的模块。芯片板端 MSP 示例不等于主机算力卡示例。

先使用本地短视频，确认帧序、颜色、框位置、时间戳和输出可播放，再替换为网络流。相机断流、重连及分辨率变化需单独验证。

## 扩展多路处理

从一路逐步增加路数，分别记录输入、解码、推理和输出 FPS，检查队列增长、丢帧和端到端延迟。减少复制、调整推理频率或降低输入分辨率时重新检查业务效果。

完整示例见[AX8850 六路 AI 视频推流](../projects/six-streams.md)。先在项目总览确认开发版或演示版，再按对应说明启动。项目性能数据仅适用于记录中的模型组合与环境，更换模型后需重新测量。
