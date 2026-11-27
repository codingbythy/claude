#!/usr/bin/env python3
"""Assembles the long video from the parts in this folder. Copied into every scene's video-kit as build.py.

Usage: build.py [output.mp4] [--type lofi|ambience] [--loops N] [--scale 4] [--music-dir folder] [--fire-dir folder]
With no --type it makes the scene's home type; with no --loops, the number of hours written in kit.json.
lofi is music over the scene's own sounds; ambience is the scene's sounds only. Needs ffmpeg and numpy.

What it does, in order:
  1. Enlarges the loop. The loop is three minutes at the scene's own size (640x360, every pixel exact). It is scaled up by a
     whole number (4 = 2560x1440, 3 = 1920x1080) with hard pixel edges, so the picture stays perfectly sharp, and encoded once
     at high quality for YouTube. The ending (20 s fading to black) is made the same way. A type can have its own picture
     (the room without the foxes), an opening (the snow blowing clear) that replaces the first seconds of the first loop,
     and the channel's mark in the bottom right-hand corner.
  2. Makes the sound. The weather comes as several takes of the same three minutes: the same storm, different detail. They are
     played in a shuffled order, never the same one twice running, each blended into the next over four seconds. lofi adds music:
     tracks from --music-dir if given (levelled, crossfaded, reshuffled each time round), otherwise music composed by
     music-long.py. Everything is levelled to the loudness YouTube plays at, full level from the first frame, fading out at the end.
  3. Joins the parts without re-encoding and adds the sound.
"""
import glob, json, math, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
opt = lambda name, default: argv[argv.index(name) + 1] if name in argv else default
args = [a for i, a in enumerate(argv) if not a.startswith('--') and (i == 0 or not argv[i - 1].startswith('--'))]
music_dir = os.path.abspath(opt('--music-dir', '')) if '--music-dir' in argv else None
fire_dir = os.path.abspath(opt('--fire-dir', '')) if '--fire-dir' in argv else None
out = os.path.abspath(args[0]) if args else None
os.chdir(HERE)
K = json.load(open('kit.json'))
kind = opt('--type', K['home'])
if kind not in K['mixes']:
    sys.exit(f"This scene is not set up as {kind}; it has: {', '.join(K['mixes'])}")
M = dict({'target_lufs': K['target_lufs']}, **K['mixes'][kind])          # a type can set its own loudness
HOURS = M.get('hours', K['hours'])                                   # a type can have its own length (ambience runs all night)
Y = dict(K['youtube'], **M.get('youtube', {}))                        # and its own encoding (a smaller file for the long ones)
loops = int(opt('--loops', round(HOURS * 3600 / K['loop_seconds'])))
scale = int(opt('--scale', Y['scale']))
out = out or f"{K['slug']}-{kind}-{HOURS}h.mp4"
LOOP, OUTRO, SR = K['loop_seconds'], K['outro_seconds'], 48000
total = loops * LOOP + OUTRO
W, H = K['width'] * scale, K['height'] * scale
P = K.get('pictures', {}).get(kind) or K.get('pictures', {}).get('default') or {'loop': 'loop-360.mp4'}       # the picture this type shows
mark = K.get('mark') if M.get('mark') else None
ff = ['ffmpeg', '-y', '-loglevel', 'error']


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def loudness(path, chain=''):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', chain + 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', log[log.rindex('Summary:'):]).group(1))


def decode(path):
    import numpy as np
    return np.frombuffer(run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout, '<f4').reshape(-1, 2)


# 1. the picture: whole-number enlargement with hard edges, tagged as standard HD colour (BT.709) so YouTube reads it correctly
big = f"scale={W}:{H}:flags=neighbor+accurate_rnd+full_chroma_int:out_color_matrix=bt709:out_range=tv,format=yuv420p"
V = ['-c:v', 'libx264', '-preset', Y['preset'], '-crf', str(Y['crf']), '-profile:v', 'high', '-bf', '2', '-g', '60', '-keyint_min', '60', '-sc_threshold', '0', '-r', '30',
     '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-video_track_timescale', '15360', '-an']


def encode(src, dst, start=0, seconds=None, fade_out=None, mark_from=None):
    """One part of the video: src from `start` for `seconds`, enlarged, with the corner mark if this type has one.
    mark_from = (second, seconds): the mark fades in then, instead of being there from the first frame."""
    cut = ['-ss', str(start)] if start else []
    pre = f'fade=out:st={fade_out[0]}:d={fade_out[1]},' if fade_out else ''
    if mark:
        size = f'scale=iw*{scale}/4:-1:flags=lanczos,' if scale != 4 else ''
        fade = f',fade=t=in:st={mark_from[0]}:d={mark_from[1]}:alpha=1' if mark_from else ''
        graph = (f'[0:v]{pre}{big}[v];[1:v]{size}scale=out_color_matrix=bt709:out_range=tv,format=yuva420p{fade}[m];'
                 f'[v][m]overlay=W-w-{round(0.022 * W)}:H-h-{round(0.03 * H)}:format=yuv420:shortest=1[o]')
        cmd = ff + ['-i', src, '-loop', '1', '-framerate', '30', '-i', mark, '-filter_complex', graph, '-map', '[o]'] + cut
    else:
        cmd = ff + ['-i', src, '-vf', pre + big] + cut
    run(cmd + (['-t', str(seconds)] if seconds else []) + V + [dst])


