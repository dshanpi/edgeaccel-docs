---
title: "启动并检查六路视频推流"
sidebar_label: "3. 启动并检查"
pagination_prev: ax650n/applications/six-streams/implementation
pagination_next: ax650n/applications/six-streams/local-preview
---

# 启动并检查

在 RK3576 上进入项目目录。确认资源校验通过、没有其他任务占用算力卡后启动服务。

启动前确认散热风扇正在转动，并按[环境准备](prepare.md#确认散热后再启动)检查温度。测试期间保持散热，不要在推流运行时关闭风扇。

## 启动两个服务

```bash
cd ~/ax8850-multistream-demo
bash start.sh
systemctl is-active ax8850-multistream ax8850-local-preview
```

两个服务应分别输出 `active`：`ax8850-multistream` 运行六路处理与 RTSP，`ax8850-local-preview` 提供本机 HTTP 预览。脚本会通过 `sudo` 申请权限。

这里创建的是临时 systemd 服务，断开 SSH 后仍会运行，**不会因此设置开机自启**。已有推流服务运行时，重复执行 `start.sh` 会直接返回，不会重新加载配置；修改配置后须[先停止再启动](../../../usage/services.md)。

## 检查六路是否持续处理

```bash
sudo journalctl -u ax8850-multistream -n 50 --no-pager
sudo journalctl -u ax8850-multistream -f
```

观察六路的周期统计，确认解码、推理、渲染和编码计数持续增加。按 `Ctrl+C` 退出日志查看，不会停止服务。仅有 `active` 状态不能证明六路均正常工作。

启动约 30 秒后执行：

```bash
python3 tools/fps.py
axcl-smi
```

帧率表应包含 `pcd`、`vehicle`、`seg`、`driving`、`depth`、`count`，各路 `New video`、`AI`、`Encode` 应有非零进展。采样不足时等待下一次统计再执行；`Errors` 增长或某一路持续为零时，先查看日志并进入[排错](vlc-troubleshooting.md)。

## 核对输出入口

```bash
sudo ss -ltnp | grep -E ':(8554|8850)\b'
hostname -I
```

电脑播放使用开发板局域网地址的 `8554` 端口，本机 HTTP 预览仅监听 `127.0.0.1:8850`。继续[观看与录制](local-preview.md)，确认实际视频可以解码。

## 可选：前台限时运行

需要直接查看程序输出时，先停止后台服务，再运行 60 秒：

```bash
bash stop.sh
bash run.sh configs/six.json 60
```

`run.sh` 单独启动处理与 RTSP，不启动 HTTP 预览服务。限时运行结束后执行 `bash start.sh` 恢复常规服务模式。前台日志和服务日志来自不同运行方式，`tools/fps.py` 用于常规服务模式。
