#!/usr/bin/env python3
"""Long, non-repeating music bed for a Somewhere Sheltered video.

Builds a sequence of pieces, each with its own chord progression, key, register, pace and shape
(sparse opening, fuller middle, thinning ending), plus occasional quiet pad-only interludes, and
overlaps them so each one dissolves into the next. Same instruments as the loop version
(soft piano and warm pads), so every episode still sounds like the same channel.

Usage: music-long.py <seconds> <out.wav> [seed=21] [transpose=0] [rms=0.075] [slow=1.0] [bpm]
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
