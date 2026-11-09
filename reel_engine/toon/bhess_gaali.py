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
    """A limb as straight sausages, one per bone: the ink outline is their union, so bends never self-cross."""
    r1 = r0 if r1 is None else r1
    segs = list(zip(pts[:-1], pts[1:]))
    rad = [r0 + (r1 - r0) * i / max(1, len(segs)) for i in range(len(segs) + 1)]
    edge = w * K.LINE * 0.55
    for i, (a, b) in enumerate(segs):
        ink.fill(tube([a, b], rad[i] + edge, rad[i + 1] + edge), INK, 1.4, off=(0, 0))
    for i, (a, b) in enumerate(segs):
        ink.fill(tube([a, b], rad[i], rad[i + 1]), col, 1.0, off=(0, 0))


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


# ---------------------------------------------------------------- posing helpers
def ik(sx, sy, hx, hy, l1, l2, bend=1):
    """Elbow for a two-bone arm from shoulder (sx, sy) to hand (hx, hy); bend=+1/-1 picks the side."""
    d = math.hypot(hx - sx, hy - sy)
    d = min(d, l1 + l2 - 1e-3)
    a = math.atan2(hy - sy, hx - sx)
    c = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d) if d > 1e-6 else 1.0
    b = math.acos(max(-1.0, min(1.0, c)))
    return sx + l1 * math.cos(a + bend * b), sy + l1 * math.sin(a + bend * b)


def rot_about(pts, ox, oy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c) for x, y in pts]


def star(cx, cy, r, k=5, inner=0.45, rot=0.0):
    return [(cx + (r if i % 2 == 0 else r * inner) * math.cos(rot + math.pi * i / k),
             cy + (r if i % 2 == 0 else r * inner) * math.sin(rot + math.pi * i / k)) for i in range(2 * k)]


# ---------------------------------------------------------------- the kid (5-6, baniyan + chaddi, oiled hair)
def kid(ink, x, y, mood="excited", talk=0.0, look=(0.0, 0.0), arms="tablet", tilt=0.0, cheeks=0, sweat=0.0,
        bob=0.0, glow=True):
    """(x, y): where he sits on the bed. arms: tablet / chin / show / cry / stiff. tilt: head roll (radians)."""
    y = y - bob
    # crossed legs in shorts
    ink.shape(smooth([(x - 150, y - 10), (x, y - 70), (x + 150, y - 10), (x + 120, y + 40), (x - 120, y + 40)], 6), SHORTS, 4.2)
    for side in (-1, 1):
        ink.shape(smooth([(x + side * 20, y + 10), (x + side * 150, y - 4), (x + side * 170, y + 40), (x + side * 60, y + 56)], 6),
                  SKIN_KID, 3.8)
        ink.shape(ell(x + side * 40, y + 50 + (bob * 0.6 if side > 0 else 0), 34, 18, n=16), dark(SKIN_KID, 0.92), 3.4)
    ink.shape(K.dense(rect(x - 34, y - 260, 68, 60)), SKIN_KID, 3.6)                                    # neck
    ink.shape(smooth([(x - 100, y - 40), (x - 112, y - 190), (x - 70, y - 238), (x - 40, y - 200), (x + 40, y - 200),
                      (x + 70, y - 238), (x + 112, y - 190), (x + 100, y - 40)], 6), VEST, 4.2,
              shade_pts=smooth([(x + 40, y - 190), (x + 104, y - 180), (x + 100, y - 46), (x + 50, y - 46)], 5))
    hx, hy = x, y - 330
    sl, sr = (x - 100, y - 196), (x + 100, y - 196)
    after = []                                   # arm parts drawn over the head (hands at the face)
    if arms == "tablet":
        for (sx, sy), side in ((sl, -1), (sr, 1)):
            limb(ink, [(sx, sy), (x + side * 122, y - 120), (x + side * 70, y - 92)], 22, SKIN_KID)
        _tablet_back(ink, x, y - 85)
        for side in (-1, 1):
            hand(ink, x + side * 100, y - 100, 22, SKIN_KID)
    elif arms == "stiff":
        for (sx, sy), side in ((sl, -1), (sr, 1)):
            limb(ink, [(sx, sy), (x + side * 132, y - 110), (x + side * 128, y - 40)], 22, SKIN_KID)
            hand(ink, x + side * 128, y - 30, 22, SKIN_KID)
        _tablet_lap(ink, x, y - 20)
    elif arms == "chin":
        _tablet_lap(ink, x, y - 20)
        limb(ink, [sl, (x - 130, y - 110), (x - 60, y - 40)], 22, SKIN_KID)
        hand(ink, x - 60, y - 36, 22, SKIN_KID)
        el = (x + 140, y - 110)
        after.append(lambda: (limb(ink, [sr, el, (hx + 40, hy + 124)], 22, SKIN_KID),            # fist under the chin, thinking
                              hand(ink, hx + 36, hy + 116, 27, SKIN_KID)))
    elif arms == "show":                                           # tablet held up beside his face, screen out
        limb(ink, [sr, (x + 140, y - 110), (x + 70, y - 40)], 22, SKIN_KID)
        hand(ink, x + 70, y - 36, 22, SKIN_KID)
        after.append(lambda: (limb(ink, [sl, (x - 170, y - 170), (x - 190, y - 260)], 22, SKIN_KID),
                              _tablet_front(ink, x - 215, y - 330, 0.62),
                              hand(ink, x - 196, y - 250, 24, SKIN_KID)))
    elif arms == "cry":                                            # fists at the eyes, elbows out
        _tablet_lap(ink, x, y - 20)
        for (sx, sy), side in ((sl, -1), (sr, 1)):
            fx, fy = hx + side * 50, hy + 4
            after.append(lambda sx=sx, sy=sy, side=side, fx=fx, fy=fy: (
                limb(ink, [(sx, sy), (x + side * 190, y - 200), (fx + side * 30, fy + 30)], 22, SKIN_KID),
                hand(ink, fx, fy + 10, 28, SKIN_KID)))
    _head(ink, hx, hy, mood, talk, look, glow=glow and arms == "tablet", cheeks=cheeks, tilt=tilt, sweat=sweat)
    for f in after:
        f()


