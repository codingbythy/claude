#!/usr/bin/env python3
"""Long, non-repeating music bed for a Somewhere Sheltered video.

Builds a sequence of pieces, each with its own chord progression, key, register, pace and shape
(sparse opening, fuller middle, thinning ending), plus occasional quiet pad-only interludes, and
overlaps them so each one dissolves into the next. Same instruments as the loop version
(soft piano and warm pads), so every episode still sounds like the same channel.

Usage: music-long.py <seconds> <out.wav> [seed=21] [transpose=0] [rms=0.075] [slow=1.0] [bpm] [style=ambient|lofi]
(bpm, if given, holds the pulse near that tempo: one beat is the 1.5 s step of the default grid)
Needs only numpy. Writes 24 kHz stereo WAV, streamed piece by piece to keep memory low.
"""
import sys, wave, math
import numpy as np

SECONDS = float(sys.argv[1]); OUT = sys.argv[2]
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 21
TR = int(sys.argv[4]) if len(sys.argv) > 4 else 0
RMS = float(sys.argv[5]) if len(sys.argv) > 5 else 0.075
SLOW = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
import os
NOTES = [] if os.environ.get('MUSIC_NOTES') else None   # set MUSIC_NOTES=1 to print the first piece's melody timing
BPM = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0   # optional: fix the pulse (one beat = 1.5 s of the grid) instead of SLOW
if BPM > 0:
    SLOW = 40.0 / BPM
SR = 24000
STYLE = sys.argv[8] if len(sys.argv) > 8 else 'ambient'   # 'ambient' (sleep) or 'lofi' (a gentle groove for reading)
XF = 10.0                       # seconds each piece overlaps the next
master = np.random.default_rng(SEED)

# Progressions in D major (MIDI), voiced low for pads; the melody uses D major pentatonic.
BANK = [
    [[50,57,62,66],[47,54,57,62],[43,50,59,66],[45,52,57,61],[50,57,62,66],[42,49,57,64],[43,50,59,62],[45,52,59,64]],
    [[50,57,62,66],[47,54,59,62],[43,50,59,62],[45,52,57,61]],                 # I vi IV V
    [[43,50,59,62],[50,57,62,66],[45,52,57,64],[47,54,59,62]],                 # IV I V vi
    [[47,54,59,62],[43,50,59,62],[50,57,62,66],[45,52,57,62]],                 # vi IV I Vsus
    [[50,57,62,66],[42,49,54,57],[43,50,59,62],[40,47,55,62]],                 # I iii IV ii7
    [[50,57,61,66],[43,50,59,66]],                                             # Imaj7 IVmaj7, slow and open
]
PENTA = [62, 64, 66, 69, 71, 74, 76, 78, 81]
KEYS = [0, 5, 0, -5, 2, -3]          # neighbours a fourth or fifth apart, so the crossfades stay consonant


def hz(m, key):
    return 440 * 2 ** ((m + TR + key - 69) / 12)


def piano(rng, f, vel, dur=7.0):
    t = np.arange(int(dur * SR)) / SR; s = np.zeros_like(t)
    for n in range(1, 6):                                   # felt-piano: few, quickly fading overtones
        fn = n * f * math.sqrt(1 + 0.0004 * n * n)
        if fn > 3200:
            break
        tau = (3.0 / n ** 1.1) * (261.6 / f) ** 0.35
        s += np.sin(2 * np.pi * fn * t + rng.uniform(0, 6.28)) * np.exp(-t / tau) / n ** 2.4
    a = int(0.03 * SR); s[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    r = int(0.5 * SR); s[-r:] *= np.linspace(1, 0, r)
    return s * vel


def pad(rng, f, dur, amp):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * 1.0016 * t) + np.sin(2 * np.pi * f * 0.9984 * t + 1.3) + 0.22 * np.sin(2 * np.pi * 2 * f * t + 0.5)
    e = np.sin(np.pi * t / dur) ** 1.5
    return s * e * amp * (1 + 0.12 * np.sin(2 * np.pi * 0.11 * t + rng.uniform(0, 6.28)))


