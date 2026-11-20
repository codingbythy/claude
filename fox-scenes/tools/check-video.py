#!/usr/bin/env python3
"""Checks a built fox-scene video: the opening, the joins between parts, and the sound level. Prints pass or FAIL per line.

Usage: check-video.py <video.mp4> [--loop 180] [--open 6]
  opening   the first frame is a full picture (not black) and the first second of sound is at full level
  joins     at each place two parts meet (after the opening, and each time the loop comes round) the picture changes no more
            than it does between ordinary frames, and the sound has no click or jump in level
  loudness  overall level and peak
"""
import re, subprocess, sys
import numpy as np

path = sys.argv[1]
LOOP = int(sys.argv[sys.argv.index('--loop') + 1]) if '--loop' in sys.argv else 180
OPEN = int(sys.argv[sys.argv.index('--open') + 1]) if '--open' in sys.argv else 6
SR = 48000; W, H = 480, 270
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True).stdout)
ok = lambda c: 'pass' if c else 'FAIL'


def frames(t, n):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.4f}', '-i', path, '-frames:v', str(n), '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).astype(np.float64).reshape(-1, W * H)


def audio(t, secs):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.4f}', '-t', str(secs), '-i', path, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, '<f4').astype(np.float64)


db = lambda p: 10 * np.log10(max(float(p), 1e-20))
psnr = lambda a, b: 10 * np.log10(255 ** 2 / max(np.mean((a - b) ** 2), 1e-9))

print(f'{path}: {int(dur // 3600)} h {int(dur % 3600 // 60)} min {dur % 60:.0f} s')
first = frames(0, 1)[0].mean(); later = frames(20, 1)[0].mean()
a = audio(0, 30); lv1 = db(np.mean(a[:SR] ** 2)); lvr = db(np.mean(a[5 * SR:] ** 2))
print(f'  opening: first frame brightness {first:.0f} (20 s in: {later:.0f}) {ok(first > 0.8 * later)} | first second of sound {lv1 - lvr:+.1f} dB against the next 25 s {ok(lv1 - lvr > -3)}')

joins = [(OPEN, 'opening -> loop')] + [(k * LOOP, f'loop comes round ({k})') for k in range(1, int((dur - 1) // LOOP) + 1) if k * LOOP < dur - 1][:3]
if len(joins) > 1:
    joins.append((joins[1][0] + OPEN, 'loop start -> rest of loop'))
ref = []
for t in (40, 75, 110):
    f = frames(t, 5); ref += [psnr(f[i], f[i + 1]) for i in range(4)]
floor = min(ref)                                    # the largest ordinary frame-to-frame change (lowest PSNR) seen away from any join
for t, label in joins:
    f = frames(t - 2 / 30, 4); p = min(psnr(f[i], f[i + 1]) for i in range(3))
    line = f'  join at {t:6.1f} s ({label}): picture {p:.1f} dB vs ordinary frames {floor:.1f}-{max(ref):.1f} {ok(p > floor - 2.5)}'
    if 'comes round' in label:                      # the only places the sound itself joins: where the weather loop wraps
        x = audio(t - 1.5, 3); j = int(1.5 * SR); d = np.abs(np.diff(x))
        step = d[j - 300:j + 300].max(); typical = np.percentile(d, 99.9)
        jump = db(np.mean(x[j:j + SR // 2] ** 2)) - db(np.mean(x[j - SR // 2:j] ** 2))
        line += f' | sound step {step / typical:.1f}x typical {ok(step < 4 * typical)}, level change {jump:+.1f} dB {ok(abs(jump) < 2.5)}'
    print(line)

log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
s = log[log.rindex('Summary:'):]; I = float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1)); pk = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1)); lra = float(re.search(r'LRA:\s+([\d.]+) LU', s).group(1))
print(f'  loudness: {I:.1f} LUFS {ok(-17.5 <= I <= -14.5)} | peak {pk:.1f} dBFS {ok(pk <= -1)} | quiet-to-loud range {lra:.1f} LU')