def _tablet_back(ink, cx, cy):
    ink.shape(K.dense(rect(cx - 104, cy - 65, 208, 130)), (60, 62, 70), 4.5)
    ink.stroke([(cx - 90, cy - 55), (cx - 50, cy - 55)], 2, (130, 134, 150), closed=False)
    ink.dot(cx + 80, cy - 50, 4, (30, 30, 34))


def _tablet_lap(ink, cx, cy):
    ink.shape([(cx - 110, cy), (cx + 100, cy - 6), (cx + 120, cy + 26), (cx - 96, cy + 32)], (60, 62, 70), 4)
    ink.fill([(cx - 96, cy + 6), (cx + 96, cy + 1), (cx + 108, cy + 22), (cx - 86, cy + 26)], (120, 170, 220), 1, off=(0, 0))


def channel_page(ink, x0, y0, w, h, subscribed=False, bell=False, press=0.0):
    """The tablet screen: the channel page with a big SUBSCRIBE button (drawn in screen units)."""
    k = w / 600.0
    ink.fill(K.dense(rect(x0, y0, w, h), 30), (250, 250, 250), 0.8, off=(0, 0))
    ink.fill(K.dense(rect(x0, y0, w, h * 0.3), 30), (92, 62, 44), 1, off=(0, 0))                    # banner
    cx, cy = x0 + w * 0.5, y0 + h * 0.15
    ink.shape(ell(cx, cy, 120 * k, 54 * k, n=30), (255, 255, 255), 3 * k)                             # the eye
    ink.dot(cx + 10 * k, cy, 34 * k, (120, 74, 40))
    ink.dot(cx + 10 * k, cy, 16 * k, INK)
    ink.dot(cx + 22 * k, cy - 12 * k, 8 * k, (255, 255, 255))
    ink.shape(ell(x0 + w * 0.16, y0 + h * 0.42, 52 * k, 52 * k, n=24), (92, 62, 44), 3 * k)            # avatar
    ink.dot(x0 + w * 0.16, y0 + h * 0.42, 18 * k, (255, 255, 255))
    ink.dot(x0 + w * 0.16 + 4 * k, y0 + h * 0.42, 9 * k, INK)
    _label(ink, "Bhess ki Eyes", x0 + w * 0.3, y0 + h * 0.37, int(46 * k), INK)
    _label(ink, "dark comedy, desi style", x0 + w * 0.3, y0 + h * 0.45, int(26 * k), (110, 110, 110))
    bw, bh = w * 0.62 * (1 - 0.06 * press), h * 0.15 * (1 - 0.1 * press)
    bx, by = x0 + (w - bw) / 2 - (w * 0.05 if bell else 0), y0 + h * 0.6 + h * 0.01 * press
    col = (230, 230, 230) if subscribed else (220, 30, 36)
    ink.shape(smooth(rect(bx, by, bw, bh), 3), col, 3.4 * k)
    _label(ink, "SUBSCRIBED" if subscribed else "SUBSCRIBE", bx + bw / 2, by + bh / 2, int(44 * k),
           (90, 90, 90) if subscribed else (255, 255, 255), centre=True)
    if bell:
        bx2, by2 = bx + bw + 30 * k, by + bh / 2
        ink.shape(smooth([(bx2, by2 - 34 * k), (bx2 + 26 * k, by2 + 14 * k), (bx2 + 34 * k, by2 + 24 * k), (bx2 - 34 * k, by2 + 24 * k),
                          (bx2 - 26 * k, by2 + 14 * k)], 4), (255, 214, 60), 3 * k)
        ink.dot(bx2, by2 + 32 * k, 8 * k, INK)


_FONTS = {}


def _font(size, bold=True):
    from ..core.text import font_file
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pg.font.Font(font_file("Poppins-ExtraBold" if bold else "Poppins-SemiBold"), max(8, size * K.S))
    return _FONTS[key]


def _label(ink, text, x, y, size, col, centre=False):
    s = _font(size).render(text, True, col)
    r = s.get_rect()
    if centre:
        r.center = (int(x * K.S), int(y * K.S))
    else:
        r.midleft = (int(x * K.S), int(y * K.S))
    ink.surf.blit(s, r)


def _tablet_front(ink, cx, cy, s=1.0, subscribed=False):
    w, h = 300 * s, 400 * s
    ink.shape(smooth(rect(cx - w / 2 - 14 * s, cy - h / 2 - 14 * s, w + 28 * s, h + 28 * s), 3), (60, 62, 70), 4)
    channel_page(ink, cx - w / 2, cy - h / 2, w, h, subscribed)


