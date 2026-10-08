---
title: "编译 AXCL 大模型运行时"
description: "在 Linux 主机编译固定版本 AX-LLM，检查 AXCL 后端并匹配模型配置。"
mdx:
  format: mdx
---

import {GuideHero, GuideNext} from '@site/src/components/ModelGuideLayout';

# 编译 AXCL 大模型运行时

<GuideHero label="公共部署环境 · AX-LLM" title="先固定运行程序，再匹配模型包" description="在连接 M.2 算力卡的 Linux 主机完成编译，确认程序使用 PCIe AXCL 后端，再进入具体模型部署页。" facts={[["执行位置", "ARM64 / x86_64 Linux 主机"], ["生成程序", "axllm · AXCL 后端"], ["完成标志", "版本与依赖检查通过"]]} />

本页使用 `AXERA-TECH/ax-llm` 的固定提交，适用于已安装 AXCL 3.16 或符合该版本要求的主机。所有命令在连接算力卡的 Linux 主机执行。独立模型页若指定专用程序或另一提交，应使用该页的配套组合。

## 确定是否需要编译

| 当前情况 | 操作入口 |
| --- | --- |
| 部署页要求使用统一 `axllm`，尚无配套程序 | 按本页编译并检查后端。 |
| 已有同一固定提交的程序，版本与依赖检查通过 | 直接进入模型部署页，不重复编译。 |
| 模型使用 `main_axcl`、专用 Python 或旧分词服务 | 按该模型页操作，不直接替换为 `axllm`。 |
| 只有源权重，尚无适配模型包 | 先阅读[自定义模型接入](custom-model.md)。 |

## 检查主机与依赖

先完成[设备检查](../usage/device-check.md)，确认 `axcl-smi` 能显示目标卡。在主机终端检查架构、AXCL 头文件与运行库：

```bash
uname -m
test -d /usr/include/axcl && test -d /usr/lib/axcl \
  && echo "AXCL headers and libraries found"
```

架构应为 `aarch64` 或 `x86_64`。目录缺失时先修复 AXCL 安装；本页使用系统安装路径。目录存在只说明文件位置可用，设备状态仍以设备检查结果为准。

## 获取固定版本

```bash
sudo apt install -y git build-essential cmake libopencv-dev
mkdir -p ~/edgeaccel/src
cd ~/edgeaccel/src
git clone --branch axllm https://github.com/AXERA-TECH/ax-llm.git
cd ax-llm
git checkout 8501c22b940f8c5804cb35044c5ffc136918b8f1
git submodule update --init --recursive
git rev-parse HEAD
git submodule status --recursive
```

提交号应为 `8501c22b940f8c5804cb35044c5ffc136918b8f1`。子模块下载失败或版本不匹配时先处理下载，不继续编译。上述克隆步骤用于首次准备；目录已存在时先检查其版本与本地修改，保留已有文件。

## 编译 AXCL 后端

```bash
cmake -S . -B build-axcl \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON \
  -DCMAKE_INSTALL_PREFIX="$PWD/build-axcl/install"
cmake --build build-axcl --parallel 4
cmake --install build-axcl
```

显式关闭 `BUILD_AX650`，选择 PCIe 算力卡后端。编译与安装完成后应生成 `build-axcl/install/bin/axllm`。主机内存较小时，将 `--parallel 4` 降为 `--parallel 2` 或 `1`，不修改模型运行参数来处理编译问题。

## 检查后端与依赖

```bash
AXLLM=~/edgeaccel/src/ax-llm/build-axcl/install/bin/axllm
test -x "$AXLLM"
ldd "$AXLLM"
"$AXLLM" version
"$AXLLM" --help
```

版本信息中的 backend 应为 `AXCL`，依赖不能出现 `not found`。将版本输出与 Git 提交号一起记录。

后续每个新终端先设置同一 `AXLLM` 路径，或直接使用完整路径。这里不安装到 `/usr/bin`，便于与旧 `main_axcl` 或历史项目共存。

## 匹配模型包与运行方式

模型目录必须包含匹配版本的 `config.json`，其中的分词器、模型分片与其他文件路径均能找到实际文件。只有旧 `run.sh`、旧 HTTP tokenizer 脚本或不同格式配置的包时，按对应部署页处理。

| 用途 | 入口 | 运行前确认 |
| --- | --- | --- |
| 本地文本或图像交互 | `axllm run 模型目录` | 模型类型和媒体输入方式与配置匹配。 |
| HTTP 问答服务 | `axllm serve 模型目录` | 端口、模型 ID 与客户端请求格式正确。 |
| 向量服务 | 对应向量配置的 `axllm serve` | 使用向量接口；该版本的向量模型不使用 `run` 交互模式。 |

具体启动参数使用独立部署页提供的命令。保留内存预检，先单请求复现样例，再评估上下文、图片数量或组合应用。

该固定提交的上游说明列出 Gemma-4 在 AXCL 后端的已知异常；不要仅按模型家族支持列表判断特定权重可用。每个模型的实际范围以独立部署页为准。

## 处理常见阻塞

| 现象 | 先检查 |
| --- | --- |
| CMake 找不到 AXCL | 系统头文件、运行库及当前主机架构是否匹配。 |
| 编译进程被系统终止 | 主机内存与系统日志，降低编译并行数后重试。 |
| `ldd` 出现 `not found` | 安装缺失的匹配库；不要用不兼容版本软链接替代。 |
| 版本报告不是 AXCL | 检查实际执行路径与构建选项，避免运行到旧程序。 |
| 模型配置、分片或分词器加载失败 | 回到模型页核对配套文件，不能仅靠编译成功判断模型适配完成。 |

## 进入模型部署

<GuideNext items={[{to: '/docs/models/text-generation', title: '部署文本模型', text: '先用短问题确认输出与容量。'}, {to: '/docs/models/vision-language', title: '部署图像问答', text: '匹配视觉编码器并核对图片回复。'}]} />

依据：[固定版本 AX-LLM](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)、[配置说明](https://github.com/AXERA-TECH/ax-llm/blob/8501c22b940f8c5804cb35044c5ffc136918b8f1/docs/configuration.md)。具体模型的实际输出与检查范围见对应部署页。
