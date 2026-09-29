---
title: "六路推流：演示版服务管理"
sidebar_label: "演示版：服务与开机自启"
pagination_prev: projects/six-streams
pagination_next: null
---

# 管理演示版服务与开机自启

项目源码见 [GitHub 仓库](https://github.com/dshanpi/ax8850-multistream-demo)。从仓库新部署时，按仓库 README 管理服务；本页的开机自启与桌面服务说明仅对应下述预装环境。

本节适用于已安装 `~/ax8850-multistream-demo` 的 RK3576 演示环境。其他部署应先核对本机路径与服务名。切换到单模型测试前停止占用卡资源的演示任务。

## 确认部署说明

在该主机的 Linux 终端执行：

```bash
test -d ~/ax8850-multistream-demo
cat ~/ax8850-multistream-demo/deploy/8GB-开机自启说明.md
systemctl status ax8850-multistream ax8850-local-preview --no-pager
systemctl --user status ax8850-vlc-preview --no-pager
```

本页对应演示版；`~/ax-pipeline/six` 开发版的服务名与启停命令见[启动与观看](../ax650n/applications/six-streams/usage.md)。尚未确定部署版本时，先查阅[项目总览](../projects/six-streams.md)。

## 临时停止演示

```bash
systemctl --user stop ax8850-vlc-preview
sudo systemctl stop ax8850-local-preview ax8850-multistream
systemctl show ax8850-multistream ax8850-local-preview \
  -p Id -p ActiveState -p SubState -p MainPID -p Result
pgrep -af 'six_app|local_preview|vlc'
```

目标服务应无运行中的主进程，演示程序不再占用设备。`pgrep` 可能列出其他无关 VLC 进程，应核对命令路径，不能直接全部终止。停止超时会使服务显示 `failed`；检查 `MainPID`、相关进程和日志后再判断是否确实退出。

这一步只停止当前运行，保留开机自启。再次启动主机后演示可能重新运行。

## 按需关闭开机自启

需要长期保留设备给其他模型时，确认该部署的启停关系后执行：

```bash
systemctl --user stop ax8850-vlc-preview
sudo systemctl disable --now ax8850-local-preview ax8850-multistream

mkdir -p ~/.config/autostart-disabled
for name in ax8850-preview.desktop ax8850-preview.desktop.disabled; do
  if [ -f "$HOME/.config/autostart/$name" ]; then
    mv --backup=numbered -- "$HOME/.config/autostart/$name" \
      "$HOME/.config/autostart-disabled/$name"
  fi
done
systemctl --user daemon-reload
```

桌面启动文件必须移出 `~/.config/autostart/`。本机的 `systemd-xdg-autostart-generator` 仍会读取目录内改名为 `.desktop.disabled` 的文件，并生成登录启动任务。上面的循环兼容原文件名和已经改名的文件；目标位置存在同名文件时保留编号备份。

`ax8850-vlc-preview.service` 是由桌面入口触发的 `static` 用户服务，没有独立的启用配置。停止该服务并移走桌面入口即可，不用对它执行 `enable` 或 `disable`。

完成后检查：

```bash
systemctl show ax8850-multistream ax8850-local-preview \
  -p Id -p UnitFileState -p ActiveState -p MainPID
systemctl --user show ax8850-vlc-preview -p ActiveState -p MainPID
systemctl --user list-unit-files --no-pager | grep -F 'app-ax8850'
ps -eo pid,args | grep -E '[s]ix_app|[a]x8850-multistream-demo|[a]x8850-vlc'
ss -ltnp | grep -E ':8554|:8850'
```

两项系统服务应为 `disabled`、`inactive`、`MainPID=0`，VLC 用户服务应为 `inactive`、`MainPID=0`。后面三项检查应无匹配输出；有输出时先核对具体服务、进程或端口用途。重新登录或重启后可重复检查，确认没有再次启动。

恢复自启时按设备上的部署说明恢复服务和桌面文件，避免同时启用多个预览入口。首次恢复后检查模型配置、端口及进程数量。

## 保留停机日志

```bash
journalctl -u ax8850-multistream -u ax8850-local-preview \
  -n 100 --no-pager
```

释放资源后再按[设备检查](device-check.md)确认空闲状态。需要重新观看时，按本机 `deploy/8GB-开机自启说明.md` 恢复对应服务与预览，不套用开发版的 `start.sh`。

<details>
<summary>参考配置的重启检查记录（2026-09-23）</summary>

原测试主机重启后的状态如下：

| 检查项 | 重启后实测状态 |
|---|---|
| `ax8850-multistream.service` | `disabled`、`inactive`、`MainPID=0` |
| `ax8850-local-preview.service` | `disabled`、`inactive`、`MainPID=0` |
| 用户服务 `ax8850-vlc-preview.service` | `inactive`、`MainPID=0` |
| 用户启动单元 `app-ax8850*` | 无匹配单元 |

六路推流和预览服务没有随此次重启重新启动。该记录仅验证演示服务的停用配置，不代表模型部署或长期稳定性验证通过。

</details>
