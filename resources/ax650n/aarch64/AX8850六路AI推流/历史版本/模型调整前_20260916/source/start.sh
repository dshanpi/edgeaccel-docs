#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
if systemctl is-active --quiet ax-six-rtsp; then
  echo 'Six-channel service is already running.'
  exit 0
fi
sudo systemctl stop ax-pipeline-pcd 2>/dev/null || true
sudo systemd-run --unit=ax-six-rtsp --collect --property=WorkingDirectory="$ROOT" --property=TimeoutStopSec=30 /bin/bash "$ROOT/run.sh"
echo 'Overview: rtsp://192.168.1.44:8554/overview'
