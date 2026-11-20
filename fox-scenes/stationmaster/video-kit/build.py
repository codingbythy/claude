#!/usr/bin/env python3
"""Assembles the long video from the parts in this folder. Copied into every scene's video-kit as build.py.

Usage: build.py [output.mp4] [--loops N]
With no --loops, it makes the number of hours written in kit.json. Needs ffmpeg, and numpy for scenes with music.
The picture is copied without re-encoding; only the sound is mixed.

How the video is laid out:
  open.mp4      the first 6 s: the foxes nestle into each other (it is the start of the loop, with that added)
  loop-b.mp4    the rest of the 3-minute loop
  loop-a.mp4 + loop-b.mp4, repeated: the loop itself
  outro.mp4     20 s of the loop fading to black
The sound starts at full level on the first frame and fades out with the picture at the end.
"""
import json, os, re, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
K = json.load(open('kit.json')); M = K['mix']
args = [a for a in sys.argv[1:] if not a.startswith('--')]
loops = int(sys.argv[sys.argv.index('--loops') + 1]) if '--loops' in sys.argv else round(K['hours'] * 3600 / K['loop_seconds'])
out = args[0] if args else f"{K['file_name']}.mp4"
total = loops * K['loop_seconds'] + K['outro_seconds']


def run(cmd):
    subprocess.run(cmd, check=True)


def loudness(path, chain=''):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', chain + 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', log[log.rindex('Summary:'):]).group(1))


inputs = ['-stream_loop', '-1', '-i', 'ambience.flac']
tail = f"alimiter=limit=0.84:level=disabled,afade=out:st={total - 14}:d=14[a]"
music = M.get('music')
if music:
    # compose music for the whole length (it does not repeat), then sit the weather a set distance underneath it
    print(f'Composing {total // 60} minutes of music...')
    run(['python3', 'music-long.py', str(total + 2), 'music.wav', str(music['seed']), str(music.get('transpose', 0)), '0.075', '1.0', str(music.get('bpm', 0)), music.get('style', 'ambient')])
    eq = M['music_eq'] + ',' if M.get('music_eq') else ''
    mus = loudness('music.wav', eq)
    amb_level = -20 + M['ambience_vs_music_db']
    both = 10 * __import__('math').log10(10 ** (-20 / 10) + 10 ** (amb_level / 10))            # the two together
    graph = (f"[0:a]volume={amb_level - K['ambience_lufs']:.2f}dB[amb];[1:a]aresample=48000,{eq}volume={-20 - mus:.2f}dB[mus];"
             f"[amb][mus]amix=inputs=2:normalize=0,volume={M['target_lufs'] - both:.2f}dB,{tail}")
    inputs += ['-i', 'music.wav']
else:
    graph = f"[0:a]volume={M['target_lufs'] - K['ambience_lufs']:.2f}dB,{tail}"
print('Mixing the sound...')
run(['ffmpeg', '-y', '-loglevel', 'error'] + inputs + ['-filter_complex', graph, '-map', '[a]', '-t', str(total), '-c:a', 'aac', '-b:a', '192k', 'audio.m4a'])

with open('list.txt', 'w') as f:
    f.write('file open.mp4\nfile loop-b.mp4\n' + 'file loop-a.mp4\nfile loop-b.mp4\n' * (loops - 1) + 'file outro.mp4\n')
print('Joining the picture...')
run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'list.txt', '-i', 'audio.m4a', '-map', '0:v', '-map', '1:a', '-c', 'copy', '-shortest', '-movflags', '+faststart', out])
for f in ('list.txt', 'audio.m4a', 'music.wav'):
    if os.path.exists(f):
        os.remove(f)
print(f'Built {out}: {total // 3600} h {total % 3600 // 60} min {total % 60} s')
