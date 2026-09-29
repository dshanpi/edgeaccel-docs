---
title: "检查设备与运行环境"
sidebar_label: "手动操作：检查设备"
pagination_prev: null
pagination_next: null
---

# 检查设备与运行环境

本页是首次推理的手动操作步骤，用于确认设备、驱动与运行依赖，也可用于排查问题。选择[脚本运行](first-inference.md)时，这些检查由脚本自动完成，无需重复执行。

以下命令在已安装 AXCL、已部署配套 PAC 的 Linux 主机执行。

## 先确认设备可用

需要手动确认设备状态时执行：

```bash
sudo /usr/bin/axcl/axcl-smi
```

设备列表应显示算力卡、温度和 CMM 内存信息。无初始化错误时可继续[手动下载模型](download-models.md)，下方详细检查仅在排错时使用。

<details>
<summary>设备识别异常时，检查 PCIe、驱动与开发文件</summary>

## 检查 PCIe 与驱动

```bash
mkdir -p ~/edgeaccel/logs
lspci -nn | tee ~/edgeaccel/logs/pci.txt
uname -r
modinfo -F vermagic axcl_host
dpkg-query -W -f='${Status} ${Version}\n' axclhost
```

`dpkg-query` 适用于 Debian / Ubuntu 安装。确认 PCIe 列表包含目标设备，模块的内核版本与 `uname -r` 一致，软件包状态为 `install ok installed`。原始资料中的默认 PCI ID 为 `1f4b:0650`，以实际卡资料为准。

## 判断设备内存与温度

在上方 `axcl-smi` 的输出中查看设备编号、版本、温度、CMM 总量与已用量。CMM 是卡端供模型等任务使用的内存，不等同于主机 `free -h` 的输出，也不必等于卡标称容量。随卡旧版 PAC 的 7040MiB / 15232MiB 仅供对照。

出现 `init fail`、无设备或命令持续不返回时，不继续加载模型。保存 `sudo dmesg`，核对供电、PAC、内核和 AXCL 配套关系，参阅[故障处理](troubleshooting.md)。

## 检查应用依赖

```bash
ls /usr/include/axcl
ls /usr/lib/axcl
test -x /usr/bin/axcl/axcl_run_model
```

运行已下载的 Linux 二进制前，执行 `file /实际路径/程序` 和 `ldd /实际路径/程序`。架构必须匹配主机，依赖列表不得含 `not found`。Windows 程序不能用 Linux `ldd` 检查。

</details>

## 继续首次推理

设备可识别后，继续[下载并核对模型文件](download-models.md)。也可返回[脚本运行](first-inference.md)自动完成后续操作。只有模型成功执行才能确认该模型的基本运行能力；本节不验证算法效果或长期稳定性。

依据：[AXCL SMI](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_axcl_smi.html)、[安装说明](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_setup.html)。
