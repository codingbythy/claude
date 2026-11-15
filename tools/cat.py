#!/usr/bin/env python3
"""The recurring black cat, drawn as a pixel-art overlay on a rendered scene loop.

The cat lives on the scene's quarter-resolution pixel grid (the same grid as the rain and snow),
so it matches the painting's chunky pixels. Scene coordinates are the 1672x941 painting; the
overlay is produced at the 1920x1080 video size.

Usage:
  cat.py stream <mode> <seconds> > frames.rgba   raw RGBA frames of the overlay region at 30 fps
  cat.py preview <frame.png> <out.png> <mode> <t> [<t> ...]   composite on a still for checking
  cat.py region                                   print the overlay region (x y w h) in the video

Modes (t is seconds from the start of that video part):
  intro   walks in from behind the bed, hops onto the window seat, sits facing the sea
  loop    sits facing the sea (180 s period, so it repeats seamlessly)
  outro   gets up, hops down, walks back behind the bed

Scene-specific placement lives in SCENE below.
"""
import sys, math
import numpy as np

FPS = 30
K = 4 * (1920 / 1672)          # one sprite pixel in video pixels (4 scene px, scaled to 1080p)
OY = -0.29                     # vertical offset of the scene in the 1080p frame
REG = (960, 470, 680, 430)     # overlay region in the video: x, y, w, h

# Cartographer's Cottage placement, in sprite (quarter-scene) pixels.
SCENE = dict(
    bed_edge=229,      # x where the bed's foot post hides the cat (scene x 916)
    floor=188,         # feet on the floor in front of the window seat (scene y 752)
    cushion=148,       # feet on the window-seat cushion (scene y 592)
    sit_x=270,         # centre of the sitting cat (scene x 1080)
    walk_from=203, jump_from=250, land_x=258,
    strikes=[13.03, 57.03, 92.03, 137.03],   # lightning flashes in the loop (seconds)
)
LOOP = 180.0

BODY = np.array([17, 15, 22]); RIM = np.array([48, 58, 88]); WARM = np.array([84, 56, 36]); EYE = np.array([196, 186, 70])


def blank(w, h):
    return np.zeros((h, w), np.uint8)


def fill_ellipse(m, cx, cy, rx, ry):
    h, w = m.shape
    ys, xs = np.mgrid[0:h, 0:w]
    m[((xs + 0.5 - cx) / rx) ** 2 + ((ys + 0.5 - cy) / ry) ** 2 <= 1] = 1


def fill_tri(m, pts):
    h, w = m.shape
    ys, xs = np.mgrid[0:h, 0:w]
    px, py = xs + 0.5, ys + 0.5
    (x1, y1), (x2, y2), (x3, y3) = pts
    d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    a = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / d
    b = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / d
    m[(a >= -0.05) & (b >= -0.05) & (1 - a - b >= -0.05)] = 1


