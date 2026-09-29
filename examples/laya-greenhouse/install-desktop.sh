#!/usr/bin/env bash
set -euo pipefail
APP_DIR=$(dirname "$(readlink -f "$0")")
chmod +x "$APP_DIR/launch.sh"
mkdir -p "$HOME/.local/share/applications"
LAUNCHER="$HOME/.local/share/applications/laya-greenhouse.desktop"
cat > "$LAUNCHER" <<EOF
[Desktop Entry]
Type=Application
Name=Laya 智能温室
Comment=在 AX8850 算力卡上运行真实的温室决策演示
Exec=bash "$APP_DIR/launch.sh"
Icon=applications-science
Terminal=false
Categories=Education;Science;
EOF
DESKTOP_DIR=$(xdg-user-dir DESKTOP)
if [[ -d "$DESKTOP_DIR" ]]; then
  cp "$LAUNCHER" "$DESKTOP_DIR/laya-greenhouse.desktop"
  chmod +x "$DESKTOP_DIR/laya-greenhouse.desktop"
  gio set "$DESKTOP_DIR/laya-greenhouse.desktop" metadata::trusted true 2>/dev/null || true
fi
echo '已安装 Laya 智能温室桌面入口。服务仅手动启动，不设置开机自启。'
