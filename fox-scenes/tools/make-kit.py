#!/usr/bin/env python3
"""Packs a finished loop into a scene's video-kit: the parts the Colab notebook downloads to build the long video.

Usage: make-kit.py <scene> [--crf 25]
Reads fox-scenes/work/<scene>/loop/{loopv.mp4,loop.wav} (tools/make-loop.py) and fox-scenes/work/<scene>/open/raw.mp4
(tools/render.js with &open=14 and 10 seconds: the same opening seconds of the loop, with the foxes nestling in).
Writes fox-scenes/<scene>/video-kit/: open.mp4, loop-a.mp4, loop-b.mp4, outro.mp4, ambience.flac, kit.json, build.py
(and music-long.py for scenes with music).
"""
import json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
scene = sys.argv[1]; crf = sys.argv[sys.argv.index('--crf') + 1] if '--crf' in sys.argv else '25'
C = json.load(open(f'{ROOT}/{scene}/scene.json')); W = f'{ROOT}/work/{scene}'; KIT = f'{ROOT}/{scene}/video-kit'
os.makedirs(KIT, exist_ok=True)
OPEN, X, LOOP, OUTRO = 6, 4, 180, 20            # seconds: opening clip, where the loop starts inside the opening render, loop, ending
V = ['-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-g', '60', '-keyint_min', '60', '-sc_threshold', '0', '-pix_fmt', 'yuv420p', '-r', '30', '-video_track_timescale', '15360', '-an']


def run(cmd):
    subprocess.run(cmd, check=True)


ff = ['ffmpeg', '-y', '-loglevel', 'error']
run(ff + ['-i', f'{W}/open/raw.mp4', '-ss', str(X), '-t', str(OPEN)] + V + [f'{KIT}/open.mp4'])
run(ff + ['-i', f'{W}/loop/loopv.mp4', '-t', str(OPEN)] + V + [f'{KIT}/loop-a.mp4'])
run(ff + ['-i', f'{W}/loop/loopv.mp4', '-ss', str(OPEN), '-t', str(LOOP - OPEN)] + V + [f'{KIT}/loop-b.mp4'])
run(ff + ['-i', f'{W}/loop/loopv.mp4', '-t', str(OUTRO), '-vf', f'fade=out:st={OUTRO - 10}:d=10'] + V + [f'{KIT}/outro.mp4'])

# the weather loop, stored at a known loudness so the build needs no measuring of its own
log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f'{W}/loop/loop.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
s = log[log.rindex('Summary:'):]; lufs = float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1)); peak = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))
gain = -20 - lufs
if peak + gain > -1:
    sys.exit(f'{scene}: ambience would peak at {peak + gain:.1f} dBFS at -20 LUFS; lower the loud moments in the scene sound first')
run(ff + ['-i', f'{W}/loop/loop.wav', '-af', f'volume={gain:.2f}dB', '-sample_fmt', 's16', '-c:a', 'flac', f'{KIT}/ambience.flac'])

files = ['open.mp4', 'loop-a.mp4', 'loop-b.mp4', 'outro.mp4', 'ambience.flac', 'build.py']
shutil.copy(f'{HERE}/kit-build.py', f'{KIT}/build.py')
if C['mix'].get('music'):
    shutil.copy(f'{REPO}/tools/music-long.py', f'{KIT}/music-long.py'); files.append('music-long.py')
slug = re.sub(r'[^a-z0-9]+', '-', C['title'].lower().replace("'", '')).strip('-')
json.dump({'title': C['title'], 'file_name': f"{slug}-{C['hours']}h", 'hours': C['hours'], 'loop_seconds': LOOP, 'open_seconds': OPEN, 'outro_seconds': OUTRO,
           'ambience_lufs': -20, 'mix': C['mix'], 'files': files}, open(f'{KIT}/kit.json', 'w'), indent=1)
for f in sorted(os.listdir(KIT)):
    print(f'  {os.path.getsize(f"{KIT}/{f}") / 1e6:7.1f} MB  {f}')