def line(m, x0, y0, x1, y1, width=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n; y = y0 + (y1 - y0) * i / n
        for dx in range(width):
            xi, yi = int(math.floor(x)) + dx, int(math.floor(y))
            if 0 <= yi < m.shape[0] and 0 <= xi < m.shape[1]:
                m[yi, xi] = 1


def side(phase=None, pose='walk', look_up=0):
    """Side view facing right, 28 x 16. Feet on the bottom row."""
    m = blank(28, 16); eye = None
    by = 9 if pose != 'crouch' else 11
    fill_ellipse(m, 12.5, by, 8.6, 3.6)                      # body
    hy = 6.2 - look_up + (2 if pose == 'crouch' else 0)
    fill_ellipse(m, 21.3, hy, 3.4, 2.9)                      # head
    fill_tri(m, [(18.6, hy - 1.6), (19.4, hy - 4.8), (21.2, hy - 2.2)])   # ears
    fill_tri(m, [(21.6, hy - 2.2), (23.2, hy - 5.0), (24.0, hy - 1.4)])
    fill_ellipse(m, 24.4, hy + 0.9, 1.4, 1.1)                # muzzle
    eye = (int(22.6), int(hy - 0.3))
    if pose == 'walk':
        for hip, off in ((6.5, 0.0), (8.5, math.pi), (16.5, math.pi), (18.5, 0.0)):
            s = math.sin(phase + off)
            line(m, hip, by + 1.5, hip + 1.8 * s, 15.6)
    elif pose == 'jump':
        line(m, 17.5, by + 1, 22.5, by + 4.5); line(m, 18.5, by + 1, 23.5, by + 3.5)   # front legs reaching
        line(m, 6.5, by + 1, 1.5, by + 5.5); line(m, 7.5, by + 1, 2.5, by + 6.0)       # back legs pushing
    else:  # crouch: legs tucked
        line(m, 6.0, 14.6, 9.0, 14.6); line(m, 16.0, 14.6, 19.0, 14.6)
    # tail: rises from the rump and curls over
    t0 = (4.5, by - 0.5)
    pts = [t0, (2.4, by - 2.5), (1.6, by - 5.0), (2.4, by - 7.2), (3.6, by - 7.8)] if pose != 'jump' else [t0, (1.5, by - 0.8), (-0.5, by - 0.5)]
    for a, b in zip(pts, pts[1:]):
        line(m, a[0], a[1], b[0], b[1])
    return m, eye


def back(breath=0, tail_up=0, ear_l=0, ear_r=0, perk=0):
    """Sitting, seen from behind, facing the window. 22 x 21. Feet on the bottom row."""
    m = blank(22, 21)
    hy = 5.4 - perk
    fill_ellipse(m, 8.5, 14.4, 7.4 + 0.4 * breath, 6.0)     # haunches
    fill_ellipse(m, 8.5, 10.4, 4.4, 4.0)                     # shoulders
    fill_ellipse(m, 8.5, hy + 0.6, 3.7, 3.0)                 # head
    fill_tri(m, [(5.0 - ear_l, hy - 0.2), (5.2 - ear_l, hy - 4.4), (8.0, hy - 1.6)])
    fill_tri(m, [(9.0, hy - 1.6), (11.8 + ear_r, hy - 4.4), (12.0 + ear_r, hy - 0.2)])
    m[20, 2:16] = 1                                          # base on the cushion
    # tail lies along the cushion to the right and curls up at the tip
    line(m, 14.0, 19.6, 19.0, 19.6); line(m, 14.0, 20.0, 19.0, 20.0)
    line(m, 19.0, 19.6, 20.6, 18.0 - tail_up); line(m, 20.6, 18.0 - tail_up, 20.8, 16.6 - tail_up)
    return m, None


def shade(mask, eye, flip, flash, warm_side):
    """Colour a silhouette: body, cool rim from the window, warm rim from the lantern side."""
    h, w = mask.shape
    pad = np.pad(mask, 1)
    edge = mask & ((pad[:-2, 1:-1] == 0) | (pad[1:-1, :-2] == 0) | (pad[1:-1, 2:] == 0))   # lit from above and the sides, not underneath
    rgb = np.zeros((h, w, 3)); rgb[:] = BODY
    rim = np.clip(RIM * (1 + 2.2 * flash), 0, 230)
    rgb[edge.astype(bool)] = rim
    if warm_side:
        xs = np.arange(w)[None, :].repeat(h, 0); ys = np.arange(h)[:, None].repeat(w, 1)
        sel = edge.astype(bool) & (xs >= w * 0.6) & (ys >= h * 0.55) & (pad[1:-1, 2:] == 0)
        rgb[sel] = WARM
    if eye is not None:
        rgb[eye[1], eye[0]] = EYE
        mask = mask.copy(); mask[eye[1], eye[0]] = 1
    rgba = np.zeros((h, w, 4), np.uint8); rgba[..., :3] = rgb; rgba[..., 3] = mask * 255
    if flip:
        rgba = rgba[:, ::-1]
    return rgba


def flash_at(t):
    v = 0.0
    for s in SCENE['strikes']:
        for base in (s, s + LOOP, s - LOOP):
            if base <= t < base + 1.5:
                v = max(v, math.exp(-(t - base) / 0.25))
    return v


def rest_pose(t):
    t = t % LOOP
    breath = 1 if (t % 4.0) < 2.0 else 0
    tail_up = 1 if (t % 12.0) < 0.6 else 0
    ear_l = 1 if 7.0 <= (t % 20.0) < 7.4 else 0
    ear_r = 1 if 19.0 <= (t % 30.0) < 19.3 else 0
    perk = 1 if any(s + 0.1 <= t < s + 1.8 for s in SCENE['strikes']) else 0
    m, _ = back(breath, tail_up, ear_l, ear_r, perk)
    return dict(kind='back', spr=shade(m, None, False, flash_at(t), True), x=SCENE['sit_x'] - 9, feet=SCENE['cushion'], shadow=None)


def side_pose(m_eye, x, feet, face_left, t, shadow):
    m, eye = m_eye
    return dict(kind='side', spr=shade(m, eye, face_left, flash_at(t), not face_left), x=x, feet=feet, shadow=shadow,
                hide_x=SCENE['bed_edge'] if feet == SCENE['floor'] else None)


WALK = 12.0   # sprite pixels per second


def intro_pose(t):
    S = SCENE
    if t < 9.0:
        return None
    if t < 12.9:
        x = S['walk_from'] + (S['jump_from'] - S['walk_from']) * (t - 9.0) / 3.9
        return side_pose(side(phase=(t - 9.0) * 2 * math.pi * 1.6), round(x), S['floor'], False, t, 'floor')
    if t < 14.2:
        return side_pose(side(pose='crouch', look_up=1 if t > 13.4 else 0), S['jump_from'], S['floor'], False, t, 'floor')
    if t < 14.8:
        k = (t - 14.2) / 0.6
        x = S['jump_from'] + (S['land_x'] - S['jump_from']) * k
        feet = S['floor'] + (S['cushion'] - S['floor']) * k - 22 * k * (1 - k)
        return side_pose(side(pose='jump'), round(x), round(feet), False, t, None)
    if t < 15.4:
        return side_pose(side(pose='crouch'), S['land_x'], S['cushion'], False, t, 'cushion')
    return rest_pose(t + 10.0)   # the intro starts 10 s into the loop


def outro_pose(t):
    S = SCENE
    if t < 5.0:
        return rest_pose(t)
    if t < 5.6:
        return side_pose(side(pose='crouch'), S['land_x'] - 2, S['cushion'], True, t, 'cushion')
    if t < 6.2:
        k = (t - 5.6) / 0.6
        x = S['land_x'] - 2 + (S['jump_from'] - 4 - S['land_x'] + 2) * k
        feet = S['cushion'] + (S['floor'] - S['cushion']) * k - 22 * k * (1 - k)
        return side_pose(side(pose='jump'), round(x), round(feet), True, t, None)
    if t < 6.6:
        return side_pose(side(pose='crouch'), S['jump_from'] - 4, S['floor'], True, t, 'floor')
    x = S['jump_from'] - 4 - WALK * (t - 6.6)
    if x + 28 < S['bed_edge']:
        return None
    return side_pose(side(phase=(t - 6.6) * 2 * math.pi * 1.6), round(x), S['floor'], True, t, 'floor')


POSES = {'intro': intro_pose, 'loop': lambda t: rest_pose(t), 'outro': outro_pose}


# ---------------------------------------------------------------------------------------------
# Glasshouse (episode 3): a rounder, cuter cat that walks in from behind the fern pot and curls
# up asleep on the floor in front of the warm radiator.
# ---------------------------------------------------------------------------------------------
GH = dict(
    pot_edge=43,                     # the fern pot hides the cat left of scene x 172
    start_x=8, stop_x=150,           # sprite left edge where the walk starts (hidden) and stops
    region=(40, 860, 1000, 220),     # overlay region in the video
)
GH_BODY = np.array([22, 19, 27]); GH_RIM = np.array([104, 78, 56]); GH_COOL = np.array([60, 66, 88])
GH_EYE = np.array([150, 205, 96]); GH_SHINE = np.array([236, 244, 226]); GH_NOSE = np.array([214, 128, 140])
Z = 1.45                             # the cat is nearer the camera here, so a little bigger


def gh_feet(x):
    """Feet line along the floor in front of the radiator (sprite px), following the room's perspective."""
    cx = (x + 17) * 4
    return int(round((915 - 0.138 * (cx - 150)) / 4))


def cute_side(phase=None, pose='walk', look_up=0, z=Z):
    """Side view facing right: big round head, short body, stubby legs. Returns (mask, features)."""
    w, h = int(31 * z) + 1, int(17 * z) + 1
    m = blank(w, h)
    by = (10.6 if pose != 'crouch' else 12.4) * z
    fill_ellipse(m, 12.0 * z, by, 7.6 * z, 3.7 * z)
    hy = (7.0 - look_up + (1.8 if pose == 'crouch' else 0)) * z
    hx = 22.0 * z
    fill_ellipse(m, hx, hy, 4.3 * z, 3.9 * z)
    fill_tri(m, [(hx - 3.6 * z, hy - 1.4 * z), (hx - 3.1 * z, hy - 6.2 * z), (hx - 0.6 * z, hy - 3.0 * z)])
    fill_tri(m, [(hx + 0.6 * z, hy - 3.0 * z), (hx + 3.0 * z, hy - 6.2 * z), (hx + 3.8 * z, hy - 1.2 * z)])
    feats = {'eye': (int(hx + 1.6 * z), int(hy - 0.4 * z)), 'nose': (int(hx + 4.0 * z), int(hy + 0.8 * z))}
    foot = h - 0.4
    if pose == 'walk':
        for hip, off in ((7.2, 0.0), (9.4, math.pi), (15.0, math.pi), (17.2, 0.0)):
            s = math.sin(phase + off)
            line(m, hip * z, by + 2.2 * z, hip * z + 1.4 * z * s, foot, width=2 if z > 1.1 else 1)
    else:
        line(m, 6.0 * z, foot, 10.0 * z, foot); line(m, 14.0 * z, foot, 18.0 * z, foot)
    t0 = (4.8 * z, by - 1.0 * z)
    pts = [t0, (2.6 * z, by - 3.0 * z), (1.8 * z, by - 5.8 * z), (2.8 * z, by - 8.0 * z), (4.2 * z, by - 8.4 * z)]
    for a, b in zip(pts, pts[1:]):
        line(m, a[0], a[1], b[0], b[1], width=2 if z > 1.1 else 1)
    return m, feats


def cute_curl(breath=0, ear=0, tail=0, awake=0, z=Z):
    """Curled up asleep, side view: a round body, head resting at the front, tail tip tucked under the chin."""
    w, h = int(30 * z) + 1, int(16 * z) + 1
    m = blank(w, h)
    bot = h - 0.5
    fill_ellipse(m, 11.8 * z, bot - 5.0 * z, 8.8 * z, (5.0 + 0.35 * breath) * z)
    m[int(bot):, int(5 * z):int(19 * z)] = 1                           # resting flat on the floor
    hx, hy = 20.6 * z, bot - (5.2 + 2.0 * awake) * z
    head = blank(w, h)
    fill_ellipse(head, hx, hy, 4.5 * z, 4.0 * z)
    fill_tri(head, [(hx - 3.8 * z, hy - 1.0 * z), (hx - 3.2 * z - ear * z, hy - 6.8 * z), (hx - 0.4 * z, hy - 3.2 * z)])
    fill_tri(head, [(hx + 0.4 * z, hy - 3.2 * z), (hx + 3.2 * z, hy - 6.8 * z), (hx + 4.0 * z, hy - 0.8 * z)])
    m |= head
    # tail wraps round the front and its tip curls up under the chin
    line(m, 14.0 * z, bot - 0.2, 25.0 * z, bot - 0.2, width=1)
    line(m, 25.0 * z, bot - 0.2, 26.4 * z, bot - (1.4 + tail) * z, width=1)
    feats = {'nose': (int(hx + 4.2 * z), int(hy + 0.8 * z))}
    # a faint line where the cheek meets the body, so the head reads as its own shape
    hp = np.pad(head, 1)
    edge = head & ((hp[:-2, 1:-1] == 0) | (hp[2:, 1:-1] == 0) | (hp[1:-1, :-2] == 0))
    ys, xs = np.nonzero(edge)
    feats['seam'] = [(x, y) for x, y in zip(xs, ys) if x < hx - 1.5 * z and y > hy - 1.0 * z]
    if awake:
        feats['eye'] = (int(hx + 1.6 * z), int(hy - 0.2 * z))
    else:
        feats['closed'] = [(int(hx + 0.8 * z), int(hy)), (int(hx + 1.8 * z), int(hy + 0.5 * z)), (int(hx + 2.8 * z), int(hy))]
    return m, feats


def cute_shade(mask, feats, flip):
    h, w = mask.shape
    pad = np.pad(mask, 1)
    top = mask & (pad[:-2, 1:-1] == 0)
    sides = mask & ((pad[1:-1, :-2] == 0) | (pad[1:-1, 2:] == 0)) & ~top
    rgb = np.zeros((h, w, 3)); rgb[:] = GH_BODY
    rgb[top.astype(bool)] = GH_RIM          # warm light from the radiator and the lamp on the top edges
    rgb[sides.astype(bool)] = GH_COOL       # cooler light from the glass on the sides
    mask = mask.copy()
    def px(p, c):
        x, y = p
        if 0 <= y < h and 0 <= x < w:
            rgb[y, x] = c; mask[y, x] = 1
    if 'eye' in feats:
        px(feats['eye'], GH_EYE); px((feats['eye'][0], feats['eye'][1] - 1), GH_SHINE)
    for p in feats.get('seam', []):
        if 0 <= p[1] < h and 0 <= p[0] < w and not top[p[1], p[0]]:
            rgb[p[1], p[0]] = GH_BODY * 0.5 + GH_COOL * 0.5
    for p in feats.get('closed', []):
        px(p, GH_RIM)
    if 'nose' in feats:
        px(feats['nose'], GH_NOSE)
    rgba = np.zeros((h, w, 4), np.uint8); rgba[..., :3] = rgb; rgba[..., 3] = mask * 255
    return rgba[:, ::-1] if flip else rgba


def gh_side(m_f, x, face_left, shadow=True):
    m, f = m_f
    return dict(kind='side', spr=cute_shade(m, f, face_left), x=x, feet=gh_feet(x), shadow='floor' if shadow else None, hide_x=GH['pot_edge'])


def gh_rest(t, awake=0):
    t = t % LOOP
    breath = 1 if (t % 4.5) < 2.25 else 0
    ear = 1 if 9.0 <= (t % 20.0) < 9.35 else 0
    tail = 1 if 4.0 <= (t % 15.0) < 4.6 else 0
    m, f = cute_curl(breath, ear, tail, awake)
    x = GH['stop_x']
    return dict(kind='side', spr=cute_shade(m, f, False), x=x, feet=gh_feet(x), shadow='floor', hide_x=None)


GH_WALK = 13.0


def gh_intro(t):
    S = GH
    t_walk = (S['stop_x'] - S['start_x']) / GH_WALK
    if t < 9.0:
        return None
    if t < 9.0 + t_walk:
        x = S['start_x'] + GH_WALK * (t - 9.0)
        return gh_side(cute_side(phase=(t - 9.0) * 2 * math.pi * 1.7), round(x), False)
    t1 = 9.0 + t_walk
    if t < t1 + 1.2:     # turns round twice before settling, the way cats do
        flip = int((t - t1) / 0.4) % 2 == 0
        return gh_side(cute_side(pose='crouch'), S['stop_x'], flip)
    if t < t1 + 2.0:
        return gh_side(cute_side(pose='crouch', look_up=0), S['stop_x'], False)
    return gh_rest(t + 10.0)


def gh_outro(t):
    S = GH
    if t < 5.0:
        return gh_rest(t)
    if t < 6.4:
        return gh_rest(t, awake=1)
    if t < 6.9:
        return gh_side(cute_side(pose='crouch'), S['stop_x'], True)
    x = S['stop_x'] - GH_WALK * 1.1 * (t - 6.9)
    if x + 34 < S['pot_edge']:
        return None
    return gh_side(cute_side(phase=(t - 6.9) * 2 * math.pi * 1.8), round(x), True)


SCENES = {
    'lighthouse-room': dict(poses=POSES, region=REG),
    'glasshouse': dict(poses={'intro': gh_intro, 'loop': lambda t: gh_rest(t), 'outro': gh_outro}, region=GH['region']),
}
import os
_cfg = SCENES[os.environ.get('CAT_SCENE', 'lighthouse-room')]
POSES = _cfg['poses']; REG = _cfg['region']


def vx(X):   # sprite-pixel column -> video x
    return int(round(X * K))


def vy(Y):
    return int(round(Y * K + OY))


def render(pose):
    """Return the overlay region as an RGBA uint8 array."""
    x0, y0, w, h = REG
    out = np.zeros((h, w, 4), np.uint8)
    if pose is None:
        return out
    spr = pose['spr']; sh, sw = spr.shape[:2]
    top = pose['feet'] - sh + 1
    if pose['shadow']:
        cx = pose['x'] + sw / 2
        for X in range(int(cx - sw * 0.4), int(cx + sw * 0.4) + 1):
            a, b, c, d = vx(X) - x0, vx(X + 1) - x0, vy(pose['feet'] + 1) - y0, vy(pose['feet'] + 2) - y0
            if 0 <= a < w and 0 <= c < h:
                out[c:d, a:b] = (0, 0, 0, 70)
    hide = pose.get('hide_x')
    for Y in range(sh):
        for X in range(sw):
            px = spr[Y, X]
            if px[3] == 0:
                continue
            gx = pose['x'] + X
            if pose.get('hide_x') is not None and gx < pose['hide_x']:
                continue          # hidden behind something in the room (bed post, plant pot)
            a, b = vx(gx) - x0, vx(gx + 1) - x0
            c, d = vy(top + Y) - y0, vy(top + Y + 1) - y0
            if b <= 0 or d <= 0 or a >= w or c >= h:
                continue
            out[max(c, 0):d, max(a, 0):b] = px
    return out


def main():
    cmd = sys.argv[1]
    if cmd == 'region':
        print(*REG); return
    if cmd == 'stream':
        mode, secs = sys.argv[2], float(sys.argv[3])
        fn = POSES[mode]; cache = {}
        o = sys.stdout.buffer
        for i in range(int(round(secs * FPS))):
            p = fn(i / FPS)
            key = None if p is None else (p['kind'], p['x'], p['feet'], p['shadow'], p['spr'].tobytes())
            if key not in cache:
                if len(cache) > 400:
                    cache.clear()
                cache[key] = render(p).tobytes()
            o.write(cache[key])
        return
    if cmd == 'preview':
        from PIL import Image
        bg = Image.open(sys.argv[2]).convert('RGBA'); out, mode = sys.argv[3], sys.argv[4]
        tiles = []
        for t in sys.argv[5:]:
            im = bg.copy(); ov = Image.fromarray(render(POSES[mode](float(t))), 'RGBA')
            im.alpha_composite(ov, (REG[0], REG[1]))
            tiles.append(im.crop((REG[0], REG[1] - 60, REG[0] + REG[2], REG[1] + REG[3])))
        W = Image.new('RGBA', (sum(x.width for x in tiles), tiles[0].height))
        for i, x in enumerate(tiles):
            W.paste(x, (i * x.width, 0))
        W.convert('RGB').save(out); return


if __name__ == '__main__':
    main()
