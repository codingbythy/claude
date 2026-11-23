#!/usr/bin/env python3
"""Measures the takes of a scene's sound: that they are the same storm, that their detail differs, and how far the
occasional sounds (a gust hitting the wall, the wind whistling in a gap, the stove settling) stand out.

Usage: check-takes.py <scene>          reads fox-scenes/work/<scene>/takes/<n>/{raw.f32,events.json}
Per take: loudness, peak, quiet-to-loud range, and for each kind of occasional sound how many there are and how far the
level rises while it lasts, over the whole range and in the part a phone speaker plays (above 400 Hz).
Between takes: how alike the slow rise and fall is (it should be: the snow in the picture follows it), and how alike the
second-by-second detail and the sound itself are (they should not be).
"""
import glob, json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SR = 48000
dirs = sorted(glob.glob(f'{ROOT}/work/{sys.argv[1]}/takes/*/raw.f32'))
if not dirs:
    sys.exit('no takes found')


def ebur(pcm):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'ebur128=peak=true', '-f', 'null', '-'], input=pcm.tobytes(), capture_output=True).stderr.decode()
    s = log[log.rindex('Summary:'):]
    return [float(re.search(p, s).group(1)) for p in (r'I:\s+(-?[\d.]+) LUFS', r'LRA:\s+([\d.]+) LU', r'Peak:\s+(-?[\d.]+) dBFS')]


def band(pcm, af):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', af, '-ac', '1', '-f', 'f32le', '-'], input=pcm.tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(out, '<f4').astype(np.float64)


def env(x, win):
    n = int(SR * win); k = len(x) // n
    return 10 * np.log10((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-12)


BANDS = {'all': 'anull', 'phone (above 400 Hz)': 'highpass=f=400,highpass=f=400', 'low (60-250 Hz)': 'highpass=f=60,lowpass=f=250', 'whistle band (800-1800 Hz)': 'highpass=f=800,lowpass=f=1800'}
LENGTH = {'buffet': 1.5, 'whistle': 2.5, 'settle': 1.0}
takes = []
for f in dirs:
    a = np.fromfile(f, '<f4').reshape(-1, 2); ev = json.load(open(os.path.join(os.path.dirname(f), 'events.json')))
    I, lra, pk = ebur(a); e = {k: env(band(a, af), 0.25) for k, af in BANDS.items()}
    takes.append(dict(name=os.path.basename(os.path.dirname(f)), a=a, e=e, ev=ev))
    print(f"take {takes[-1]['name']}: {I:.1f} LUFS, peak {pk:.1f} dBFS, quiet-to-loud range {lra:.1f} LU; " + ', '.join(f"{sum(1 for x in ev if x[0] == k)} {k}s" for k in LENGTH))
    for kind, secs in LENGTH.items():
        rises = {k: [] for k in BANDS}
        for _, t in [x for x in ev if x[0] == kind]:
            i0, n = int(t / 0.25), max(1, int(secs / 0.25))
            for k, v in e.items():
                if i0 - 16 < 0 or i0 + n + 16 > len(v):
                    continue
                around = np.concatenate([v[i0 - 16:i0 - 2], v[i0 + n + 2:i0 + n + 16]])       # the four seconds either side
                rises[k].append(v[i0:i0 + n].max() - np.median(around))
        if rises['all']:
            print(f"    {kind}: " + ' | '.join(f"{k} {np.median(r):+.1f} dB (up to {max(r):+.1f})" for k, r in rises.items()))
    # the same measure at moments with no occasional sound, for comparison: how much the level rises by itself
    busy = np.zeros(len(e['all']), bool)
    for k, t in ev:
        busy[max(0, int(t / 0.25) - 4):int((t + LENGTH[k]) / 0.25) + 4] = True
    rng = np.random.default_rng(1); base = {k: [] for k in BANDS}
    for i0 in rng.integers(20, len(busy) - 30, 400):
        if not busy[i0:i0 + 6].any():
            for k, v in e.items():
                base[k].append(v[i0:i0 + 6].max() - np.median(np.concatenate([v[i0 - 16:i0 - 2], v[i0 + 8:i0 + 22]])))
    print('    ordinary moments: ' + ' | '.join(f"{k} {np.median(r):+.1f} dB" for k, r in base.items()))

if len(takes) > 1:
    print('between takes:')
    slow = [env(t['a'].mean(1).astype(np.float64), 3.0) for t in takes]
    fine = [env(t['a'].mean(1).astype(np.float64), 0.25) for t in takes]
    detail = [f[:12 * len(s)] - np.repeat(s, 12) for f, s in zip(fine, slow)]
    n = min(len(d) for d in detail)
    for i in range(len(takes)):
        for j in range(i + 1, len(takes)):
            m = min(len(takes[i]['a']), len(takes[j]['a']))
            wave = np.corrcoef(takes[i]['a'][:m, 0], takes[j]['a'][:m, 0])[0, 1]
            print(f"  {takes[i]['name']} and {takes[j]['name']}: slow rise and fall {np.corrcoef(slow[i], slow[j])[0, 1]:.2f} alike | level differs by up to {np.abs(slow[i] - slow[j]).max():.1f} dB (typically {np.median(np.abs(slow[i] - slow[j])):.1f}) | "
                  f"quarter-second detail {np.corrcoef(detail[i][:n], detail[j][:n])[0, 1]:.2f} alike | the sound itself {wave:+.3f}")
