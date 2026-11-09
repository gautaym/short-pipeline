"""Bhess ki Aankh: a Bhess ki Eyes channel skit in the sketchbook look (toon/sketch.py).

A 5-6 year old on the bed with a tablet asks Mummy if "bhess ki aankh" is a gaali. She says no. He tries the
next one, "bhen k-", her stare stops him mid-word, and the slaps begin: "hoti hai!", "hoti hai!". Wailing,
he asks what this Bhess ki Eyes channel is then. One more slap lands his nose on SUBSCRIBE: "Subscribe kar!
Kar subscribe!" (script: the user's, 2026-11-09).

Run: python -m reel_engine.toon.bhess_gaali [--style]
"""
import math
import sys
from pathlib import Path

from . import sketch as K
from .sketch import INK, dark, ell, mix, move, pg, rect, smooth, dense

OUT = Path("out/2026-11-09/bhess_gaali")

WALL = (186, 222, 204)          # mint distemper
WALL_LO = (168, 206, 190)
FLOOR = (222, 214, 200)         # mosaic floor
WOOD = (150, 96, 60)
SHEET = (242, 160, 170)
SKIN_KID = (214, 160, 118)
SKIN_MUM = (200, 146, 104)
HAIR = (36, 28, 30)
VEST = (246, 244, 236)
SHORTS = (64, 104, 178)
NIGHTIE = (150, 84, 150)
DUPATTA = (246, 196, 70)
KITCHEN = (255, 222, 150)


# ---------------------------------------------------------------- helpers
def tube(pts, r0, r1=None):
    """Outline of a sausage around a centre line (limbs), radius r0 -> r1."""
    r1 = r0 if r1 is None else r1
    pts = smooth(pts, 6, closed=False) if len(pts) > 2 else K.dense(pts, 10, closed=False)
    m = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, m - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d, dx / d
        r = r0 + (r1 - r0) * i / max(1, m - 1)
        left.append((x + nx * r, y + ny * r))
        right.append((x - nx * r, y - ny * r))
    (ex, ey), (sx, sy) = pts[-1], pts[0]
    ae = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
    as_ = math.atan2(pts[0][1] - pts[1][1], pts[0][0] - pts[1][0])
    cap_e = [(ex + r1 * math.cos(ae + math.pi / 2 - math.pi * k / 6), ey + r1 * math.sin(ae + math.pi / 2 - math.pi * k / 6))
             for k in range(7)]
    cap_s = [(sx + r0 * math.cos(as_ + math.pi / 2 - math.pi * k / 6), sy + r0 * math.sin(as_ + math.pi / 2 - math.pi * k / 6))
             for k in range(7)]
    return left + cap_e + right[::-1] + cap_s


def limb(ink, pts, r0, col, r1=None, w=3.6):
    ink.shape(tube(pts, r0, r1), col, w)


def hand(ink, x, y, r, col, w=3.4):
    ink.shape(ell(x, y, r, r * 0.9, n=18), col, w)