print(f'Enlarging the loop to {W}x{H}...')
parts, plain = [], loops
if P.get('open'):            # the opening, then the rest of the first loop: together exactly one loop long
    encode(P['open'], 'open.mp4', mark_from=(P.get('mark_at', 3.5), 2.5))
    encode(P['loop'], 'first.mp4', start=P['open_seconds'])
    parts += ['open.mp4', 'first.mp4']; plain -= 1
if plain:
    encode(P['loop'], 'loop.mp4')
    parts += ['loop.mp4'] * plain
encode(P['loop'], 'outro.mp4', seconds=OUTRO, fade_out=(OUTRO - 10, 10))
parts.append('outro.mp4')


# 2. the sound
def weather():
    """The long weather sound as 16-bit stereo, piece by piece: takes in a shuffled order, each blended into the next."""
    import numpy as np
    T = K['takes']; lead, L = T['lead'] * SR, LOOP * SR
    takes = [decode(f) for f in T['files']]
    rng = random.Random(K['slug'] + kind); order = []
    while len(order) < loops + 2:
        block = list(range(len(takes))); rng.shuffle(block)
        if order and len(block) > 1 and block[0] == order[-1]:
            block.append(block.pop(0))                                   # never the same take twice running
        order += block
    k = np.linspace(0, 1, lead, dtype=np.float32)[:, None]; down, up = np.cos(k * np.pi / 2), np.sin(k * np.pi / 2)
    pcm = lambda x: (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    F = K.get('fire')
    if F:                                  # the fire, made from its stems for the whole length, a set distance above the storm
        if not fire_dir or not os.path.isdir(fire_dir):
            sys.exit(f"This scene's fire needs its sound files: run with --fire-dir <folder> holding {', '.join(b[s] + '.ogg' for b in F['bands'] for s in 'ab')}")
        from stemfire import StemFire
        fire = StemFire(F, fire_dir); gf = 10 ** ((K['ambience_lufs'] + F['over_storm_db'] - F['lufs']) / 20)
        bed = 10 * math.log10(10 ** (K['ambience_lufs'] / 10) + 10 ** ((K['ambience_lufs'] + F['over_storm_db']) / 10))
        gb = 10 ** ((K['ambience_lufs'] - bed) / 20)                     # storm and fire together kept at the usual level
    pos = 0
    for i in range(loops + 1):                                           # one more than the loops: the ending plays the start of the next
        a, b = takes[order[i]], takes[order[i + 1]]
        for piece in (a[lead:L], a[L:L + lead] * down + b[:lead] * up):
            if F:
                piece = (piece + gf * fire.render(pos + int(F.get('offset', 600) * SR), len(piece))) * gb      # start well in, with every stem already playing
            pos += len(piece); yield pcm(piece)


def playlist(folder, seconds, dst):
    """Joins the tracks in a folder into one long piece of music: silence trimmed off both ends, each levelled to the same
    loudness, a three-second blend from one to the next, the order reshuffled every time round."""
    import numpy as np
    files = sorted(f for f in glob.glob(os.path.join(folder, '*')) if f.lower().endswith(('.flac', '.wav', '.mp3', '.m4a', '.ogg', '.opus')))
    if len(files) < 2:
        sys.exit(f'{folder}: at least two music tracks are needed, found {len(files)}')
    X = 3 * SR; k = np.linspace(0, 1, X, dtype=np.float32)[:, None]; down, up = np.cos(k * np.pi / 2), np.sin(k * np.pi / 2)
    rng = random.Random(K['slug']); order = []; level = {}
    w = subprocess.Popen(ff + ['-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s16le', dst], stdin=subprocess.PIPE)
    done, tail, short = 0, None, 0
    while done < seconds * SR:
        if not order:
            order = files[:]; rng.shuffle(order)
            if tail is not None and len(order) > 1 and order[0] == last:
                order.append(order.pop(0))
        last = f = order.pop(0)
        if f not in level:
            level[f] = -20 - loudness(f)
        x = decode(f) * np.float32(10 ** (level[f] / 20))
        loud = np.flatnonzero(np.abs(x).max(1) > 0.003)                  # trim silence (below about -50 dBFS) from both ends
        x = x[max(0, loud[0] - SR // 20):loud[-1] + SR // 4] if len(loud) else x
        if len(x) < 4 * X:                                              # too short to blend in and out of
            short += 1
            if short > 3 * len(files):
                sys.exit(f'{folder}: the tracks are too short to use')
            continue
        if tail is not None:
            x = np.concatenate([tail * down + x[:X] * up, x[X:]])
        w.stdin.write(x[:-X].tobytes()); done += len(x) - X; tail = x[-X:]
    w.stdin.write(tail.tobytes()); w.stdin.close()
    if w.wait():
        sys.exit('ffmpeg could not write the music')
    return len(files)


# The ceiling: a gentle roll-off above 12 kHz, then a limiter working at four times the sample rate, so the sharp edges of
# crackles cannot overshoot between samples or in the AAC encoding (true peaks stay under -1 dBFS). A fire-led mix loses a
# little loudness to the limiter; "makeup_db" in the type's mix settings gives it back.
C = dict({'top_hz': 12000, 'attack': 5, 'release': 100}, **M.get('ceiling', {}))      # a recorded fire needs less taming than a made one
top = f"lowpass=f={C['top_hz']}," + (f"lowpass=f={C['top_hz'] + 2000}," if C['top_hz'] < 16000 else '')
tail = (f"{top}aresample=192000,alimiter=limit=0.7:level=disabled:attack={C['attack']}:release={C['release']},aresample=48000,"
        f"afade=out:st={total - 14}:d=14[a]")
lowcut = 'highpass=f=40,' if K.get('fire') else ''                     # nothing below 40 Hz: inaudible on most speakers
up = M.get('makeup_db', 0)
takes = K.get('takes')
inputs = ['-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-'] if takes else ['-stream_loop', '-1', '-i', 'ambience.flac']
music = M.get('music')
if music or (music_dir and kind == 'lofi'):
    if music_dir:
        print(f'Joining the music tracks in {music_dir}...')
        n = playlist(music_dir, total + 2, 'music.wav'); eq = M['tracks_eq'] + ',' if M.get('tracks_eq') else ''
        print(f'  {n} tracks')
    else:
        print(f'Composing {total // 60} minutes of music...')
        run(['python3', 'music-long.py', str(total + 2), 'music.wav', str(music['seed']), str(music.get('transpose', 0)), '0.075', '1.0', str(music.get('bpm', 0)), music.get('style', 'ambient')])
        eq = M['music_eq'] + ',' if M.get('music_eq') else ''
    mus = loudness('music.wav', eq)
    amb_level = -20 + M['ambience_vs_music_db']                                      # the weather sits this far under the music
    both = 10 * math.log10(10 ** (-20 / 10) + 10 ** (amb_level / 10))                # the two together
    graph = (f"[0:a]{lowcut}volume={amb_level - K['ambience_lufs']:.2f}dB[amb];[1:a]aresample=48000,{eq}volume={-20 - mus:.2f}dB[mus];"
             f"[amb][mus]amix=inputs=2:normalize=0,volume={M['target_lufs'] - both + up:.2f}dB,{tail}")
    inputs += ['-i', 'music.wav']
else:
    graph = f"[0:a]{lowcut}volume={M['target_lufs'] - K['ambience_lufs'] + up:.2f}dB,{tail}"
print('Mixing the sound...')
mix = ff + inputs + ['-filter_complex', graph, '-map', '[a]', '-t', str(total), '-c:a', 'aac', '-b:a', Y['audio_bitrate'], '-ar', '48000', 'audio.m4a']
if takes:
    p = subprocess.Popen(mix, stdin=subprocess.PIPE)
    try:
        for piece in weather():
            p.stdin.write(piece)
    except BrokenPipeError:                                              # ffmpeg has all it needs (-t) and has stopped reading
        pass
    try:
        p.stdin.close()
    except BrokenPipeError:
        pass
    if p.wait():
        sys.exit('ffmpeg could not mix the sound')
else:
    run(mix)

# 3. join
with open('list.txt', 'w') as f:
    f.write(''.join(f'file {x}\n' for x in parts))
print('Joining...')
run(ff + ['-f', 'concat', '-safe', '0', '-i', 'list.txt', '-i', 'audio.m4a', '-map', '0:v', '-map', '1:a', '-c', 'copy', '-shortest', '-movflags', '+faststart', out])
for f in ('list.txt', 'audio.m4a', 'music.wav', 'loop.mp4', 'outro.mp4', 'open.mp4', 'first.mp4'):
    if os.path.exists(f):
        os.remove(f)
print(f'Built {out} ({kind}): {total // 3600} h {total % 3600 // 60} min {total % 60} s, {W}x{H}, {os.path.getsize(out) / 1e9:.1f} GB')