def _head(ink, hx, hy, mood, talk, look, glow=False, cheeks=0, tilt=0.0, sweat=0.0):
    ox, oy = hx, hy + 120                                         # roll about the neck

    def T(pts):
        return rot_about(pts, ox, oy, tilt) if tilt else pts

    R = 112
    for side in (-1, 1):
        ink.shape(T(ell(hx + side * 112, hy + 6, 30, 40, n=18)), SKIN_KID, 3.8)
    face = T(smooth([(hx - R, hy - 10), (hx - R * 0.8, hy - R * 0.85), (hx, hy - R * 1.02), (hx + R * 0.8, hy - R * 0.85),
                     (hx + R, hy - 10), (hx + R * 0.82, hy + R * 0.7), (hx, hy + R * 0.98), (hx - R * 0.82, hy + R * 0.7)], 8))
    lit = mix(SKIN_KID, (190, 220, 255), 0.18) if glow else SKIN_KID
    ink.shape(face, lit, 4.4, shade=dark(lit, 0.92),
              shade_pts=T(smooth([(hx + R * 0.55, hy + R * 0.55), (hx + R * 0.97, hy + R * 0.05), (hx + R * 0.86, hy + R * 0.62),
                                  (hx + R * 0.35, hy + R * 0.92)], 6)))
    ink.shape(T(smooth([(hx - R * 1.04, hy - 6), (hx - R * 0.95, hy - R * 0.8), (hx - R * 0.3, hy - R * 1.12), (hx + R * 0.5, hy - R * 1.1),
                        (hx + R * 1.0, hy - R * 0.7), (hx + R * 1.04, hy - 6), (hx + R * 0.9, hy - R * 0.42),
                        (hx + R * 0.1, hy - R * 0.6), (hx - R * 0.35, hy - R * 0.66), (hx - R * 0.92, hy - R * 0.36)], 8)), HAIR, 4)
    ink.stroke(T([(hx - R * 0.35, hy - R * 1.06), (hx - R * 0.42, hy - R * 0.7)]), 2.4, (120, 120, 130), closed=False)
    ink.stroke(T(smooth([(hx + R * 0.2, hy - R * 0.98), (hx + R * 0.7, hy - R * 0.82), (hx + R * 0.86, hy - R * 0.55)], 4, closed=False)),
               3, (110, 110, 124), closed=False)
    ink.dot(*T([(hx - R * 0.62, hy - R * 0.38)])[0], 11, INK)                                     # kala teeka
    lx, ly = look
    ey = hy - 4
    big = {"excited": 1.12, "curious": 1.0, "frozen": 1.25, "cry": 0.0, "sob": 0.9}.get(mood, 1.0)
    for side in (-1, 1):
        ex = hx + side * 44
        if mood == "cry":
            ink.stroke(T([(ex - side * 22, ey - 16), (ex + side * 12, ey), (ex - side * 22, ey + 14)]), 5, closed=False)
            continue
        ink.shape(T(ell(ex, ey, 30 * big, (36 if mood != "sob" else 26) * big, n=20)), (255, 255, 255), 3.6)
        pr = {"frozen": 5}.get(mood, 13)
        ink.dot(*T([(ex + lx * 10, ey + 4 + ly * 10)])[0], pr, INK)
        if mood != "frozen":
            ink.dot(*T([(ex + lx * 10 - 4, ey - 2 + ly * 10)])[0], 4, (255, 255, 255))
        if mood == "sob":                                                                           # wet lower lids
            ink.fill(T(ell(ex, ey + 22, 28, 9, n=14)), (150, 210, 250), 1, off=(0, 0))
        brow = {"excited": -0.25, "curious": 0.25 * side, "frozen": -0.4, "sob": 0.55}[mood]
        by = ey - 40 * big - 6
        ink.stroke(T([(ex - 26, by + 12 * brow * side), (ex + 26, by - 12 * brow * side)]), 7, closed=False)
    ink.stroke(T(smooth([(hx - 4, hy + 30), (hx + 10, hy + 40), (hx - 2, hy + 48)], 3, closed=False)), 3, closed=False)
    my = hy + 70
    if mood == "excited":
        o = 14 + 22 * talk
        ink.shape(T(smooth([(hx - 44, my - 10), (hx + 44, my - 10), (hx + 20, my + o), (hx - 20, my + o)], 6)), (120, 30, 40), 3.8)
        ink.fill(T(ell(hx, my + o * 0.6, 18, 9, n=14)), (236, 110, 120), 1, off=(0, 0))
    elif mood == "curious":
        ink.shape(T(ell(hx + 10, my, 10 + 8 * talk, 6 + 14 * talk, n=14)), (120, 30, 40), 3.4)
    elif mood == "frozen":
        ink.stroke(T(dense([(hx - 24, my), (hx + 24, my)], 8, closed=False)), 4, closed=False)
    elif mood in ("cry", "sob"):
        o = (34 + 22 * talk) if mood == "cry" else (10 + 22 * talk)
        ww = 50 if mood == "cry" else 34
        ink.shape(T(smooth([(hx - ww, my - 12), (hx + ww, my - 12), (hx + ww * 0.7, my + o), (hx - ww * 0.7, my + o)], 6)),
                  (110, 26, 36), 4)
        ink.fill(T(ell(hx, my + o * 0.65, ww * 0.5, 9, n=14)), (236, 110, 120), 1, off=(0, 0))
        if mood == "cry":
            for side in (-1, 1):                                                                   # tear fountains
                ink.shape(T(smooth([(hx + side * 40, hy), (hx + side * 120, hy - 50), (hx + side * 170, hy + 20),
                                    (hx + side * 96, hy + 26)], 6)), (150, 210, 250), 3)
        ink.fill(T(ell(hx - 8, hy + 52, 10, 7 + 3 * talk, n=10)), (200, 230, 250), 0.6, off=(0, 0))   # a snot bubble
    marks = [(1, 70), (-1, -70)][:cheeks]
    if marks:
        for _, cxo in marks:
            ink.fill(T(ell(hx + cxo, hy + 40, 30, 26, n=16)), (236, 70, 70), 2, off=(0, 0))
            for f in range(4):
                ink.fill(T(ell(hx + cxo - 22 + f * 15, hy + 8, 6, 18, n=10)), (236, 70, 70), 1, off=(0, 0))
    else:
        for side in (-1, 1):
            ink.hatch(T(ell(hx + side * 66, hy + 40, 22, 14, n=14)), (230, 90, 100), gap=7, w=1.8, angle=-0.6, alpha=170)
    if sweat > 0:
        sx, sy = hx + R * 0.9, hy - R * 0.5 + 40 * sweat
        ink.shape(T([(sx, sy - 34), (sx + 18, sy), (sx, sy + 16), (sx - 18, sy)]), (170, 220, 255), 3)


