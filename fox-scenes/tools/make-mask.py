#!/usr/bin/env python3
"""Works out where the window glass is in a scene's painting, so weather is only drawn on the glass.

Reads <scene>/scene.json -> "glass": {"rects": [...], "exclude": [...], "exclude_polys": [...], "fur": [...], "warm": 26, "dark": 120, "green": 10}
(rects are [x0,y0,x1,y1] in the scene's layout coordinates). A pixel inside a rect counts as glass unless it is inside an exclude
rect, looks like the window frame (brown and dark), or lies in a "fur" rect and is any warm colour (a fox in front of the window). Writes <scene>/glass-mask.png on the half-size effects grid, and with
--debug <file> a picture of the painting with the mask tinted so it can be checked by eye.

Usage: make-mask.py <scene-dir> [--variant ambience] [--debug out.jpg]
With --variant the mask is made for that entry of the scene's "variants" (its own painting and mask file; without foxes there is
no fur to keep clear).
"""
import json, sys, os
import numpy as np
from PIL import Image, ImageDraw

d = sys.argv[1]
C = json.load(open(os.path.join(d, 'scene.json')))
V = C.get('variants', {}).get(sys.argv[sys.argv.index('--variant') + 1], {}) if '--variant' in sys.argv else {}
SW, SH = C['size']; G = dict(C['glass'], **({'fur': []} if V.get('foxes') is False else {})); C = dict(C, mask=V.get('mask', C['mask']))
G['exclude_polys'] = G.get('exclude_polys', []) + V.get('glass_exclude_polys', [])      # e.g. the bench back a fox used to hide
src = os.path.join(d, V.get('painting', 'painting-1280.png'))          # judge colours on the painting as made, not on the graded copy
im = Image.open(src if os.path.exists(src) else os.path.join(d, C['image'])).convert('RGB').resize((SW, SH), Image.LANCZOS)
a = np.asarray(im).astype(np.int32); r, g, b = a[..., 0], a[..., 1], a[..., 2]
lum = (299 * r + 587 * g + 114 * b) // 1000
inside = np.zeros((SH, SW), bool)
for x0, y0, x1, y1 in G['rects']:
    inside[y0:y1, x0:x1] = True
for x0, y0, x1, y1 in G.get('exclude', []):
    inside[y0:y1, x0:x1] = False
if G.get('exclude_polys'):                                               # window bars the colour test cannot tell from the night outside
    pm = Image.new('L', (SW, SH), 0); dr = ImageDraw.Draw(pm)
    for poly in G['exclude_polys']:
        dr.polygon([tuple(pt) for pt in poly], fill=255)
    inside &= np.asarray(pm) == 0
frame = (r - b > G.get('warm', 26)) & (lum < G.get('dark', 120))        # dark brown wood
for x0, y0, x1, y1 in G.get('fur', []):                                 # a fox lying in front of the window
    frame[y0:y1, x0:x1] |= (r - b > 30)[y0:y1, x0:x1]
if G.get('green'):                                                       # garlands and other dark greenery laid over the glass
    frame |= (g > r + G['green']) & (g > b + G['green']) & (lum < 150)
m = (inside & ~frame).astype(np.float32)
# settle onto the half-size grid: a cell is glass when most of it is, then knock out single stray cells
m = m[:SH // 2 * 2, :SW // 2 * 2]                                         # an odd last row or column is dropped
cell = m.reshape(SH // 2, 2, SW // 2, 2).mean(axis=(1, 3))
pad = np.pad(cell, 1, mode='edge')
near = sum(pad[1 + dy:1 + dy + cell.shape[0], 1 + dx:1 + dx + cell.shape[1]] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
keep = ((cell > 0.5) & (near > 0.34)) | (near > 0.75)
out = np.zeros(keep.shape + (4,), np.uint8); out[..., :3] = 255; out[..., 3] = keep * 255
Image.fromarray(out, 'RGBA').save(os.path.join(d, C['mask']))
print(f"{d}: {keep.mean() * 100:.1f}% of the picture is glass")
if '--debug' in sys.argv:
    big = np.asarray(Image.fromarray((keep * 255).astype(np.uint8)).resize((SW, SH), Image.NEAREST)) > 0
    dbg = a.copy(); dbg[big] = (dbg[big] * 0.45 + np.array([255, 0, 255]) * 0.55).astype(np.int32)
    Image.fromarray(dbg.astype(np.uint8)).save(sys.argv[sys.argv.index('--debug') + 1], quality=88)
