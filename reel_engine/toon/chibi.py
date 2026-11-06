"""Chibi: the vector look the user picked on 2026-11-06 (big heads, big shiny eyes, gradients, soft shadows),
plus the other looks from the same style test. Characters are animatable: they talk, blink, gesture,
breathe and catch the wind, and a camera (scale and offset) can zoom on anyone with no loss of sharpness.

    python -m reel_engine.toon.chibi        the style test sheet (out/<date>/toon_styles/sheet.png)

Everything is drawn in code at 2x (Z) and scaled down. Coordinates are "world" units: a character's feet
stand on FEET, and a Painter maps world units to pixels through its camera (k, ox, oy).
"""
import math
import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

PW, PH, Z = 1000, 860, 2          # style-sheet panel size (1x) and supersampling
FEET = 800
_K = 1.0                          # the camera scale of the fill in progress (patterns read it)


# ------------------------------------------------------------------ geometry and colour helpers
def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def dark(c, k=0.75):
    return tuple(int(v * k) for v in c)


def light(c, k=0.25):
    return mix(c, (255, 255, 255), k)


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def ell(cx, cy, rx, ry, n=72, a0=0.0, a1=2 * math.pi, rot=0.0):
    pts = []
    for k in range(n):
        a = a0 + (a1 - a0) * k / n
        dx, dy = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + dx * math.cos(rot) - dy * math.sin(rot), cy + dx * math.sin(rot) + dy * math.cos(rot)))
    return pts


