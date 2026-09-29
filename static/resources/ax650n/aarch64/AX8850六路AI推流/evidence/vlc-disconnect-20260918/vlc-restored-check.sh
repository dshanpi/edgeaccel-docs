set -eu
python3 /tmp/vlc-restored-check.py
systemctl show ax-six-rtsp ax-six-local-preview ax-six-vlc-preview -p Id -p MainPID -p ActiveState
ss -ltnp | grep -E '8554|8850|8851' || true
