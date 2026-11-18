#!/usr/bin/env python3
"""The sleeping fox on the glasshouse armchair, as a video overlay (same interface as cat.py).

The fox sprite (glasshouse/fox.png, already sized for the 1672x941 painting) sits at scene
position (1196, 566). It only breathes: the sprite stretches about 1% taller and back every 4.5 s,
which divides the 180 s loop exactly, so the loop stays seamless.

Usage: fox.py region | fox.py stream <intro|loop|outro> <seconds>
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageFilter

FPS = 30; K = 1920 / 1672; OY = -0.29
POS = (1196, 566); PERIOD = 4.5; LEVELS = 8
REG = (1352, 628, 372, 316)          # x, y, w, h in the video
HERE = os.path.dirname(os.path.abspath(__file__))


def frames():
    fox = Image.open(os.path.join(HERE, '..', 'glasshouse', 'fox.png')).convert('RGBA')
    w, h = round(fox.width * K), round(fox.height * K)
    out = []
    for i in range(LEVELS):
        hh = round(h * (1 + 0.012 * i / (LEVELS - 1)))
        f = fox.resize((w, hh), Image.LANCZOS)
        x = round(POS[0] * K) - REG[0]; y = round(POS[1] * K + OY) - REG[1] + (h - hh)
        im = Image.new('RGBA', (REG[2], REG[3]), (0, 0, 0, 0))
        sh = Image.new('L', (REG[2], REG[3]), 0); sh.paste(f.split()[3].point(lambda v: int(v * 0.5)), (x + 6, y + 10))
        im.paste((20, 6, 10, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(7)))
        im.alpha_composite(f, (x, y))
        out.append(np.asarray(im).tobytes())
    return out


def main():
    if sys.argv[1] == 'region':
        print(*REG); return
    mode, secs = sys.argv[2], float(sys.argv[3])
    fr = frames(); off = 10.0 if mode == 'intro' else 0.0      # the intro starts 10 s into the loop
    o = sys.stdout.buffer
    for i in range(int(round(secs * FPS))):
        t = i / FPS + off
        lvl = 0.5 - 0.5 * math.cos(2 * math.pi * t / PERIOD)
        o.write(fr[int(round(lvl * (LEVELS - 1)))])


if __name__ == '__main__':
    main()
