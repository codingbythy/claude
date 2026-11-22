#!/usr/bin/env python3
"""Packs a finished loop into a scene's video-kit: the parts the Colab notebook downloads to build the long video.

Usage: make-kit.py <scene>
Reads fox-scenes/work/<scene>/loop/{loopv.mp4,loop.wav} (tools/render.js --size 640x360, then tools/make-loop.py).
Writes fox-scenes/<scene>/video-kit/: loop-360.mp4 (the loop at the scene's own size, every pixel exact), ambience.flac,
kit.json, build.py (and music-long.py for scenes with music). The kit stays small; build.py enlarges the loop for YouTube.
"""
import json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
scene = sys.argv[1]
C = json.load(open(f'{ROOT}/{scene}/scene.json')); W = f'{ROOT}/work/{scene}'; KIT = f'{ROOT}/{scene}/video-kit'
if os.path.isdir(KIT):
    shutil.rmtree(KIT)
os.makedirs(KIT)
LOOP, OUTRO = 180, 20


def run(cmd):
    subprocess.run(cmd, check=True)


def probe(path, entry):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', entry, '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True).stdout.split()


w, h = map(int, probe(f'{W}/loop/loopv.mp4', 'stream=width,height'))
if w > 960:
    sys.exit(f'{scene}: the loop is {w}x{h}. Render it at the scene\'s own size (render.js --size 640x360) so it can be enlarged exactly.')
# full colour resolution and a very light compression: no visible change from the exact render, and a fraction of its size
run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{W}/loop/loopv.mp4', '-c:v', 'libx264', '-preset', 'slow', '-crf', '12', '-pix_fmt', 'yuv444p', '-g', '60', '-an', f'{KIT}/loop-360.mp4'])

# the weather loop, stored at a known loudness so the build needs no measuring of its own
log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f'{W}/loop/loop.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
s = log[log.rindex('Summary:'):]; lufs = float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1)); peak = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))
gain = -20 - lufs
if peak + gain > -1:
    sys.exit(f'{scene}: ambience would peak at {peak + gain:.1f} dBFS at -20 LUFS; lower the loud moments in the scene sound first')
run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{W}/loop/loop.wav', '-af', f'volume={gain:.2f}dB', '-sample_fmt', 's16', '-c:a', 'flac', f'{KIT}/ambience.flac'])

files = ['loop-360.mp4', 'ambience.flac', 'build.py']
shutil.copy(f'{HERE}/kit-build.py', f'{KIT}/build.py')
if C['mix'].get('music'):
    shutil.copy(f'{REPO}/tools/music-long.py', f'{KIT}/music-long.py'); files.append('music-long.py')
slug = re.sub(r'[^a-z0-9]+', '-', C['title'].lower().replace("'", '')).strip('-')
json.dump({'title': C['title'], 'file_name': f"{slug}-{C['hours']}h", 'hours': C['hours'], 'loop_seconds': LOOP, 'outro_seconds': OUTRO, 'width': w, 'height': h,
           'youtube': {'scale': 4, 'crf': 21, 'preset': 'faster', 'audio_bitrate': '384k'},
           'ambience_lufs': -20, 'mix': C['mix'], 'files': files}, open(f'{KIT}/kit.json', 'w'), indent=1)
for f in sorted(os.listdir(KIT)):
    print(f'  {os.path.getsize(f"{KIT}/{f}") / 1e6:7.1f} MB  {f}')
