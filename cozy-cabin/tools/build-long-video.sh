#!/usr/bin/env bash
# Builds the long YouTube upload from the 3-minute loop:
#   title-card intro (starts just before a lightning strike) + N loops + fade-out ending,
#   with the ambience loop mixed over a 12-minute music loop.
# Needs: loopv.mp4 (video-only loop), amb_rot.wav (ambience loop rotated by 10 s),
#        music.wav (make-music.py), title.png (make-title.js). Usage: build-long-video.sh [loops=40]
set -euo pipefail
N=${1:-40}; TOTAL=$((170 + N * 180 + 30))
V="-c:v libx264 -preset slow -crf 29 -g 60 -pix_fmt yuv420p -r 30 -video_track_timescale 15360 -an"
ffmpeg -y -loglevel error -i loopv.mp4 $V loop.mp4
ffmpeg -y -loglevel error -ss 10 -i loopv.mp4 -loop 1 -t 9 -i title.png -filter_complex \
  "[1:v]format=rgba,fade=in:st=0.8:d=1.2:alpha=1,fade=out:st=7:d=1.5:alpha=1[t];[0:v]fade=in:st=0:d=1.5[b];[b][t]overlay=eof_action=pass[v]" \
  -map "[v]" -t 170 $V intro.mp4
ffmpeg -y -loglevel error -t 30 -i loopv.mp4 -vf "fade=out:st=20:d=10" $V outro.mp4
{ echo "file intro.mp4"; for _ in $(seq "$N"); do echo "file loop.mp4"; done; echo "file outro.mp4"; } > list.txt
ffmpeg -y -loglevel error -stream_loop -1 -i amb_rot.wav -stream_loop -1 -i music.wav -filter_complex \
  "[1:a]aresample=48000[m];[0:a][m]amix=inputs=2:normalize=0,afade=in:st=0:d=2.5,afade=out:st=$((TOTAL - 14)):d=14[a]" \
  -map "[a]" -t "$TOTAL" -c:a aac -b:a 160k audio.m4a
ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -i audio.m4a -map 0:v -map 1:a -c copy -shortest -movflags +faststart long.mp4
