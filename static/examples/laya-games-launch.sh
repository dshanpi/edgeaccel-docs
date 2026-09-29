#!/usr/bin/env bash
set -euo pipefail
APP_DIR=${LAYA_GAMES_DIR:-$HOME/edgeaccel/laya-axera}
PYTHON_ENV=${LAYA_GAMES_ENV:-$HOME/edgeaccel/laya-games-env}
MODEL_DIR=${LAYA_MODEL_DIR:-$HOME/edgeaccel/models/Laya}
if [[ -f "$APP_DIR/desktop.env" ]]; then source "$APP_DIR/desktop.env"; fi
if ! systemctl --user is-active --quiet laya-games; then
  systemd-run --user --unit=laya-games --collect --property=WorkingDirectory="$APP_DIR" \
    "$PYTHON_ENV/bin/laya-axera" serve --model "multilingual=$MODEL_DIR/multilingual" \
    --host 127.0.0.1 --port 8010 --provider AXCLRTExecutionProvider --device 0
fi
# Wait for the HTTP listener only; the interface reports model loading separately.
"$PYTHON_ENV/bin/python" - <<'PY'
import time, urllib.request, urllib.error
for attempt in range(30):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8010/api/info',timeout=2) as response:
            assert response.status==200
        break
    except (OSError,urllib.error.URLError):time.sleep(.2)
else:raise SystemExit('网页服务未启动，请检查 laya-games 服务。')
PY
if command -v chromium >/dev/null && chromium --version >/dev/null 2>&1; then
  exec chromium --app=http://127.0.0.1:8010/ --no-first-run
elif command -v chromium-browser >/dev/null && chromium-browser --version >/dev/null 2>&1; then
  exec chromium-browser --app=http://127.0.0.1:8010/ --no-first-run
elif command -v firefox >/dev/null; then
  exec firefox --new-window http://127.0.0.1:8010/
else
  exec xdg-open http://127.0.0.1:8010/
fi
