#!/usr/bin/env python3
"""Assembles the long video from the parts in this folder. Copied into every scene's video-kit as build.py.

Usage: build.py [output.mp4] [--type lofi|ambience] [--loops N] [--scale 4]
With no --type it makes the scene's home type; with no --loops, the number of hours written in kit.json.
lofi is music over the scene's own sounds; ambience is the scene's sounds only. Needs ffmpeg, and numpy for lofi.

What it does, in order:
  1. Enlarges the loop. loop-360.mp4 is the three-minute loop at the scene's own size (640x360, every pixel exact). It is
     scaled up by a whole number (4 = 2560x1440, 3 = 1920x1080) with hard pixel edges, so the picture stays perfectly sharp,
     and encoded once at high quality for YouTube. The ending (20 s fading to black) is made the same way.
  2. Mixes the sound: the weather loop, plus music composed for the whole length when the scene has it, levelled to the
     loudness YouTube plays at. Full level from the first frame; it fades out with the picture at the end.
  3. Joins loop after loop without re-encoding, adds the ending and the sound.
"""
import json, math, os, re, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
K = json.load(open('kit.json')); Y = K['youtube']
argv = sys.argv[1:]
opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
args = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or not argv[i - 1].startswith('--'))]
loops = int(opt('--loops', round(K['hours'] * 3600 / K['loop_seconds'])))
scale = int(opt('--scale', Y['scale']))
kind = opt('--type', K['home'])
if kind not in K['mixes']:
    sys.exit(f"This scene is not set up as {kind}; it has: {', '.join(K['mixes'])}")
M = dict(K['mixes'][kind], target_lufs=K['target_lufs'])
out = args[0] if args else f"{K['slug']}-{kind}-{K['hours']}h.mp4"
total = loops * K['loop_seconds'] + K['outro_seconds']
W, H = K['width'] * scale, K['height'] * scale


def run(cmd):
    subprocess.run(cmd, check=True)


def loudness(path, chain=''):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', chain + 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', log[log.rindex('Summary:'):]).group(1))


# 1. the picture: whole-number enlargement with hard edges, tagged as standard HD colour (BT.709) so YouTube reads it correctly
big = f"scale={W}:{H}:flags=neighbor+accurate_rnd+full_chroma_int:out_color_matrix=bt709:out_range=tv,format=yuv420p"
V = ['-c:v', 'libx264', '-preset', Y['preset'], '-crf', str(Y['crf']), '-profile:v', 'high', '-bf', '2', '-g', '60', '-keyint_min', '60', '-sc_threshold', '0', '-r', '30',
     '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-video_track_timescale', '15360', '-an']
ff = ['ffmpeg', '-y', '-loglevel', 'error']
print(f'Enlarging the loop to {W}x{H}...')
run(ff + ['-i', 'loop-360.mp4', '-vf', big] + V + ['loop.mp4'])
run(ff + ['-i', 'loop-360.mp4', '-t', str(K['outro_seconds']), '-vf', f"fade=out:st={K['outro_seconds'] - 10}:d=10,{big}"] + V + ['outro.mp4'])

# 2. the sound
inputs = ['-stream_loop', '-1', '-i', 'ambience.flac']
tail = f"alimiter=limit=0.89:level=disabled,afade=out:st={total - 14}:d=14[a]"
music = M.get('music')
if music:
    print(f'Composing {total // 60} minutes of music...')
    run(['python3', 'music-long.py', str(total + 2), 'music.wav', str(music['seed']), str(music.get('transpose', 0)), '0.075', '1.0', str(music.get('bpm', 0)), music.get('style', 'ambient')])
    eq = M['music_eq'] + ',' if M.get('music_eq') else ''
    mus = loudness('music.wav', eq)
    amb_level = -20 + M['ambience_vs_music_db']                                      # the weather sits this far under the music
    both = 10 * math.log10(10 ** (-20 / 10) + 10 ** (amb_level / 10))                # the two together
    graph = (f"[0:a]volume={amb_level - K['ambience_lufs']:.2f}dB[amb];[1:a]aresample=48000,{eq}volume={-20 - mus:.2f}dB[mus];"
             f"[amb][mus]amix=inputs=2:normalize=0,volume={M['target_lufs'] - both:.2f}dB,{tail}")
    inputs += ['-i', 'music.wav']
else:
    graph = f"[0:a]volume={M['target_lufs'] - K['ambience_lufs']:.2f}dB,{tail}"
print('Mixing the sound...')
run(ff + inputs + ['-filter_complex', graph, '-map', '[a]', '-t', str(total), '-c:a', 'aac', '-b:a', Y['audio_bitrate'], '-ar', '48000', 'audio.m4a'])

# 3. join
with open('list.txt', 'w') as f:
    f.write('file loop.mp4\n' * loops + 'file outro.mp4\n')
print('Joining...')
run(ff + ['-f', 'concat', '-safe', '0', '-i', 'list.txt', '-i', 'audio.m4a', '-map', '0:v', '-map', '1:a', '-c', 'copy', '-shortest', '-movflags', '+faststart', out])
for f in ('list.txt', 'audio.m4a', 'music.wav', 'loop.mp4', 'outro.mp4'):
    if os.path.exists(f):
        os.remove(f)
print(f'Built {out} ({kind}): {total // 3600} h {total % 3600 // 60} min {total % 60} s, {W}x{H}, {os.path.getsize(out) / 1e9:.1f} GB')