# ---------------------------------------------------------------- Mummy (maxi nightie, dupatta, bun, bindi)
def mummy(ink, x, y, mood="angry", talk=0.0, look=(0.0, 0.0), hand_at=None, karchi=True, vein=False, smear=False):
    """(x, y): her feet. Her left hand is on her hip; hand_at=(hx, hy) puts her right hand there (IK), else it
    holds the karchi up."""
    ink.shape(smooth([(x - 110, y), (x - 96, y - 300), (x - 100, y - 500), (x - 62, y - 560), (x + 62, y - 560),
                      (x + 100, y - 500), (x + 96, y - 300), (x + 120, y)], 6), NIGHTIE, 4.4,
              shade_pts=smooth([(x + 30, y - 520), (x + 100, y - 480), (x + 118, y - 10), (x + 50, y - 10)], 5))
    r = ink._rng()
    for i in range(40):
        ink.dot(x + r.uniform(-90, 90), y - r.uniform(20, 520), 5, (240, 200, 230))
    ink.shape(smooth([(x - 110, y - 4), (x + 120, y - 4), (x + 124, y + 10), (x - 114, y + 10)], 3), dark(NIGHTIE, 0.75), 3.6)
    for side in (-1, 1):
        ink.shape(ell(x + side * 46, y + 14, 40, 16, n=16), (100, 70, 60), 3.4)
    ink.shape(smooth([(x - 70, y - 556), (x + 10, y - 520), (x + 90, y - 380), (x + 70, y - 330), (x - 10, y - 470),
                      (x - 80, y - 520)], 6), DUPATTA, 4)
    limb(ink, [(x - 86, y - 520), (x - 178, y - 450), (x - 108, y - 386)], 26, SKIN_MUM)          # hand on hip
    hand(ink, x - 104, y - 384, 26, SKIN_MUM)
    sx, sy = x + 86, y - 520
    if hand_at is None:
        limb(ink, [(sx, sy), (x + 150, y - 430), (x + 150, y - 560)], 26, SKIN_MUM)
        if karchi:
            _ladle(ink, x + 150, y - 580)
        hand(ink, x + 150, y - 574, 28, SKIN_MUM)
        arm_after = None
    else:
        tx, ty = hand_at
        ex, ey = ik(sx, sy, tx, ty, 170, 170, bend=1 if tx > sx else -1)
        arm_after = (sx, sy, ex, ey, tx, ty)
    hx, hy = x, y - 680
    ink.shape(K.dense(rect(hx - 30, hy + 80, 60, 50)), SKIN_MUM, 3.6)
    ink.shape(ell(hx + 62, hy - 70, 56, 52, n=20), HAIR, 4)
    R = 100
    ink.shape(smooth([(hx - R, hy - 10), (hx - R * 0.8, hy - R * 0.9), (hx, hy - R * 1.04), (hx + R * 0.8, hy - R * 0.9),
                      (hx + R, hy - 10), (hx + R * 0.86, hy + R * 0.66), (hx, hy + R * 1.04), (hx - R * 0.86, hy + R * 0.66)], 8),
              SKIN_MUM, 4.4)
    ink.shape(smooth([(hx - R * 1.04, hy + 10), (hx - R * 0.98, hy - R * 0.8), (hx, hy - R * 1.12), (hx + R * 0.98, hy - R * 0.8),
                      (hx + R * 1.04, hy + 10), (hx + R * 0.84, hy - R * 0.5), (hx + 6, hy - R * 0.78),
                      (hx - R * 0.84, hy - R * 0.5)], 8), HAIR, 4)
    ink.stroke([(hx + 3, hy - R * 1.1), (hx + 4, hy - R * 0.8)], 4, (210, 30, 40), closed=False)
    ink.dot(hx, hy - 52, 9, (210, 30, 40))
    for side in (-1, 1):
        ink.dot(hx + side * 98, hy + 30, 8, (240, 200, 70))
    ex_y = hy - 2
    lx, ly = look
    for side in (-1, 1):
        ex = hx + side * 40
        if mood == "angry":
            ink.shape([(ex - 24, ex_y + 6 * side - 4), (ex + 24, ex_y - 6 * side - 4), (ex + 22, ex_y + 12), (ex - 22, ex_y + 12)],
                      (255, 255, 255), 3.4)
            ink.dot(ex + lx * 8, ex_y + 6 + ly * 6, 9, INK)
            ink.stroke([(ex - side * 30, ex_y - 40), (ex + side * 22, ex_y - 18)], 8, closed=False)
        else:                                                                                    # the stare
            ink.shape(ell(ex, ex_y, 30, 32, n=18), (255, 255, 255), 3.6)
            ink.dot(ex + lx * 8, ex_y + ly * 8, 4, INK)
            ink.stroke([(ex - side * 30, ex_y - 30), (ex + side * 24, ex_y - 46)], 8, closed=False)
    ink.stroke(smooth([(hx - 6, hy + 26), (hx + 8, hy + 40), (hx - 4, hy + 46)], 3, closed=False), 3, closed=False)
    my = hy + 66
    if talk > 0.05:
        ink.shape(smooth([(hx - 40, my - 6), (hx + 40, my - 6), (hx + 26, my + 12 + 26 * talk), (hx - 26, my + 12 + 26 * talk)], 6),
                  (110, 26, 36), 3.6)
        ink.fill(K.dense(rect(hx - 30, my - 4, 60, 8)), (255, 255, 255), 0.6, off=(0, 0))
    elif mood == "stare":
        ink.stroke(dense([(hx - 26, my + 4), (hx + 26, my + 4)], 8, closed=False), 5, closed=False)
    else:
        ink.stroke(smooth([(hx - 32, my + 8), (hx, my - 2), (hx + 32, my + 8)], 4, closed=False), 5, closed=False)
    ink.stroke(smooth([(hx - 40, hy + 120), (hx, hy + 190), (hx + 40, hy + 120)], 5, closed=False), 2.4, closed=False)
    ink.dot(hx, hy + 192, 7, (240, 200, 70))
    if vein:                                                                                     # the anime anger mark
        vx, vy = hx - 62, hy - 70
        for a in range(4):
            c, s = math.cos(a * math.pi / 2 + 0.6), math.sin(a * math.pi / 2 + 0.6)
            ink.stroke(smooth([(vx + 8 * c, vy + 8 * s), (vx + 22 * c - 6 * s, vy + 22 * s + 6 * c), (vx + 30 * c, vy + 30 * s)], 3,
                              closed=False), 5, (220, 40, 50), closed=False)
    if arm_after:
        sx, sy, ex, ey, tx, ty = arm_after
        if smear:                                                                                # motion smear behind the hand
            for k in range(3):
                ink.fill(ell(tx + (k + 1) * 46, ty + (k + 1) * 10, 36 - k * 8, 30 - k * 7, n=14), mix(SKIN_MUM, (255, 255, 255), 0.3 + 0.2 * k),
                         1, off=(0, 0))
        limb(ink, [(sx, sy), (ex, ey), (tx, ty)], 26, SKIN_MUM)
        ink.shape(ell(tx, ty, 40, 34, n=18), SKIN_MUM, 3.6)                                      # open palm
        for f in range(4):
            a = math.atan2(ty - ey, tx - ex) + (f - 1.5) * 0.3
            limb(ink, [(tx + 28 * math.cos(a), ty + 28 * math.sin(a)), (tx + 56 * math.cos(a), ty + 56 * math.sin(a))], 9, SKIN_MUM, w=2.4)


