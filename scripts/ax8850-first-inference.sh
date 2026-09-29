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
