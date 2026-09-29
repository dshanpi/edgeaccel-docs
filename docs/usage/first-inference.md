---
title: "完成首次模型推理"
sidebar_label: "脚本运行：首次推理"
pagination_prev: ax650n/user-guide
pagination_next: models/selection
---

# 完成首次模型推理

使用 YOLO11 检测一张足球图片。完成 AXCL 安装后，可选择以下一种方式：

| 方式 | 操作说明 |
|---|---|
| **脚本运行（推荐）** | 按本页复制脚本运行，自动检查设备、编译示例、下载模型并推理，然后查看结果图片。 |
| **手动操作** | 依次阅读[检查设备](device-check.md)、[下载模型](download-models.md)、[编译示例](build-samples.md)，再按 [YOLO11 部署指南](../models/deploy/yolo11.md)运行并查看结果，已完成的步骤可跳过。 |

**两种方式任选其一，无需先运行脚本再重复执行手动步骤。** 同目录中的三篇“手动操作”文档也可用于了解流程或排查问题。下文介绍脚本运行方式。

适用于连接算力卡的 **Ubuntu / Debian ARM64 或 x86_64 主机**。尚未安装 AXCL 或部署配套 PAC 时，先阅读[ARM64 安装](../ax650n/quick-start/arm64.md)或[Linux x86_64 安装](../ax650n/quick-start/linux-x86.md)。Windows 请使用对应平台指南。

## 1. 确认运行环境

脚本会检查设备、按需安装编译依赖、只编译 `axcl_yolo11`，然后下载约 11 MB 的模型与图片并校验文件。

首次运行需联网访问系统软件源、GitHub 和 Hugging Face，并可能提示输入 `sudo` 密码。确认没有其他程序占用算力卡；示例使用设备列表中的第一张卡。

## 2. 运行首次推理

在算力卡主机打开 Linux 终端，展开下方脚本，点击代码块右上角的复制按钮，粘贴并执行。**无需下载脚本文件**；命令会将脚本保存到 `~/edgeaccel/ax8850-first-inference.sh`，然后开始推理。

<details>
<summary>展开首次推理脚本（完整复制到终端执行）</summary>

