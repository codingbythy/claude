#!/usr/bin/env python3
"""Builds a short preview clip of a fox scene: picture, weather sound and (for lo-fi scenes) music, mixed and levelled.

Usage: preview.py <scene> [seconds=60] [--type lofi|ambience] [--audio-only] [--port 8791]
Needs the fox-scenes folder served locally first:  python3 -m http.server 8791 --bind 127.0.0.1   (run inside fox-scenes/)
Writes fox-scenes/work/<scene>/<scene>-preview.mp4 (or .m4a with --audio-only) and prints a sound report.

The sound rules every scene is held to (the report says pass or fail for each):
  - full level from the first second: no fade-in, no silence
  - overall loudness on target (scene.json mix.target_lufs, -14 LUFS), peaks under -1 dBFS
  - still clearly there on a phone speaker: no more than 7 dB lost through a small-speaker filter
"""
import json, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
args = [a for i, a in enumerate(sys.argv[1:]) if not a.startswith('--') and sys.argv[i] not in ('--type', '--port')]
scene = args[0]; secs = int(args[1]) if len(args) > 1 else 60
audio_only = '--audio-only' in sys.argv
port = sys.argv[sys.argv.index('--port') + 1] if '--port' in sys.argv else '8791'
C = json.load(open(f'{ROOT}/{scene}/scene.json'))
kind = sys.argv[sys.argv.index('--type') + 1] if '--type' in sys.argv else C['mix']['home']
M = dict(C['mix'][kind], target_lufs=C['mix']['target_lufs'], mode=kind)
work = f'{ROOT}/work/{scene}'; os.makedirs(work, exist_ok=True)
SR = 48000


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def lufs(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    tail = out[out.rindex('Summary:'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', tail).group(1)), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', tail).group(1))


def decode(path, af=None):
    cmd = ['ffmpeg', '-v', 'error', '-i', path] + (['-af', af] if af else []) + ['-ar', str(SR), '-ac', '1', '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, '<f4').astype(np.float64)


db = lambda p: 10 * np.log10(max(float(p), 1e-20))

# 1. render picture and weather sound
run(['node', f'{HERE}/render.js', f'http://127.0.0.1:{port}/scene.html?s={scene}', work, str(secs)] + (['--audio-only'] if audio_only else []))
run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', f'{work}/raw.f32', '-c:a', 'pcm_f32le', f'{work}/ambience.wav'])
amb_l, _ = lufs(f'{work}/ambience.wav')

# 2. music, for scenes that have it
inputs = ['-i', f'{work}/ambience.wav']; graph = '[0:a]volume={a}dB[amb]'; music = M.get('music')
if music:
    run(['python3', f'{REPO}/tools/music-long.py', str(secs + 2), f'{work}/music.wav', str(music['seed']), str(music.get('transpose', 0)), '0.075', '1.0', str(music.get('bpm', 0)), music.get('style', 'ambient')], stdout=subprocess.DEVNULL)
    eq = M['music_eq'] + ',' if M.get('music_eq') else ''      # the music engine is dark; this lifts it into the range small speakers play
    if eq:
        run(['ffmpeg', '-y', '-v', 'error', '-i', f'{work}/music.wav', '-af', M['music_eq'], f'{work}/music-eq.wav'])
    mus_l, _ = lufs(f'{work}/music-eq.wav' if eq else f'{work}/music.wav')
    if M['mode'] == 'lofi':      # music leads, weather sits a set distance underneath
        g_mus, g_amb = -20 - mus_l, -20 + M['ambience_vs_music_db'] - amb_l
    else:                        # weather leads, music is a quiet bed
        g_amb, g_mus = -20 - amb_l, -20 + M['music_vs_ambience_db'] - mus_l
    inputs += ['-i', f'{work}/music.wav']
    graph = f'[0:a]volume={g_amb:.2f}dB[amb];[1:a]aresample={SR},{eq}volume={g_mus:.2f}dB[mus];[amb][mus]amix=inputs=2:normalize=0[mix]'
else:
    graph = f'[0:a]volume={-20 - amb_l:.2f}dB[mix]'
run(['ffmpeg', '-y', '-v', 'error'] + inputs + ['-filter_complex', graph, '-map', '[mix]', '-t', str(secs), '-c:a', 'pcm_s24le', f'{work}/mix.wav'])

# 3. level to target, catch peaks, and (preview only) fade the last second and a half
mix_l, _ = lufs(f'{work}/mix.wav'); gain = M['target_lufs'] - mix_l
run(['ffmpeg', '-y', '-v', 'error', '-i', f'{work}/mix.wav', '-af', f'volume={gain:.2f}dB,alimiter=limit=0.84:level=disabled,afade=out:st={secs - 1.5}:d=1.5', '-c:a', 'pcm_s24le', f'{work}/final.wav'])
out = f'{work}/{scene}-preview.' + ('m4a' if audio_only else 'mp4')
if audio_only:
    run(['ffmpeg', '-y', '-v', 'error', '-i', f'{work}/final.wav', '-c:a', 'aac', '-b:a', '192k', out])
else:
    run(['ffmpeg', '-y', '-v', 'error', '-i', f'{work}/raw.mp4', '-i', f'{work}/final.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-g', '60', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out])

# 4. report
fin_l, fin_pk = lufs(f'{work}/final.wav')
x = decode(f'{work}/final.wav'); body = np.mean(x[5 * SR:(secs - 3) * SR] ** 2)
first = db(np.mean(x[:SR] ** 2)) - db(body)
phone = db(body) - db(np.mean(decode(f'{work}/final.wav', 'highpass=f=400,highpass=f=400')[5 * SR:(secs - 3) * SR] ** 2))
n = 1 << 15; acc = np.zeros(n // 2 + 1); win = np.hanning(n)
for i in range(5 * SR, (secs - 3) * SR - n, n // 2):
    acc += np.abs(np.fft.rfft(x[i:i + n] * win)) ** 2
f = np.fft.rfftfreq(n, 1 / SR); share = lambda a, b: 100 * acc[(f >= a) & (f < b)].sum() / acc.sum()
ok = lambda c: 'pass' if c else 'FAIL'
print(f'\n{C["title"]}  ({M["mode"]}, {secs} s preview)')
print(f'  loudness {fin_l:.1f} LUFS (target {M["target_lufs"]}) {ok(abs(fin_l - M["target_lufs"]) <= 1)} | peak {fin_pk:.1f} dBFS {ok(fin_pk <= -1)}')
print(f'  first second vs the rest: {first:+.1f} dB {ok(first > -2)}')
print(f'  lost on a phone speaker: {phone:.1f} dB {ok(phone <= 7)}')
print(f'  energy: below 40 Hz {share(0, 40):.1f}% | 40-150 {share(40, 150):.0f}% | 150-400 {share(150, 400):.0f}% | 400-1k {share(400, 1000):.0f}% | 1k-4k {share(1000, 4000):.0f}% | above 4k {share(4000, 24000):.1f}%')
if music:
    print(f'  weather {amb_l + (g_amb):.1f} LUFS, music {mus_l + g_mus:.1f} LUFS before the final levelling')
print(f'  -> {out}')
