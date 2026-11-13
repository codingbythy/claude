#!/usr/bin/env bash
# Composites the recurring black cat (cat.py) onto a scene loop.
# Usage: add-cat.sh <loopv.mp4> <out-dir>
# Writes loop-cat.mp4 (180 s, cat sitting), intro-cat.mp4 (170 s from 10 s in, cat walks in)
# and outro-cat.mp4 (30 s, cat walks out). Feed them to build-kit.sh:
#   INTRO_SRC=out/intro-cat.mp4 OUTRO_SRC=out/outro-cat.mp4 build-kit.sh out/loop-cat.mp4 ...
set -euo pipefail
LOOPV=$1; OUT=$2; HERE=$(dirname "$0"); mkdir -p "$OUT"
read -r X Y W H < <(python3 "$HERE/cat.py" region)
E="-c:v libx264 -preset slow -crf 16 -g 60 -pix_fmt yuv420p -r 30 -an"
comp() {  # comp <mode> <seconds> <out> <input args...>
  local mode=$1 secs=$2 out=$3; shift 3
  python3 "$HERE/cat.py" stream "$mode" "$secs" | ffmpeg -y -loglevel error "$@" \
    -f rawvideo -pix_fmt rgba -s "${W}x${H}" -framerate 30 -i - \
    -filter_complex "[0:v][1:v]overlay=$X:$Y:eof_action=pass[v]" -map "[v]" -t "$secs" $E "$out"
}
comp loop 180 "$OUT/loop-cat.mp4" -i "$LOOPV"
comp intro 170 "$OUT/intro-cat.mp4" -ss 10 -i "$LOOPV"
comp outro 30 "$OUT/outro-cat.mp4" -i "$LOOPV"
