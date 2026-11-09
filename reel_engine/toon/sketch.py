"""Sketchbook: a hand-drawn look for Bhess ki Eyes, different from the chibi 3D one.

Wobbly ink outlines that "boil" (redrawn with fresh jitter every few frames, like hand-drawn animation),
flat marker fills printed slightly off the line, two-tone shading, and a paper grain over everything.
Pure pygame + numpy, so it renders anywhere (no Blender, no GPU).

Every shape goes through Ink: give it outline points in screen units (1080x1920) and it jitters, fills and
inks them. The jitter is seeded from (shape id, boil index), so a held frame stays still and a new boil
index redraws every line a little differently.

Run: python -m reel_engine.toon.sketch   (writes a style test frame to out/sketch/style.png)
"""
import math
import os
import random
from pathlib import Path

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame as pg

W, H = 1080, 1920
S = 3                                   # draw at 3x, scale down at the end (room for camera zooms)
LINE = 1.8                              # global line weight
INK = (46, 34, 38)
PAPER = (250, 244, 230)


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def dark(c, k=0.8):
    return tuple(int(v * k) for v in c)


# ---------------------------------------------------------------- shapes (lists of points, screen units)
def ell(cx, cy, rx, ry, rot=0.0, n=40, a0=0.0, a1=2 * math.pi):
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for i in range(n + (0 if a1 - a0 >= 2 * math.pi - 1e-6 else 1)):
        a = a0 + (a1 - a0) * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * c - y * s, cy + x * s + y * c))
    return out


