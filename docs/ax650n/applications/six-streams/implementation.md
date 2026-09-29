---
title: "六路推流：模型配置与构建"
sidebar_label: "模型配置与构建"
slug: /ax650n/applications/six-streams/implementation
---

# 修改模型配置与构建程序

**源码入口：[dshanpi/ax8850-multistream-demo](https://github.com/dshanpi/ax8850-multistream-demo)。** 新获取的项目使用仓库中的[源码](https://github.com/dshanpi/ax8850-multistream-demo/tree/main/src)、[配置](https://github.com/dshanpi/ax8850-multistream-demo/tree/main/configs)与[构建脚本](https://github.com/dshanpi/ax8850-multistream-demo/blob/main/build.sh)，操作以仓库 README 为准。下文保留原开发版的配置与构建方法。

适用于已部署 `~/ax-pipeline/six` 的开发版。先按[启动与观看](usage.md)确认现有配置能运行，再修改输入、模型或源码。演示版的服务管理见[对应说明](/docs/usage/services)。

## 核对构建环境

| 项目 | 位置或要求 |
|---|---|
| 应用源码 | `~/ax-pipeline/six/src/six_app.cpp` |
| 通道配置 | `~/ax-pipeline/six/config.json` |
| 编译入口 | `~/ax-pipeline/six/build.sh` |
| 依赖 | 原 ax-pipeline 源码与构建目录、AXCL、OpenCV、ax-video-sdk |
| 原 ax-pipeline 基线 | `ab4c3855c4ce694438c9752c3f56a52061952fef` |

[原开发版构建脚本（归档）](@site/static/resources/ax650n/aarch64/AX8850六路AI推流/source/build.sh)使用原主机 `/home/baiwen/ax-pipeline` 路径和 `build_axcl-aarch64_ci` 构建目录，并调用 `npu-perf-src/build-release.py`。迁移主机时先核对这些路径、依赖和服务用户；仅复制应用二进制或一份源码不能替代完整环境。

## 修改通道配置

在开发板停止项目并备份配置：

```bash
cd ~/ax-pipeline/six
./stop.sh
cp -a config.json "config.json.backup-$(date +%Y%m%d-%H%M%S)"
```

使用编辑器修改 `config.json`，参考[原开发版配置（归档）](@site/static/resources/ax650n/aarch64/AX8850六路AI推流/source/config.json)。

| 配置项 | 修改时核对 |
|---|---|
| `input`、`model`、`plugin` | 文件实际存在，模型与插件后处理匹配 |
| `source_fps` | 与输入视频帧率一致；总览 `output_fps` 不代替源帧率 |
| `output`、`overview` | 端口可用，单路路径互不冲突 |
| 第四路通道 `enable_tracking` | `true` 表示由六路应用执行 ByteTrack |
| 第四路插件 `plugin_options.enable_tracking` | 保持 `false`，避免重复跟踪 |
| `show_unconfirmed_detections` | 保留尚未形成确认轨迹的检测框 |
| 第六路 `line_x` | `0.4` 表示参考线位于画面宽度的 40% |
| 第六路 `source_loop_us` | 更换视频后重新计算循环时长；RTSP 实时源设为 0 |

输入视频、源帧率与半速处理说明见[本地预览与输入视频](local-preview.md)。更换模型时同时核对输入尺寸、预处理、输出张量和后处理插件，不能只替换 `.axmodel` 文件名。

## 编译并检查

仅修改配置时无需重新编译，执行 `./start.sh` 后检查即可。修改源码或插件后，在同一开发板终端执行：

```bash
cd ~/ax-pipeline/six
./stop.sh
bash build.sh && ./start.sh
```

构建成功后才启动程序。日志、单路画面和六宫格均按[使用说明](usage.md)重新检查；更换模型或线程配置后重新测量帧率。编译通过不等于模型输出或长时间稳定性已经验证。

## 保留版本与回退

修改前保存源码、二进制、插件、配置与构建脚本。回退时先停止服务，再恢复同一版本的配套文件。原项目的备份目录和回退范围见[帧率优化](frame-rate.md#回退)与[推理性能优化](inference.md#使用与回退)。其他主机不能假定这些备份已存在。

<details>
<summary>2026-09-16 模型调整记录</summary>

第三路采用 YOLO26n-Seg，第四路采用 YOLO26n + ByteTrack，第五路采用 YOLO26n-Depth；第一路 PCD、第二路 YOLOv8s 与第六路计数保持原配置。当时第四路输入为 `traffic2.mp4`，之后替换为 `traffic7_slow_0p5x.mp4`。

YOLO26n 模型来自 AXERA-TECH/yolo26 的 `ax650/yolo26n.axmodel`，使用 `libax_plugin_yolo26.so` 解码六个输出头。原模型校验记录见[模型清单](@site/static/resources/ax650n/aarch64/AX8850六路AI推流/evidence/models.json)。

当次修改重新编译了 `six/bin/six_app`，没有修改 AXP、PAC、AXCL 驱动、内核或原 PCD 模型。调整前文件保存在原主机 `six/backups/before-yolo26-20260916-170303/`。

</details>