def _ladle(ink, x, y):
    """A steel karchi held up, bowl at the top."""
    limb(ink, [(x, y + 40), (x + 6, y - 150)], 7, (190, 194, 200), w=2.6)
    ink.shape(ell(x + 8, y - 176, 34, 26, n=16), (206, 210, 216), 3.4, shade_pts=ell(x + 8, y - 168, 26, 14, n=14))


# ---------------------------------------------------------------- effects
def speed_lines(ink, cx, cy, n=28, r0=380, r1=1400, col=INK, seed=0):
    r = ink._rng()
    for i in range(n):
        a = r.uniform(0, 2 * math.pi)
        rr = r.uniform(r0, r0 * 1.4)
        w = r.uniform(2, 6)
        ink.fill([(cx + rr * math.cos(a), cy + rr * math.sin(a)),
                  (cx + r1 * math.cos(a + 0.02), cy + r1 * math.sin(a + 0.02)),
                  (cx + r1 * math.cos(a - 0.02), cy + r1 * math.sin(a - 0.02))], col, 0.5, off=(0, 0))


def impact(ink, cx, cy, t):
    """A slap's impact frame: a jagged burst and spinning stars."""
    burst = [(cx + (150 if i % 2 == 0 else 70) * math.cos(i * math.pi / 8), cy + (150 if i % 2 == 0 else 70) * math.sin(i * math.pi / 8))
             for i in range(16)]
    ink.shape(burst, (255, 240, 120), 5)
    for k in range(5):
        a = k * 2 * math.pi / 5 + t * 6
        ink.shape(star(cx + 210 * math.cos(a), cy - 120 + 60 * math.sin(a), 30, rot=t * 4), (255, 214, 60), 3.4)


# ---------------------------------------------------------------- the timeline (stand-in voice timing)
FPS, BOIL = 30, 2                         # drawn on twos: 15 drawings a second, the hand-drawn look
KID_AT = (330, 1090)
MUM_DOOR = (860, 1250)
MUM_BED = (660, 1420)                     # at the bedside, in front of the bed
# (start, end, who, caption): when each line is spoken; the cartoon mouth flaps inside these windows
LINES = [
    (0.25, 2.75, "kid", "Mummyyy! Bhess ki aankh\ngaali hoti hai kya?"),
    (3.15, 4.05, "mummy", "Nahi hoti hai."),
    (4.65, 6.00, "kid", "Mummy... bhen k—"),
    (8.10, 8.80, "mummy", "HOTI HAI!"),
    (9.45, 10.25, "mummy", "HOTI HAI!!"),
    (11.00, 13.00, "kid", "AAAAAAN... AAN... AAAN!"),
    (13.25, 15.45, "kid", "Toh yeh... Bhess ki Eyes\nchannel kya hai?"),
    (16.35, 17.10, "mummy", "SUBSCRIBE KAR!"),
    (17.45, 18.25, "mummy", "KAR SUBSCRIBE!"),
]
SLAPS = [8.0, 9.3, 16.0]
SQUASH_END = 16.25                        # he peels off the glass: SUBSCRIBED
DING = [16.3, 19.9]
TOTAL = 21.0