# ---------------------------------------------------------------- the room
def room(ink, door_light=1.0):
    surf = ink.surf
    # wall + floor
    ink.fill(K.dense(rect(-20, -20, 1120, 1290)), WALL, 3)
    ink.fill(K.dense(rect(-20, 1010, 1120, 260)), WALL_LO, 3, off=(0, 0))           # damp/darker lower wall
    ink.shape(K.dense(rect(-20, 1240, 1120, 720)), FLOOR, 4)
    for i in range(260):                                                             # mosaic chips
        r = ink._rng()
        x, y = r.uniform(0, 1080), r.uniform(1260, 1920)
        ink.dot(x, y, r.uniform(2, 5), r.choice([(180, 168, 150), (150, 140, 128), (236, 230, 220), (196, 120, 100)]))
    ink.stroke([(-20, 1240), (1100, 1240)], 5, closed=False)
    ink.stroke([(-20, 1214), (1100, 1214)], 3, closed=False)                         # skirting
    # tube light
    ink.shape(K.dense(rect(330, 150, 330, 22)), (250, 252, 240), 3.5)
    ink.shape(K.dense(rect(318, 146, 16, 30)), (210, 210, 200), 3)
    ink.shape(K.dense(rect(656, 146, 16, 30)), (210, 210, 200), 3)
    # ceiling fan (blades going)
    ink.stroke([(540, -10), (540, 62)], 5, closed=False)
    ink.shape(ell(540, 72, 34, 16, n=20), (120, 90, 70), 3.5)
    for a in (0.3, 2.4, 4.5):
        ink.shape(ell(540 + 150 * math.cos(a), 74 + 22 * math.sin(a), 130, 14, rot=math.atan2(22 * math.sin(a), 150 * math.cos(a)), n=24),
                  (170, 130, 96), 3)
    # window with a grill and a curtain
    wx, wy, ww, wh = 70, 300, 300, 400
    ink.shape(K.dense(rect(wx - 18, wy - 18, ww + 36, wh + 36)), (232, 224, 206), 4)
    ink.shape(K.dense(rect(wx, wy, ww, wh)), (150, 204, 236), 4)
    ink.fill(ell(wx + 200, wy + 120, 60, 26, n=20), (250, 252, 255), 1.5, off=(0, 0))
    ink.fill(ell(wx + 140, wy + 130, 46, 20, n=20), (250, 252, 255), 1.5, off=(0, 0))
    ink.fill(K.dense(rect(wx, wy + 300, ww, 100)), (120, 170, 110), 2, off=(0, 0))     # a tree outside
    for k in range(1, 6):
        ink.stroke([(wx + ww * k / 6, wy), (wx + ww * k / 6, wy + wh)], 2.6, (70, 70, 80), 0.8, closed=False)
    for k in range(1, 4):
        ink.stroke([(wx, wy + wh * k / 4), (wx + ww, wy + wh * k / 4)], 2.6, (70, 70, 80), 0.8, closed=False)
    ink.stroke([(wx - 40, wy - 40), (wx + ww + 40, wy - 40)], 5, (120, 90, 70), closed=False)
    cur = smooth([(wx - 40, wy - 40), (wx + 90, wy - 40), (wx + 70, wy + 120), (wx + 30, wy + 200), (wx + 60, wy + 300),
                  (wx + 96, wy + 450), (wx - 10, wy + 456), (wx - 30, wy + 300), (wx - 6, wy + 200), (wx - 40, wy + 120)], 8)
    ink.shape(cur, (238, 120, 70), 3.6, shade_pts=smooth([(wx + 20, wy - 36), (wx + 86, wy - 36), (wx + 66, wy + 120),
                                                         (wx + 30, wy + 196), (wx + 20, wy + 120)], 5))
    for fx in (wx - 10, wx + 30):
        ink.stroke(smooth([(fx, wy - 30), (fx + 10, wy + 90)], 2, closed=False), 2.2, closed=False)
        ink.stroke(smooth([(fx + 6, wy + 230), (fx + 30, wy + 440)], 2, closed=False), 2.2, closed=False)
    ink.shape(ell(wx + 24, wy + 200, 50, 14, n=16), (200, 80, 50), 3)                       # tie-back
    # calendar (a mountain picture)
    cx, cy = 470, 330
    ink.stroke([(cx + 70, cy - 30), (cx + 50, cy), (cx + 90, cy)], 2.4, closed=False)
    ink.shape(K.dense(rect(cx, cy, 140, 200)), (252, 250, 244), 3.4)
    ink.shape([(cx + 10, cy + 90), (cx + 50, cy + 30), (cx + 80, cy + 70), (cx + 100, cy + 45), (cx + 130, cy + 90)],
              (110, 150, 200), 2.4)
    for r in range(3):
        for c in range(5):
            ink.dot(cx + 20 + c * 25, cy + 115 + r * 25, 3, (120, 110, 110))
    # door to the kitchen, with Mummy's warm light
    dx, dy, dw, dh = 740, 360, 290, 880
    ink.shape(K.dense(rect(dx - 22, dy - 22, dw + 44, dh + 22)), WOOD, 4.5)
    ink.shape(K.dense(rect(dx, dy, dw, dh)), mix((150, 120, 90), KITCHEN, door_light), 4)
    ink.fill(K.dense(rect(dx, dy + 520, dw, 40)), (200, 160, 110), 1.5, off=(0, 0))   # kitchen slab
    for k in range(3):                                                                 # steel utensils on a rack
        ink.shape(ell(dx + 60 + k * 70, dy + 470, 28, 22, n=16), (200, 204, 210), 2.6)
    ink.stroke([(dx + 20, dy + 430), (dx + dw - 20, dy + 430)], 3, closed=False)


