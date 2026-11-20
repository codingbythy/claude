#!/usr/bin/env python3
"""Colour-grades a scene's painting: <scene>/painting-1280.png -> <scene>/room.webp (1920x1080).

Usage: grade.py <scene-dir> [--compare out.jpg]
The look is set by the "grade" block of the scene's scene.json (a scene without one is only enlarged). Everything is plain
arithmetic on the picture, so the same settings always give the same result and nothing is repainted or generated:

  sat          overall colour strength (1 = unchanged)
  rolloff      how hard the most saturated colours are pulled back (takes the neon edge off)
  contrast     strength of a gentle S-curve; black_point lifts or deepens the darkest tones
  shadows / highlights   colour added to the dark and bright ends (cool shadows, warm lights)
  hues         per-colour moves, each {"from", "to" (degrees), "sat", "lum", "shift", "keep_subject"}:
               e.g. quieten the orange of wood panelling while leaving the foxes' orange alone
  window       separate contrast / sat / lum / shift for what is seen through the glass
  subject      lifts the foxes a little and lets the room fall away around them
  vignette     darkening toward the corners
  pixel        snap the picture to a true pixel grid of this many screen pixels, with "colours" in the palette (0 = off)
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

d = sys.argv[1]
C = json.load(open(os.path.join(d, 'scene.json'))); G = C.get('grade', {})
SW, SH = C['size']
src = Image.open(os.path.join(d, 'painting-1280.png')).convert('RGB')
a = np.asarray(src).astype(np.float64) / 255
H, W = a.shape[:2]


def to_hsv(x):
    r, g, b = x[..., 0], x[..., 1], x[..., 2]; mx = x.max(-1); mn = x.min(-1); df = mx - mn + 1e-12
    h = np.where(mx == r, ((g - b) / df) % 6, np.where(mx == g, (b - r) / df + 2, (r - g) / df + 4)) * 60
    return h, np.where(mx > 0, (mx - mn) / (mx + 1e-12), 0), mx


def to_rgb(h, s, v):
    h = (h % 360) / 60; i = np.floor(h); f = h - i; p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f)); i = i.astype(int) % 6
    return np.stack([np.choose(i, [v, q, p, p, t, v]), np.choose(i, [t, v, v, q, p, p]), np.choose(i, [p, p, t, v, v, q])], -1)


def soft(mask, radius):
    return np.asarray(Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))).astype(np.float64) / 255


yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
sx, sy = W / SW, H / SH
# where the foxes are (from the breathing regions) and where the glass is
subj = np.zeros((H, W))
for b in C.get('breathe', []):
    subj = np.maximum(subj, (((xx - b['cx'] * sx) / (b['rx'] * sx * 1.12)) ** 2 + ((yy - b['cy'] * sy) / (b['ry'] * sy * 1.2)) ** 2 < 1) * 1.0)
subj = soft(subj, 26)
glass = np.asarray(Image.open(os.path.join(d, C['mask'])).split()[3].resize((W, H), Image.BILINEAR)).astype(np.float64) / 255
glass = soft(glass, 2)

if G:
    h, s, v = to_hsv(a)
    # per-colour moves
    for m in G.get('hues', []):
        lo, hi = m['from'], m['to']; mid = (lo + hi) / 2; half = (hi - lo) / 2
        dist = np.abs(((h - mid + 180) % 360) - 180)
        w = np.clip(1.25 - dist / half, 0, 1) * np.clip(s * 4, 0, 1)                 # soft-edged band; greys are left alone
        if m.get('keep_subject'):
            w = w * (1 - subj)
        if m.get('not_window'):
            w = w * (1 - glass)
        h = h + w * m.get('shift', 0); s = s * (1 + w * (m.get('sat', 1) - 1)); v = v * (1 + w * (m.get('lum', 1) - 1))
    # what is seen through the window
    if G.get('window'):
        wn = G['window']; h = h + glass * wn.get('shift', 0); s = s * (1 + glass * (wn.get('sat', 1) - 1)); v = v * (1 + glass * (wn.get('lum', 1) - 1))
        c = wn.get('contrast', 0); v = v + glass * c * (v - 0.35) * (1 - np.abs(2 * v - 1)) * 2
    # overall colour strength, with the strongest colours pulled back the most
    s = s * G.get('sat', 1); r = G.get('rolloff', 0); s = np.where(s > 0.55, 0.55 + (s - 0.55) * (1 - r), s)
    a = to_rgb(h, np.clip(s, 0, 1), np.clip(v, 0, 1))
    lum = a @ np.array([0.299, 0.587, 0.114])
    # tone: S-curve, then the foxes lifted and the room allowed to fall away, then the corners
    c = G.get('contrast', 0); a = a + c * (a - 0.5) * (1 - np.abs(2 * a - 1)) * 2
    if G.get('subject'):
        sb = G['subject']; a = a * (1 + sb.get('lift', 0) * subj - sb.get('fall', 0) * (1 - subj) * (1 - glass * sb.get('spare_window', 1)))[..., None]
    if G.get('vignette'):
        rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
        a = a * (1 - G['vignette'] * np.clip((rr - 0.45) / 0.55, 0, 1) ** 2)[..., None]
    lum = np.clip(a @ np.array([0.299, 0.587, 0.114]), 0, 1)[..., None]
    a = a + np.array(G.get('shadows', [0, 0, 0])) * (1 - lum) ** 2 + np.array(G.get('highlights', [0, 0, 0])) * lum ** 1.5
    bp = G.get('black_point', 0); a = (a - bp) / (1 - bp) if bp > 0 else a * (1 + bp) - bp
    a = np.clip(a, 0, 1)

out = Image.fromarray((a * 255 + 0.5).astype(np.uint8))
px = G.get('pixel', 0)
if px:      # a true pixel grid and a limited palette: every "pixel" the same size, colours chosen from one set
    small = out.resize((1920 // px, 1080 // px), Image.BOX)
    small = small.quantize(G.get('colours', 64), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE, kmeans=3).convert('RGB')
    small.save(os.path.join(d, C['image']), lossless=True)            # stored at grid size; the scene page scales it up crisply
    big = small.resize((1920, 1080), Image.NEAREST)
else:
    big = out.resize((1920, 1080), Image.LANCZOS)
    big.save(os.path.join(d, C['image']), quality=93, method=6)
print(f'{d}: graded' if G else f'{d}: enlarged only (no grade settings)')
if '--compare' in sys.argv:
    before = src.resize((1280, 720), Image.LANCZOS); after = big.resize((1280, 720), Image.LANCZOS)
    sheet = Image.new('RGB', (1280, 1440)); sheet.paste(before, (0, 0)); sheet.paste(after, (0, 720))
    sheet.save(sys.argv[sys.argv.index('--compare') + 1], quality=90)