def reverb(x, seed):
    r = np.random.default_rng(seed); n = int(3.8 * SR); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t / 0.9); ir = np.convolve(ir, np.ones(6) / 6, 'same'); ir[:int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    return x + 0.9 * y


def make_piece(k, length, interlude):
    rng = np.random.default_rng(SEED * 1000 + k)
    key = KEYS[(k + SEED) % len(KEYS)]
    prog = BANK[int(rng.integers(len(BANK)))] if not interlude else BANK[5]
    slow = SLOW * (rng.uniform(0.97, 1.03) if BPM > 0 else rng.uniform(0.9, 1.35)) * (1.4 if interlude else 1.0)
    low = rng.random() < 0.35                                   # some pieces sit an octave lower and warmer
    n = int((length + 8) * SR)
    L = np.zeros(n); R = np.zeros(n)

    def add(sig, start, pan):
        start = int(start)
        if start < 0:                                   # already sounding when the piece begins
            sig = sig[-start:]; start = 0
        if start >= n:
            return
        sig = sig[:n - start]
        L[start:start + len(sig)] += sig * math.cos(pan * math.pi / 2)
        R[start:start + len(sig)] += sig * math.sin(pan * math.pi / 2)

    CH = 12.0 * slow
    for c in range(int(length / CH) + 1):
        for i, m in enumerate(prog[c % len(prog)]):
            add(pad(rng, hz(m, key), CH * 1.55, 0.05 if not interlude else 0.065), ((c * CH - CH * 0.275) if c else (-CH * 0.7 if k == 0 else 0)) * SR, 0.3 + 0.4 * (i / 3))   # first chord of the video starts at full swell
    beat = 1.5 * slow                                        # one step of the grid
    RHYTHMS = [[1, 1, 2], [1, 0.5, 0.5, 2], [1.5, 0.5, 1, 2], [0.5, 0.5, 1, 1, 2], [2, 1, 1, 2], [1, 1, 1, 1, 3], [1.5, 1.5, 3]]
    CONTOURS = {'arch': [1, 1, -1, -1, -1, 1], 'fall': [-1, -1, 1, -1, -1, -1], 'rise': [1, 1, 1, -1, 1, -1], 'wave': [1, -1, 1, 1, -1, -1]}
    chord_at = lambda tt: prog[int(tt / CH) % len(prog)]
    reg = -12 if low else 0
    t = 0.01 if k == 0 else rng.uniform(2, 5)
    pos = int(rng.integers(3, 6)); last_pitch = None; motif = None
    # soft rolled chords and low roots at chord changes give the harmony some movement of its own
    for c in range(int(length / CH) + 1):
        tc = c * CH
        if tc > length - 4:
            break
        ch = chord_at(tc + 0.01)
        if rng.random() < 0.6:
            add(piano(rng, hz(ch[0], key), rng.uniform(0.18, 0.26)), tc * SR, 0.45)
        if not (k == 0 and c == 0) and rng.random() < 0.4:
            for j, m in enumerate(ch[1:]):
                add(piano(rng, hz(m + 12, key), rng.uniform(0.1, 0.16)), (tc + 0.14 * j) * SR, 0.3 + 0.2 * j)
    while t < length - 4:
        shape = math.sin(math.pi * min(1.0, t / length)) ** 0.8         # sparse start, fuller middle, thin ending
        opening = k == 0 and t < 40                                     # the first 40 s play steadily
        if k == 0 and t < 90:
            shape = max(shape, 0.7)
        dens = (0.3 if interlude else 0.55) + (0.2 if interlude else 0.4) * shape
        if not opening and rng.random() > dens:
            t += rng.choice([1, 2, 3]) * beat                            # a longer rest now and then
            continue
        # a phrase: either a fresh idea or the last one again, moved to fit the new chord
        if motif is not None and rng.random() < 0.35:
            contour, rhythm = motif
        else:
            contour = CONTOURS[rng.choice(list(CONTOURS))]
            rhythm = RHYTHMS[int(rng.integers(len(RHYTHMS)))]
            motif = (contour, rhythm)
        base = rng.uniform(0.28, 0.42) if not interlude else rng.uniform(0.22, 0.32)
        nn = len(rhythm)
        for i, dur in enumerate(rhythm):
            if t >= length - 4:
                break
            chord = set(x % 12 for x in chord_at(t))
            if i > 0:
                step = contour[(i - 1) % len(contour)] * (2 if rng.random() < 0.25 else 1)
                pos = int(np.clip(pos + step, 0, len(PENTA) - 1))
                if pos in (0, len(PENTA) - 1):                         # turn round at the edges of the range
                    contour = [-x for x in contour]
            if i == nn - 1:                                          # end the phrase on a chord tone
                for d in (0, -1, 1, -2, 2):
                    q = int(np.clip(pos + d, 0, len(PENTA) - 1))
                    if PENTA[q] % 12 in chord and PENTA[q] != last_pitch:
                        pos = q; break
            if PENTA[pos] == last_pitch:                             # never the same note twice in a row
                pos = pos + 1 if pos < len(PENTA) - 1 else pos - 1
            pitch = PENTA[pos]
            vel = base * (0.8 + 0.3 * math.sin(math.pi * i / max(1, nn - 1)))   # each phrase swells and settles
            add(piano(rng, hz(pitch + reg, key), vel), t * SR, rng.uniform(0.3, 0.7))
            if NOTES is not None and k == 0: NOTES.append((round(float(t), 2), int(pitch)))
            if i == nn - 1 and rng.random() < 0.35 * (0.5 + shape):     # a soft harmony note under the last one
                add(piano(rng, hz(PENTA[max(0, pos - 2)] + reg, key), vel * 0.55), (t + 0.05) * SR, 0.5)
            last_pitch = pitch
            t += (min(dur, 1.5) if opening else dur) * beat
        t += rng.choice([0, 0.5, 1] if opening else [0.5, 1, 1, 1.5, 2]) * beat   # a short breath after the phrase
    L = reverb(L, 1); R = reverb(R, 2)
    st = np.stack([L, R], 1)
    body = st[int(10 * SR):int((length - 10) * SR)]
    st *= RMS * (0.8 if interlude else 1.0) / max(1e-9, np.sqrt((body ** 2).mean()))
    env = np.ones(n)
    fi, fo = int(6 * SR), int(XF * SR)
    if k > 0:
        env[:fi] = np.linspace(0, 1, fi) ** 2
    end = int(length * SR)
    env[end - fo:end] *= np.linspace(1, 0, fo) ** 1.5
    env[end:] = 0
    return st * env[:, None], key, prog is BANK[5], low



# ---------------------------------------------------------------------------------------------
# Lo-fi style: a warm, gently swung groove for winding down with a book. Electric piano comping
# jazzy 7th/9th chords, a soft round bass, quiet brushed drums with a light swing, short felt-piano
# melodies; pieces with their own progression and key, sections with and without drums, one-bar
# handovers on the same tempo so the groove never stumbles.
# ---------------------------------------------------------------------------------------------

import math, wave, zlib
import numpy as np


# chord qualities as rootless voicings (semitones above the root) plus the scale tones a melody may use
VOICING = {'maj7': [4, 7, 11, 14], 'm7': [3, 7, 10, 14], '7': [4, 9, 10, 14], 'm9': [3, 10, 14, 17]}
TONES = {'maj7': [0, 4, 7, 11, 14], 'm7': [0, 3, 7, 10, 14], '7': [0, 4, 7, 10, 14], 'm9': [0, 3, 7, 10, 14]}
PROGS = [
    [(2, 'm7'), (7, '7'), (0, 'maj7'), (9, 'm7')],        # ii V I vi
    [(0, 'maj7'), (9, 'm7'), (2, 'm7'), (7, '7')],        # I vi ii V
    [(5, 'maj7'), (4, 'm7'), (2, 'm7'), (0, 'maj7')],     # IV iii ii I
    [(0, 'maj7'), (0, 'maj7'), (5, 'maj7'), (5, 'maj7')], # I . IV .
    [(9, 'm9'), (2, 'm7'), (7, '7'), (0, 'maj7')],        # vi ii V I
    [(4, 'm7'), (9, 'm7'), (2, 'm7'), (7, '7')],          # iii vi ii V
    [(5, 'maj7'), (7, '7'), (4, 'm7'), (9, 'm9')],        # IV V iii vi
]
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def _env(n, attack, tau):
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    a = max(1, int(attack * SR)); e[:a] *= np.linspace(0, 1, a)
    return e, t


class Kit:
    """Instrument sounds, cached per pitch so a two-hour score stays quick to build."""
    def __init__(self, rng):
        self.rng = rng; self.cache = {}

    def _get(self, key, make):
        if key not in self.cache:
            self.cache[key] = make()
        return self.cache[key]

    def rhodes(self, midi):
        def make():
            f = 440 * 2 ** ((midi - 69) / 12); n = int(4.5 * SR)
            e, t = _env(n, 0.006, 1.9 * (220 / f) ** 0.3)
            tine = 0.55 * np.exp(-t / 0.15)                                  # a softened bell-like strike, fading fast
            s = np.sin(2 * np.pi * f * t + tine * np.sin(2 * np.pi * f * 7 * t))
            s += 0.22 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.6)
            return s * e
        return self._get(('rh', midi), make)

    def piano(self, midi):
        def make():
            f = 440 * 2 ** ((midi - 69) / 12); n = int(5 * SR)
            e, t = _env(n, 0.012, 1.0); s = np.zeros(n)
            for h in range(1, 6):
                fh = h * f * math.sqrt(1 + 0.0004 * h * h)
                if fh > 4000: break
                tau = (2.8 / h ** 1.0) * (261.6 / f) ** 0.35
                s += np.sin(2 * np.pi * fh * t) * np.exp(-t / tau) / h ** 2.0
            a = int(0.012 * SR); s[:a] *= np.linspace(0, 1, a)
            return s
        return self._get(('pn', midi), make)

    def lead(self, midi):
        """A smooth, rounded melody voice: swells in instead of being struck, mostly fundamental,
        two slightly detuned voices for warmth, and a slow vibrato that eases in."""
        def make():
            f = 440 * 2 ** ((midi - 69) / 12); n = int(5 * SR); t = np.arange(n) / SR
            vib = 1 + 0.0018 * np.sin(2 * np.pi * 4.6 * t) * np.clip((t - 0.35) / 0.6, 0, 1)
            out = np.zeros(n)
            for det, amp in ((1.0, 1.0), (1.0035, 0.55), (0.9968, 0.4)):
                ph = 2 * np.pi * np.cumsum(f * det * vib) / SR
                out += amp * (np.sin(ph) + 0.18 * np.sin(2 * ph) * np.exp(-t / 1.2) + 0.04 * np.sin(3 * ph))
            a = int(0.085 * SR); env = np.exp(-t / 2.6) * 0.8 + 0.2 * np.exp(-t / 0.5)
            env[:a] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a))
            return out * env / 1.95
        return self._get(('ld', midi), make)

    def bass(self, midi):
        def make():
            f = 440 * 2 ** ((midi - 69) / 12); n = int(2.5 * SR)
            e, t = _env(n, 0.01, 0.9)
            s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)
            return s * e
        return self._get(('bs', midi), make)

    def drum(self, kind, v):
        def make():
            r = np.random.default_rng(zlib.crc32(f'{kind}{v}'.encode()))
            if kind == 'kick':
                n = int(0.45 * SR); t = np.arange(n) / SR
                f = 48 + 70 * np.exp(-t / 0.04)
                return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
            if kind == 'snare':                       # a brushed, soft snare: body plus a little filtered noise
                n = int(0.3 * SR); t = np.arange(n) / SR
                noise = np.convolve(r.standard_normal(n), np.ones(5) / 5, 'same')
                return 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) + 0.45 * noise * np.exp(-t / 0.09)
            n = int(0.09 * SR); t = np.arange(n) / SR   # brush on the hi-hat: short, dark, quiet
            noise = r.standard_normal(n); noise = noise - np.convolve(noise, np.ones(3) / 3, 'same')
            noise = np.convolve(noise, np.ones(3) / 3, 'same')
            return noise * np.exp(-t / 0.025)
        return self._get(('dr', kind, v), make)


