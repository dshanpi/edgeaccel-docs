---
title: "升级、备份与恢复环境"
---

# 升级、备份与恢复环境

适用于 Linux 主机。AXCL、PAC、模型和应用分别记录版本；升级其中一项后重新完成设备与模型检查。

## 保存可恢复的配置

停止占卡程序后，在主机执行：

```bash
BACKUP_DIR="$HOME/edgeaccel/backup/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
uname -a > "$BACKUP_DIR/kernel.txt"
dpkg-query -W axclhost > "$BACKUP_DIR/axcl-version.txt"
sudo cp /lib/firmware/axcl/ax650_card.pac "$BACKUP_DIR/ax650_card.pac"
sha256sum "$BACKUP_DIR/ax650_card.pac" > "$BACKUP_DIR/pac.sha256"
```

同时保存当前安装包、模型校验值、应用配置、Git 提交号和服务文件。不要将 SSH 密码或访问令牌写入公开日志。

## 执行配套升级

1. 查阅目标版本发布说明，确认卡容量、主机内核与模型兼容性。
2. 按官方安装说明处理旧软件包，保留已知可用版本以便回退。
3. 安装新 AXCL 后重新部署该版本配套 PAC，并比较校验值。
4. 按要求重启主机，再完成设备检查与一个固定基准模型。
5. 基本测试通过后再恢复应用服务。

升级内核会改变驱动编译环境，必须重新匹配 headers 和模块。首次模型部署过程中不同时升级内核、驱动、PAC 和模型，避免失去可用基线。

## 恢复失去响应的设备

出现设备心跳超时后，先停止占卡应用和自动测试队列，保存故障日志。不要反复启动模型或 SMI 查询；`axcl-smi is already running` 表示还需检查已有查询进程。

确认设备编号后，在 Linux 主机执行单卡复位。以下编号为逻辑设备 0：

```bash
axcl-smi reboot -d 0
```

按提示确认，等待固件重新加载，再执行一次 `axcl-smi`。若复位未恢复，可在停止全部占卡应用后重新加载驱动；该操作影响主机上的全部 AXCL 卡：

```bash
sudo modprobe -r axcl_host
sudo modprobe axcl_host
axcl-smi
```

若卸载提示模块仍被占用，不强制卸载。先保存主机工作并正常重启；软件重启仍未恢复时，确认文件写入已停止，再现场检查供电和重新上电。恢复后先运行一个已知可用的小模型，确认实际输出与资源释放，再继续较大的模型。

单卡复位接口见 [AXCL-SMI 重启说明](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_axcl_smi.html#reboot)，驱动重载见 [AXCL FAQ](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_faq.html)。复位成功不代表此前失败的模型已经通过。

## 恢复旧环境

使用备份的同套安装包、PAC 和应用配置回退，不只恢复一个 `.ko` 或 PAC。恢复后重新启动并核对版本，再运行保存的基准输入。

恢复仍失败时保存安装日志、内核日志和包版本，按[故障处理](troubleshooting.md)定位。没有匹配版本的备份时先获取配套文件，不组合猜测版本继续试装。

依据：[AXCL 安装与卸载](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_setup.html)、[常见问题](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_faq.html)。