def bed(ink):
    # headboard, mattress, floral sheet, pillow
    ink.shape(smooth([(30, 1000), (300, 940), (580, 1000), (580, 1120), (30, 1120)], 6), WOOD, 4.5,
              shade_pts=smooth([(30, 1060), (580, 1060), (580, 1120), (30, 1120)], 4))
    ink.shape(K.dense(rect(10, 1100, 700, 110)), SHEET, 4.5)
    ink.shape(K.dense(rect(30, 1210, 660, 200)), WOOD, 4.5, shade=dark(WOOD, 0.8),
              shade_pts=K.dense(rect(30, 1330, 660, 80)))
    for i in range(16):
        r = ink._rng()
        x, y = r.uniform(40, 680), r.uniform(1112, 1195)
        for a in range(5):
            ink.dot(x + 9 * math.cos(a * 1.257), y + 9 * math.sin(a * 1.257), 5, (250, 230, 120))
        ink.dot(x, y, 4, (220, 80, 90))
    ink.shape(smooth([(60, 1060), (230, 1040), (250, 1100), (70, 1110)], 6), (250, 250, 236), 3.6)
    for x in (40, 680):                                                                # legs
        ink.shape(K.dense(rect(x, 1405, 30, 90)), dark(WOOD, 0.75), 3.6)


# ---------------------------------------------------------------- the kid (5-6, baniyan + chaddi, oiled hair)
def kid(ink, x, y, s=1.0, mood="excited", talk=0.0, look=(0.0, 0.0), tablet=True, cheek=0.0):
    """(x, y): where he sits on the bed. mood: excited / curious / frozen / cry."""
    def T(pts):
        return move(pts, sx=s, ox=0, oy=0, dx=0, dy=0) if s == 1.0 else [(x + (px - x) * s, y + (py - y) * s) for px, py in pts]

    # crossed legs in shorts
    ink.shape(T(smooth([(x - 150, y - 10), (x, y - 70), (x + 150, y - 10), (x + 120, y + 40), (x - 120, y + 40)], 6)),
              SHORTS, 4.2)
    for side in (-1, 1):
        ink.shape(T(smooth([(x + side * 20, y + 10), (x + side * 150, y - 4), (x + side * 170, y + 40),
                            (x + side * 60, y + 56)], 6)), SKIN_KID, 3.8)
        ink.shape(T(ell(x + side * 40, y + 50, 34, 18, n=16)), dark(SKIN_KID, 0.92), 3.4)       # foot
    ink.shape(T(K.dense(rect(x - 34, y - 260, 68, 60))), SKIN_KID, 3.6)                          # neck
    # baniyan
    ink.shape(T(smooth([(x - 100, y - 40), (x - 112, y - 190), (x - 70, y - 238), (x - 40, y - 200),
                        (x + 40, y - 200), (x + 70, y - 238), (x + 112, y - 190), (x + 100, y - 40)], 6)),
              VEST, 4.2, shade_pts=T(smooth([(x + 40, y - 190), (x + 104, y - 180), (x + 100, y - 46), (x + 50, y - 46)], 5)))
    # arms + tablet held in front of the tummy, screen facing him
    if tablet:
        for side in (-1, 1):
            limb(ink, T([(x + side * 96, y - 196), (x + side * 120, y - 120), (x + side * 70, y - 92)]), 22, SKIN_KID)
        ink.shape(T(K.dense(rect(x - 104, y - 150, 208, 130))), (60, 62, 70), 4.5)
        ink.stroke(T([(x - 90, y - 140), (x - 50, y - 140)]), 2, (130, 134, 150), closed=False)
        ink.dot(*T([(x + 80, y - 134)])[0], 4, (30, 30, 34))
        for side in (-1, 1):
            hand(ink, *T([(x + side * 100, y - 100)])[0], 22 * s, SKIN_KID)
    # head
    hx, hy = x, y - 330
    _head(ink, hx, hy, s, mood, talk, look, glow=tablet, cheek=cheek)


