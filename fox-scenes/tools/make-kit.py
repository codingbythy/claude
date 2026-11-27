#!/usr/bin/env python3
"""Packs a scene's finished renders into its video-kit: the parts the Colab notebook downloads to build the long video.

Usage: make-kit.py <scene> [--settings-only]
Reads from fox-scenes/work/<scene>/:
  loop/loopv.mp4            the three-minute loop (tools/render.js --size 640x360, then tools/make-loop.py)
  loop-<type>/loopv.mp4     the same for a type with its own picture (scene.json "variants", e.g. the room without the foxes)
  open-<type>/raw.mp4       that type's opening, when its mix sets "open" (render.js on the page with &type=..&open=.., 16 s)
  takes/<n>/raw.f32         takes of the sound (render.js --audio-only on the page with &take=<n>, 184 s each)
  loop/loop.wav             the single sound loop, used only when there are no takes
  fire-stems/               a fire made from recorded stems (scene.json mix.fire), used to measure its loudness; the
                            stems themselves never go into the kit (see tools/stemfire.py)
Writes fox-scenes/<scene>/video-kit/: the loops and openings at the scene's own size (every pixel exact), the sound takes,
the corner mark if a type uses it, kit.json, build.py (and music-long.py for scenes made as lo-fi). The kit stays small;
build.py enlarges the picture for YouTube and can make either type the scene is set up for. --settings-only rewrites
kit.json and build.py and leaves the picture and sound files as they are (for when only the mix or the hours changed).
"""
import glob, json, os, re, shutil, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = os.path.dirname(ROOT)
scene = sys.argv[1]
C = json.load(open(f'{ROOT}/{scene}/scene.json')); W = f'{ROOT}/work/{scene}'; KIT = f'{ROOT}/{scene}/video-kit'
ONLY = '--settings-only' in sys.argv
if not ONLY and os.path.isdir(KIT):
    shutil.rmtree(KIT)
os.makedirs(KIT, exist_ok=True)
LOOP, OUTRO, LEAD, OPEN, SR = 180, 20, 4, 12, 48000       # LEAD: a render starts this long before the loop does. OPEN: length of an opening part
mixes = {k: v for k, v in C['mix'].items() if k in ('lofi', 'ambience')}
PIC = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '12', '-pix_fmt', 'yuv444p', '-g', '60', '-an']      # full colour resolution, very light compression


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path, entry):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', entry, '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True).stdout.split()


def measure(pcm):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'ebur128=peak=true', '-f', 'null', '-'], input=pcm.astype('<f4').tobytes(), capture_output=True).stderr.decode()
    s = log[log.rindex('Summary:'):]
    return float(re.search(r'I:\s+(-?[\d.]+) LUFS', s).group(1)), float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', s).group(1))


def flac(pcm, gain, dst):
    run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', f'volume={gain:.2f}dB', '-sample_fmt', 's16', '-c:a', 'flac', dst], input=pcm.astype('<f4').tobytes())


def picture(src, dst, cut=()):
    w, h = map(int, probe(src, 'stream=width,height'))
    if w > 960:
        sys.exit(f'{src} is {w}x{h}. Render at the scene\'s own size (render.js --size 640x360) so it can be enlarged exactly.')
    run(['ffmpeg', '-y', '-loglevel', 'error'] + list(cut[:2]) + ['-i', src] + list(cut[2:]) + PIC + [f'{KIT}/{dst}'])
    return w, h


pictures = {'default': {'loop': 'loop-360.mp4'}}
for k, m in mixes.items():
    if k in C.get('variants', {}):
        pictures[k] = {'loop': f'loop-{k}-360.mp4'}
        if m.get('open'):
            pictures[k].update(open=f'open-{k}-360.mp4', open_seconds=OPEN)
