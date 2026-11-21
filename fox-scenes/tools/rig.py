#!/usr/bin/env python3
"""Cuts the foxes' heads and ears out of a scene's picture so they can move as separate pieces.

Usage: rig.py <scene-dir> [--debug out.jpg]
Reads the "rig" block of <scene>/scene.json and the scene's picture (room.webp, already graded). Each part has:
  name, poly   the outline of the piece, in layout coordinates
  pivot        the point it turns about (a neck or the base of an ear)
  fade         two points [from, to]: the piece is fully see-through at "from" and solid by "to". Laid across a neck or an ear
               base, it makes a soft joint, so the piece bends away from the body instead of showing a cut edge
  parent       a head, for ears (they ride on it)
  fill         what lies behind the piece: {"clone": [dx, dy]} copies fur from that far away (the animal's own body), and
               {"chin_y": y, "chin_clone": [dx, dy]} does the same for the part below y (the paws under a chin).
               Pieces without it (ears) are filled from the background around them
Writes <scene>/rig/: one PNG per part, plate.webp (the picture with the pieces lifted out and the gaps behind them filled in from
their surroundings), and rig.json. With every piece in its resting place the result is the original picture.
Needs opencv-python-headless (for the fill).
"""
import json, os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

d = sys.argv[1]
C = json.load(open(os.path.join(d, 'scene.json'))); RIG = C['rig']
SW, SH = C['size']
img = Image.open(os.path.join(d, C['image'])).convert('RGB')
W, H = img.size; K = W / SW                          # picture pixels per layout pixel (0.5 on the pixel grid, 1.5 otherwise)
a = np.asarray(img).astype(np.uint8)
out = os.path.join(d, 'rig'); os.makedirs(out, exist_ok=True)
SS = 4                                               # supersampling for smooth outlines
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64); lx, ly = (xx + 0.5) / K, (yy + 0.5) / K

hole = np.zeros((H, W), bool); meta = []; crisps = []
for p in RIG['parts']:
    m = Image.new('L', (W * SS, H * SS), 0)
    ImageDraw.Draw(m).polygon([(x * K * SS, y * K * SS) for x, y in p['poly']], fill=255)
    crisp = np.asarray(m.resize((W, H), Image.BOX)).astype(np.float64) / 255
    ramp = np.ones((H, W))
    if p.get('fade'):
        (x0, y0), (x1, y1) = p['fade']; vx, vy = x1 - x0, y1 - y0
        t = np.clip(((lx - x0) * vx + (ly - y0) * vy) / (vx * vx + vy * vy), 0, 1); ramp = t * t * (3 - 2 * t)
    alpha = crisp * ramp
    crisps.append(crisp > 0.02); hole |= (crisp > 0.02) & (ramp > 0.98)
    ys, xs = np.nonzero(alpha > 0.004); x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    rgba = np.dstack([a[y0:y1, x0:x1], (alpha[y0:y1, x0:x1] * 255 + 0.5).astype(np.uint8)])
    Image.fromarray(rgba, 'RGBA').save(os.path.join(out, p['name'] + '.png'))
    meta.append({'name': p['name'], 'file': p['name'] + '.png', 'x': int(x0), 'y': int(y0), 'w': int(x1 - x0), 'h': int(y1 - y0), 'pivot': p['pivot'], 'parent': p.get('parent')})

# What was behind the pieces. First a picture with every piece taken out whole (soft joints included) and the gap filled from
# what surrounds it, so no ear or cheek colour leaks into the fill; then fur copied from the animal's own body where asked.
# The plate keeps the original picture everywhere except where a piece is solid, so soft joints still blend into the real fur.
whole = cv2.dilate(np.any(crisps, axis=0).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2)
fill = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(a, cv2.COLOR_RGB2BGR), whole * 255, max(3, int(round(5 * K))), cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
for p, m in zip(RIG['parts'], crisps):
    f = p.get('fill')
    if not f:
        continue
    for sel, (dx, dy) in ((ly < f.get('chin_y', 1e9), f['clone']), (ly >= f.get('chin_y', 1e9), f.get('chin_clone', f['clone']))):
        ys, xs = np.nonzero(m & sel)
        sy, sx = np.clip(ys + int(round(dy * K)), 0, H - 1), np.clip(xs + int(round(dx * K)), 0, W - 1)
        ok = ~whole[sy, sx].astype(bool)                     # only copy from places that are not themselves behind a piece
        fill[ys[ok], xs[ok]] = (a[sy[ok], sx[ok]] * 0.46).astype(np.uint8)        # in shadow: it is the hollow between head and body
fill = cv2.GaussianBlur(fill, (0, 0), max(1.0, 2.0 * K))                       # the fill is only ever glimpsed; keep it soft
grow = cv2.dilate(hole.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
plate = np.where(grow[..., None] > 0, fill, a).astype(np.uint8)
if K < 1:
    Image.fromarray(plate).save(os.path.join(out, 'plate.webp'), lossless=True)
else:
    Image.fromarray(plate).save(os.path.join(out, 'plate.webp'), quality=95, method=6)
json.dump({'parts': meta, 'order': RIG['order']}, open(os.path.join(out, 'rig.json'), 'w'), indent=1)
print(f'{d}: {len(meta)} parts cut, {hole.mean() * 100:.1f}% of the picture filled in behind them')

if '--debug' in sys.argv:       # the plate on the left; on the right every piece lifted a few pixels over magenta, to judge the cut
    box = [int(v * K) for v in RIG.get('debug_box', [0, 0, SW, SH])]
    lifted = np.zeros((H, W, 3), np.float64); lifted[:] = (255, 0, 255)
    for i, m in enumerate(meta):
        s = np.asarray(Image.open(os.path.join(out, m['file']))).astype(np.float64); al = s[..., 3:] / 255
        oy = m['y']; ox = m['x']
        lifted[oy:oy + m['h'], ox:ox + m['w']] = s[..., :3] * al + lifted[oy:oy + m['h'], ox:ox + m['w']] * (1 - al)
    sheet = np.concatenate([plate[box[1]:box[3], box[0]:box[2]], lifted[box[1]:box[3], box[0]:box[2]].astype(np.uint8)], axis=1)
    z = max(1, int(round(3 / K / 1.5)))
    Image.fromarray(sheet).resize((sheet.shape[1] * z, sheet.shape[0] * z), Image.NEAREST if K < 1 else Image.LANCZOS).save(sys.argv[sys.argv.index('--debug') + 1], quality=90)
