#!/bin/bash
set -euo pipefail
ROOT=/home/baiwen/ax-pipeline/six
BACKUP="$ROOT/backups/before-npu-opt-20260916-182855"
cd "$ROOT"
for f in config.json run.sh build.sh six_app.cpp six_app; do test -f "$BACKUP/$f"; done
sudo systemctl stop ax-six-rtsp
sudo install -m 0644 "$BACKUP/config.json" config.json
sudo install -m 0755 "$BACKUP/run.sh" run.sh
sudo install -m 0755 "$BACKUP/build.sh" build.sh
sudo install -m 0644 "$BACKUP/six_app.cpp" src/six_app.cpp
sudo install -m 0755 "$BACKUP/six_app" bin/six_app.restore
sudo mv -f bin/six_app.restore bin/six_app
./start.sh
echo 'Restored the version from before inference optimization.'