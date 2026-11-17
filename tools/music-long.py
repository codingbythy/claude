#!/usr/bin/env python3
"""Long, non-repeating music bed for a Somewhere Sheltered video.

Builds a sequence of pieces, each with its own chord progression, key, register, pace and shape
(sparse opening, fuller middle, thinning ending), plus occasional quiet pad-only interludes, and
overlaps them so each one dissolves into the next. Same instruments as the loop version
(soft piano and warm pads), so every episode still sounds like the same channel.

Usage: music-long.py <seconds> <out.wav> [seed=21] [transpose=0] [rms=0.075] [slow=1.0]
Needs only numpy. Writes 24 kHz stereo WAV, streamed piece by piece to keep memory low.
"""
import sys, wave, math
import numpy as np

SECONDS = float(sys.argv[1]); OUT = sys.argv[2]
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 21
TR = int(sys.argv[4]) if len(sys.argv) > 4 else 0
RMS = float(sys.argv[5]) if len(sys.argv) > 5 else 0.075
SLOW = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
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
    for n in range(1, 7):
        fn = n * f * math.sqrt(1 + 0.0004 * n * n)
        if fn > SR * 0.45:
            break
        tau = (2.6 / n ** 0.8) * (261.6 / f) ** 0.35
        s += np.sin(2 * np.pi * fn * t + rng.uniform(0, 6.28)) * np.exp(-t / tau) / n ** 1.9
    a = int(0.018 * SR); s[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
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
    slow = SLOW * rng.uniform(0.9, 1.35) * (1.4 if interlude else 1.0)
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
    t = 0.01 if k == 0 else rng.uniform(2, 5); pos = int(rng.integers(2, 6))   # the video opens on a note
    while t < length - 4:
        shape = math.sin(math.pi * min(1.0, t / length)) ** 0.8         # sparse start, fuller middle, thin ending
        if k == 0 and t < 90:
            shape = max(shape, 0.7)                                     # the video opens on real music, not a slow fade
        dens = (0.25 if interlude else 0.5) + (0.2 if interlude else 0.5) * shape
        if rng.random() < dens:
            chord = set(x % 12 for x in prog[int(t / CH) % len(prog)])
            for _ in range(6):
                cand = int(np.clip(pos + rng.integers(-2, 3), 0, len(PENTA) - 1))
                if PENTA[cand] % 12 in chord or rng.random() < 0.3:
                    pos = cand; break
            mel = PENTA[pos] - (12 if low else 0)
            add(piano(rng, hz(mel, key), rng.uniform(0.35, 0.75)), t * SR, rng.uniform(0.25, 0.75))
            if rng.random() < 0.3 * (0.5 + shape):
                add(piano(rng, hz(prog[int(t / CH) % len(prog)][0], key), rng.uniform(0.3, 0.5)), t * SR, 0.5)
            if not interlude and rng.random() < 0.3 * shape:
                p2 = int(np.clip(pos + rng.choice([-2, -1, 1, 2]), 0, len(PENTA) - 1))
                add(piano(rng, hz(PENTA[p2] - (12 if low else 0), key), rng.uniform(0.25, 0.5)), (t + 0.75 * slow) * SR, rng.uniform(0.25, 0.75))
        t += rng.choice([1.5, 3, 3, 3, 4.5, 4.5, 6]) * slow
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