def talking(t, who):
    for s, e, w, _ in LINES:
        if w == who and s <= t < e:
            u = t - s
            return 0.5 + 0.5 * abs(math.sin(u * 13.0 + 0.7 * math.sin(u * 5.1)))
    return 0.0


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def scene(t):
    """Draw the moment t (seconds) and return the camera for it."""
    big = K.canvas()
    ink = K.Ink(big, boil=int(t * FPS) // BOIL, seed=11)
    kx, ky = KID_AT
    kt, mt = talking(t, "kid"), talking(t, "mummy")
    shake = 0.0

    if t < 3.0:                                                         # 1. wide: the question
        room(ink)
        bed(ink)
        kid(ink, kx, ky, "excited", kt, look=(0.6, -0.2), bob=abs(math.sin(t * 9)) * 10)
        mummy(ink, *MUM_DOOR, mood="angry", look=(-0.8, 0.3))
        cam = (lerp(560, 430, ease(t / 3.0)), lerp(860, 820, ease(t / 3.0)), lerp(1.12, 1.45, ease(t / 3.0)))
    elif t < 4.4:                                                       # 2. Mummy, flat: "nahi hoti hai"
        room(ink)
        bed(ink)
        kid(ink, kx, ky, "excited", 0.0, look=(0.8, 0.0))
        mummy(ink, *MUM_DOOR, mood="angry", talk=mt, look=(-0.4, 0.5))
        cam = (850, 760, 1.9)
    elif t < 6.0:                                                       # 3. the kid, curious: "mummy... bhen k-"
        room(ink)
        bed(ink)
        kid(ink, kx, ky, "curious", kt, look=(0.4, -0.6), arms="chin")
        cam = (kx + 20, ky - 300, lerp(2.0, 2.3, ease((t - 4.4) / 1.6)))
    elif t < 7.0:                                                       # 4. silence: Mummy's eyes (snap zoom)
        room(ink)
        mummy(ink, *MUM_DOOR, mood="stare", look=(-1, 0))
        z = 2.6 if t < 6.08 else 4.2
        cam = (860, 1250 - 682, z)
    elif t < 7.6:                                                       # 5. the kid's pupils shrink, sweat
        room(ink)
        bed(ink)
        kid(ink, kx, ky, "frozen", 0.0, arms="chin", sweat=ease((t - 7.0) / 0.6))
        cam = (kx, ky - 340, 3.0)
    elif t < 8.0:                                                       # 6. whoosh: she's at the bed, hand up
        room(ink)
        bed(ink)
        speed_lines(ink, 600, 900, col=(200, 200, 200))
        kid(ink, kx, ky, "frozen", 0.0, arms="stiff", look=(1, 0))
        mummy(ink, *MUM_BED, mood="angry", hand_at=(MUM_BED[0] + 210, MUM_BED[1] - 900), vein=True, karchi=False)
        cam = (520, 900, 1.5)
    elif t < 10.6:                                                      # 7-8. two slaps: forehand, backhand
        room(ink)
        bed(ink)
        second = t >= 9.3
        s0 = 9.3 if second else 8.0
        u = t - s0
        hit = u < 0.12
        cheeks = 2 if second and u > 0.05 else 1 if (second or u > 0.05) else 0
        tilt = (0.42 if not second else -0.42) * math.exp(-max(0.0, u - 0.05) * 3) * (1 if u > 0.04 else 0)
        tilt += (0.12 if second else 0) if u <= 0.04 else 0
        kid(ink, kx, ky, "frozen", 0.0, arms="stiff", tilt=tilt, cheeks=cheeks, look=(-1 if not second else 1, 0))
        if u < 0.06:                                                    # the swing
            hand_at = (kx + 170, ky - 330) if not second else (kx - 60, ky - 360)
            smear = True
        elif u < 0.5:                                                   # follow-through
            hand_at = (kx - 150, ky - 300) if not second else (kx + 280, ky - 420)
            smear = False
        else:                                                           # wind back up, finger-wag while talking
            hand_at = (MUM_BED[0] + 200, MUM_BED[1] - 880 + 20 * math.sin(t * 20))
            smear = False
        if t >= 10.25:
            hand_at = (MUM_BED[0] + 150, MUM_BED[1] - 600)
        mummy(ink, *MUM_BED, mood="angry", talk=mt, hand_at=hand_at, smear=smear, vein=True, karchi=False, look=(-1, 0.4))
        if hit:
            impact(ink, kx + (110 if not second else -110), ky - 330, u)
            shake = 18
        cam = (500, 850, 1.55)
    elif t < 13.2:                                                      # 9-10. stunned, then the wail
        room(ink)
        bed(ink)
        if t < 11.0:
            kid(ink, kx, ky, "frozen", 0.0, arms="stiff", cheeks=2)
            cam = (kx, ky - 320, 2.2)
        else:
            kid(ink, kx, ky, "cry", kt, arms="cry", cheeks=2, tilt=0.06 * math.sin(t * 14), bob=6 * abs(math.sin(t * 11)))
            cam = (kx, ky - 300, 2.0)
            shake = 4
    elif t < 15.9:                                                      # 11. sobbing, he shows her the channel
        room(ink)
        bed(ink)
        windup = t >= 15.5
        kid(ink, kx, ky, "sob", kt, arms="tablet" if windup else "show", cheeks=2, look=(0.0, 0.6) if windup else (0.8, 0),
            bob=4 * abs(math.sin(t * 7)))
        mummy(ink, *MUM_BED, mood="angry", look=(-1, 0.2), karchi=False, vein=windup,
              hand_at=(kx + 80, ky - 640) if windup else (MUM_BED[0] + 150, MUM_BED[1] - 600))
        cam = (480, 820, 1.6)
    elif t < 18.5:                                                      # 12-13. SLAP: his nose lands on SUBSCRIBE
        cam = (540, 960, 1.0)
        tablet_closeup(ink, t)
        if t < 16.12:
            shake = 16
    else:                                                               # 14. she's gone; he taps the bell too
        room(ink, door_light=1.0)
        bed(ink)
        kid(ink, kx, ky, "sob", 0.15 * abs(math.sin(t * 6)), arms="tablet", cheeks=2, look=(0.0, 0.7))
        if t >= DING[1]:                                                # he taps the bell too
            u = ease((t - DING[1]) / 0.15)
            bx, by, r = kx + 200, ky - 430 - 40 * u, 50 * u
            ink.shape(smooth([(bx, by - r), (bx + r * 0.75, by + r * 0.4), (bx + r, by + r * 0.7), (bx - r, by + r * 0.7),
                              (bx - r * 0.75, by + r * 0.4)], 4), (255, 214, 60), 4)
            ink.dot(bx, by + r * 0.95, r * 0.22, INK)
            for a in (-0.5, 0.5):
                ink.stroke([(bx + math.copysign(r * 1.2, a), by - r * 0.4), (bx + math.copysign(r * 1.6, a), by - r * 0.7)], 4,
                           closed=False)
        cam = (lerp(470, 540, ease((t - 18.5) / 2.5)), lerp(840, 900, ease((t - 18.5) / 2.5)), lerp(1.7, 1.35, ease((t - 18.5) / 2.5)))
    if shake:
        r = ink._rng()
        cam = (cam[0] + r.uniform(-shake, shake), cam[1] + r.uniform(-shake, shake), cam[2])
    return big, cam


def tablet_closeup(ink, t):
    """The tablet fills the frame: the kid's face squashed onto it, his nose pressing SUBSCRIBE."""
    ink.fill(K.dense(rect(-20, -20, 1120, 1960)), (232, 214, 190), 2, off=(0, 0))
    ink.shape(smooth(rect(70, 260, 940, 1300), 3), (52, 54, 62), 6)
    subscribed = t >= SQUASH_END
    channel_page(ink, 110, 300, 860, 1220, subscribed=subscribed, bell=True)
    bx, by = 540 - 43, 300 + 1220 * 0.6 + 1220 * 0.075                  # the button's centre
    if t < SQUASH_END:                                                  # his face flat on the glass, nose on the button
        k = lerp(0.75, 1.0, ease((t - 16.0) / 0.06))
        _squash_face(ink, bx, by, k)
        if t < 16.08:
            speed_lines(ink, bx, by, n=36, r0=520, col=(255, 255, 255))
    else:                                                               # the greasy nose print left behind
        lay = pg.Surface(ink.surf.get_size(), pg.SRCALPHA)
        for i, (rx, ry, a) in enumerate(((70, 52, 50), (54, 38, 40), (34, 24, 60))):
            pg.draw.ellipse(lay, (200, 190, 170, a), pg.Rect((bx - rx) * K.S, (by - 60 - ry) * K.S, 2 * rx * K.S, 2 * ry * K.S),
                            0 if i == 2 else 5 * K.S)
        for side in (-1, 1):
            pg.draw.ellipse(lay, (200, 190, 170, 45), pg.Rect((bx + side * 60 - 14) * K.S, (by - 30) * K.S, 28 * K.S, 20 * K.S))
        ink.surf.blit(lay, (0, 0))
    if subscribed and t < 16.9:
        for k in range(6):                                                                       # sparkles
            a = k * math.pi / 3 + t * 3
            ink.shape(star(540 + 330 * math.cos(a), 1100 + 130 * math.sin(a), 22), (255, 214, 60), 3)
    if t >= 16.9:                                                       # Mummy's finger over the top: "kar subscribe!"
        wag = 30 * math.sin(t * 22)
        fx = 820 + wag
        limb(ink, [(1200, 120), (fx + 60, 160), (fx, 220)], 30, SKIN_MUM)
        limb(ink, [(fx - 4, 216), (fx - 50, 250)], 12, SKIN_MUM, w=3)


def _squash_face(ink, nx, ny, k=1.0):
    """Seen through the glass: his face flattened on the screen, nose (nx, ny) on the button, eyes clenched."""
    cx, cy = nx, ny + 40 * k

    def P(pts):
        return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in pts]
    ink.shape(P(ell(cx, cy, 430, 400, n=48)), mix(SKIN_KID, (255, 255, 255), 0.08), 6)
    ink.shape(P(smooth([(cx - 440, cy - 120), (cx - 300, cy - 400), (cx, cy - 470), (cx + 300, cy - 400), (cx + 440, cy - 120),
                        (cx + 300, cy - 300), (cx, cy - 330), (cx - 300, cy - 300)], 8)), HAIR, 5)
    for side in (-1, 1):
        ex = cx + side * 170
        ink.stroke(P([(ex - side * 70, cy - 170), (ex + side * 30, cy - 125), (ex - side * 70, cy - 80)]), 10, closed=False)
        ink.stroke(P([(ex - 70, cy - 236 - side * 6), (ex + 70, cy - 236 + side * 6)]), 9, closed=False)
        ink.fill(P(ell(cx + side * 270, cy + 40, 90, 70, n=18)), (236, 70, 70), 2, off=(0, 0))       # both slap marks
        ink.fill(P(ell(cx + side * 330, cy - 40, 34, 70, n=14)), (150, 210, 250), 2, off=(0, 0))      # tears
    ink.shape(P(ell(cx, cy - 40, 110, 80, n=24)), mix(SKIN_KID, (255, 230, 220), 0.35), 5)          # flattened nose
    for side in (-1, 1):
        ink.dot(*P([(cx + side * 34, cy - 30)])[0], 13 * k, dark(SKIN_KID, 0.55))
    ink.shape(P(smooth([(cx - 150, cy + 150), (cx + 150, cy + 140), (cx + 90, cy + 220), (cx - 100, cy + 226)], 5)), (110, 26, 36), 5)


