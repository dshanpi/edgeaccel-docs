---
title: "准备主机与算力卡"
---

# 准备主机与算力卡

本节适用于首次安装。了解板卡接口、内存、功耗与散热要求，请先阅读[硬件介绍](hardware.md)。已能正常运行 AXCL 的主机可直接进入[首次推理](../usage/first-inference.md)。

## 核对硬件

| 项目 | 安装前确认 |
|---|---|
| 算力卡 | 记录产品标签、芯片型号、8GB / 16GB 容量与硬件版本 |
| 插槽或转接板 | 支持 PCIe，键位和机械尺寸匹配；仅支持 SATA 的 M.2 插槽不适用 |
| 供电 | 按卡和主机手册核对功率、线材、转接板供电要求 |
| 散热 | 散热片固定，风扇连接正确，风道无遮挡 |
| 主机 | 记录架构、发行版、内核、可用内存与磁盘空间 |

先正常关机并切断电源再插拔。M.2 插槽外观相同不代表提供相同的 PCIe 连接能力。

## 核对配套文件

准备与主机架构一致的 AXCL 安装包，以及供货方确认的 PAC。PAC 是卡启动时加载的运行环境文件。已完成出厂配置的卡按主机加载流程使用，无需重复执行芯片开发板的烧录、分区或系统制作步骤。

| 文件 | 选择依据 |
|---|---|
| Linux `.deb` / `.rpm`、Windows `.exe` | 主机系统、架构、AXCL 版本 |
| 配套 `.pac` | 卡型号、容量、硬件版本、AXCL 配套关系 |
| `.axmodel` 与应用程序 | 编译目标、模型版本、输入输出结构、运行时版本 |

不把“同为 AX650”作为所有文件可互换的依据。没有随卡 PAC 时，先向供货方获取。

## 记录主机环境

以下命令在连接算力卡的 Linux 主机执行。

```bash
uname -m
uname -r
cat /etc/os-release
free -h
df -h "$HOME"
```

ARM64 主机应为 `aarch64`，Intel / AMD 64 位主机应为 `x86_64`。选择对应[安装入口](../ax650n/user-guide.md)。源码编译、模型下载和应用运行都在该主机完成；也可先在工作站下载完整文件，再传入主机。

## 建立应用目录

```bash
mkdir -p ~/edgeaccel/{models,inputs,outputs,logs,src}
```

安装包保存在 `~/axcl-setup`，模型保存在 `~/edgeaccel/models`，结果和日志分别放入 `outputs`、`logs`。后续示例使用这些路径。

依据：[AXCL 安装说明](https://axcl-docs.readthedocs.io/zh-cn/latest/doc_guide_setup.html)、随卡原始资料。
