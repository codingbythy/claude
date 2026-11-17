#!/usr/bin/env bash
# Assembles the long video from the parts in this folder.
# Usage: build.sh [loops=40] [output=video.mp4]   (40 loops + intro + ending = about 2 hours)
# Needs ffmpeg. Video is copied without re-encoding; only the audio is mixed.
set -euo pipefail
cd "$(dirname "$0")"
N=${1:-40}; OUT=${2:-video.mp4}
TOTAL=$((170 + N * 180 + 30))
# Music: with music-long.py and music.conf in the kit, compose a fresh, non-repeating bed for the
# whole length (a few minutes of work); otherwise loop music.flac.
MUSIC=music.flac
if [ -f music-long.py ] && [ -f music.conf ] && python3 -c "import numpy" 2>/dev/null; then
  read -r SEED TR RMS SLOW < music.conf
  echo "Composing $((TOTAL / 60)) minutes of music..."
  python3 music-long.py "$TOTAL" music-long.wav "$SEED" "$TR" "$RMS" "$SLOW" >/dev/null
  MUSIC=music-long.wav
fi
{ echo "file intro.mp4"; for _ in $(seq "$N"); do echo "file loop.mp4"; done; echo "file outro.mp4"; } > list.txt
ffmpeg -y -loglevel error -stream_loop -1 -i ambience.flac -stream_loop -1 -i "$MUSIC" -filter_complex \
  "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0[amb];[1:a]aresample=48000[m];[amb][m]amix=inputs=2:normalize=0,afade=in:st=0:d=0.5,afade=out:st=$((TOTAL - 14)):d=14[a]" \
  -map "[a]" -t "$TOTAL" -c:a aac -b:a 160k audio.m4a
ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -i audio.m4a -map 0:v -map 1:a -c copy -shortest -movflags +faststart "$OUT"
rm -f list.txt audio.m4a music-long.wav
echo "Built $OUT ($((TOTAL / 60)) minutes)"
