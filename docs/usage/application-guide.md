---
title: "接入应用与维护"
pagination_prev: null
pagination_next: null
---

# 接入应用与维护

完成[首次推理](first-inference.md)并核对结果后，根据应用需要选择接口。以下内容按任务查阅，无需全部依次执行。

## 选择接入方式

| 需要完成的任务 | 阅读入口 |
|---|---|
| 用 Python 完成 YOLOv8n 图片检测 | [通过 Python 调用算力卡](python.md) |
| 通过 HTTP 调用 Qwen3-0.6B 中文问答 | [通过 HTTP 接入大模型](api-service.md) |
| 将图片推理扩展到本地视频与 HTTP 视频输入 | [处理视频与接入视频流](video.md) |
| 运行多路检测、分割、深度与跟踪演示 | [AX8850 六路 AI 视频推流](../projects/six-streams.md) |

## 检查与维护运行环境

| 使用场景 | 阅读入口 |
|---|---|
| 测量延迟、吞吐和连续运行表现 | [测量性能与稳定性](performance.md) |
| 备份、升级、回退或恢复设备 | [升级、备份与恢复环境](maintenance.md) |
| 驱动、内存、动态库或服务异常 | [按故障现象定位问题](troubleshooting.md) |
| DShanPi-A1 指定镜像的内核头问题 | [RK3576 内核头安装说明](../ax650n/reference/kernel-headers/install.md)与[编译验证记录](../ax650n/reference/kernel-headers/fixes.md)，仅用于文中注明的系统 |

六路演示的启停和开机自启管理已归入对应项目。操作前先在[项目总览](../projects/six-streams.md)确认部署目录与服务名。
