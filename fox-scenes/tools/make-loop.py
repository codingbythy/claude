#!/usr/bin/env python3
"""Turns a render into a seamless loop: the last few seconds are blended into the first few, so the end meets the start.

Usage: make-loop.py <render-dir> [loop-seconds=180] [crossfade-seconds=4]
Reads raw.mp4 and raw.f32 (48 kHz stereo float, from tools/render.js with seconds = loop + crossfade).
Writes loopv.mp4 (picture only, high quality) and loop.wav (stereo, 32-bit float) in the same folder.

The loop begins <crossfade> seconds into the render and ends on the blend, so its last frame leads into its first.
"""
import subprocess, sys, wave
import numpy as np

D = sys.argv[1]; L = int(sys.argv[2]) if len(sys.argv) > 2 else 180; X = int(sys.argv[3]) if len(sys.argv) > 3 else 4
SR = 48000
a = np.fromfile(f'{D}/raw.f32', '<f4').reshape(-1, 2).astype(np.float64)
if len(a) < (L + X) * SR:
    sys.exit(f'{D}/raw.f32 holds {len(a) / SR:.1f} s; {L + X} s are needed')
head, mid, tail = a[:X * SR], a[X * SR:L * SR], a[L * SR:(L + X) * SR]
k = np.linspace(0, 1, X * SR)[:, None]
loop = np.concatenate([mid, tail * np.cos(k * np.pi / 2) + head * np.sin(k * np.pi / 2)])       # equal-power blend, both channels
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_f32le', f'{D}/loop.wav'],
               input=loop.astype('<f4').tobytes(), check=True)
fmt = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=pix_fmt', '-of', 'default=nw=1:nk=1', f'{D}/raw.mp4'], capture_output=True, text=True).stdout.strip()
# a native-resolution render (tools/render.js --size) is exact RGB: keep it exact. A 1080p render is already compressed: keep it light.
enc = ['-c:v', 'libx264rgb', '-preset', 'medium', '-crf', '0'] if 'rgb' in fmt or 'bgr' in fmt or 'gbr' in fmt else ['-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p']
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', f'{D}/raw.mp4', '-filter_complex',
                f'[0:v]split=3[a][b][c];[a]trim=0:{X},setpts=PTS-STARTPTS[head];[b]trim={X}:{L},setpts=PTS-STARTPTS[mid];'
                f'[c]trim={L}:{L + X},setpts=PTS-STARTPTS[tail];[tail][head]xfade=transition=fade:duration={X}:offset=0[xf];[mid][xf]concat=n=2:v=1[v]',
                '-map', '[v]', '-r', '30'] + enc + ['-g', '60', f'{D}/loopv.mp4'], check=True)
print(f'{D}: loop of {len(loop) / SR:.0f} s written (loopv.mp4, loop.wav)')