def _reverb_warm(x, seed, wet=0.32, lp_hz=8500):
    r = np.random.default_rng(seed); n = int(2.2 * SR); t = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-t / 0.5); ir = np.convolve(ir, np.ones(8) / 8, 'same'); ir[:int(0.015 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    m = len(x) + n
    X = np.fft.rfft(x, m); H = 1 + wet * np.fft.rfft(ir, m)
    f = np.fft.rfftfreq(m, 1 / SR); lp = 1 / np.sqrt(1 + (f / lp_hz) ** 4)        # gentle warmth roll-off
    return np.fft.irfft(X * H * lp, m)[:len(x)]


def lofi_piece(k, bars, seed, tr, bpm, first):
    rng = np.random.default_rng(seed * 1000 + k)
    kit = Kit(rng)
    beat = 60.0 / bpm; bar = 4 * beat; swing = 0.09 * beat
    key = KEYS[(k + seed) % len(KEYS)] + tr
    tonic = 60 + key
    while tonic > 64: tonic -= 12
    while tonic < 53: tonic += 12
    n = int((bars * bar + 3) * SR)
    L = np.zeros(n); R = np.zeros(n)

    def add(sig, at, vel, pan, dur=None):
        s0 = int(at * SR)
        if s0 >= n or s0 < 0: return
        if dur is not None:
            m = min(len(sig), int((dur + 0.25) * SR)); sig = sig[:m].copy()
            fr = min(int(0.25 * SR), m); sig[m - fr:] *= np.linspace(1, 0, fr) ** 1.5
        sig = sig[:n - s0] * vel
        L[s0:s0 + len(sig)] += sig * math.cos(pan * math.pi / 2)
        R[s0:s0 + len(sig)] += sig * math.sin(pan * math.pi / 2)

    def sw(b):          # swing the off-beat eighths
        return b * beat + (swing if abs(b * 2 - round(b * 2)) < 1e-6 and (round(b * 2) % 2 == 1) else 0)

    # arrangement: 8-bar sections; the first piece of the video starts with the full groove
    progA = PROGS[int(rng.integers(len(PROGS)))]
    progB = PROGS[int(rng.integers(len(PROGS)))]
    sections = []
    nsec = max(2, bars // 8)
    for i in range(nsec):
        prog = progA if i % 3 != 2 else progB
        drums = not (i == nsec - 1 or (i > 1 and rng.random() < 0.2))
        if i == 0 and not first:
            drums = False                         # a soft way in after the handover
        sections.append((prog, drums, i > 0 or first))
    comp_pats = [[0, 1.5], [0, 2.5], [0.5, 2], [0, 2], [0, 1.5, 3], [0]]
    last_mel = None; motif = None
    for si, (prog, drums, melody) in enumerate(sections):
        for b in range(8):
            bi = si * 8 + b
            if bi >= bars: break
            t0 = bi * bar
            root_deg, q = prog[b % 4]
            root = tonic + root_deg
            # electric piano comp
            vo = [root + x for x in VOICING[q]]
            while min(vo) > 62: vo = [v - 12 for v in vo]
            while min(vo) < 50: vo = [v + 12 for v in vo]
            pat = comp_pats[int(rng.integers(len(comp_pats)))]
            for j, pb in enumerate(pat):
                nxt = pat[j + 1] if j + 1 < len(pat) else 4
                dur = (nxt - pb) * beat
                for vi, v in enumerate(vo):
                    add(kit.rhodes(v), t0 + sw(pb) + 0.008 * vi, rng.uniform(0.1, 0.14), 0.35 + 0.1 * vi, dur)
            # bass: root, then fifth or octave, with an occasional step into the next chord
            br = root - 24
            while br < 36: br += 12
            add(kit.bass(br), t0, 0.22, 0.5, 1.6 * beat)
            second = br + (7 if rng.random() < 0.6 else 12)
            add(kit.bass(second if second < 55 else br), t0 + 2 * beat, 0.18, 0.5, 1.2 * beat)
            if rng.random() < 0.4:
                nroot = tonic + prog[(b + 1) % 4][0] - 24
                while nroot < 36: nroot += 12
                add(kit.bass(nroot + (1 if rng.random() < 0.5 else -1)), t0 + sw(3.5), 0.14, 0.5, 0.45 * beat)
            # drums
            if drums:
                for kb in ([0, 2.5] if rng.random() < 0.6 else [0, 1.5, 2.5]):
                    add(kit.drum('kick', 0), t0 + sw(kb), 0.32, 0.5)
                for sb in (1, 3):
                    add(kit.drum('snare', sb), t0 + sb * beat, 0.16, 0.55)
                for hb in range(8):
                    add(kit.drum('hat', hb % 2), t0 + sw(hb / 2), 0.09 if hb % 2 == 0 else 0.055, 0.62)
        # melody: two-bar phrases, every other pair of bars, on the swung eighth grid
        if not melody:
            continue
        for pb in range(0, 8, 2):
            if pb % 4 == 2 and rng.random() < 0.5:
                continue                           # leave room to breathe
            bi = si * 8 + pb
            if bi >= bars - 1: break
            t0 = bi * bar
            if motif is not None and rng.random() < 0.4:
                rhythm, contour = motif
            else:
                rhythm = sorted(rng.choice(np.arange(0, 7.5, 0.5), size=int(rng.integers(3, 6)), replace=False).tolist())
                contour = [int(x) for x in rng.choice([-2, -1, 1, 2], size=6)]
                motif = (rhythm, contour)
            root_deg, q = prog[pb % 4]
            pool = sorted({tonic + d + o for d in MAJOR for o in (0, 12, 24) if 62 <= tonic + d + o <= 79})   # a lower, warmer register
            chord_pcs = {(tonic + root_deg + x) % 12 for x in TONES[q]}
            idx = min(range(len(pool)), key=lambda i: abs(pool[i] - (last_mel or 70)))
            for j, rb in enumerate(rhythm):
                if j:
                    idx = int(np.clip(idx + contour[(j - 1) % len(contour)], 0, len(pool) - 1))
                cur = prog[(pb + (1 if rb >= 4 else 0)) % 4]
                pcs = {(tonic + cur[0] + x) % 12 for x in TONES[cur[1]]}
                if (j == len(rhythm) - 1 or rb % 1 == 0) and pool[idx] % 12 not in pcs:   # land on chord tones on the beat
                    for d in (1, -1, 2, -2):
                        q2 = int(np.clip(idx + d, 0, len(pool) - 1))
                        if pool[q2] % 12 in pcs: idx = q2; break
                if pool[idx] == last_mel:
                    idx = idx + 1 if idx < len(pool) - 1 else idx - 1
                nxt = rhythm[j + 1] if j + 1 < len(rhythm) else 8
                add(kit.lead(pool[idx]), t0 + sw(rb), rng.uniform(0.2, 0.25), 0.45, (nxt - rb) * beat + 0.45)
                last_mel = pool[idx]
    L = _reverb_warm(L, 1); R = _reverb_warm(R, 2)
    return np.stack([L, R], 1), key


def lofi_write(seconds, out, seed, tr, rms, bpm):
    bpm = bpm or 74.0
    bar = 4 * 60.0 / bpm
    master = np.random.default_rng(seed)
    w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    total = int(seconds * SR); written = 0; k = 0; carry = np.zeros((0, 2)); log = []
    gain = None
    while written < total:
        bars = int(master.choice([48, 64, 64, 80]))
        piece, key = lofi_piece(k, bars, seed, tr, bpm, k == 0)
        if gain is None:
            body = piece[int(4 * bar * SR):int((bars - 2) * bar * SR)]
            gain = rms / max(1e-9, np.sqrt((body ** 2).mean()))           # one gain for the whole score
        piece *= gain
        hand = int(1 * bar * SR)                                            # one bar of handover into the next piece
        end = int(bars * bar * SR)
        piece[end - hand:end] *= np.linspace(1, 0, hand)[:, None] ** 1.2
        piece[end:] = 0
        piece[:len(carry)] += carry
        keep = end - hand
        outp = piece[:keep]; carry = piece[keep:end]
        outp = outp[:total - written]
        w.writeframes((np.clip(outp, -0.98, 0.98) * 32767).astype('<i2').tobytes())
        written += len(outp); k += 1
        log.append(f'piece {k}: {bars} bars ({bars * bar / 60:.1f} min) at {bpm:.0f} BPM, key {key:+d}')
    w.close()
    print('\n'.join(log))


if STYLE == 'lofi':
    lofi_write(SECONDS, OUT, SEED, TR, RMS, BPM)
    sys.exit(0)

w = wave.open(OUT, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
carry = np.zeros((0, 2)); written = 0; total = int(SECONDS * SR); k = 0
log = []
while written < total:
    interlude = k > 0 and master.random() < 0.22
    length = master.uniform(60, 95) if interlude else master.uniform(300, 540)
    piece, key, slowprog, low = make_piece(k, length, interlude)
    log.append(f"{'interlude' if interlude else 'piece'} {k + 1}: {length / 60:.1f} min, key {key:+d}{', low register' if low else ''}")
    keep = int((length - XF) * SR)                       # where the next piece starts
    piece[:len(carry)] += carry
    out = piece[:keep]; carry = piece[keep:int(length * SR)]
    out = out[:total - written]
    w.writeframes((np.clip(out, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    written += len(out); k += 1
w.close()
print('\n'.join(log))
if NOTES is not None:
    first = [x for x in NOTES if x[0] < 60]
    print('melody notes in the first minute (time, MIDI pitch):', first)
    reps = sum(1 for a, b in zip(first, first[1:]) if a[1] == b[1])
    print('%d notes, %d back-to-back repeats, %d different pitches' % (len(first), reps, len(set(p for _, p in first))))