def _head(ink, hx, hy, s, mood, talk, look, glow=False, cheek=0.0):
    def T(pts):
        return [(hx + (px - hx) * s, hy + (py - hy) * s) for px, py in pts]
    R = 112
    for side in (-1, 1):                                                                       # ears
        ink.shape(T(ell(hx + side * 112, hy + 6, 30, 40, n=18)), SKIN_KID, 3.8)
    face = T(smooth([(hx - R, hy - 10), (hx - R * 0.8, hy - R * 0.85), (hx, hy - R * 1.02), (hx + R * 0.8, hy - R * 0.85),
                     (hx + R, hy - 10), (hx + R * 0.82, hy + R * 0.7), (hx, hy + R * 0.98), (hx - R * 0.82, hy + R * 0.7)], 8))
    lit = mix(SKIN_KID, (190, 220, 255), 0.18) if glow else SKIN_KID                           # blue tablet glow
    ink.shape(face, lit, 4.4, shade=dark(lit, 0.92),
              shade_pts=T(smooth([(hx + R * 0.55, hy + R * 0.55), (hx + R * 0.97, hy + R * 0.05), (hx + R * 0.86, hy + R * 0.62),
                                  (hx + R * 0.35, hy + R * 0.92)], 6)))
    # oiled hair, side parting, flat to the head
    ink.shape(T(smooth([(hx - R * 1.04, hy - 6), (hx - R * 0.95, hy - R * 0.8), (hx - R * 0.3, hy - R * 1.12), (hx + R * 0.5, hy - R * 1.1),
                        (hx + R * 1.0, hy - R * 0.7), (hx + R * 1.04, hy - 6), (hx + R * 0.9, hy - R * 0.42),
                        (hx + R * 0.1, hy - R * 0.6), (hx - R * 0.35, hy - R * 0.66), (hx - R * 0.92, hy - R * 0.36)], 8)), HAIR, 4)
    ink.stroke(T([(hx - R * 0.35, hy - R * 1.06), (hx - R * 0.42, hy - R * 0.7)]), 2.4, (120, 120, 130), closed=False)  # parting shine
    ink.stroke(T(smooth([(hx + R * 0.2, hy - R * 0.98), (hx + R * 0.7, hy - R * 0.82), (hx + R * 0.86, hy - R * 0.55)], 4, closed=False)),
               3, (110, 110, 124), closed=False)
    ink.dot(*T([(hx - R * 0.62, hy - R * 0.38)])[0], 11 * s, INK)                                 # kala teeka
    # eyes
    lx, ly = look
    ey = hy - 4
    big = {"excited": 1.12, "curious": 1.0, "frozen": 1.25, "cry": 0.0}.get(mood, 1.0)
    for side in (-1, 1):
        ex = hx + side * 44
        if mood == "cry":                                                                       # squeezed shut: ><
            ink.stroke(T([(ex - side * 22, ey - 16), (ex + side * 12, ey), (ex - side * 22, ey + 14)]), 5, closed=False)
            continue
        ink.shape(T(ell(ex, ey, 30 * big, 36 * big, n=20)), (255, 255, 255), 3.6)
        pr = 13 if mood != "frozen" else 6
        ink.dot(*T([(ex + lx * 10, ey + 4 + ly * 10)])[0], pr * s, INK)
        if mood != "frozen":
            ink.dot(*T([(ex + lx * 10 - 4, ey - 2 + ly * 10)])[0], 4 * s, (255, 255, 255))
        brow = {"excited": -0.25, "curious": 0.25 * side, "frozen": -0.4, "cry": 0.5}[mood]
        by = ey - 40 * big - 6
        ink.stroke(T([(ex - 26, by + 12 * brow * side), (ex + 26, by - 12 * brow * side)]), 7, closed=False)
    # nose
    ink.stroke(T(smooth([(hx - 4, hy + 30), (hx + 10, hy + 40), (hx - 2, hy + 48)], 3, closed=False)), 3, closed=False)
    # mouth
    my = hy + 70
    if mood == "excited":
        o = 20 + 14 * talk
        ink.shape(T(smooth([(hx - 44, my - 10), (hx + 44, my - 10), (hx + 20, my + o), (hx - 20, my + o)], 6)), (120, 30, 40), 3.8)
        ink.fill(T(ell(hx, my + o * 0.6, 18, 9, n=14)), (236, 110, 120), 1, off=(0, 0))
    elif mood == "curious":
        ink.shape(T(ell(hx + 10, my, 12 + 6 * talk, 9 + 10 * talk, n=14)), (120, 30, 40), 3.4)
    elif mood == "frozen":
        ink.stroke(T(dense([(hx - 24, my), (hx + 24, my)], 8, closed=False)), 4, closed=False)
    elif mood == "cry":
        o = 34 + 16 * talk                                                                       # the full rural wail
        ink.shape(T(smooth([(hx - 50, my - 16), (hx + 50, my - 16), (hx + 34, my + o), (hx - 34, my + o)], 6)), (110, 26, 36), 4)
        ink.fill(T(ell(hx, my + o * 0.65, 26, 10, n=14)), (236, 110, 120), 1, off=(0, 0))
        for side in (-1, 1):                                                                     # tear fountains
            ink.shape(T(smooth([(hx + side * 40, hy), (hx + side * 110, hy - 30), (hx + side * 150, hy + 30),
                                (hx + side * 90, hy + 20)], 6)), (150, 210, 250), 3)
    if cheek > 0:                                                                                 # a slap mark: red hand
        cx = hx + 70
        ink.fill(T(ell(cx, hy + 36, 30 * cheek, 26 * cheek, n=16)), (236, 70, 70), 2, off=(0, 0))
        for f in range(4):
            ink.fill(T(ell(cx - 22 + f * 15, hy + 4, 6 * cheek, 18 * cheek, n=10)), (236, 70, 70), 1, off=(0, 0))
    else:
        for side in (-1, 1):
            ink.hatch(T(ell(hx + side * 66, hy + 40, 22, 14, n=14)), (230, 90, 100), gap=7, w=1.8, angle=-0.6, alpha=170)


