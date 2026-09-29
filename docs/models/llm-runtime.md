---
title: "编译 AXCL 大模型运行时"
---

# 编译 AXCL 大模型运行时

适用于已安装 AXCL 3.16 或符合所选运行时要求版本的 ARM64 / x86_64 Linux 主机。使用 `AXERA-TECH/ax-llm` 的 `axllm` 分支，显式选择 PCIe AXCL 后端。

## 获取固定版本

```bash
sudo apt install -y git build-essential cmake libopencv-dev
mkdir -p ~/edgeaccel/src
cd ~/edgeaccel/src
git clone --branch axllm https://github.com/AXERA-TECH/ax-llm.git
cd ax-llm
git checkout 8501c22b940f8c5804cb35044c5ffc136918b8f1
git submodule update --init --recursive
```

这里固定源码版本，避免模型教程与后续分支更新混用。子模块下载失败时先完成下载，不继续编译。

## 编译 AXCL 后端

```bash
cmake -S . -B build-axcl \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_AX650=OFF -DBUILD_AXCL=ON \
  -DCMAKE_INSTALL_PREFIX="$PWD/build-axcl/install"
cmake --build build-axcl --parallel 4
cmake --install build-axcl
```

显式关闭 `BUILD_AX650`，避免生成芯片板端后端。系统中需存在 `/usr/include/axcl` 与 `/usr/lib/axcl`。主机内存不足时降低并行编译数量。

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

## 选择模型包

当前入口为 `axllm run 模型目录` 或 `axllm serve 模型目录`，模型目录必须包含匹配版本的 `config.json`。只有旧 `run.sh`、旧 HTTP tokenizer 脚本或不同格式配置的包，不能直接沿用新命令。

先完成[文本对话](text-generation.md)，再部署[多模态](vision-language.md)和[服务接口](../usage/api-service.md)。运行时对部分模型家族支持不代表每个权重版本都已适配。上游已注明 Gemma-4 在 AXCL 后端存在异常，本指南不将其列为可用方案。

依据：[固定版本 AX-LLM](https://github.com/AXERA-TECH/ax-llm/tree/8501c22b940f8c5804cb35044c5ffc136918b8f1)、[配置说明](https://github.com/AXERA-TECH/ax-llm/blob/8501c22b940f8c5804cb35044c5ffc136918b8f1/docs/configuration.md)。具体模型的实际输出与检查范围见对应部署页。
