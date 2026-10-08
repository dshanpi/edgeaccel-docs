---
title: "排查六路推流部署与播放问题"
sidebar_label: "9. 部署与播放排错"
pagination_prev: ax650n/applications/six-streams/inference
pagination_next: null
---

# 排查部署与播放问题

按资源 → 程序依赖 → 服务 → 码流 → 播放器的顺序检查。所有命令默认在 RK3576 项目目录执行。

## 根据现象定位

| 现象 | 优先检查 | 处理入口 |
|---|---|---|
| 提示 Git LFS pointer 或资源校验失败 | 模型、视频是否为真实文件 | `git lfs pull` 后重新运行 `tools/verify_assets.py` |
| `libopencv_*.so.406` 等库找不到 | 预编译程序与系统 ABI 是否匹配 | [检查依赖或源码构建](implementation.md) |
| 配置提示路径不存在 | 输入、模型、插件与运行目录 | [生成配置](implementation.md#生成配置并检查路径) |
| 提示端口占用 | `8554`、`8850` 的监听进程 | 确认旧部署后停止对应服务 |
| `axcl-smi` 找不到 | AXCL 工具路径和安装状态 | 尝试 `/usr/bin/axcl/axcl-smi`；检查 AXCL 环境安装 |
| `axcl-smi` 无法识别或访问设备 | PCIe、驱动、固件与设备状态 | 先恢复算力卡环境，再启动演示 |
| 服务 active 但某格不动 | 对应通道解码、AI、编码计数 | 查看当前实例日志与 `tools/fps.py` |
| 运行一段时间后推理停止或设备报错 | 风扇是否转动、温度变化、设备日志 | 停止负载，恢复散热，再检查设备与模型运行 |
| 本机可播、电脑不能播放 | IP、网络、防火墙、RTSP 传输方式 | 电脑使用开发板 IP 的 RTSP 地址，尝试 TCP |
| RTSP 可解码，本机 HTTP 不通 | `ax8850-local-preview` 服务 | 查看预览服务日志 |
| 命令行解码成功，但 VLC 卡顿 | 桌面解码、缓存、播放器日志 | 使用下方调试入口 |

## 查看服务与应用日志

```bash
systemctl status ax8850-multistream ax8850-local-preview --no-pager
sudo journalctl -u ax8850-multistream -n 100 --no-pager
sudo journalctl -u ax8850-local-preview -n 50 --no-pager
sudo ss -ltnp | grep -E ':(8554|8850)\b' || true
```

如果看到模型加载、NPU 执行或设备通信错误，先保存日志并停止本次任务。播放器重连不能修复算力卡执行错误。恢复设备后从资源、启动和码流检查重新验收。

设备错误码本身不能直接说明内存不足或硬件损坏。应同时核对散热、实际资源占用、驱动与固件版本，并在恢复条件后复测；重新运行成功也不能代替长期稳定性测试。

## 区分码流问题与播放器问题

先在板端执行[七路 RTSP 和 HTTP 解码检查](validation.md#检查七路-rtsp-解码)。本机 RTSP 正常但 HTTP 失败时，重点检查预览服务和 FFmpeg；两者均正常而 VLC 异常时，再检查桌面播放器。

在开发板图形桌面的普通用户终端运行：

```bash
cd ~/ax8850-multistream-demo
bash preview-debug.sh overview
```

脚本开启独立 VLC 实例，并将日志写入 `logs/vlc/`。测试单路时将 `overview` 换为对应名称。不要以 root 启动 VLC，也不要在没有图形会话的 SSH 终端中将无法显示窗口误判为推流失败。

## 恢复并复查

```bash
bash stop.sh
bash start.sh
```

重新启动后确认六路处理计数、七路解码和实际画面均恢复。若修改过输入或模型，优先[恢复已验收配置](frame-rate.md#回退)再复查。反复重启仍出现同一设备错误时，应继续检查驱动、固件和硬件状态，不以重复启动作为通过依据。