# ---------------------------------------------------------------- captions, sound, render
def caption(img, t):
    from ..core.text import outlined
    for s, e, who, text in LINES:
        if s - 0.05 <= t < e + 0.35:
            col = (255, 236, 90) if who == "kid" else (255, 255, 255)
            fnt = pg.font.Font(_font_path(), 66 if "\n" in text else 78)
            y = 1360
            for ln in text.split("\n"):
                s_ = outlined(pg, fnt, ln, col, outline=7, outline_colour=(30, 20, 24))
                img.blit(s_, s_.get_rect(midtop=(540, y)))
                y += s_.get_height() - 8


def _font_path():
    from ..core.text import font_file
    return font_file("Poppins-ExtraBold")


def soundtrack(path: Path):
    import numpy as np
    from ..core.audio import SR, sample, whoosh, write_wav
    from ..core.music import compose
    from .positive_bhai_3d import boing, chan, crickets, tok, slide_whistle, wah
    n = int(SR * TOTAL)
    mixb = np.zeros(n, np.float32)

    def put(t, x, level=1.0):
        a = int(t * SR)
        b = min(n, a + len(x))
        if b > a:
            mixb[a:b] += x[:b - a] * level

    def fade(x, fin=0.02, fout=0.05):
        x = x.copy()
        a, b = int(fin * SR), int(fout * SR)
        if a:
            x[:a] *= np.linspace(0, 1, a)
        if b:
            x[-b:] *= np.linspace(1, 0, b)
        return x

    bouncy = compose(7.0, 17, "upbeat")
    put(0.0, fade(bouncy[:int(6.0 * SR)], 0.05, 0.004), 0.32)                 # dead stop at "bhen k-"
    put(6.0, sample("scratch", 0.5))
    put(6.05, crickets(1.5, 0.14))
    creak = np.sin(2 * np.pi * np.cumsum(np.full(int(0.5 * SR), 1.0) * (300 + 60 * np.sin(np.linspace(0, 6, int(0.5 * SR))))) / SR)
    put(6.25, (creak * np.hanning(len(creak)) * 0.08).astype(np.float32))       # the fan creaks
    put(7.25, boing(0.35, 0.25))                                               # gulp
    put(7.6, whoosh(0.4, 300, 4000, 0.6, seed=3))
    for s in SLAPS:
        crack = np.random.default_rng(int(s * 10)).uniform(-1, 1, int(0.09 * SR)).astype(np.float32)
        crack = np.diff(crack, prepend=0) * np.exp(-np.arange(len(crack)) / (0.015 * SR))
        put(s, crack, 0.9)
        put(s, sample("punch_heavy", 0.6))
        put(s - 0.08, whoosh(0.12, 800, 6000, 0.4, seed=int(s)))
        put(s + 0.05, chan(0.18))
    put(10.4, tok(0.5))
    put(11.0, wah(0.18))
    tense = compose(3.0, 5, "tense")
    put(13.2, fade(tense[:int(2.8 * SR)], 0.3, 0.05), 0.22)
    put(DING[0], sample("bell", 0.55))
    put(DING[0], sample("sparkle", 0.35))
    end = compose(5.0, 23, "upbeat")
    put(16.3, fade(end[:int(4.7 * SR)], 0.1, 1.2), 0.3)
    put(DING[1], sample("bell", 0.4))
    put(18.6, slide_whistle(0.45, 0.12, up=False))
    peak = float(np.abs(mixb).max()) or 1.0
    write_wav((mixb / max(peak, 1.0) * 0.95 * 32767).astype(np.int16) if mixb.dtype != np.int16 else mixb, str(path))