def smooth(ctrl, n=10, closed=True):
    """Catmull-Rom through control points."""
    m = len(ctrl)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = ctrl[(i - 1) % m] if closed else ctrl[max(i - 1, 0)]
        p1, p2 = ctrl[i], ctrl[(i + 1) % m]
        p3 = ctrl[(i + 2) % m] if closed else ctrl[min(i + 2, m - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    if not closed:
        out.append(ctrl[-1])
    return out


def rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def dense(pts, step=14.0, closed=True):
    """Extra points along straight edges, so the jitter bends them like a hand-drawn line."""
    out = []
    m = len(pts)
    for i in range(m if closed else m - 1):
        a, b = pts[i], pts[(i + 1) % m]
        d = math.dist(a, b)
        k = max(1, int(d / step))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    if not closed:
        out.append(pts[-1])
    return out


def move(pts, dx=0.0, dy=0.0, sx=1.0, sy=None, ox=0.0, oy=0.0, rot=0.0):
    """Scale about (ox, oy), rotate about it, then shift."""
    sy = sx if sy is None else sy
    c, s = math.cos(rot), math.sin(rot)
    out = []
    for x, y in pts:
        x, y = (x - ox) * sx, (y - oy) * sy
        out.append((ox + x * c - y * s + dx, oy + x * s + y * c + dy))
    return out


# ---------------------------------------------------------------- the pen
class Ink:
    def __init__(self, surf, boil=0, seed=7, amp=1.0):
        self.surf, self.boil, self.seed, self.amp = surf, boil, seed, amp
        self.n = 0                                      # shapes drawn so far: each gets its own jitter

    def _rng(self):
        self.n += 1
        return random.Random(hash((self.seed, self.boil, self.n)) & 0xFFFFFFFF)

    def jit(self, pts, amp, closed=True):
        r = self._rng()
        amp *= self.amp
        f1, f2 = r.uniform(0.15, 0.3), r.uniform(0.5, 0.9)
        p1, p2 = r.uniform(0, 6.3), r.uniform(0, 6.3)
        ax, ay = r.uniform(0.6, 1.0), r.uniform(0.6, 1.0)
        out = []
        for i, (x, y) in enumerate(pts):
            dx = amp * ax * (math.sin(i * f1 + p1) + 0.4 * math.sin(i * f2 + p2))
            dy = amp * ay * (math.cos(i * f1 * 1.1 + p2) + 0.4 * math.cos(i * f2 + p1))
            out.append((x + dx, y + dy))
        return out

    def _P(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def fill(self, pts, col, amp=2.0, off=(2.5, 2.0)):
        """Marker fill, a touch off the line."""
        p = self.jit(pts, amp)
        if len(p) >= 3:
            pg.draw.polygon(self.surf, col, self._P(move(p, *off)))
        return p

    def stroke(self, pts, w=4.0, col=INK, amp=1.6, closed=True, taper=True):
        """A wobbly ink line, thicker in the middle of each stroke and thin at the ends."""
        p = self.jit(pts, amp, closed)
        if closed:
            p = p + [p[0]]
        r = self._rng()
        ph = r.uniform(0, 6.3)
        m = len(p)
        for i in range(m - 1):
            u = i / max(1, m - 2)
            k = 0.75 + 0.35 * math.sin(i * 0.21 + ph)
            if taper and not closed:
                k *= 0.35 + 0.65 * math.sin(math.pi * min(1.0, max(0.0, u)))
            ww = max(1, int(w * LINE * S * k))
            a, b = (p[i][0] * S, p[i][1] * S), (p[i + 1][0] * S, p[i + 1][1] * S)
            pg.draw.line(self.surf, col, a, b, ww)
            pg.draw.circle(self.surf, col, a, ww / 2)
        return p

    def shape(self, pts, col, w=4.0, ink=INK, amp=2.0, shade=None, shade_pts=None):
        """Fill, optional shade shape (clipped by eye, drawn before the line), then the outline."""
        self.fill(pts, col, amp)
        if shade_pts:
            self.fill(shade_pts, shade or dark(col, 0.84), amp, off=(0, 0))
        if w:
            self.stroke(pts, w, ink, amp * 0.8)

    def dot(self, x, y, r, col=INK):
        rr = self._rng()
        pg.draw.circle(self.surf, col, ((x + rr.uniform(-0.6, 0.6)) * S, (y + rr.uniform(-0.6, 0.6)) * S), r * S)

    def hatch(self, pts, col=INK, gap=11, w=1.6, angle=-0.9, alpha=90):
        """Pencil hatching inside a shape (shadows)."""
        lay = pg.Surface(self.surf.get_size(), pg.SRCALPHA)
        mask = pg.Surface(self.surf.get_size(), pg.SRCALPHA)
        pg.draw.polygon(mask, (255, 255, 255, 255), self._P(self.jit(pts, 1.5)))
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        c, s = math.cos(angle), math.sin(angle)
        span = (x1 - x0) + (y1 - y0)
        r = self._rng()
        k = -span
        while k < span:
            cx, cy = (x0 + x1) / 2 + k * s, (y0 + y1) / 2 - k * c
            a = (cx - c * span, cy - s * span)
            b = (cx + c * span, cy + s * span)
            pg.draw.line(lay, (*col, alpha), (a[0] * S, a[1] * S), (b[0] * S, b[1] * S),
                         max(1, int(w * S * r.uniform(0.7, 1.2))))
            k += gap * r.uniform(0.85, 1.15)
        lay.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
        self.surf.blit(lay, (0, 0))


# ---------------------------------------------------------------- paper
_GRAIN = {}


def paper_grain(seed=3):
    if seed not in _GRAIN:
        rng = np.random.default_rng(seed)
        g = rng.normal(0, 1, (H // 4 + 2, W // 4 + 2)).astype(np.float32)
        g = np.kron(g, np.ones((4, 4), np.float32))[:H, :W]
        fine = rng.normal(0, 1, (H, W)).astype(np.float32)
        fibre = np.cumsum(rng.normal(0, 1, (H, W)).astype(np.float32), axis=1)
        fibre -= fibre.mean(axis=1, keepdims=True)
        fibre /= (fibre.std() + 1e-6)
        _GRAIN[seed] = (1.0 + 0.018 * g + 0.022 * fine + 0.008 * fibre).T[..., None]
    return _GRAIN[seed]


def finish(big, vignette=0.18, cam=(540, 960, 1.0)):
    """cam: (centre x, centre y, zoom) in screen units: zoom 1.25 frames 1/1.25 of the page."""
    cx, cy, z = cam
    w, h = W / z, H / z
    x0 = min(max(cx - w / 2, 0), W - w)
    y0 = min(max(cy - h / 2, 0), H - h)
    view = big.subsurface(pg.Rect(int(x0 * S), int(y0 * S), int(w * S), int(h * S)))
    small = pg.transform.smoothscale(view, (W, H))
    a = pg.surfarray.pixels3d(small).astype(np.float32)
    a *= paper_grain()
    if vignette:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = ((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2
        a *= (1 - vignette * np.clip(d, 0, 1.4)).T[..., None]
    out = pg.surfarray.make_surface(np.clip(a, 0, 255).astype(np.uint8))
    return out


def canvas():
    s = pg.Surface((W * S, H * S))
    s.fill(PAPER)
    return s