def spline(ctrl, n=10, closed=True):
    """Catmull-Rom through the control points: smooth, organic outlines from a handful of points."""
    out, m = [], len(ctrl)
    for i in range(m if closed else m - 1):
        p0 = ctrl[(i - 1) % m] if closed else ctrl[max(i - 1, 0)]
        p1, p2 = ctrl[i], ctrl[(i + 1) % m]
        p3 = ctrl[(i + 2) % m] if closed else ctrl[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(ctrl[-1])
    return out


def reach(s, h, side, l1, l2, bend="out"):
    """Two-bone arm: the hand goes as far toward h as the arm allows; the elbow bows outward (side), or
    down toward the body for talking gestures (bend="down")."""
    dx, dy = h[0] - s[0], h[1] - s[1]
    d = math.hypot(dx, dy) or 1.0
    if d > (l1 + l2) * 0.98:
        k = (l1 + l2) * 0.98 / d
        dx, dy, d = dx * k, dy * k, (l1 + l2) * 0.98
        h = (s[0] + dx, s[1] + dy)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    hh = math.sqrt(max(0.0, l1 * l1 - a * a))
    mx, my = s[0] + dx * a / d, s[1] + dy * a / d
    nx, ny = -dy / d, dx / d
    if (bend == "down" and ny < 0) or (bend != "down" and nx * side < 0):
        nx, ny = -nx, -ny
    return (mx + nx * hh, my + ny * hh), h


@dataclass
class Style:
    name: str
    ink: tuple = None                # outline colour; None = a darker shade of each fill
    ink_w: float = 3.0
    grad: bool = False               # vertical gradient inside each fill
    shade: float = 0.0               # strength of the lower-right shadow crescent (0 = none)
    eyes: str = "big"                # big, small, almond
    bg: tuple = (250, 246, 240)
    hr: float = 60                   # head radius
    m_torso: float = 150
    m_legs: float = 200
    f_torso: float = 140
    f_skirt: float = 260
    neck: float = 12
    shoulder: float = 1.05           # shoulder half-width, in head radii
    limb: float = 24                 # arm thickness
    blush: float = 0.0
    saree: tuple = (200, 40, 110)
    border: tuple = (236, 182, 60)
    blouse: tuple = (40, 140, 80)
    motif: str = "dots"
    skin: dict = field(default_factory=lambda: {"dost": (236, 190, 150), "bhai": (205, 150, 105), "aunty": (222, 164, 118)})


@dataclass
class Act:
    """What a character is doing this frame."""
    t: float = 0.0
    talk: float = 0.0                # mouth opening, 0..1 (from the voice's loudness)
    gesture: float = 0.0             # 0 idle pose .. 1 talking gestures
    blink: bool = False
    look: float = 0.0                # -1 left .. 1 right
    wind: float = 0.0                # breeze strength, 0..1
    mood: str = "happy"              # happy, goofy, laugh, shock
    arm_r: tuple = None              # (from pose, to pose, progress 0..1); None = the character's idle pose
    arm_l: tuple = None
    walk: float = 0.0                # stride phase while walking (0 = standing)


class Painter:
    def __init__(self, pg, surf, st: Style, seed=1, k=1.0, ox=0.0, oy=0.0):
        self.pg, self.surf, self.st = pg, surf, st
        self.rng = random.Random(seed)
        self.k, self.ox, self.oy = k, ox, oy

    def z(self, p):
        return (self.ox + p[0] * Z * self.k, self.oy + p[1] * Z * self.k)

    def stroke(self, pts, w, col, closed=True):
        pg = self.pg
        zp = [self.z(p) for p in pts]
        ww = w * Z * self.k
        if len(zp) < 2 or ww <= 0:
            return
        pg.draw.lines(self.surf, col, closed, zp, max(1, int(ww)))
        if ww >= 3:
            for p in zp:
                pg.draw.circle(self.surf, col, p, ww / 2)

    def fill(self, pts, col, shade=True, pattern=None, ink=True, grad=None, alpha=255):
        """A filled shape in this style: gradient or flat, a shadow crescent, an optional pattern, an outline."""
        global _K
        pg, st = self.pg, self.st
        zp = [self.z(p) for p in pts]
        xs, ys = [p[0] for p in zp], [p[1] for p in zp]
        sw, sh_ = self.surf.get_size()
        if max(xs) < 0 or min(xs) > sw or max(ys) < 0 or min(ys) > sh_:
            return                                                        # off camera
        rect = pg.Rect(int(min(xs)) - 2, int(min(ys)) - 2, int(max(xs) - min(xs)) + 6, int(max(ys) - min(ys)) + 6)
        loc = [(x - rect.x, y - rect.y) for x, y in zp]
        layer = pg.Surface(rect.size, pg.SRCALPHA)
        if grad if grad is not None else st.grad:
            for row in range(0, rect.height, 2):
                pg.draw.rect(layer, mix(light(col, 0.2), dark(col, 0.9), row / max(1, rect.height)) + (alpha,), (0, row, rect.width, 2))
        else:
            layer.fill(col + (alpha,))
        if pattern:
            _K = self.k
            pattern(layer)
        if shade and st.shade:
            sh = pg.Surface(rect.size, pg.SRCALPHA)
            sh.fill(dark(col, 0.72) + (int(255 * st.shade),))
            pg.draw.polygon(sh, (0, 0, 0, 0), [(x - rect.width * 0.12, y - rect.height * 0.06) for x, y in loc])
            layer.blit(sh, (0, 0))
        m = pg.Surface(rect.size, pg.SRCALPHA)
        pg.draw.polygon(m, (255, 255, 255, 255), loc)
        a = pg.surfarray.pixels_alpha(layer)
        np.minimum(a, pg.surfarray.pixels_alpha(m), out=a)
        del a
        self.surf.blit(layer, rect)
        if ink and st.ink_w:
            self.stroke(pts, st.ink_w, st.ink or dark(col, 0.5))

    def oval(self, c, rx, ry, col, **kw):
        self.fill(ell(c[0], c[1], rx, ry), col, **kw)

    def limb(self, pts, w, col):
        """An arm or leg: an outlined tube along the points."""
        ink = self.st.ink or dark(col, 0.5)
        if self.st.ink_w:
            self.stroke(pts, w + self.st.ink_w * 2, ink, closed=False)
        self.stroke(pts, w, col, closed=False)
        if self.st.shade:
            self.stroke([(x + w * 0.22, y) for x, y in pts], w * 0.35, dark(col, 0.85), closed=False)

    def dot(self, c, r, col):
        self.pg.draw.circle(self.surf, col, self.z(c), r * Z * self.k)

    def arc(self, c, rx, ry, a0, a1, w, col):
        self.stroke(ell(c[0], c[1], rx, ry, 24, a0, a1), w, col, closed=False)

    def glow(self, c, rx, ry, col, a):
        pg = self.pg
        g = pg.Surface((max(2, int(rx * 2 * Z * self.k)), max(2, int(ry * 2 * Z * self.k))), pg.SRCALPHA)
        pg.draw.ellipse(g, col + (a,), g.get_rect())
        self.surf.blit(g, g.get_rect(center=self.z(c)))


# ------------------------------------------------------------------ patterns
def motif(kind, col, step=34):
    def draw(layer):
        import pygame as pg
        w, h = layer.get_size()
        s = max(4, int(step * Z * _K))
        r = max(1, int(3 * Z * _K))
        for j, y in enumerate(range(0, h, s)):
            for x in range((j % 2) * s // 2, w, s):
                if kind == "dots":
                    pg.draw.circle(layer, col + (255,), (x, y), r)
                else:                                                     # four-petal flower buti
                    for a in range(4):
                        pg.draw.circle(layer, col + (255,), (x + int(5 * Z * _K * math.cos(a * math.pi / 2)),
                                                              y + int(5 * Z * _K * math.sin(a * math.pi / 2))), r)
                    pg.draw.circle(layer, dark(col, 0.7) + (255,), (x, y), max(1, int(2 * Z * _K)))
    return draw


# ------------------------------------------------------------------ faces
def eyes(p, st, x, ey, hr, act: Act, lady=False, brow=(50, 30, 24)):
    gap = hr * 0.38
    look = act.look
    for side in (-1, 1):
        cx = x + side * gap
        r = hr * (0.24 if st.eyes == "big" else 0.11 if st.eyes == "small" else 0.2)
        lash = 4 if lady else 3
        if act.mood == "dead":                                            # + +, the cartoon way
            for dx, dy in ((r * 0.7, 0), (0, r * 0.7)):
                p.stroke([(cx - dx, ey - dy), (cx + dx, ey + dy)], lash + 2, (40, 24, 20), closed=False)
        elif act.mood == "laugh":                                         # ^ ^
            p.arc((cx, ey + r * 0.4), r * 0.8, r * 0.7, math.pi * 1.1, math.pi * 1.9, lash + 1, (40, 24, 20))
        elif act.blink:                                                   # a closed lid: a soft downward curve
            p.arc((cx, ey - r * 0.1), r * 0.85, r * 0.5, math.pi * 0.1, math.pi * 0.9, lash + 1, (40, 24, 20))
            if lady:
                p.stroke([(cx + side * r * 0.8, ey), (cx + side * r * 1.05, ey - r * 0.15)], 3, (40, 24, 20), closed=False)
        elif st.eyes == "big":
            wide = 1.15 if act.mood == "shock" else 1.0
            p.oval((cx, ey), r * 0.85 * wide, r * wide, (255, 255, 255), shade=False, grad=False)
            p.oval((cx + look * r * 0.25, ey + r * 0.15), r * 0.62, r * 0.75, (110, 64, 34), shade=False, grad=True, ink=False)
            p.dot((cx + look * r * 0.25, ey + r * 0.18), r * 0.36, (30, 18, 14))
            p.dot((cx + look * r * 0.25 - r * 0.25, ey - r * 0.12), r * 0.2, (255, 255, 255))
            p.dot((cx + look * r * 0.25 + r * 0.2, ey + r * 0.35), r * 0.1, (255, 255, 255))
            p.arc((cx, ey + 2), r * 0.95, r * 1.08, math.pi * 1.05, math.pi * 1.95, lash, (40, 24, 20))
            if lady:
                p.stroke([(cx + side * r * 0.85, ey - r * 0.55), (cx + side * r * 1.15, ey - r * 0.8)], 3, (40, 24, 20), closed=False)
        elif st.eyes == "small":
            p.oval((cx, ey), r * 0.8, r, (50, 30, 26), shade=False, grad=False, ink=False)
            p.dot((cx - r * 0.25, ey - r * 0.3), r * 0.25, (255, 255, 255))
            if lady:
                p.stroke([(cx + side * r * 0.7, ey - r * 0.7), (cx + side * r * 1.5, ey - r * 1.3)], 2.5, (50, 30, 26), closed=False)
        else:                                                             # almond
            alm = [(cx - r * 1.1, ey), (cx - r * 0.4, ey - r * 0.6), (cx + r * 0.4, ey - r * 0.6), (cx + r * 1.1, ey),
                   (cx + r * 0.4, ey + r * 0.45), (cx - r * 0.4, ey + r * 0.45)]
            p.fill(spline(alm, 6), (255, 255, 255), shade=False, grad=False)
            p.dot((cx + look * r * 0.3, ey - r * 0.02), r * 0.5, (96, 58, 34))
            p.dot((cx + look * r * 0.3, ey - r * 0.02), r * 0.26, (20, 14, 10))
            p.dot((cx + look * r * 0.3 - r * 0.18, ey - r * 0.2), r * 0.12, (255, 255, 255))
            p.stroke(spline(alm, 6)[: len(alm) * 6 // 2 + 1], st.ink_w * 0.9 + 1, (20, 20, 20), closed=False)
        brow_y = ey - hr * (0.34 if st.eyes == "big" else 0.28)
        lift = hr * ((0.1 if act.mood in ("goofy", "shock") else 0.0) + 0.06 * act.talk)
        inner = {"sad": -0.1, "angry": 0.12}.get(act.mood, 0.0) * hr   # sad: inner ends up; angry: down
        p.stroke(spline([(cx - side * hr * 0.14, brow_y - lift + hr * 0.02 + inner), (cx + side * hr * 0.0, brow_y - lift - hr * 0.06 + inner * 0.3),
                         (cx + side * hr * 0.17, brow_y - lift + hr * 0.01 - inner * 0.4)], 6, closed=False),
                 3 if lady else 4.5, brow, closed=False)


def mouth(p, st, x, my, hr, kind, talk=0.0, mood="happy"):
    if mood == "dead":                                                    # no smile: a flat line
        p.stroke([(x - hr * 0.16, my + hr * 0.08), (x + hr * 0.16, my + hr * 0.08)], 4.5, (110, 40, 40), closed=False)
        return
    if mood in ("sad", "angry") and talk < 0.15:                          # a frown
        p.arc((x, my + hr * 0.16), hr * 0.18, hr * 0.11, math.pi * 1.15, math.pi * 1.85, 4.5, (110, 40, 40))
        return
    if mood == "shock" and talk < 0.3:                                    # a little "o"
        p.oval((x, my + hr * 0.08), hr * 0.11, hr * 0.15, (150, 40, 50), shade=False, grad=False)
        return
    if kind == "lady" and talk < 0.12 and mood != "laugh":
        lips = [(x - hr * 0.2, my), (x, my + hr * 0.02), (x + hr * 0.2, my), (x + hr * 0.1, my + hr * 0.13), (x - hr * 0.1, my + hr * 0.13)]
        p.fill(spline(lips, 6), (196, 50, 70), shade=False)
        p.stroke([(x - hr * 0.16, my + hr * 0.03), (x + hr * 0.16, my + hr * 0.03)], 2, (255, 236, 236), closed=False)
        return
    open_ = max(talk, 0.7 if mood == "laugh" else 0.0)
    w = hr * (0.34 if kind == "grin" else 0.24 if kind == "lady" else 0.28)
    h = hr * (0.24 if kind == "grin" else 0.18) * (0.55 + 0.9 * open_)
    if mood in ("sad", "angry", "shock"):
        w, h = w * 0.7, h * 0.85
    d = [(x + math.cos(a) * w, my + math.sin(a) * h) for a in [math.pi * k / 20 for k in range(21)]]
    p.fill(d, (150, 40, 50), shade=False, grad=False, ink=True)
    if kind == "lady":
        p.stroke(d, 3, (196, 50, 70))
    p.fill([(x - w * 0.8, my), (x + w * 0.8, my), (x + w * 0.7, my + h * 0.3), (x - w * 0.7, my + h * 0.3)], (255, 255, 255),
           shade=False, grad=False, ink=False)
    p.fill(ell(x, my + h * 0.72, w * 0.45, h * 0.28), (236, 110, 110), shade=False, grad=False, ink=False)
    if kind == "grin":                                                    # the Dost's buck teeth
        for side in (-1, 1):
            p.fill([(x, my - 2), (x + side * w * 0.3, my - 2), (x + side * w * 0.3, my + hr * 0.12), (x, my + hr * 0.12)],
                   (255, 255, 255), shade=False, grad=False)


def cheeks(p, st, x, cy, hr):
    if st.blush:
        for side in (-1, 1):
            p.glow((x + side * hr * 0.55, cy), hr * 0.25, hr * 0.13, (240, 100, 110), int(140 * st.blush))


# ------------------------------------------------------------------ hands and arm poses
def backout(u):
    """0 -> 1 with a small overshoot and settle: a hand arriving at a pose."""
    u = max(0.0, min(1.0, u))
    c = 1.3
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


POSES = {   # where the hand goes, from the shoulder in head radii (x outward from the body), and its shape
    "rest": (0.22, 1.7, "relaxed"),
    "explain": (0.7, 0.5, "open"),
    "present": (1.15, 0.1, "open"),
    "shrug": (1.0, 0.3, "open"),
    "point": (1.4, 0.05, "point"),
    "chest": (-0.55, 0.62, "relaxed"),
    "up": (0.85, -0.8, "open"),
    "thumb": (0.8, -0.5, "thumb"),
    "hold": (-0.2, 1.0, "fist"),                      # both hands on something carried in front
}


def pose_at(name, side, s, head, hr, hip_pt, t):
    if name == "scratch":                                                 # fingers rubbing the side of the head
        return (head[0] + side * hr * 0.8 + math.sin(t * 13) * hr * 0.04, head[1] - hr * 0.5 + math.cos(t * 13) * hr * 0.03), "relaxed"
    if name == "hip":
        return hip_pt, "fist"
    if name == "wipe":                                                    # wiping tears under the eye
        return (head[0] + side * hr * 0.42 + math.sin(t * 9) * hr * 0.05, head[1] + hr * 0.18), "relaxed"
    if name == "phone":                                                   # a phone at the ear
        return (head[0] + side * hr * 0.98, head[1] + hr * 0.18), "fist"
    dx, dy, kind = POSES[name]
    return (s[0] + side * dx * hr, s[1] + dy * hr), kind


def arm_target(spec, default, side, s, head, hr, hip_pt, t, ph):
    """The hand's target and shape: blending from one pose to the next with overshoot, then holding with
    a tiny drift so it never freezes."""
    a, b, u = spec if spec else (default, default, 1.0)
    pa, ka = pose_at(a, side, s, head, hr, hip_pt, t)
    pb, kb = pose_at(b, side, s, head, hr, hip_pt, t)
    k = backout(u)
    drift = 0.0 if b in ("scratch", "hip", "wipe", "phone", "hold") else hr * 0.025
    pos = (pa[0] + (pb[0] - pa[0]) * k + math.sin(t * 2.1 + ph) * drift, pa[1] + (pb[1] - pa[1]) * k + math.cos(t * 1.7 + ph) * drift)
    return pos, (kb if u > 0.45 else ka), ("out" if b in ("scratch", "hip", "wipe") else "down")


def hand(p, st, wrist, elbow, kind, side, skin, size):
    """A cartoon hand at the wrist, turned along the forearm: open palm with spread fingers, relaxed (a
    curled mitten), fist, thumbs up, or pointing. side puts the thumb on the correct side."""
    ang = math.atan2(wrist[1] - elbow[1], wrist[0] - elbow[0])
    ca, sa = math.cos(ang), math.sin(ang)

    def at(u, v):                                                         # u along the forearm, v across (thumb side +)
        v *= side
        return (wrist[0] + u * ca - v * sa, wrist[1] + u * sa + v * ca)
    L, Wd = size * 1.1, size
    fw = size * 0.34
    ink = st.ink or dark(skin, 0.5)
    palm_c = at(L * 0.5, 0)
    if kind == "open":
        for k, (spread, ln) in enumerate(((-0.28, 0.62), (-0.09, 0.74), (0.09, 0.72), (0.27, 0.58))):
            v0 = Wd * (-0.34 + 0.22 * k)
            p.limb([at(L * 0.7, v0), at(L * 0.7 + L * ln * math.cos(spread), v0 + L * ln * math.sin(spread))], fw, skin)
        p.limb([at(L * 0.25, Wd * 0.4), at(L * 0.6, Wd * 0.95)], fw * 1.1, skin)
        p.fill(ell(palm_c[0], palm_c[1], L * 0.5, Wd * 0.5, 30, rot=ang), skin, shade=False, grad=False)
        p.stroke([at(L * 0.45, -Wd * 0.05), at(L * 0.7, Wd * 0.15)], 1.6, dark(skin, 0.7), closed=False)
    elif kind == "relaxed":
        p.limb([at(L * 0.2, Wd * 0.42), at(L * 0.62, Wd * 0.5)], fw * 1.05, skin)
        mitt = [at(0, -Wd * 0.45), at(L * 0.75, -Wd * 0.5), at(L * 1.05, -Wd * 0.2), at(L * 1.05, Wd * 0.2), at(L * 0.75, Wd * 0.38), at(0, Wd * 0.4)]
        p.fill(spline(mitt, 6), skin, shade=False, grad=False)
        for k in (-0.2, 0.05):                                            # the gaps between curled fingers
            p.stroke([at(L * 0.78, Wd * k), at(L * 1.0, Wd * k)], 1.6, ink, closed=False)
    else:                                                                 # fist, thumb, point
        r = Wd * 0.55
        fc = at(L * 0.5, 0)
        if kind == "point":
            p.limb([at(L * 0.75, -Wd * 0.2), at(L * 1.65, -Wd * 0.2)], fw, skin)
        p.fill(ell(fc[0], fc[1], r * 1.05, r, 30, rot=ang), skin, shade=False, grad=False)
        for k in (-0.25, 0.05, 0.35):                                     # knuckle creases
            p.stroke([at(L * 0.75, Wd * (k - 0.12)), at(L * 0.95, Wd * (k - 0.12))], 1.6, ink, closed=False)
        if kind == "thumb":                                               # always pointing at the sky
            p.limb([(fc[0], fc[1] - r * 0.4), (fc[0], fc[1] - r * 1.55)], fw * 1.15, skin)
        else:
            p.limb([at(L * 0.3, Wd * 0.4), at(L * 0.75, Wd * 0.1)], fw * 1.05, skin)


# ------------------------------------------------------------------ characters
def man(p, st, x, who, act: Act = None):
    """The Dost (mustard tee, jeans, messy hair, buck teeth; scratches his head when idle), Positive Bhai
    (purple shirt with a collar, glasses, side parting; thumbs up when idle), or an elder, "uncle" or
    "dadaji" (white kurta-pyjama, bald with white tufts, white moustache, glasses). Returns the head
    centre, head radius, hands and top of the head."""
    act = act or Act(mood="goofy" if who == "dost" else "happy", look=0.3 if who == "dost" else -0.3)
    t = act.t
    hr, skin = st.hr, st.skin.get(who, (224, 176, 138))
    y = FEET
    elder = who in ("uncle", "dadaji")
    phase = 0.0 if who == "dost" else 1.7
    breath = math.sin(t * 2.2 + phase) * 2.5
    hip = y - st.m_legs
    sh = hip - st.m_torso + breath
    hx = x + math.sin(t * 1.3 + phase) * 2.5
    hy = sh - st.neck - hr * 0.95 + breath * 0.4 + act.talk * 2.5
    sw, ww = hr * st.shoulder, hr * st.shoulder * 0.86
    shirt = {"dost": (246, 170, 40), "bhai": (126, 84, 196)}.get(who, (246, 244, 236))
    pants = {"dost": (60, 92, 150), "bhai": (196, 174, 140)}.get(who, (234, 230, 220))
    shoes = {"dost": (250, 250, 250), "bhai": (110, 66, 40)}.get(who, (120, 80, 50))
    p.fill(ell(x + 10, y + 6, sw * 1.5, hr * 0.18), (0, 0, 0), shade=False, ink=False, grad=False, alpha=45)
    for side in (-1, 1):                                                  # legs and shoes (striding when walking)
        step = math.sin(act.walk) * side * ww * 0.55 if act.walk else 0.0
        up = max(0.0, math.sin(act.walk) * side) * 14 if act.walk else 0.0
        leg = [(x + side * 4, hip), (x + side * ww * 0.95, hip), (x + side * ww * 0.8 + step, y - 16 - up), (x + side * ww * 0.18 + step, y - 16 - up)]
        p.fill(leg, pants)
        p.oval((x + side * ww * 0.55 + side * 6 + step, y - 10 - up), ww * 0.5, hr * 0.17, shoes, shade=False)
    flap = act.wind * 6 * math.sin(t * 7)                                 # the shirt hem in the breeze
    torso = spline([(x - sw, sh + hr * 0.15), (x - sw * 0.6, sh), (x + sw * 0.6, sh), (x + sw, sh + hr * 0.15),
                    (x + ww * (1.1 if elder else 1) + flap, hip + (st.m_legs * 0.45 if elder else 8)),
                    (x - ww * (1.1 if elder else 1) + flap * 0.5, hip + (st.m_legs * 0.45 if elder else 8))], 8)
    l1 = l2 = st.m_torso * 0.5
    s_l, s_r = (x - sw * 0.92, sh + hr * 0.2), (x + sw * 0.92, sh + hr * 0.2)
    t_l, k_l, b_l = arm_target(act.arm_l, "rest", -1, s_l, (hx, hy), hr, None, t, phase)
    t_r, k_r, b_r = arm_target(act.arm_r, {"dost": "scratch", "bhai": "thumb"}.get(who, "rest"), 1, s_r, (hx, hy), hr, None, t, phase + 1)
    e_l, h_l = reach(s_l, t_l, -1, l1, l2, b_l)
    e_r, h_r = reach(s_r, t_r, 1, l1, l2, b_r)

    def draw_arm(s_, e_, h_, kind, side):
        if who == "dost":                                                 # short sleeves, bare forearms
            mid = ((s_[0] + e_[0]) / 2, (s_[1] + e_[1]) / 2)
            p.limb([s_, mid], st.limb * 1.35, shirt)
            p.limb([mid, e_, h_], st.limb, skin)
        else:                                                             # full sleeves with a cuff
            cuff = (e_[0] + (h_[0] - e_[0]) * 0.82, e_[1] + (h_[1] - e_[1]) * 0.82)
            p.limb([s_, e_, cuff], st.limb * 1.15, shirt)
            p.limb([cuff, h_], st.limb * 0.85, skin)
        hand(p, st, h_, e_, kind, side, skin, st.limb * 1.3)
    arms = [(s_l, e_l, h_l, k_l, -1), (s_r, e_r, h_r, k_r, 1)]
    late = [a_ for a_ in arms if a_[2][1] < sh]                           # hands up by the head go over it
    p.fill(ell(x, sh - st.neck * 0.3, hr * 0.32, st.neck + hr * 0.2), skin, shade=False)       # neck
    p.fill(torso, shirt)
    if who != "dost":                                                     # collar (shirt) and placket (shirt or kurta)
        for side in ((-1, 1) if who == "bhai" else ()):
            p.fill([(x, sh + hr * 0.3), (x + side * hr * 0.42, sh - 2), (x + side * hr * 0.12, sh - 6)], light(shirt, 0.15), shade=False)
        p.stroke([(x, sh + hr * 0.3), (x, hip)], 2.5, dark(shirt, 0.6), closed=False)
        for k in range(3):
            p.dot((x + 7, sh + hr * 0.5 + k * st.m_torso * 0.22), 3.5, (240, 230, 200))
    else:
        p.arc((x, sh), hr * 0.36, hr * 0.26, 0.1, math.pi - 0.1, 4, dark(shirt, 0.6))
    for a_ in arms:
        if a_ not in late:
            draw_arm(*a_)
    # head
    for side in (-1, 1):
        p.oval((hx + side * hr * 0.92, hy + hr * 0.08), hr * 0.16, hr * 0.22, skin, shade=False)
    p.oval((hx, hy), hr * 0.9, hr, skin)
    hair = {"dost": (60, 36, 26), "bhai": (30, 24, 40)}.get(who, (236, 236, 240))
    blow = act.wind * 10 + math.sin(t * 6) * 2 * act.wind
    if elder:                                                             # bald on top, white tufts over the ears
        for side in (-1, 1):
            p.oval((hx + side * hr * 0.86, hy - hr * 0.2), hr * 0.2, hr * 0.32, hair, shade=False)
        p.stroke([(hx - hr * 0.4, hy - hr * 0.78), (hx - hr * 0.1, hy - hr * 0.88)], 4, (255, 255, 255), closed=False)
    elif who == "dost":                                                     # messy: a cap with a spiky fringe, tips in the wind
        cap = ell(hx, hy, hr * 0.96, hr * 1.04, 30, math.pi * 1.02, math.pi * 1.98)
        fringe = []
        for k in range(9):
            u = 1 - k / 8
            fringe.append((hx + (u * 2 - 1) * hr * 0.9 + (blow * 0.4 if k % 2 == 0 else 0), hy - hr * (0.38 if k % 2 else 0.58)))
        p.fill(cap + fringe, hair)
        for dx, dy in ((-0.3, -1.12), (0.1, -1.18), (0.45, -1.05)):
            p.fill([(hx + dx * hr - 12, hy - hr * 0.95), (hx + dx * hr + blow, hy + dy * hr - 18), (hx + dx * hr + 14, hy - hr * 0.95)], hair, shade=False)
    else:                                                                 # neat side parting
        cap = ell(hx, hy, hr * 0.97, hr * 1.06, 30, math.pi * 1.02, math.pi * 1.98)
        p.fill(cap + [(hx + hr * 0.9, hy - hr * 0.3), (hx + hr * 0.2, hy - hr * 0.62), (hx - hr * 0.5, hy - hr * 0.42), (hx - hr * 0.92, hy - hr * 0.2)], hair)
        p.stroke([(hx - hr * 0.35, hy - hr * 0.98), (hx - hr * 0.2, hy - hr * 0.5)], 2.5, light(hair, 0.3), closed=False)
    ey = hy + hr * 0.12
    eyes(p, st, hx, ey, hr, act, brow=(220, 220, 226) if elder else (50, 30, 24))
    cheeks(p, st, hx, ey + hr * 0.3, hr)
    p.stroke([(hx + 2, ey + hr * 0.12), (hx + 6, ey + hr * 0.3), (hx - 3, ey + hr * 0.32)], 2.5, dark(skin, 0.6), closed=False)
    mouth(p, st, hx, hy + hr * 0.55, hr, "grin" if who == "dost" else "smile", act.talk, act.mood)
    if elder:                                                             # a white moustache
        for side in (-1, 1):
            p.fill(spline([(hx, hy + hr * 0.4), (hx + side * hr * 0.3, hy + hr * 0.36), (hx + side * hr * 0.42, hy + hr * 0.5),
                           (hx + side * hr * 0.2, hy + hr * 0.52), (hx, hy + hr * 0.48)], 5), (240, 240, 244), shade=False)
    if who != "dost":                                                     # glasses
        for side in (-1, 1):
            p.stroke(ell(hx + side * hr * 0.38, ey + hr * 0.04, hr * 0.27, hr * 0.25, 36), 3.5, (30, 24, 30))
        p.stroke([(hx - hr * 0.12, ey), (hx + hr * 0.12, ey)], 3.5, (30, 24, 30), closed=False)
    for a_ in late:
        draw_arm(*a_)
    return {"head": (hx, hy), "r": hr, "hands": (h_l, h_r), "top": hy - hr * 1.05}


def lady(p, st, x, act: Act = None, saree=None, blouse=None, hair=None, grey=False):
    """An aunty in a saree: gold-bordered pallu over the shoulder, blouse, bindi, nath, jhumkas, a bun with
    gajra, a necklace and mangalsutra, bangles, one hand on her hip; the other hand talks. The pallu, a loose
    lock of hair and the jhumkas move in the breeze. Returns where the head is."""
    act = act or Act()
    t = act.t
    hr, skin = st.hr, st.skin["aunty"]
    y = FEET
    breath = math.sin(t * 2.0 + 0.8) * 2.5
    waist = y - st.f_skirt
    sh = waist - st.f_torso + breath
    hx = x + math.sin(t * 1.1 + 0.8) * 2.5
    hy = sh - st.neck - hr * 0.95 + breath * 0.4 + act.talk * 2.5
    sw, ww, hb = hr * st.shoulder * 0.95, hr * st.shoulder * 0.7, hr * st.shoulder * 1.15
    sar, bor, blo = saree or st.saree, st.border, blouse or st.blouse
    hair = hair or ((70, 66, 72) if grey else (40, 26, 22))
    gust = act.wind
    p.fill(ell(x + 10, y + 6, hb * 1.4, hr * 0.18), (0, 0, 0), shade=False, ink=False, grad=False, alpha=45)
    # the pallu falling behind her right shoulder, lifting and rippling in the breeze
    back = [(x + sw * 0.5, sh - 4), (x + sw * 1.25, sh + hr * 0.3), (x + sw * 1.55, waist + st.f_skirt * 0.45),
            (x + sw * 1.05, waist + st.f_skirt * 0.5), (x + sw * 0.7, waist)]
    span = (waist + st.f_skirt * 0.5) - sh
    back = [(px + ((py - sh) / span) * (gust * 40 + math.sin(t * 5 + py * 0.03) * 7 * (0.3 + gust)), py - ((py - sh) / span) * gust * 18)
            for px, py in back]
    p.fill(spline(back, 8), dark(sar, 0.9), pattern=motif(st.motif, bor))
    p.stroke(spline(back, 8)[24:34], 7, bor, closed=False)
    # the bun with gajra, behind the head
    p.oval((hx + hr * 0.1, hy - hr * 0.9), hr * 0.44, hr * 0.34, hair)
    for k in range(7):
        a = math.pi * (0.95 + 0.12 * k)
        p.dot((hx + hr * 0.1 + math.cos(a) * hr * 0.46, hy - hr * 0.9 + math.sin(a) * hr * 0.36), hr * 0.07, (252, 250, 240))
    # feet, then the saree's lower part with pleats and a border at the hem
    for side in (-1, 1):
        p.oval((x + side * hb * 0.32, y - 6), hb * 0.2, hr * 0.12, skin, shade=False)
    hem = gust * 8 * math.sin(t * 6)

    def cloth(layer, base=motif(st.motif, bor)):
        import pygame as pg
        base(layer)
        h = layer.get_height()
        pg.draw.rect(layer, bor + (255,), (0, h - int(36 * Z * _K), layer.get_width(), int(30 * Z * _K)))
        pg.draw.rect(layer, dark(bor, 0.8) + (255,), (0, h - int(36 * Z * _K), layer.get_width(), max(1, int(4 * Z * _K))))
    skirt = spline([(x - ww, waist), (x + ww, waist), (x + hb * 0.95 + hem * 0.5, waist + st.f_skirt * 0.6), (x + hb + hem, y - 12),
                    (x - hb + hem, y - 12), (x - hb * 0.95, waist + st.f_skirt * 0.6)], 8)
    p.fill(skirt, sar, pattern=cloth)
    for k in (-0.6, -0.2, 0.2, 0.6):                                      # pleats fanning down the front
        p.stroke([(x + ww * 0.15 + k * 6, waist + st.f_skirt * 0.25), (x + k * hb * 0.55 + hem * 0.6, y - 40)], 2.5, dark(sar, 0.7), closed=False)
    # torso: blouse above, a little midriff below
    p.fill(ell(hx, sh - st.neck * 0.3, hr * 0.3, st.neck + hr * 0.2), skin, shade=False)
    body = spline([(x - sw, sh + hr * 0.1), (x - sw * 0.5, sh - 4), (x + sw * 0.5, sh - 4), (x + sw, sh + hr * 0.1),
                   (x + ww, waist + 4), (x - ww, waist + 4)], 8)
    p.fill(body, skin)
    blouse = spline([(x - sw, sh + hr * 0.1), (x - sw * 0.5, sh - 4), (x + sw * 0.5, sh - 4), (x + sw, sh + hr * 0.1),
                     (x + sw * 0.85, sh + st.f_torso * 0.55), (x - sw * 0.85, sh + st.f_torso * 0.55)], 8)
    p.fill(blouse, blo)
    p.arc((x, sh), hr * 0.38, hr * 0.32, 0.15, math.pi - 0.15, 3, dark(blo, 0.6))
    # the pallu across the body, from her left hip over her right shoulder, gold on both edges
    band = [(x - ww * 1.0, waist + 26), (x - ww * 0.05, waist + 26), (x + sw * 1.0, sh + 8), (x + sw * 0.32, sh - 8)]
    p.fill(band, sar, pattern=motif(st.motif, bor))
    p.stroke([band[0], band[3]], 7, bor, closed=False)
    p.stroke([band[1], band[2]], 7, bor, closed=False)
    # necklace and mangalsutra
    p.arc((x, sh + 2), hr * 0.42, hr * 0.42, 0.25, math.pi - 0.25, 5, (238, 186, 60))
    for k in range(13):
        a = 0.3 + (math.pi - 0.6) * k / 12
        p.dot((x + math.cos(a) * hr * 0.55, sh + 4 + math.sin(a) * hr * 0.7), 2.6, (30, 24, 30))
    p.oval((x, sh + hr * 0.72), 7, 9, (238, 186, 60), shade=False)
    # arms: the left hand on her hip; the right one rests, or talks in poses timed to her speech
    l1 = l2 = st.f_torso * 0.55
    s_l, s_r = (x - sw * 0.9, sh + hr * 0.2), (x + sw * 0.9, sh + hr * 0.2)
    t_l, k_l, b_l = arm_target(act.arm_l, "hip", -1, s_l, (hx, hy), hr, (x - ww * 0.95, waist + 6), t, 0.4)
    t_r, k_r, b_r = arm_target(act.arm_r, "rest", 1, s_r, (hx, hy), hr, None, t, 1.4)
    hands = []
    for side, s_, tg, kind, bend in ((-1, s_l, t_l, k_l, b_l), (1, s_r, t_r, k_r, b_r)):
        e_, h_ = reach(s_, tg, side, l1, l2, bend)
        mid = (s_[0] * 0.55 + e_[0] * 0.45, s_[1] * 0.55 + e_[1] * 0.45)
        p.limb([s_, mid], st.limb * 1.25, blo)
        p.limb([mid, e_, h_], st.limb * 0.9, skin)
        wx, wy = e_[0] * 0.2 + h_[0] * 0.8, e_[1] * 0.2 + h_[1] * 0.8
        ang = math.atan2(h_[1] - e_[1], h_[0] - e_[0]) + math.pi / 2
        for k, c_ in enumerate(((60, 160, 80), bor, (60, 160, 80))):    # bangles, across the wrist
            off = (k - 1) * 6
            p.stroke(ell(wx - math.sin(ang) * off, wy + math.cos(ang) * off, st.limb * 0.62, st.limb * 0.22, 24, rot=ang), 3, c_)
        hand(p, st, h_, e_, kind, side, skin, st.limb * 1.15)
        hands.append(h_)
    # head: ears with swinging jhumkas, face, hair parted in the middle, a lock lifting in the wind
    sway = math.sin(t * 3.2) * 3 + gust * 5
    for side in (-1, 1):
        ex = hx + side * hr * 0.88
        p.oval((ex, hy + hr * 0.1), hr * 0.14, hr * 0.2, skin, shade=False)
        jx = ex + sway
        p.fill(ell(jx, hy + hr * 0.42, hr * 0.13, hr * 0.12, 24, math.pi, 2 * math.pi) + [(jx + hr * 0.13, hy + hr * 0.42)],
               (238, 186, 60), shade=False)
        for k in (-1, 0, 1):
            p.dot((jx + k * hr * 0.08 + sway * 0.3, hy + hr * 0.48), 2.6, (238, 186, 60))
    p.oval((hx, hy), hr * 0.86, hr, skin)
    cap = ell(hx, hy, hr * 0.92, hr * 1.04, 30, math.pi * 1.0, math.pi * 2.0)
    line_ = [(hx + hr * 0.92, hy + hr * 0.15), (hx + hr * 0.62, hy - hr * 0.45), (hx + hr * 0.15, hy - hr * 0.62), (hx, hy - hr * 0.55),
             (hx - hr * 0.15, hy - hr * 0.62), (hx - hr * 0.62, hy - hr * 0.45), (hx - hr * 0.92, hy + hr * 0.15)]
    p.fill(cap + line_, hair)
    if grey:
        for side in (-1, 1):
            p.stroke(spline([(hx + side * hr * 0.1, hy - hr * 0.62), (hx + side * hr * 0.5, hy - hr * 0.55), (hx + side * hr * 0.85, hy - hr * 0.1)], 6, closed=False),
                     4, (220, 220, 226), closed=False)
    lock = spline([(hx + hr * 0.86, hy - hr * 0.2), (hx + hr * 1.0 + gust * 12, hy + hr * 0.3),     # on the windward-free side
                   (hx + hr * 0.98 + gust * 30 + math.sin(t * 5) * 5 * (0.4 + gust), hy + hr * 0.8)], 8, closed=False)
    p.stroke(lock, 5, hair, closed=False)
    p.stroke([(hx, hy - hr * 0.57), (hx, hy - hr * 1.0)], 2.5, (200, 40, 50), closed=False)    # sindoor in the parting
    ey = hy + hr * 0.14
    eyes(p, st, hx, ey, hr, act, lady=True)
    cheeks(p, st, hx, ey + hr * 0.32, hr)
    p.dot((hx, hy - hr * 0.3), hr * 0.07, (210, 30, 50))                                       # bindi
    p.stroke([(hx + 2, ey + hr * 0.14), (hx + 5, ey + hr * 0.3), (hx - 3, ey + hr * 0.32)], 2.5, dark(skin, 0.6), closed=False)
    p.stroke(ell(hx + hr * 0.12, ey + hr * 0.34, hr * 0.07, hr * 0.07, 20), 2.5, (238, 186, 60))  # nath
    mouth(p, st, hx, hy + hr * 0.52, hr, "lady", act.talk, act.mood)
    return {"head": (hx, hy), "r": hr, "hands": tuple(hands), "top": hy - hr * 1.3}


# ------------------------------------------------------------------ the style test sheet
STYLES = [
    Style("CHIBI VECTOR", ink=None, ink_w=2.5, grad=True, shade=0.45, eyes="big", bg=(214, 236, 246), hr=95,
          m_torso=150, m_legs=150, f_torso=125, f_skirt=270, neck=8, shoulder=0.95, limb=26, blush=0.9,
          saree=(30, 120, 96), border=(236, 182, 60), blouse=(150, 40, 90), motif="dots"),
    Style("FLAT ILLUSTRATION", ink=(86, 46, 36), ink_w=2.5, grad=False, shade=0.0, eyes="small", bg=(244, 228, 212), hr=50,
          m_torso=175, m_legs=260, f_torso=165, f_skirt=310, neck=20, shoulder=1.45, limb=20, blush=0.35,
          saree=(196, 68, 108), border=(240, 150, 60), blouse=(130, 170, 90), motif="buti"),
    Style("BOLD MARKER", ink=(10, 10, 10), ink_w=6.0, grad=False, shade=0.0, eyes="almond", bg=(255, 255, 255), hr=66,
          m_torso=165, m_legs=220, f_torso=150, f_skirt=285, neck=14, shoulder=1.2, limb=26, blush=0.0,
          saree=(226, 30, 150), border=(255, 220, 0), blouse=(20, 150, 60), motif="dots"),
]
CHIBI = STYLES[0]


def backdrop(pg, surf, st, k):
    w, h = surf.get_size()
    surf.fill(st.bg)
    if k == 0:                                                            # chibi: a soft disc behind each figure
        for cx in (180, 500, 820):
            pg.draw.circle(surf, (150, 200, 226), (int(cx * Z), int(330 * Z)), int(150 * Z))
    elif k == 1:                                                          # flat: sparkle marks
        rng = random.Random(5)
        for _ in range(10):
            x, y = rng.uniform(40, PW - 40), rng.uniform(80, 400)
            for dx, dy in ((10, 0), (0, 10)):
                pg.draw.line(surf, (86, 46, 36), ((x - dx) * Z, (y - dy) * Z), ((x + dx) * Z, (y + dy) * Z), int(2 * Z))
    else:
        pg.draw.line(surf, (200, 200, 200), (0, FEET * Z + 8), (w, FEET * Z + 8), int(3 * Z))


def current_toon(pg, out_size):
    """The baseline: today's toon kit on a plain wall."""
    from . import kit
    from .positive_bhai import GOOFY, POSITIVE
    surf = pg.Surface((PW * kit.S, PH * kit.S))
    for yy in range(0, PH * kit.S, 2):
        pg.draw.rect(surf, mix((226, 196, 150), (240, 214, 168), yy / (PH * kit.S)), (0, yy, PW * kit.S, 2))
    pg.draw.rect(surf, (238, 214, 166), (0, (FEET - 30) * kit.S, PW * kit.S, PH * kit.S))
    lady_ = kit.Bean(shirt=(226, 70, 130), hair=(96, 90, 100), skin=(236, 196, 160), size=0.95, buttons=0)
    big = lambda b: kit.Bean(shirt=b.shirt, hair=b.hair, skin=b.skin, size=0.95, buttons=b.buttons)
    kit.bean(pg, surf, 180, FEET, big(GOOFY), "happy", 0.5, False, t=0.3, look=0.4, extras=("teeth",))
    kit.bean(pg, surf, 500, FEET, lady_, "happy", 0.0, False, t=0.6, extras=("veil", "long_saree", "saree", "side_plait", "bindi"))
    kit.bean(pg, surf, 820, FEET, big(POSITIVE), "happy", 0.3, False, t=1.0, look=-0.4, extras=("specs",),
             reach=((820 - 170, FEET - 560), None))
    return pg.transform.smoothscale(surf, out_size)


def render_sheet(out: Path):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    from ..core.text import font_file
    font = pg.font.Font(font_file("Poppins-ExtraBold"), 34)
    out.mkdir(parents=True, exist_ok=True)
    panels = [current_toon(pg, (PW, PH))]
    names = ["CURRENT TOON"] + [s.name for s in STYLES]
    for k, st in enumerate(STYLES):
        surf = pg.Surface((PW * Z, PH * Z))
        backdrop(pg, surf, st, k)
        p = Painter(pg, surf, st, seed=k)
        man(p, st, 180, "dost")
        lady(p, st, 500)
        man(p, st, 820, "bhai")
        panels.append(pg.transform.smoothscale(surf, (PW, PH)))
    for n, (panel, name) in enumerate(zip(panels, names)):
        tag = font.render(f"{n + 1}. {name}", True, (255, 255, 255))
        r = tag.get_rect(topleft=(24, 20)).inflate(28, 12)
        pg.draw.rect(panel, (40, 30, 60), r, border_radius=16)
        panel.blit(tag, tag.get_rect(center=r.center))
        pg.image.save(panel, str(out / f"style_{n + 1}.png"))
    sheet = pg.Surface((PW * 2 + 20, PH * 2 + 20))
    sheet.fill((30, 30, 36))
    for n, panel in enumerate(panels):
        sheet.blit(panel, ((n % 2) * (PW + 20), (n // 2) * (PH + 20)))
    pg.image.save(sheet, str(out / "sheet.png"))
    return out / "sheet.png"


if __name__ == "__main__":
    import datetime
    from ..config import REPO_ROOT
    print(render_sheet(REPO_ROOT / "out" / datetime.date.today().isoformat() / "toon_styles"))