# ---------------------------------------------------------------- Mummy (maxi nightie, dupatta, bun, bindi)
def mummy(ink, x, y, mood="angry", talk=0.0, arm="hip", look=(0.0, 0.0)):
    """(x, y): her feet. arm: hip / raised (the slap wind-up) / swing."""
    # nightie
    ink.shape(smooth([(x - 110, y), (x - 96, y - 300), (x - 100, y - 500), (x - 62, y - 560), (x + 62, y - 560),
                      (x + 100, y - 500), (x + 96, y - 300), (x + 120, y)], 6), NIGHTIE, 4.4,
              shade_pts=smooth([(x + 30, y - 520), (x + 100, y - 480), (x + 118, y - 10), (x + 50, y - 10)], 5))
    for i in range(40):                                                                         # print
        r = ink._rng()
        px, py = r.uniform(x - 90, x + 90), r.uniform(y - 520, y - 20)
        ink.dot(px, py, 5, (240, 200, 230))
    ink.shape(smooth([(x - 110, y - 4), (x + 120, y - 4), (x + 124, y + 10), (x - 114, y + 10)], 3), dark(NIGHTIE, 0.75), 3.6)
    for side in (-1, 1):
        ink.shape(ell(x + side * 46, y + 14, 40, 16, n=16), (100, 70, 60), 3.4)                  # chappals
    # dupatta over one shoulder
    ink.shape(smooth([(x - 70, y - 556), (x + 10, y - 520), (x + 90, y - 380), (x + 70, y - 330), (x - 10, y - 470),
                      (x - 80, y - 520)], 6), DUPATTA, 4)
    # arms
    if arm == "hip":
        limb(ink, [(x - 86, y - 520), (x - 178, y - 450), (x - 108, y - 386)], 26, SKIN_MUM)
        limb(ink, [(x + 86, y - 520), (x + 150, y - 430), (x + 150, y - 560)], 26, SKIN_MUM)
        _ladle(ink, x + 150, y - 580)
        hand(ink, x + 150, y - 574, 28, SKIN_MUM)
    elif arm == "raised":
        limb(ink, [(x - 86, y - 520), (x - 150, y - 420), (x - 92, y - 350)], 26, SKIN_MUM)
        limb(ink, [(x + 86, y - 520), (x + 170, y - 600), (x + 190, y - 720)], 26, SKIN_MUM)
        hand(ink, x + 192, y - 740, 34, SKIN_MUM)
    else:                                                                                        # swing (blurred)
        limb(ink, [(x - 86, y - 520), (x - 150, y - 420), (x - 92, y - 350)], 26, SKIN_MUM)
        limb(ink, [(x + 80, y - 520), (x - 40, y - 470), (x - 180, y - 470)], 26, SKIN_MUM)
        hand(ink, x - 200, y - 470, 34, SKIN_MUM)
    if arm == "hip":
        hand(ink, x - 104, y - 384, 26, SKIN_MUM)
    else:
        hand(ink, x - 92, y - 344, 24, SKIN_MUM)
    # head
    hx, hy = x, y - 680
    ink.shape(K.dense(rect(hx - 30, hy + 80, 60, 50)), SKIN_MUM, 3.6)
    ink.shape(ell(hx + 62, hy - 70, 56, 52, n=20), HAIR, 4)                                     # bun
    R = 100
    ink.shape(smooth([(hx - R, hy - 10), (hx - R * 0.8, hy - R * 0.9), (hx, hy - R * 1.04), (hx + R * 0.8, hy - R * 0.9),
                      (hx + R, hy - 10), (hx + R * 0.86, hy + R * 0.66), (hx, hy + R * 1.04), (hx - R * 0.86, hy + R * 0.66)], 8),
              SKIN_MUM, 4.4)
    ink.shape(smooth([(hx - R * 1.04, hy + 10), (hx - R * 0.98, hy - R * 0.8), (hx, hy - R * 1.12), (hx + R * 0.98, hy - R * 0.8),
                      (hx + R * 1.04, hy + 10), (hx + R * 0.84, hy - R * 0.5), (hx + 6, hy - R * 0.78),
                      (hx - R * 0.84, hy - R * 0.5)], 8), HAIR, 4)
    ink.stroke([(hx + 3, hy - R * 1.1), (hx + 4, hy - R * 0.8)], 4, (210, 30, 40), closed=False)  # sindoor
    ink.dot(hx, hy - 52, 9, (210, 30, 40))                                                       # bindi
    for side in (-1, 1):
        ink.dot(hx + side * 98, hy + 30, 8, (240, 200, 70))                                     # earrings
    ex_y = hy - 2
    lx, ly = look
    for side in (-1, 1):
        ex = hx + side * 40
        if mood == "angry":
            ink.shape([(ex - 24, ex_y - 6 * side * -1 - 4), (ex + 24, ex_y + 6 * side * -1 - 4), (ex + 22, ex_y + 12), (ex - 22, ex_y + 12)],
                      (255, 255, 255), 3.4)
            ink.dot(ex + lx * 8, ex_y + 6 + ly * 6, 9, INK)
            ink.stroke([(ex - side * 30, ex_y - 40), (ex + side * 22, ex_y - 18)], 8, closed=False)    # V brows
        else:                                                                                    # the stare: tiny pupils, wide
            ink.shape(ell(ex, ex_y, 28, 30, n=18), (255, 255, 255), 3.6)
            ink.dot(ex + lx * 8, ex_y + ly * 8, 5, INK)
            ink.stroke([(ex - side * 30, ex_y - 46), (ex + side * 24, ex_y - 30)], 8, closed=False)
    ink.stroke(smooth([(hx - 6, hy + 26), (hx + 8, hy + 40), (hx - 4, hy + 46)], 3, closed=False), 3, closed=False)
    my = hy + 66
    if talk > 0.05:
        ink.shape(smooth([(hx - 40, my - 6), (hx + 40, my - 6), (hx + 26, my + 12 + 26 * talk), (hx - 26, my + 12 + 26 * talk)], 6),
                  (110, 26, 36), 3.6)
        ink.fill(K.dense(rect(hx - 30, my - 4, 60, 8)), (255, 255, 255), 0.6, off=(0, 0))     # gritted teeth
    else:
        ink.stroke(smooth([(hx - 32, my + 8), (hx, my - 2), (hx + 32, my + 8)], 4, closed=False), 5, closed=False)
    # mangalsutra
    ink.stroke(smooth([(hx - 40, hy + 120), (hx, hy + 190), (hx + 40, hy + 120)], 5, closed=False), 2.4, closed=False)
    ink.dot(hx, hy + 192, 7, (240, 200, 70))


def _ladle(ink, x, y):
    """A steel karchi held up, bowl at the top."""
    limb(ink, [(x, y + 40), (x + 6, y - 150)], 7, (190, 194, 200), w=2.6)
    ink.shape(ell(x + 8, y - 176, 34, 26, n=16), (206, 210, 216), 3.4,
              shade_pts=ell(x + 8, y - 168, 26, 14, n=14))


# ---------------------------------------------------------------- style test frame
def style_frame(path: Path):
    pg.init()
    big = K.canvas()
    ink = K.Ink(big, boil=0, seed=11)
    room(ink)
    bed(ink)
    kid(ink, 330, 1090, mood="excited", talk=0.6, look=(0.6, -0.3))
    mummy(ink, 860, 1250, mood="angry", arm="hip", look=(-0.8, 0.2))
    img = K.finish(big, cam=(560, 860, 1.12))
    path.parent.mkdir(parents=True, exist_ok=True)
    pg.image.save(img, str(path))
    print(path.resolve())


if __name__ == "__main__":
    if "--style" in sys.argv or len(sys.argv) == 1:
        style_frame(OUT / "style.png")
