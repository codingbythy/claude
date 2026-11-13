#!/usr/bin/env bash
# Crossfades the end of a render-scene.js output into its start, giving a seamless loop.
# Usage: make-loop.sh <render-dir> [loop-seconds=180] [crossfade-seconds=4]
# Reads raw.mp4 + raw.f32 from render-dir; writes loopv.mp4 (video only) and loop.wav there.
set -euo pipefail
D=$1; L=${2:-180}; X=${3:-4}
python3 - "$D" "$L" "$X" <<'PY'
import sys, wave, numpy as np
D, L, X = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); SR = 48000; PRE = 10
a = np.fromfile(D + '/raw.f32', '<f4')[PRE*SR:(PRE+L+X)*SR].astype(np.float64)
head, mid, tail = a[:X*SR], a[X*SR:L*SR], a[L*SR:(L+X)*SR]
k = np.linspace(0, 1, X*SR); loop = np.concatenate([mid, tail*np.cos(k*np.pi/2) + head*np.sin(k*np.pi/2)])
loop *= min(0.89/abs(loop).max(), 0.11/np.sqrt((loop**2).mean()))
st = np.repeat((loop*32767).astype('<i2')[:, None], 2, axis=1)
w = wave.open(D + '/loop.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
PY
ffmpeg -y -loglevel error -i "$D/raw.mp4" -filter_complex \
  "[0:v]split=3[a][b][c];[a]trim=0:$X,setpts=PTS-STARTPTS[head];[b]trim=$X:$L,setpts=PTS-STARTPTS[mid];[c]trim=$L:$((L+X)),setpts=PTS-STARTPTS[tail];[tail][head]xfade=transition=fade:duration=$X:offset=0[xf];[mid][xf]concat=n=2:v=1[v]" \
  -map "[v]" -r 30 -c:v libx264 -preset slow -crf 19 -g 60 -pix_fmt yuv420p -movflags +faststart "$D/loopv.mp4"
