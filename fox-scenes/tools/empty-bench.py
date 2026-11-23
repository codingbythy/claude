#!/usr/bin/env python3
"""Makes the stationmaster painting without the foxes: painting-1280.png -> painting-empty-1280.png.

Nothing is generated. What the foxes hid is rebuilt from what is visible around them:
  - the strip of window and window post above the bench back: carried over from the same window beside it
  - the wall behind their heads: the same planks, continued from the wall to the right
  - the bench back: the bench's own front board (the same wood), laid in rows under a rail drawn to join the two visible ends
  - the seat and the front of the blanket where the tail hung: the blanket's own tartan, continued sideways and upward
Usage: empty-bench.py <scene-dir> [--debug out.jpg]
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

d = sys.argv[1]
a = np.asarray(Image.open(os.path.join(d, 'painting-1280.png')).convert('RGB')).astype(np.float64)
H, W = a.shape[:2]; out = a.copy(); rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:H, 0:W]

# the foxes' outline, a little generous, with a soft edge
FOX = [(430, 428), (438, 380), (452, 342), (478, 305), (520, 290), (570, 285), (620, 287), (660, 297), (684, 288), (692, 256), (706, 252), (722, 278),
       (742, 298), (768, 284), (790, 258), (802, 264), (803, 300), (816, 308), (832, 322), (878, 292), (892, 297), (898, 338), (932, 332), (982, 329),
       (1042, 337), (1092, 357), (1128, 393), (1139, 430), (1134, 458), (1122, 474), (1088, 504), (1054, 544), (1014, 594), (988, 630), (970, 646),
       (956, 636), (936, 602), (921, 562), (911, 522), (920, 494), (898, 484), (858, 482), (800, 474), (760, 474), (735, 486), (700, 492), (640, 489),
       (560, 484), (480, 472), (443, 454)]
m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon(FOX, fill=255)
m = m.filter(ImageFilter.MaxFilter(13))                                  # grow by 6 px
mask = np.asarray(m.filter(ImageFilter.GaussianBlur(2.2))).astype(np.float64) / 255

rail = lambda x: 336 - (x - 430) * 11 / 675          # top edge of the bench back, joining its two visible ends
SEAT = 452                                           # where the back meets the blanket on the seat
layer = a.copy()

# 1. above the bench back
for y in range(250, 345):
    for x0, x1, src in ((447, 598, lambda x: (y, x - 202)),                 # window pane: the pane to its left, same height
                        (598, 646, lambda x: (y - 44 * ((y - 246) // 44 + 1) if y > 290 else y, x)),      # window post: itself, from higher up
                        (646, 1110, lambda x: (y, 946 + (x - 646) % 150))):                              # wall: the planks to the right
        xs = np.arange(x0, x1); sy, sx = zip(*[src(x) for x in xs]); layer[y, xs] = a[list(sy), list(sx)]

# 2. the bench back: rows of the bench's own front board, lit more toward the stove, under a top rail
board = a[612:638, 566:896]                                              # clean wood between the two fringes
BW = board.shape[1]
for x in range(425, 1106):
    top = int(round(rail(x)))
    lit = 0.85 + 0.95 * ((x - 425) / 685) ** 1.6                          # warmer and brighter toward the stove on the right
    for y in range(top, SEAT + 6):
        k = y - top; col = board[:, (x - 425 + 61 * (max(k - 20, 0) // 26)) % BW]     # each row of planks starts somewhere else along the board
        if k < 3:   c = np.array([150, 84, 46]) * lit * 0.9               # the worn top edge catching the light
        elif k < 17: c = col[(k * 2) % 26] * lit * 1.5                    # the rail
        elif k < 20: c = np.array([20, 11, 10])                           # the shadow line under it
        else:        c = col[(k - 20) % 26] * lit * (1.0 + 0.12 * np.cos((k - 20) / 26 * 2 * np.pi))
        layer[y, x] = c
# the far end of the bench, where the right-hand fox's back hid it: the near end's post, turned round and lit by the stove
post = a[330:475, 385:428][:, ::-1] * 1.7
layer[322:467, 1103:1146] = post
layer[300:470, 425:1146] += rng.normal(0, 2.2, (170, 721, 1))            # a little grain so it is not flat

# 3. the seat (the blanket's top) and the blanket's front where the tail hung: the same tartan, continued
P = 172                                                                  # the plaid's repeat, measured
front = a.copy()
for x in range(882, 1088):                                               # front face under the tail: one repeat to the left
    front[462:664, x] = a[462:664, x - P]
layer[462:664, 882:1088] = front[462:664, 882:1088]
for y in range(SEAT, 500):                                               # where they lay on the seat: the same blanket from a little lower down
    layer[y, 436:1142] = front[y + 39, 436:1142] * (1.1 if y < 466 else 1.0)
layer[SEAT - 2:SEAT + 1, 436:1142] *= 0.55                               # where the seat meets the back

out = a * (1 - mask[..., None]) + layer * mask[..., None]
# the last pale hairs of the tail's tip, outside the outline: the bench front from a little to the left, edges feathered
w = np.clip(np.minimum(np.arange(34) + 1, 34 - np.arange(34)) / 4, 0, 1)[None, :, None]
out[572:640, 914:948] = out[572:640, 874:908] * w + out[572:640, 914:948] * (1 - w)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(os.path.join(d, 'painting-empty-1280.png'))
print('written', os.path.join(d, 'painting-empty-1280.png'))
if '--debug' in sys.argv:
    box = (300, 220, 1280, 660)
    s = Image.new('RGB', (980, 880)); s.paste(Image.fromarray(a.astype(np.uint8)).crop(box), (0, 0)); s.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).crop(box), (0, 440))
    s.save(sys.argv[sys.argv.index('--debug') + 1], quality=90)