take_dirs = sorted(glob.glob(f'{W}/takes/*/raw.f32'))
if not ONLY:
    w, h = picture(f'{W}/loop/loopv.mp4', 'loop-360.mp4')
    for k, p in pictures.items():
        if k != 'default':
            picture(f'{W}/loop-{k}/loopv.mp4', p['loop'])
            if p.get('open'):                                        # the render starts LEAD seconds before the loop does
                picture(f'{W}/open-{k}/raw.mp4', p['open'], ('-ss', str(LEAD), '-t', str(OPEN)))
    # the sound, stored at a known loudness so the build needs no measuring of its own
    if take_dirs:
        takes = [np.fromfile(f, '<f4').reshape(-1, 2) for f in take_dirs]
        for f, a in zip(take_dirs, takes):
            if len(a) < (LOOP + LEAD) * SR:
                sys.exit(f'{f} holds {len(a) / SR:.0f} s; a take is {LOOP + LEAD} s')
        lufs, peak = measure(np.concatenate([a[LEAD * SR:(LOOP + LEAD) * SR] for a in takes])); gain = -20 - lufs       # one gain for all, so they keep their own balance
        under = 0.0
        if C['mix'].get('fire'):            # with a fire on top, the storm ends up this much lower in the finished sound
            over = C['mix']['fire']['over_storm_db']; under = -10 * np.log10(1 + 10 ** (over / 10))
        if peak + gain + under > -1:
            sys.exit(f'{scene}: the sound would peak at {peak + gain + under:.1f} dBFS at -20 LUFS; lower the loud moments in the scene sound first')
        for i, a in enumerate(takes):
            flac(a[:(LOOP + LEAD) * SR], gain, f'{KIT}/ambience-{i + 1}.flac')
    else:
        a = np.frombuffer(run(['ffmpeg', '-v', 'error', '-i', f'{W}/loop/loop.wav', '-f', 'f32le', '-ac', '2', '-'], capture_output=True).stdout, '<f4').reshape(-1, 2)
        lufs, peak = measure(a); gain = -20 - lufs
        if peak + gain > -1:
            sys.exit(f'{scene}: ambience would peak at {peak + gain:.1f} dBFS at -20 LUFS; lower the loud moments in the scene sound first')
        flac(a, gain, f'{KIT}/ambience.flac')
else:
    w, h = map(int, probe(f'{KIT}/loop-360.mp4', 'stream=width,height'))

sound = sorted(os.path.basename(f) for f in glob.glob(f'{KIT}/ambience-*.flac'))
files = [p[x] for p in pictures.values() for x in ('loop', 'open') if x in p] + (sound or ['ambience.flac']) + ['build.py']
shutil.copy(f'{HERE}/kit-build.py', f'{KIT}/build.py')
if any(m.get('music') for m in mixes.values()):
    shutil.copy(f'{REPO}/tools/music-long.py', f'{KIT}/music-long.py'); files.append('music-long.py')
kit = {'title': C['title'], 'slug': re.sub(r'[^a-z0-9]+', '-', C['title'].lower().replace("'", '')).strip('-'), 'hours': C['hours'], 'loop_seconds': LOOP, 'outro_seconds': OUTRO,
       'width': w, 'height': h, 'youtube': {'scale': 4, 'crf': 21, 'preset': 'faster', 'audio_bitrate': '384k'},
       'ambience_lufs': -20, 'target_lufs': C['mix']['target_lufs'], 'home': C['mix']['home'], 'mixes': mixes, 'pictures': pictures}
if sound:
    kit['takes'] = {'files': sound, 'lead': LEAD}
if C['mix'].get('fire'):                 # the fire: its settings and measured loudness go in the kit, its stems do not
    sys.path.insert(0, HERE); from stemfire import StemFire
    F = dict(C['mix']['fire']); fire = StemFire(F, f'{W}/fire-stems').render(300 * SR, 600 * SR)
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'highpass=f=40,ebur128', '-f', 'null', '-'], input=fire.tobytes(), capture_output=True).stderr.decode()
    F['lufs'] = float(re.search(r'I:\s+(-?[\d.]+) LUFS', log[log.rindex('Summary:'):]).group(1))
    kit['fire'] = F; shutil.copy(f'{HERE}/stemfire.py', f'{KIT}/stemfire.py'); files.append('stemfire.py')
    print(f"  fire: {F['name']}, {F['lufs']:.1f} LUFS as made; stems from Drive / {F['drive_folder']}")
if any(m.get('mark') for m in mixes.values()):
    shutil.copy(f'{REPO}/channel/somewhere-sheltered-mark.png', f'{KIT}/mark.png'); kit['mark'] = 'mark.png'; files.append('mark.png')
kit['files'] = files
json.dump(kit, open(f'{KIT}/kit.json', 'w'), indent=1)
for f in sorted(os.listdir(KIT)):
    print(f'  {os.path.getsize(f"{KIT}/{f}") / 1e6:7.1f} MB  {f}')