def render(stills=None):
    import subprocess
    pg.init()
    OUT.mkdir(parents=True, exist_ok=True)
    if stills:
        for t in stills:
            big, cam = scene(t)
            img = K.finish(big, cam=cam)
            caption(img, t)
            pg.image.save(img, str(OUT / f"still_{t:05.2f}.png"))
            print(OUT / f"still_{t:05.2f}.png")
        return
    wav = OUT / "sound.wav"
    soundtrack(wav)
    final = OUT / "bhess_gaali_novoice.mp4"
    proc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{K.W}x{K.H}",
                             "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
                             str(final)], stdin=subprocess.PIPE)
    frames = int(TOTAL * FPS)
    held = None
    for f in range(frames):
        t = f / FPS
        if f % BOIL == 0 or held is None:
            big, cam = scene(t)
            img = K.finish(big, cam=cam)
            held = img
        img = held.copy()
        caption(img, t)
        proc.stdin.write(pg.image.tobytes(img, "RGB"))
        if f % 60 == 0:
            print(f"frame {f}/{frames}", flush=True)
    proc.stdin.close()
    proc.wait()
    print(final.resolve())
    return final


def style_frame(path: Path):
    pg.init()
    big = K.canvas()
    ink = K.Ink(big, boil=0, seed=11)
    room(ink)
    bed(ink)
    kid(ink, 330, 1090, mood="excited", talk=0.6, look=(0.6, -0.3))
    mummy(ink, 860, 1250, mood="angry", look=(-0.8, 0.2))
    img = K.finish(big, cam=(560, 860, 1.12))
    path.parent.mkdir(parents=True, exist_ok=True)
    pg.image.save(img, str(path))
    print(path.resolve())


if __name__ == "__main__":
    if "--still" in sys.argv:
        render([float(a) for a in sys.argv[sys.argv.index("--still") + 1:]])
    elif "--style" in sys.argv:
        style_frame(OUT / "style.png")
    else:
        render()
