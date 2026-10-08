---
title: "内核头修复与验证"
sidebar_label: "内核头修复与验证"
slug: /ax650n/reference/kernel-headers/fixes
---

> **指定内核版本资料**：仅适用于正文注明的系统与内核。安装前必须核对 `uname -r`，不能用于替换其他内核的 headers。当前安装入口见[ARM64 快速上手](/docs/ax650n/quick-start/arm64)。

# 修复与验证记录

目标为当前 DShanPi-A1 主机的 AXCL 驱动编译环境。

## 为什么原包编译出的驱动不匹配

原始 `linux-headers-vendor-rk35xx 25.11.0-trunk` 包内启用了 BTF，但其安装脚本执行 `make olddefconfig`，依赖列表没有包含 `pahole`。当前系统缺少该工具，安装后的 headers 因此关闭了 BTF 相关选项，与实际运行的内核配置不一致。

这会改变内核 `struct module` 的布局。故障模块的 `.gnu.linkonce.this_module` 大小是 `0x340`，`cleanup_module` 偏移为 `0x328`；可用备份模块分别为 `0x380` 和 `0x340`。仅检查内核版本或 vermagic 无法发现这一差异。

## 修正版修改

1. 使用当前运行内核的完整配置，并同步 `auto.conf`、`autoconf.h`；保留 BTF 与 `CONFIG_DEBUG_INFO_BTF_MODULES=y`。
2. 同步原 headers 与运行内核之间的 GOODIX 配置差异（运行内核为模块）。
3. 在独立目录编译 ARM64 的 kbuild 辅助工具，随 headers 一起打包。
4. 增加 `pahole >= 1.25` 等依赖；附带 Ubuntu 官方 `pahole_1.25-0ubuntu3_arm64.deb`。
5. 安装脚本改为验证目标内核和已准备的文件，不再执行 `olddefconfig`。新增安装前后检查工具，检查配置、符号表和辅助程序。
6. 新包的卸载脚本不再递归删除整个 headers 目录，由 dpkg 管理包内文件。安装入口先检查目标，避免不匹配系统进入升级流程。

新包沿用包名，版本增加为 `25.11.0-trunk+ax8850.1`，属于本地修正版，不是 Armbian 或爱芯官方发布版本。

## 验证范围

在开发板的独立目录中编译 AXCL 3.16 源码；没有执行系统级安装或加载模块。

- 七个模块均编译成功：`ax_pcie_host_dev`、`ax_pcie_mmb`、`ax_pcie_msg`、`ax_pcie_net_host`、`ax_pcie_p2p_rc`、`axcl_host`、`vtty`。
- 七个模块的结构大小均为 `0x380`，`cleanup_module` 偏移均为 `0x340`，vermagic 与目标内核一致。
- 打包后重新解压，并在新路径再次编译，验证包不依赖原构建目录。
- 比较五个当前可用核心模块与新编译模块所引用符号的版本 CRC。
- 检查 apt 安装模拟、包内文件校验，以及检查工具拒绝损坏配置的行为。
- 对比当前系统的 headers、已安装 AXCL 模块、PAC 和软件包版本，确认未被本次构建修改。

详细结果见 `final-package-validation.json`，包身份及配置文件校验值见 `package-manifest.json`。

headers 未提供 `vmlinux`，编译日志可能出现 `Skipping BTF generation ... due to unavailability of vmlinux`。本记录中的模块已完成编译链接；这条提示与关闭 `CONFIG_DEBUG_INFO_BTF_MODULES` 改变模块结构是不同情况。

**验证边界：** 本记录仅验证编译与模块结构；未安装此 deb、加载新编译模块或测试运行稳定性。

## 目标身份

| 项目 | 值 |
|---|---|
| 内核 | `6.1.115-vendor-rk35xx` |
| `/boot/Image` SHA256 | `68fbb255175f1bd758672b1e8bf88b1e8b7aa9f61d37d891712f2efe5d8d33a5` |
| 运行内核配置 SHA256 | `bd6e9db8dc43a68f7ea5f8423f00c66765cdd93d3b23b4842713c64626e26911` |
| 原始 headers deb SHA256 | `8cbba4243297b94f76c555dc8e339eabe340ee4b3f76fdf1220b6f6dcab79bb2` |

包内没有 AXCL `.ko`、内核 Image、PAC、AXP 或 DDR 固件。本次修改不涉及算力卡 8GB/16GB 容量与 DDR 频率。
