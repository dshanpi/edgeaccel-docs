#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [[ -f config.env ]]; then source config.env; fi
LAYA_PYTHON=${LAYA_PYTHON:-$HOME/edgeaccel/laya-env/bin/python}
LAYA_MODEL_DIR=${LAYA_MODEL_DIR:-$HOME/edgeaccel/models/Laya}
systemctl --user is-active --quiet laya-greenhouse.service || systemd-run --user --unit=laya-greenhouse --collect --property=WorkingDirectory="$PWD" "$LAYA_PYTHON" "$PWD/server.py" --model-dir "$LAYA_MODEL_DIR"
if command -v chromium >/dev/null && chromium --version >/dev/null 2>&1; then
  exec chromium --app=http://127.0.0.1:8855/ --no-first-run
elif command -v chromium-browser >/dev/null && chromium-browser --version >/dev/null 2>&1; then
  exec chromium-browser --app=http://127.0.0.1:8855/ --no-first-run
elif command -v firefox >/dev/null; then
  exec firefox --new-window http://127.0.0.1:8855/
else
  exec xdg-open http://127.0.0.1:8855/
fi
