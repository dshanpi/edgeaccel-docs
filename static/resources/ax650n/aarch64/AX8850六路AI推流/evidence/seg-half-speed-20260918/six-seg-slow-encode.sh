set -eu
BASE=/home/baiwen/ax-pipeline
SRC=$BASE/video/1080p/traffic3.mp4
DST=$BASE/video/1080p/traffic3_slow_0p5x.mp4
PART=$BASE/video/1080p/traffic3_slow_0p5x.partial.mp4
EVD=$BASE/six/evidence/seg-half-speed-20260918
test -f "$SRC"
test ! -e "$DST"
test ! -e "$PART"
mkdir -p "$EVD"
ffprobe -v error -show_format -show_streams -of json "$SRC" > "$EVD/input-probe.json"
sha256sum "$SRC" > "$EVD/input-sha256-before.txt"
nice -n 10 ffmpeg -hide_banner -nostdin -nostats -stats_period 20 -progress pipe:1 \
  -threads 2 -i "$SRC" -map 0:v:0 -an -filter_threads 1 \
  -vf 'setpts=2*(PTS-STARTPTS),fps=30/1,tpad=stop_mode=clone:stop_duration=0.1' \
  -frames:v 2404 -c:v libx264 -preset veryfast -crf 20 -threads 2 \
  -pix_fmt yuv420p -movflags +faststart -n "$PART"
ffprobe -v error -show_format -show_streams -of json "$PART" > "$EVD/output-probe.json"
python3 - "$EVD" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); a=json.loads((p/'input-probe.json').read_text()); b=json.loads((p/'output-probe.json').read_text())
av=next(s for s in a['streams'] if s['codec_type']=='video'); bv=next(s for s in b['streams'] if s['codec_type']=='video')
assert (bv['width'],bv['height'],bv['codec_name'])==(1920,1080,'h264'),bv
assert bv['avg_frame_rate']=='30/1',bv
assert int(bv['nb_frames'])==2404,bv
assert abs(float(bv['duration'])-2*float(av['duration']))<.05,(av,bv)
print('VALIDATED', json.dumps({k:bv[k] for k in ['codec_name','width','height','avg_frame_rate','duration','nb_frames']}))
PY
nice -n 10 ffmpeg -hide_banner -nostdin -v error -xerror -threads 2 -i "$PART" -map 0:v:0 -f null -
sha256sum -c "$EVD/input-sha256-before.txt"
mv "$PART" "$DST"
chown baiwen:baiwen "$DST"
sha256sum "$DST" > "$EVD/output-sha256.txt"
printf 'SLOW_FILE_READY\n'
