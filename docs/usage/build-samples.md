---
title: "编译 AXCL 视觉示例"
sidebar_label: "手动操作：编译示例"
pagination_prev: null
pagination_next: null
---

# 编译 AXCL 视觉示例

本页是首次推理的手动操作步骤，用于编译视觉示例，也适用于修改源码后重新编译。选择[脚本运行](first-inference.md)时，YOLO11 示例由脚本自动编译，无需重复执行。

适用于已安装 AXCL 的 ARM64 或 x86_64 Linux 主机。设备异常时先按[设备检查](device-check.md)排查。下面在主机本地编译，不使用 AX 芯片板端的交叉编译工具链。

## 安装编译依赖

```bash
sudo apt update
sudo apt install -y git build-essential cmake libopencv-dev
mkdir -p ~/edgeaccel/src
cd ~/edgeaccel/src
git clone https://github.com/AXERA-TECH/axcl-samples.git
cd axcl-samples
git checkout cbfa4c76891758983ca2b0c99c11d6621d59af39
```

该提交用于固定本文核对的示例名称与参数。目录已经存在时先保留已有修改，确认版本后再使用，不在同一目录重复克隆。

## 编译并安装到项目目录

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/install"
cmake --build build --parallel 4
cmake --install build
```

编译进程因主机内存不足被终止时，改用 `--parallel 1` 重试。找不到 AXCL 头文件或库时，先检查主机软件安装，不从其他架构主机复制 `.so`。

## 检查生成的程序

```bash
build/install/bin/axcl_yolo11 --help
```

本文固定版本的 CMake 目标使用 `axcl_` 前缀。部分旧 README 使用 `ax_yolo11` 等名称，不能据此误用板端程序。

能显示参数帮助即可继续。启动失败时，用 `file` 检查程序架构、`ldd` 检查缺失库，具体见[设备与依赖检查](device-check.md)。

| 任务 | 程序 |
|---|---|
| 目标检测 | `axcl_yolo11`、`axcl_yolo26`、`axcl_yolov8` |
| 实例分割 | `axcl_yolo11_seg`、`axcl_yolov8_seg` |
| 人体姿态 | `axcl_yolo11_pose`、`axcl_yolov8_pose` |
| 深度估计 | `axcl_depth_anything` |
| 开放词汇检测 | `axcl_yolo_world_open_vocabulary` |
| 分类、手部 | `axcl_classification`、`axcl_palm_detection`、`axcl_handpose` |

程序存在且依赖齐全后，进入 [YOLO11 检测](../models/deploy/yolo11.md)。编译成功不代表模型已在设备上验证。

依据：[固定版本源码](https://github.com/AXERA-TECH/axcl-samples/tree/cbfa4c76891758983ca2b0c99c11d6621d59af39)。