```bash
mkdir -p ~/edgeaccel
cat > ~/edgeaccel/ax8850-first-inference.sh <<'AX8850_SCRIPT_EOF'
#!/usr/bin/env bash
# Ubuntu/Debian ARM64 or x86_64 host with AXCL already installed.
# Versions match the site's evidence-backed YOLO11 deployment guide.
set -Eeuo pipefail

SOURCE_REV=cbfa4c76891758983ca2b0c99c11d6621d59af39
MODEL_REV=e178719ba1b03eaf07c981f859027f3278c1cb29
WORK_DIR="$HOME/edgeaccel/first-inference"
SOURCE_DIR="$WORK_DIR/src/$SOURCE_REV"
BUILD_DIR="$WORK_DIR/build/$SOURCE_REV"
MODEL_DIR="$WORK_DIR/models/$MODEL_REV"

fail() { printf '\n停止：%s\n' "$*" >&2; exit 1; }
step() { printf '\n%s\n' "$*"; }

check_environment() {
  [[ $(uname -s) == Linux ]] || fail '请在连接算力卡的 Linux 主机运行。'
  case $(uname -m) in aarch64|x86_64) ;; *) fail '仅支持 ARM64 或 x86_64 主机。';; esac
  command -v apt-get >/dev/null || fail '本脚本适用于 Ubuntu / Debian；其他系统请使用手动指南。'
  [[ -x /usr/bin/axcl/axcl-smi && -d /usr/include/axcl && -d /usr/lib/axcl ]] ||
    fail '请先安装 AXCL 主机软件及开发文件，并部署随卡 PAC。'
  command -v timeout >/dev/null || fail '缺少 coreutils 提供的 timeout 命令。'
  command -v sudo >/dev/null || fail '需要 sudo 权限检查设备及安装编译依赖。'
  step '[1/4] 检查算力卡'
  sudo -v
  timeout 30s sudo -n /usr/bin/axcl/axcl-smi
}

install_dependencies() {
  local missing=0 cmd
  for cmd in git curl cmake make g++ pkg-config; do
    command -v "$cmd" >/dev/null || missing=1
  done
  if ! command -v pkg-config >/dev/null || ! pkg-config --exists opencv4; then missing=1; fi
  if ((missing)); then
    step '安装编译与下载依赖（可能需要输入 sudo 密码）'
    sudo apt-get update
    sudo apt-get install -y git curl ca-certificates build-essential cmake pkg-config libopencv-dev
  fi
}

prepare_source() {
  step '[2/4] 准备并编译 YOLO11 示例'
  mkdir -p "$WORK_DIR/src" "$BUILD_DIR"
  if [[ ! -e "$SOURCE_DIR" ]]; then
    # A failed fetch leaves a temporary directory; existing projects are untouched.
    local checkout_dir
    checkout_dir=$(mktemp -d "$WORK_DIR/src/download.XXXXXX")
    git -C "$checkout_dir" init -q
    git -C "$checkout_dir" remote add origin https://github.com/AXERA-TECH/axcl-samples.git
    git -C "$checkout_dir" fetch --depth 1 origin "$SOURCE_REV"
    git -C "$checkout_dir" checkout --detach "$SOURCE_REV"
    mv "$checkout_dir" "$SOURCE_DIR"
  fi
  [[ $(git -C "$SOURCE_DIR" rev-parse HEAD) == "$SOURCE_REV" ]] || fail "源码版本不匹配：$SOURCE_DIR"
  [[ -z $(git -C "$SOURCE_DIR" status --porcelain) ]] || fail "源码目录已有修改，请保留原目录后再运行：$SOURCE_DIR"
  cmake -S "$SOURCE_DIR" -B "$BUILD_DIR" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="$BUILD_DIR/bin"
  cmake --build "$BUILD_DIR" --target axcl_yolo11 --parallel "${JOBS:-2}"
  [[ -x "$BUILD_DIR/bin/axcl_yolo11" ]] || fail '未找到生成的 axcl_yolo11 程序。'
}

fetch_verified() {
  local relative=$1 expected=$2 destination="$MODEL_DIR/$1" temporary
  mkdir -p "$(dirname "$destination")"
  if [[ -f "$destination" ]] && printf '%s  %s\n' "$expected" "$destination" | sha256sum --check --status; then
    printf '复用已校验文件：%s\n' "$relative"
    return
  fi
  [[ ! -e "$destination" ]] || fail "文件校验不一致，请保留或移走该文件后重试：$destination"
  temporary=$(mktemp "${destination}.download.XXXXXX")
  curl --fail --location --retry 2 --connect-timeout 20 --max-time 600 \
    "https://huggingface.co/AXERA-TECH/YOLO11/resolve/$MODEL_REV/$relative" --output "$temporary"
  printf '%s  %s\n' "$expected" "$temporary" | sha256sum --check
  mv "$temporary" "$destination"
}

download_model() {
  step '[3/4] 下载模型和样例图，核对 SHA256'
  fetch_verified ax650/yolo11s.axmodel bad83368e9d68ae9740e9bb72c34e6b8173635faca7eb366e5484f578fa10fa2
  fetch_verified football.jpg e7c4b752ef447bfec409888cea8709be15c01d0f6bf91bd16b7762deb90950dc
}

run_inference() {
  step '[4/4] 执行图片推理'
  local result_dir dependencies
  dependencies=$(ldd "$BUILD_DIR/bin/axcl_yolo11")
  [[ "$dependencies" != *'not found'* ]] || fail "程序缺少动态库：$dependencies"
  mkdir -p "$WORK_DIR/results"
  result_dir=$(mktemp -d "$WORK_DIR/results/run.XXXXXX")
  (
    cd "$result_dir"
    "$BUILD_DIR/bin/axcl_yolo11" -m "$MODEL_DIR/ax650/yolo11s.axmodel" \
      -i "$MODEL_DIR/football.jpg" -g 640,640 -r 1 2>&1 | tee run.log
    [[ -s yolo11_out.jpg ]] || fail '程序未生成结果图片，请检查本次 run.log。'
  )
  printf '\n推理已结束，请打开图片核对检测框：\n%s/yolo11_out.jpg\n日志：%s/run.log\n' "$result_dir" "$result_dir"
}

main() {
  if [[ ${1:-} == --help ]]; then
    printf '用法：bash ax8850-first-inference.sh\n前提：Ubuntu/Debian ARM64 或 x86_64，已安装 AXCL 与配套 PAC。\n工作目录：%s\n降低编译内存：JOBS=1 bash ax8850-first-inference.sh\n' "$WORK_DIR"
    return
  fi
  (($# == 0)) || fail '不支持该参数；使用 --help 查看说明。'
  [[ ${JOBS:-2} =~ ^[1-9][0-9]*$ ]] || fail 'JOBS 必须为正整数。'
  trap 'printf "\n执行失败，已停止。请根据上方错误处理后重试；已有文件和结果予以保留。\n" >&2' ERR
  check_environment
  install_dependencies
  prepare_source
  download_model
  run_inference
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
AX8850_SCRIPT_EOF
bash ~/edgeaccel/ax8850-first-inference.sh
```

