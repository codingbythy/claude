#!/usr/bin/env bash
# Turns a rendered 3-minute loop into a video kit (the parts the Colab notebook downloads).
# Usage: build-kit.sh <loopv.mp4> <ambience.wav> <music.wav> <title.png> <kit-dir>
#   loopv.mp4    seamless 180 s loop, video only (crossfaded output of render-scene.js)
#   ambience.wav seamless 180 s ambience matching the loop
#   music.wav    music loop (make-music.py), any length
#   title.png    transparent title card (make-title.js)
set -euo pipefail
LOOPV=$1; AMB=$2; MUSIC=$3; TITLE=$4; KIT=$5
mkdir -p "$KIT"
V="-c:v libx264 -preset slow -crf 29 -g 60 -pix_fmt yuv420p -r 30 -video_track_timescale 15360 -an"
ffmpeg -y -loglevel error -i "$LOOPV" $V "$KIT/loop.mp4"
# intro: the loop from 10 s on, with the title card fading in and out; the loop's first lightning strike (13 s) lands 3 s in.
# The ambience is rotated by the same 10 s so picture and sound stay in sync through every repeat.
ffmpeg -y -loglevel error -ss 10 -i "$LOOPV" -loop 1 -t 9 -i "$TITLE" -filter_complex \
  "[1:v]format=rgba,fade=in:st=0.8:d=1.2:alpha=1,fade=out:st=7:d=1.5:alpha=1[t];[0:v]fade=in:st=0:d=1.5[b];[b][t]overlay=eof_action=pass[v]" \
  -map "[v]" -t 170 $V "$KIT/intro.mp4"
ffmpeg -y -loglevel error -t 30 -i "$LOOPV" -vf "fade=out:st=20:d=10" $V "$KIT/outro.mp4"
ffmpeg -y -loglevel error -stream_loop 1 -i "$AMB" -ss 10 -t 180 -ac 1 -c:a flac "$KIT/ambience.flac"
ffmpeg -y -loglevel error -i "$MUSIC" -c:a flac "$KIT/music.flac"
cp "$(dirname "$0")/kit-build.sh" "$KIT/build.sh"; chmod +x "$KIT/build.sh"
ls -la "$KIT"
