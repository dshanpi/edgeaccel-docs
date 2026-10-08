---
title: "管理六路推流服务"
sidebar_label: "6. 停止与重启"
pagination_prev: ax650n/applications/six-streams/validation
pagination_next: ax650n/applications/six-streams/frame-rate
---

# 停止与重启六路推流

本页对应 `dshanpi/ax8850-multistream-demo` 仓库根目录脚本，服务名称为 `ax8850-multistream` 和 `ax8850-local-preview`。

## 停止服务并释放算力卡

先关闭播放器，在 RK3576 上执行：

```bash
cd ~/ax8850-multistream-demo
bash stop.sh
systemctl is-active ax8850-multistream ax8850-local-preview
sudo ss -ltnp | grep -E ':(8554|8850)\b' || true
```

两个服务应不再为 `active`，对应端口不再由本项目监听。临时服务停止后可能被 systemd 回收，因此显示未找到也正常。若仍有监听进程，检查所属应用，不要直接终止其他业务。

查看退出记录：

```bash
sudo journalctl -u ax8850-multistream -n 30 --no-pager
```

正常结束记录包含 `event` 为 `exit` 且 `errors` 为 `0`；异常退出时保留日志并排查，不能仅以端口消失判定处理流程正常。

## 重新加载配置

修改 `configs/six.json` 后，先停止再启动：

```bash
cd ~/ax8850-multistream-demo
bash stop.sh
bash start.sh
systemctl is-active ax8850-multistream ax8850-local-preview
```

两个服务恢复 `active` 后，重新检查六路统计和播放效果。运行中再次执行 `start.sh` 不会加载新的配置。

## 区分临时服务与开机自启

仓库的 `start.sh` 使用 `systemd-run --collect` 创建临时服务。关闭 SSH 不影响运行，但系统重启后需要再次执行 `bash start.sh`。无需对这些临时服务执行 `systemctl enable`。

若重启后演示自动出现，说明系统另有预装服务或桌面自启动项。先检查配置来源：

```bash
systemctl cat ax8850-multistream ax8850-local-preview
systemctl is-enabled ax8850-multistream ax8850-local-preview
systemctl --user status ax8850-vlc-preview --no-pager
ls ~/.config/autostart/
```

只有确认是需要取消的持久化演示服务后，才执行对应命令：

```bash
sudo systemctl disable --now ax8850-multistream ax8850-local-preview
systemctl --user disable --now ax8850-vlc-preview
```

用户服务命令在原桌面用户下执行；系统不存在该服务时跳过。若自启动来自 `.desktop` 文件，按实际文件处理，不要删除整个自启动目录。

旧开发环境可能使用 `ax-six-rtsp` 和 `ax-six-local-preview`。它们与新仓库服务不同；迁移时先确认旧服务占用情况，再停止旧部署。历史 `deploy/8GB-开机自启说明.md` 属于预装环境，不是本指南所用仓库的安装步骤。