</details>

等待终端依次显示设备检查、编译、下载校验和图片推理四个阶段。编译和下载时间取决于主机与网络；出现错误时脚本停止，按提示处理后，使用以下命令重试，无需再次复制完整脚本：

```bash
bash ~/edgeaccel/ax8850-first-inference.sh
```

## 3. 查看结果图片

终端最后会显示本次 **`yolo11_out.jpg` 的完整路径**。用主机文件管理器打开，或复制回自己的电脑查看；同目录的 `run.log` 保存推理输出。

检查人物和足球上的检测框及类别是否合理。可对照 [YOLO11 原图与实测结果](../models/deploy/yolo11.md#查看部署效果)。生成图片表示运行流程已完成，仍需检查画面内容。

每次运行创建独立的结果目录，避免把旧图片误当作本次输出。源码、模型和结果保存在 `~/edgeaccel/first-inference/`；重复运行复用校验通过的模型，并进行增量编译。

## 遇到问题时

| 现象 | 处理 |
|---|---|
| 提示未安装 AXCL，或设备检查失败 | 按[设备检查](device-check.md)核对驱动、PAC 与供电 |
| 下载失败或文件校验不一致 | 查看[下载与文件校验](download-models.md)，网络恢复后重试；校验失败文件按提示保留后移走 |
| 编译提示 `Killed` | 主机内存可能不足，用下方命令改为单任务编译 |
| 缺少动态库，或没有生成图片 | 查看终端错误和本次 `run.log`，参阅[故障处理](troubleshooting.md) |

```bash
JOBS=1 bash ~/edgeaccel/ax8850-first-inference.sh
```

## 首次推理完成后

确认结果图片中的检测框与类别合理后，即完成首次推理。接下来从[模型目录](../models/catalog.mdx)选择其他任务，按对应模型的部署文档继续。

## 手动操作文档

选择手动方式时，按以下顺序准备；使用脚本遇到问题时，只需查阅相关页面：

1. [检查设备与运行环境](device-check.md)：确认设备识别、驱动与运行依赖。
2. [下载并核对模型文件](download-models.md)：选择下载来源并校验模型文件。
3. [编译 AXCL 视觉示例](build-samples.md)：编译示例程序，再进入 YOLO11 部署指南执行推理。

<details>
<summary>脚本使用的固定版本</summary>

- 示例源码：`axcl-samples` 提交 `cbfa4c76891758983ca2b0c99c11d6621d59af39`。
- 模型仓库：`AXERA-TECH/YOLO11` 提交 `e178719ba1b03eaf07c981f859027f3278c1cb29`。
- 下载文件：`ax650/yolo11s.axmodel`、`football.jpg`，与 YOLO11 页的实测清单一致。
- 脚本不安装 AXCL、更新 PAC 或修改已有应用项目。手动运行命令见 [YOLO11 部署指南](../models/deploy/yolo11.md)。

</details>
