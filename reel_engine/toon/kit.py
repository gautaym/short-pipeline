"""Toon: a richer look for Stick Katha. Bean-bodied figures in a lit, cel-shaded set.

Everything is still drawn in code, but at twice the size and scaled down (smooth edges), with soft cast
shadows, two-tone shading on every shape, a sunlit ground and a gentle vignette and grain at the end.
Run as a module for a short test clip: python -m reel_engine.toon.kit
"""
import math
import random
from dataclasses import dataclass

import numpy as np

W, H, FPS = 1080, 1920, 30
S = 2                                  # supersampling: draw at 2x, scale down at the end
INK = (34, 28, 40)
GROUND = 1240


def P(x, y):
    return (int(x * S), int(y * S))


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def shade(c, k=0.78):
    return tuple(int(v * k) for v in c)


# ------------------------------------------------------------------ shading helpers
def shaded_ellipse(pg, surf, cx, cy, rx, ry, col, ink=INK, edge=6, light=(-0.28, -0.3), dark=0.8, gloss=True):
    """An ellipse with an ink edge, lit from the upper left: a darker crescent on the lower right."""
    w, h = int(2 * (rx + edge) * S) + 4, int(2 * (ry + edge) * S) + 4
    tmp = pg.Surface((w, h), pg.SRCALPHA)
    c = (w / 2, h / 2)
    pg.draw.ellipse(tmp, ink, pg.Rect(0, 0, 2 * (rx + edge) * S, 2 * (ry + edge) * S).move(2, 2))
    inner = pg.Rect(0, 0, 2 * rx * S, 2 * ry * S)
    inner.center = c
    body = pg.Surface((w, h), pg.SRCALPHA)
    pg.draw.ellipse(body, shade(col, dark), inner)
    lit = inner.inflate(-inner.width * 0.12, -inner.height * 0.08).move(light[0] * rx * S * 0.5, light[1] * ry * S * 0.5)
    lit_s = pg.Surface((w, h), pg.SRCALPHA)
    pg.draw.ellipse(lit_s, col, lit)
    if gloss:
        g = pg.Rect(0, 0, rx * S * 0.5, ry * S * 0.18)
        g.center = (c[0] - rx * S * 0.38, c[1] - ry * S * 0.55)
        pg.draw.ellipse(lit_s, mix(col, (255, 255, 255), 0.35), g)
    a = pg.surfarray.pixels_alpha(body)
    la = pg.surfarray.pixels_alpha(lit_s)
    np.minimum(la, a, out=la)
    del a, la
    body.blit(lit_s, (0, 0))
    tmp.blit(body, (0, 0))
    surf.blit(tmp, tmp.get_rect(center=P(cx, cy)))


def line(pg, surf, a, b, col, w):
    pg.draw.line(surf, col, P(*a), P(*b), int(w * S))
    pg.draw.circle(surf, col, P(*a), int(w * S / 2))
    pg.draw.circle(surf, col, P(*b), int(w * S / 2))


def poly(pg, surf, pts, col, ink=INK, edge=5):
    q = [P(*p) for p in pts]
    pg.draw.polygon(surf, col, q)
    if edge:
        pg.draw.polygon(surf, ink, q, int(edge * S))


def soft_shadow(pg, surf, cx, cy, rx, ry, alpha=90):
    """A blurred dark ellipse on the ground (drawn small and scaled up, which softens it)."""
    k = 4
    s = pg.Surface((int(rx * 2 * S / k) + 16, int(ry * 2 * S / k) + 16), pg.SRCALPHA)
    pg.draw.ellipse(s, (60, 40, 30, alpha), s.get_rect().inflate(-16, -16))
    s = pg.transform.smoothscale(pg.transform.smoothscale(s, (s.get_width() // 2, s.get_height() // 2)),
                                 (s.get_width() * k, s.get_height() * k))
    surf.blit(s, s.get_rect(center=P(cx, cy)))


# ------------------------------------------------------------------ the set
SUN = (255, 236, 196)
WALL = (240, 214, 168)
WALL_TOP = (226, 196, 150)
SAND = (238, 214, 166)
GLASS = (74, 140, 196)


def window(pg, surf, x, y, w, h, shadows):
    """A sash window: frame, four panes with a sky reflection, and a sill that throws a shadow."""
    shadows.append(("poly", [(x + 18, y + 14), (x + w + 30, y + 14), (x + w + 30, y + h + 40), (x + 18, y + h + 40)]))
    poly(pg, surf, [(x - 14, y - 14), (x + w + 14, y - 14), (x + w + 14, y + h + 14), (x - 14, y + h + 14)], (250, 246, 236), edge=4)
    for i in range(2):
        for j in range(2):
            px, py = x + i * w / 2 + 6, y + j * h / 2 + 6
            pw, ph = w / 2 - 12, h / 2 - 12
            r = pg.Rect(*P(px, py), int(pw * S), int(ph * S))
            for k in range(r.height):                                   # sky-blue gradient, lighter at the top
                pg.draw.line(surf, mix(mix(GLASS, (150, 200, 235), 0.4), GLASS, k / r.height), (r.left, r.top + k), (r.right, r.top + k))
            pg.draw.polygon(surf, mix(GLASS, (255, 255, 255), 0.25),
                            [P(px + pw * 0.15, py), P(px + pw * 0.35, py), P(px, py + ph * 0.45), P(px, py + ph * 0.2)])
            pg.draw.rect(surf, INK, r, int(3 * S))
    # sill: a slab with a top face and a front face
    poly(pg, surf, [(x - 30, y + h + 14), (x + w + 30, y + h + 14), (x + w + 22, y + h + 4), (x - 22, y + h + 4)], (252, 250, 244), edge=3)
    poly(pg, surf, [(x - 30, y + h + 14), (x + w + 30, y + h + 14), (x + w + 30, y + h + 34), (x - 30, y + h + 34)], (214, 208, 196), edge=3)
    shadows.append(("poly", [(x - 24, y + h + 34), (x + w + 36, y + h + 34), (x + w + 50, y + h + 70), (x - 10, y + h + 70)]))


def door(pg, surf, x, y, w, h, shadows):
    shadows.append(("poly", [(x + w + 22, y - 10), (x + w + 54, y + 20), (x + w + 54, y + h), (x + w + 22, y + h)]))
    poly(pg, surf, [(x - 22, y - 22), (x + w + 22, y - 22), (x + w + 22, y + h), (x - 22, y + h)], (250, 246, 236), edge=4)
    poly(pg, surf, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], (178, 140, 98), edge=4)
    for k in range(1, 6):                                               # planks, each with a lit top edge
        yy = y + h * k / 6
        line(pg, surf, (x + 4, yy), (x + w - 4, yy), shade((178, 140, 98), 0.72), 3)
        line(pg, surf, (x + 4, yy + 4), (x + w - 4, yy + 4), (196, 160, 118), 2)
    pg.draw.rect(surf, (150, 114, 78), (*P(x + 4, y + 4), int(14 * S), int((h - 8) * S)))   # the frame's inner shadow
    shaded_ellipse(pg, surf, x + w - 30, y + h * 0.52, 11, 11, (232, 180, 60), edge=3)


def slab(pg, surf, cx, cy, w, d, col=(236, 234, 228), skew=0.0):
    """A stepping stone in perspective: top face, then a darker front face."""
    hw = w / 2
    top = [(cx - hw + skew, cy - d), (cx + hw + skew, cy - d), (cx + hw, cy), (cx - hw, cy)]
    poly(pg, surf, top, col, edge=3)
    poly(pg, surf, [(cx - hw, cy), (cx + hw, cy), (cx + hw, cy + 14), (cx - hw, cy + 14)], shade(col, 0.8), edge=3)


def fence(pg, surf, x0, y0, x1, y1, n, h, shadows):
    """A wooden rail fence receding from (x0, y0) to (x1, y1): posts shrink with distance."""
    wood, side = (196, 176, 160), (150, 128, 116)
    pts = []
    for i in range(n):
        k = i / (n - 1)
        x, y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        sc = 1 - 0.45 * k
        pts.append((x, y, sc))
    for rail in (0.35, 0.7):                                            # rails first, posts over them
        for (xa, ya, sa), (xb, yb, sb) in zip(pts, pts[1:]):
            ta, tb = ya - h * sa * rail, yb - h * sb * rail
            poly(pg, surf, [(xa, ta), (xb, tb), (xb, tb + 16 * sb), (xa, ta + 16 * sa)], side, edge=3)
    for x, y, sc in reversed(pts):
        pw = 34 * sc
        shadows.append(("poly", [(x + pw / 2, y), (x + pw / 2 + 70 * sc, y + 30 * sc), (x + pw / 2 + 70 * sc, y + 14 * sc), (x + pw / 2, y - 10)]))
        poly(pg, surf, [(x - pw / 2, y - h * sc), (x + pw / 2, y - h * sc), (x + pw / 2, y), (x - pw / 2, y)], wood, edge=4)
        poly(pg, surf, [(x + pw / 2, y - h * sc), (x + pw / 2 + 12 * sc, y - h * sc - 8 * sc), (x + pw / 2 + 12 * sc, y - 8 * sc), (x + pw / 2, y)], side, edge=3)
        poly(pg, surf, [(x - pw / 2, y - h * sc), (x + pw / 2, y - h * sc), (x + pw / 2 + 12 * sc, y - h * sc - 8 * sc), (x - pw / 2 + 12 * sc, y - h * sc - 8 * sc)], (226, 210, 196), edge=3)


def plant(pg, surf, x, y, col=(200, 120, 160)):
    poly(pg, surf, [(x - 34, y - 70), (x + 34, y - 70), (x + 26, y), (x - 26, y)], (186, 100, 80), edge=4)
    for dx, dy, r in ((-30, -110, 30), (8, -130, 34), (34, -100, 26), (-6, -96, 28)):
        shaded_ellipse(pg, surf, x + dx, y + dy, r, r, col, edge=3, gloss=False)


def build_set(pg):
    """The courtyard: wall, windows, door, steps, path, fence, plants, light and shadow. Drawn once."""
    surf = pg.Surface((W * S, H * S))
    for yy in range(0, H * S, 2):                                       # wall: darker under the eaves
        k = min(1.0, yy / (GROUND * S * 0.7))
        pg.draw.rect(surf, mix(WALL_TOP, WALL, k), (0, yy, W * S, 2))
    shadows = []
    for x, y in ((40, 40), (720, 40), (40, 600), (720, 600)):
        window(pg, surf, x, y, 300, 330 if y < 300 else 300, shadows)
    door(pg, surf, 400, 600, 270, 520, shadows)
    poly(pg, surf, [(0, 1080), (W, 1080), (W, 1110), (0, 1110)], (210, 200, 190), edge=3)   # plinth
    # the ground: sand, lighter where the sun falls
    pg.draw.rect(surf, SAND, (0, *P(0, 1110)[1:], W * S, (H - 1110) * S))
    for yy in range(1110 * S, H * S, 2):
        k = (yy / S - 1110) / (H - 1110)
        pg.draw.rect(surf, mix((214, 192, 150), SAND, min(1, k * 3)), (0, yy, W * S, 2))
    for i, (cx, cy, w) in enumerate(((540, 1150, 230), (520, 1210, 240), (548, 1275, 250), (510, 1345, 260),
                                      (540, 1425, 270), (500, 1515, 280))):
        slab(pg, surf, cx, cy, w, 26 + i * 2, skew=-10 + i * 4)
    plant(pg, surf, 20, 1110)
    plant(pg, surf, 1060, 1110, (230, 170, 200))
    fence(pg, surf, 1010, 1600, 820, 1090, 5, 260, shadows)
    # shadows: drawn into one layer, softened, multiplied in
    lay = pg.Surface((W * S // 4, H * S // 4), pg.SRCALPHA)
    for kind, pts in shadows:
        pg.draw.polygon(lay, (90, 60, 70, 70), [(px * S // 4, py * S // 4) for px, py in pts])
    lay = pg.transform.smoothscale(pg.transform.smoothscale(lay, (W // 6, H // 6)), (W * S, H * S))
    surf.blit(lay, (0, 0))
    # warm sunbeam across the ground and a cool shade at the top
    q = 4                                                               # the ground in shade, with sunlit patches
    shade_l = pg.Surface((W // q, H // q), pg.SRCALPHA)
    pg.draw.rect(shade_l, (70, 50, 80, 60), (0, 1112 // q, W // q, H // q))
    pg.draw.rect(shade_l, (70, 50, 80, 40), (0, 0, W // q, 1080 // q))
    for poly_ in ([(0, 1260), (W, 1150), (W, 1330), (0, 1480)], [(0, 1620), (W, 1480), (W, 1600), (0, 1760)]):
        pg.draw.polygon(shade_l, (0, 0, 0, 0), [(x // q, y // q) for x, y in poly_])
    shade_l = pg.transform.smoothscale(pg.transform.smoothscale(shade_l, (W // 24, H // 24)), (W * S, H * S))
    surf.blit(shade_l, (0, 0))
    sun = pg.Surface((W // q, H // q), pg.SRCALPHA)
    for poly_ in ([(0, 1260), (W, 1150), (W, 1330), (0, 1480)], [(0, 1620), (W, 1480), (W, 1600), (0, 1760)]):
        pg.draw.polygon(sun, (255, 236, 170, 70), [(x // q, y // q) for x, y in poly_])
    sun = pg.transform.smoothscale(pg.transform.smoothscale(sun, (W // 24, H // 24)), (W * S, H * S))
    surf.blit(sun, (0, 0))
    plinth = pg.Surface((W // q, H // q), pg.SRCALPHA)                  # contact shadow along the wall's foot
    pg.draw.rect(plinth, (60, 40, 50, 90), (0, 1108 // q, W // q, 10))
    plinth = pg.transform.smoothscale(pg.transform.smoothscale(plinth, (W // 8, H // 8)), (W * S, H * S))
    surf.blit(plinth, (0, 0))
    return surf


# ------------------------------------------------------------------ characters
@dataclass
class Bean:
    shirt: tuple = (40, 150, 170)
    skin: tuple = (250, 222, 196)
    hair: tuple = (110, 62, 36)
    size: float = 1.0
    buttons: int = 3


def _elbow(sx, sy, hx, hy, side, l1, l2):
    """Two-bone reach: the hand goes as far toward (hx, hy) as the arm allows; the elbow bows outward."""
    dx, dy = hx - sx, hy - sy
    d = math.hypot(dx, dy) or 1.0
    if d > (l1 + l2) * 0.98:
        k = (l1 + l2) * 0.98 / d
        hx, hy, dx, dy, d = sx + dx * k, sy + dy * k, dx * k, dy * k, (l1 + l2) * 0.98
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    mx, my = sx + dx * a / d, sy + dy * a / d
    nx, ny = -dy / d, dx / d
    if nx * side < 0 or (abs(nx) < 0.2 and ny < 0):
        nx, ny = -nx, -ny
    return (mx + nx * h, my + ny * h), (hx, hy)


def bean(pg, surf, x, y, b: Bean, mood="happy", talk=0.0, blink=False, arms=None, t=0.0, look=0.0, breathe=True,
         grip=None, reach=(None, None), extras=(), blush=0.0, skin=None, lift=0.0):
    """A bean-bodied figure with feet at (x, y).
    arms: two (shoulder angle, elbow angle) pairs, 0 = hanging. reach: per arm (left, right) a hand target
    in 1x pixels, which overrides arms. grip: (cx, cy, half-width), both hands on a held thing.
    extras: "crown", "mukut" (a tall crown), "mustache", "tilak", "four_arms". Returns a dict:
    hands, head (centre), r (head radius), top (top of the head), upper (the second pair of hands)."""
    s = b.size
    skin = skin or b.skin
    bob = math.sin(t * 2.4) * 2.5 * s if breathe else 0
    y = y - lift
    leg = 250 * s
    bw, bh = 82 * s, 128 * s
    by = y - leg - bh * 0.7 + bob * 0.4
    hr = 96 * s
    hy = by - bh * 0.95 - hr * 0.55 + bob
    if lift < 40:
        soft_shadow(pg, surf, x + 18 * s, y + lift + 6, 110 * s, 22 * s, int(110 * (1 - lift / 40)))
    if "long_saree" in extras:                                         # the saree falls to the feet
        for dx in (-22, 22):
            r = pg.Rect(0, 0, int(44 * s * S), int(18 * s * S))
            r.center = P(x + dx * s + 8 * s, y - 4)
            pg.draw.ellipse(surf, (120, 70, 50), r)
            pg.draw.ellipse(surf, INK, r, int(3 * s * S))
        skirt = [(x - bw * 0.8, by + bh * 0.2), (x + bw * 0.8, by + bh * 0.2), (x + bw * 1.08, y - 12), (x - bw * 1.08, y - 12)]
        poly(pg, surf, skirt, b.shirt, edge=6)
        poly(pg, surf, [(x + bw * 0.25, by + bh * 0.4), (x + bw * 0.8, by + bh * 0.3), (x + bw * 1.06, y - 14), (x + bw * 0.45, y - 14)],
             shade(b.shirt, 0.85), edge=0)
        for f in (-0.4, 0.0, 0.4):                                     # pleats
            line(pg, surf, (x + bw * f * 0.6, by + bh * 0.6), (x + bw * f * 0.9, y - 16), shade(b.shirt, 0.75), 3 * s)
        line(pg, surf, (x - bw * 1.06, y - 22 * s), (x + bw * 1.06, y - 22 * s), (240, 190, 60), 8 * s)
    else:
        for dx in (-30, 30):
            line(pg, surf, (x + dx * s, by + bh * 0.7), (x + dx * s * 1.05, y - 6), INK, 9 * s)
            r = pg.Rect(0, 0, int(58 * s * S), int(20 * s * S))
            r.center = P(x + dx * s * 1.05 + 10 * s, y - 4)
            pg.draw.ellipse(surf, (60, 34, 54), r)
    upper = []
    if "four_arms" in extras:                                          # the raised pair, behind the body
        for side in (-1, 1):
            sx, sy = x + side * bw * 0.7, by - bh * 0.55
            e, h = _elbow(sx, sy, x + side * (bw + 120 * s), by - bh - 70 * s + math.sin(t * 2 + side) * 6, side, 100 * s, 95 * s)
            line(pg, surf, (sx, sy), e, INK, 9 * s)
            line(pg, surf, e, h, INK, 9 * s)
            upper.append(h)
    if "veil" in extras:
        hood = [(x + math.cos(a) * (hr + 18 * s), hy + math.sin(a) * (hr + 18 * s)) for a in [math.pi * (1 + k / 20) for k in range(21)]]
        hood += [(x + hr + 18 * s, hy + hr * 0.4), (x + bw * 1.05, by - bh * 0.3), (x + bw * 0.95, by + bh * 0.75),
                 (x - bw * 0.95, by + bh * 0.75), (x - bw * 1.05, by - bh * 0.3), (x - hr - 18 * s, hy + hr * 0.4)]
        poly(pg, surf, hood, shade(b.shirt, 0.88), edge=6)
    if "kurta" in extras:
        poly(pg, surf, [(x - bw * 0.9, by - bh * 0.2), (x + bw * 0.9, by - bh * 0.2), (x + bw * 1.0, by + bh * 1.25),
                        (x - bw * 1.0, by + bh * 1.25)], b.shirt, edge=6)
        line(pg, surf, (x, by + bh * 0.5), (x, by + bh * 1.2), shade(b.shirt, 0.8), 3 * s)
    shaded_ellipse(pg, surf, x, by, bw, bh, b.shirt, edge=7)
    for k in range(b.buttons):
        shaded_ellipse(pg, surf, x - 4 * s, by - bh * 0.55 + k * 38 * s, 7 * s, 7 * s, (246, 210, 120), edge=2, gloss=False)
    if "saree" in extras:                                              # the pallu, shoulder to hip, gold-edged
        band = [(x - 0.62 * bw, by - 0.7 * bh), (x - 0.2 * bw, by - 0.93 * bh), (x + 0.78 * bw, by + 0.42 * bh), (x + 0.42 * bw, by + 0.74 * bh)]
        poly(pg, surf, band, mix(b.shirt, (255, 255, 255), 0.35), edge=0)
        line(pg, surf, band[0], band[3], (240, 190, 60), 5 * s)
        line(pg, surf, band[1], band[2], (240, 190, 60), 5 * s)
    if "side_plait" in extras:
        for k in range(4):
            shaded_ellipse(pg, surf, x - hr * 0.62 + k * 2 * s, hy + hr * 0.75 + k * 26 * s, 15 * s, 17 * s, b.hair, edge=4, gloss=False)
        poly(pg, surf, [(x - hr * 0.62, hy + hr * 0.75 + 4 * 26 * s), (x - hr * 0.62 + 16 * s, hy + hr * 0.75 + 5 * 26 * s),
                        (x - hr * 0.62 - 12 * s, hy + hr * 0.75 + 5 * 26 * s)], (230, 60, 90), edge=3)
    arms = arms or ((0.12, 0.05), (0.12, 0.05))
    hands, segs = [], []
    for n, (side, (a1, a2)) in enumerate(zip((-1, 1), arms)):
        sx, sy = x + side * bw * 0.86, by - bh * 0.35
        if grip:
            e, h = _elbow(sx, sy, grip[0] + side * grip[2], grip[1], side, 105 * s, 100 * s)
        elif reach[n] is not None:
            e, h = _elbow(sx, sy, reach[n][0], reach[n][1], side, 105 * s, 100 * s)
        else:
            e = (sx + side * math.sin(a1) * 105 * s, sy + math.cos(a1) * 105 * s)
            h = (e[0] + side * math.sin(a1 + a2) * 100 * s, e[1] + math.cos(a1 + a2) * 100 * s)
        segs.append(((sx, sy), e, h))
        hands.append(h)
    late = [sg for sg in segs if sg[2][1] < hy + hr * 0.9]             # hands up at the face go over the head
    for sg in segs:
        if sg not in late:
            line(pg, surf, sg[0], sg[1], INK, 9 * s)
            line(pg, surf, sg[1], sg[2], INK, 9 * s)
    # head
    shaded_ellipse(pg, surf, x, hy, hr, hr * 0.98, skin, edge=7, dark=0.86)
    cap = []
    for k in range(0, 41):
        a = math.pi + math.pi * k / 40
        cap.append((x + math.cos(a) * (hr + 4), hy + math.sin(a) * (hr + 4) * 0.98))
    fringe_y = hy - hr * 0.42
    for k in range(0, 21):
        u = 1 - k / 20
        cap.append((x + (u * 2 - 1) * (hr + 2), fringe_y + math.sin(u * math.pi) * 10 * s))
    if "bald" in extras:                                               # white tufts over the ears, a shiny top
        for side in (-1, 1):
            shaded_ellipse(pg, surf, x + side * hr * 0.9, hy - hr * 0.05, hr * 0.2, hr * 0.36, b.hair, edge=5, gloss=False)
        line(pg, surf, (x - hr * 0.35, hy - hr * 0.72), (x - hr * 0.05, hy - hr * 0.8), (255, 255, 255), 5 * s)
    elif "veil" in extras or "parted" in extras:                       # hair parted in the middle
        hair = [(x + math.cos(a) * (hr + 3), hy + math.sin(a) * (hr + 3)) for a in [math.pi * (1 + k / 30) for k in range(31)]]
        hair += [(x + hr * 0.95, hy + hr * 0.15), (x + hr * 0.7, hy - hr * 0.35), (x + hr * 0.3, hy - hr * 0.52), (x, hy - hr * 0.45),
                 (x - hr * 0.3, hy - hr * 0.52), (x - hr * 0.7, hy - hr * 0.35), (x - hr * 0.95, hy + hr * 0.15)]
        poly(pg, surf, hair, b.hair, edge=6)
        line(pg, surf, (x, hy - hr * 0.47), (x, hy - hr * 0.95), mix(b.hair, (255, 255, 255), 0.4), 3 * s)
    else:
        poly(pg, surf, cap, b.hair, edge=7)
        poly(pg, surf, [(x - hr * 0.6, hy - hr * 0.75), (x - hr * 0.1, hy - hr * 0.88), (x - hr * 0.5, hy - hr * 0.62)],
             mix(b.hair, (255, 255, 255), 0.25), edge=0)
    if "veil" in extras:                                               # the pallu's front edge over the hair
        outer = [(x + math.cos(a) * (hr + 18 * s), hy + math.sin(a) * (hr + 18 * s)) for a in [math.pi * (1 + k / 24) for k in range(25)]]
        inner = [(x + math.cos(a) * hr * 0.86, hy + hr * 0.32 + math.sin(a) * hr * 1.05) for a in [math.pi * (2 - k / 24) for k in range(25)]]
        band = outer + inner
        poly(pg, surf, band, b.shirt, edge=6)
        line(pg, surf, inner[3], inner[-4], (240, 190, 60), 0.1)
        pg.draw.lines(surf, (240, 190, 60), False, [P(*q) for q in inner[2:-2]], int(6 * s * S))
    top = hy - hr
    if "bun" in extras:
        shaded_ellipse(pg, surf, x, hy - hr * 1.02, hr * 0.38, hr * 0.3, b.hair, edge=6, gloss=False)
        top = hy - hr * 1.3
    gold = (250, 196, 50)
    if "mukut" in extras or "crown" in extras:
        tall = 1.0 if "mukut" in extras else 0.55
        cw = hr * (0.8 if "mukut" in extras else 0.7)
        base = hy - hr * 0.7
        pts = [(x - cw, base), (x - cw * 0.9, base - hr * 0.5 * tall), (x - cw * 0.5, base - hr * 0.35 * tall),
               (x - cw * 0.3, base - hr * 0.95 * tall), (x, base - hr * 1.35 * tall), (x + cw * 0.3, base - hr * 0.95 * tall),
               (x + cw * 0.5, base - hr * 0.35 * tall), (x + cw * 0.9, base - hr * 0.5 * tall), (x + cw, base)]
        poly(pg, surf, pts, gold, edge=6)
        poly(pg, surf, [(x - cw, base), (x + cw, base), (x + cw * 0.95, base - 22 * s), (x - cw * 0.95, base - 22 * s)],
             shade(gold, 0.85), edge=5)
        shaded_ellipse(pg, surf, x, base - hr * 0.55 * tall, 13 * s, 15 * s, (220, 40, 70), edge=3)
        for dx in (-0.55, 0.55):
            shaded_ellipse(pg, surf, x + cw * dx, base - 11 * s, 8 * s, 8 * s, (60, 170, 120), edge=2, gloss=False)
        top = base - hr * 1.35 * tall
    fx = x + look * 22 * s
    ey = hy + hr * 0.08
    if "tilak" in extras:
        poly(pg, surf, [(fx - 7 * s, ey - 60 * s), (fx + 7 * s, ey - 60 * s), (fx, ey - 22 * s)], (230, 40, 50), edge=0)
    if "bindi" in extras:
        shaded_ellipse(pg, surf, fx, ey - 46 * s, 7 * s, 7 * s, (220, 30, 50), edge=2, gloss=False)
    tilt = {"angry": 0.85, "happy": -0.12, "shock": -0.25, "worried": -0.45, "shy": -0.3}.get(mood, 0.0)
    for side in (-1, 1):
        cx = fx + side * hr * 0.36
        inner, outer = cx - side * 18 * s, cx + side * 18 * s
        by_ = ey - 30 * s
        line(pg, surf, (inner, by_ + tilt * 12 * s), (outer, by_ - tilt * 12 * s), INK, 5 * s)
    for side in (-1, 1):
        cx = fx + side * hr * 0.36
        if blink or mood in ("happy", "shy", "closed"):
            r = pg.Rect(0, 0, int(36 * s * S), int(24 * s * S))
            r.center = P(cx, ey + 6 * s)
            pg.draw.arc(surf, INK, r, 0.2, math.pi - 0.2, int(5 * s * S))
        elif mood == "angry":
            line(pg, surf, (cx - 16 * s, ey), (cx + 16 * s, ey), INK, 5 * s)
            pg.draw.circle(surf, INK, P(cx + look * 4, ey + 6 * s), int(7 * s * S))
        elif mood == "shock":
            pg.draw.circle(surf, (255, 255, 255), P(cx, ey), int(15 * s * S))
            pg.draw.circle(surf, INK, P(cx, ey), int(15 * s * S), int(3 * s * S))
            pg.draw.circle(surf, INK, P(cx + look * 4, ey), int(6 * s * S))
        else:
            pg.draw.circle(surf, INK, P(cx + look * 4, ey), int(8 * s * S))
    if blush or mood == "shy":
        for side in (-1, 1):
            g = pg.Surface((int(40 * s * S), int(20 * s * S)), pg.SRCALPHA)
            pg.draw.ellipse(g, (240, 110, 130, int(170 * max(blush, 0.7 if mood == "shy" else 0))), g.get_rect())
            surf.blit(g, g.get_rect(center=P(fx + side * hr * 0.55, ey + 30 * s)))
    my = hy + hr * 0.45
    if "mustache" in extras:
        for side in (-1, 1):
            poly(pg, surf, [(fx, my - 12 * s), (fx + side * 34 * s, my - 18 * s), (fx + side * 50 * s, my - 30 * s),
                            (fx + side * 40 * s, my - 6 * s), (fx + side * 10 * s, my - 2 * s)],
                 (236, 236, 236) if "grey" in extras else (40, 30, 30), edge=3 if "grey" in extras else 0)
    open_ = (0.35 + 0.65 * talk) if mood == "happy" else talk
    if mood == "shock" and talk < 0.3:
        r = pg.Rect(0, 0, int(26 * s * S), int(32 * s * S))
        r.center = P(fx, my + 6 * s)
        pg.draw.ellipse(surf, (150, 40, 50), r)
        pg.draw.ellipse(surf, INK, r, int(4 * s * S))
    elif mood == "worried" and open_ > 0.08:                           # uneasy talk: a small wobbly oval
        r = pg.Rect(0, 0, int((22 + 6 * open_) * s * S), int((8 + 16 * open_) * s * S))
        r.center = P(fx, my + 8 * s)
        pg.draw.ellipse(surf, (150, 40, 50), r)
        pg.draw.ellipse(surf, INK, r, int(4 * s * S))
    elif mood == "angry" and open_ > 0.08:                             # shouting: round on top, flat below
        mw, mh = 30 * s, 10 * s + 22 * s * open_
        base_m = my + 18 * s
        d = [(fx + math.cos(a) * mw, base_m - math.sin(a) * mh) for a in [math.pi * k / 24 for k in range(25)]]
        poly(pg, surf, d, (150, 40, 50), edge=0)
        line(pg, surf, (fx - mw * 0.7, base_m - mh * 0.8), (fx + mw * 0.7, base_m - mh * 0.8), (255, 255, 255), 5 * s)
        pg.draw.polygon(surf, INK, [P(*q) for q in d], int(4 * s * S))
    elif open_ > 0.08:
        mw, mh = 26 * s, 8 * s + 26 * s * open_
        top_m = my - 6 * s
        d = [(fx + math.cos(a) * mw, top_m + math.sin(a) * mh) for a in [math.pi * k / 24 for k in range(25)]]
        poly(pg, surf, d, (150, 40, 50), edge=0)
        tongue = [(fx + math.cos(a) * mw * 0.55, top_m + mh * 0.55 + math.sin(a) * mh * 0.42) for a in [math.pi * k / 16 for k in range(17)]]
        poly(pg, surf, tongue, (236, 110, 110), edge=0)
        pg.draw.polygon(surf, INK, [P(*q) for q in d], int(4 * s * S))
    elif mood in ("angry", "worried"):
        r = pg.Rect(0, 0, int(36 * s * S), int(22 * s * S))
        r.center = P(fx, my + 10 * s)
        pg.draw.arc(surf, INK, r, 0.3, math.pi - 0.3, int(5 * s * S))
    elif mood in ("closed", "shy", "neutral"):
        r = pg.Rect(0, 0, int(34 * s * S), int(20 * s * S))
        r.center = P(fx, my - 4 * s)
        pg.draw.arc(surf, INK, r, math.pi + 0.4, 2 * math.pi - 0.4, int(5 * s * S))
    else:
        line(pg, surf, (fx - 14 * s, my), (fx + 14 * s, my), INK, 5 * s)
    if "specs" in extras:
        for side in (-1, 1):
            pg.draw.circle(surf, INK, P(fx + side * hr * 0.36, ey + 2 * s), int(25 * s * S), int(4 * s * S))
        line(pg, surf, (fx - hr * 0.36 + 25 * s, ey), (fx + hr * 0.36 - 25 * s, ey), INK, 4 * s)
    if "teeth" in extras:                                              # goofy buck teeth under the lip
        ty = my - 4 * s if open_ <= 0.08 else my - 6 * s
        for side in (-1, 1):
            r = pg.Rect(*P(fx + (0 if side > 0 else -13 * s), ty), int(13 * s * S), int(15 * s * S))
            pg.draw.rect(surf, (255, 255, 255), r, border_radius=int(3 * S))
            pg.draw.rect(surf, INK, r, int(3 * s * S), border_radius=int(3 * S))
    for sg in late:
        line(pg, surf, sg[0], sg[1], INK, 9 * s)
        line(pg, surf, sg[1], sg[2], INK, 9 * s)
    return {"hands": hands, "head": (x, hy), "r": hr, "top": top, "upper": upper, "body": (x, by, bw, bh)}


def basket(pg, surf, cx, cy, s=1.0):
    for i, dx in enumerate((-58, -30, 0, 30, 58)):
        shaded_ellipse(pg, surf, cx + dx * s, cy - 30 * s - (6 if i % 2 else 0) * s, 17 * s, 23 * s, (252, 250, 244), edge=4)
    poly(pg, surf, [(cx - 92 * s, cy - 26 * s), (cx + 92 * s, cy - 26 * s), (cx + 74 * s, cy + 52 * s), (cx - 74 * s, cy + 52 * s)],
         (214, 158, 84), edge=6)
    for k in range(1, 4):
        yy = cy - 26 * s + k * 19 * s
        line(pg, surf, (cx - (92 - k * 4.5) * s, yy), (cx + (92 - k * 4.5) * s, yy), (176, 120, 60), 3)
    poly(pg, surf, [(cx - 98 * s, cy - 36 * s), (cx + 98 * s, cy - 36 * s), (cx + 98 * s, cy - 18 * s), (cx - 98 * s, cy - 18 * s)],
         (150, 98, 54), edge=5)


def chicken(pg, surf, x, y, t, phase, s=1.0, face=-1):
    """A hen with feet at (x, y), facing left (face=-1) or right, pecking now and then."""
    peck = max(0.0, math.sin(t * 3 + phase)) ** 6
    soft_shadow(pg, surf, x + 10 * s, y + 4, 60 * s, 12 * s, 90)
    for dx in (-12, 12):
        line(pg, surf, (x + dx * s, y - 34 * s), (x + dx * s, y), (230, 140, 60), 4 * s)
    bx, by = x, y - 62 * s
    poly(pg, surf, [(bx - face * 50 * s, by - 6 * s), (bx - face * 84 * s, by - 52 * s), (bx - face * 70 * s, by - 4 * s)],
         (252, 250, 244), edge=4)
    poly(pg, surf, [(bx - face * 72 * s, by - 34 * s), (bx - face * 84 * s, by - 52 * s), (bx - face * 64 * s, by - 26 * s)],
         (40, 150, 150), edge=3)
    shaded_ellipse(pg, surf, bx, by, 58 * s, 36 * s, (252, 250, 244), edge=5)
    shaded_ellipse(pg, surf, bx - face * 6 * s, by + 2 * s, 30 * s, 18 * s, (246, 220, 170), edge=4, gloss=False)
    hx, hy = bx + face * (46 + 18 * peck) * s, by - (40 - 54 * peck) * s
    line(pg, surf, (bx + face * 36 * s, by - 16 * s), (hx, hy), (252, 250, 244), 22 * s)
    for k in range(3):
        shaded_ellipse(pg, surf, hx - face * (8 - k * 9) * s, hy - (22 + (k % 2) * 4) * s, 8 * s, 9 * s, (220, 40, 50), edge=2, gloss=False)
    shaded_ellipse(pg, surf, hx, hy, 20 * s, 19 * s, (252, 250, 244), edge=4)
    poly(pg, surf, [(hx + face * 16 * s, hy - 4 * s), (hx + face * 36 * s, hy + 3 * s), (hx + face * 16 * s, hy + 9 * s)], (246, 168, 50), edge=3)
    shaded_ellipse(pg, surf, hx + face * 8 * s, hy + 16 * s, 6 * s, 8 * s, (220, 40, 50), edge=2, gloss=False)
    pg.draw.circle(surf, INK, P(hx + face * 6 * s, hy - 4 * s), int(4 * s * S))


def finish(pg, small, grain, vignette):
    """Vignette and film grain on the final 1080x1920 frame."""
    a = pg.surfarray.pixels3d(small)
    f = a.astype(np.float32) * vignette[..., None] + grain[..., None]
    np.clip(f, 0, 255, out=f)
    a[...] = f.astype(np.uint8)
    del a


# ------------------------------------------------------------------ test clip
def render_test(out: "Path", seconds=8.0, still=None):
    import os
    import subprocess
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    pg.display.set_mode((1, 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    bg = build_set(pg)
    xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H), indexing="ij")
    vignette = (1 - 0.28 * np.clip((xs ** 2 * 0.8 + ys ** 2 * 0.6) - 0.25, 0, None)).astype(np.float32)
    rng = np.random.default_rng(3)
    grains = [rng.normal(0, 4.0, (W, H)).astype(np.float32) for _ in range(4)]
    boy = Bean(shirt=(36, 150, 168), hair=(108, 62, 36))
    dost = Bean(shirt=(126, 84, 196), hair=(52, 36, 90), skin=(222, 176, 128))
    hens = [(700, 1560, 0.0, 0.8), (880, 1500, 1.7, 0.7), (640, 1690, 3.1, 0.9), (960, 1700, 4.4, 0.85)]
    seeds = [(random.Random(i).uniform(600, 1000), random.Random(i + 99).uniform(1520, 1760)) for i in range(40)]
    ff = None
    if still is None:
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)],
                              stdin=subprocess.PIPE)
    n = 1 if still is not None else int(seconds * FPS)
    for f in range(n):
        t = still if still is not None else f / FPS
        frame = bg.copy()
        for sx, sy in seeds:
            pg.draw.circle(frame, (90, 70, 50), P(sx, sy), 2 * S)
        for hx, hy, ph, sc in sorted(hens, key=lambda h: h[1]):
            chicken(pg, frame, hx + math.sin(t * 0.7 + ph) * 18, hy, t, ph, sc, -1 if ph < 3 else 1)
        speaker = int(t / 2) % 2                                       # they take turns talking
        talk = abs(math.sin(t * 11)) * (0.6 + 0.4 * math.sin(t * 3.7))
        blink = (t % 3.1) < 0.12
        hands = bean(pg, frame, 230, GROUND + 40, boy, "happy", talk if speaker == 0 else 0, blink, t=t,
                     grip=(230, GROUND - 280 + math.sin(t * 2.4) * 3, 96), look=0.6)
        basket(pg, frame, 230, hands["hands"][0][1] + 20)
        bean(pg, frame, 820, GROUND + 70, dost, "happy" if t % 4 < 3 else "shock", talk if speaker == 1 else 0,
             (t % 3.7) < 0.12, t=t + 1, arms=((0.12 + 0.1 * math.sin(t * 2), 0.1), (0.15, 0.1)), look=-0.6)
        # a slow push-in, then scale down (this is the antialiasing step)
        z = 1 + 0.05 * (t / max(seconds, 0.01))
        cw, ch = int(W * S / z), int(H * S / z)
        crop = frame.subsurface(((W * S - cw) // 2, (H * S - ch) // 2, cw, ch))
        small = pg.transform.smoothscale(crop, (W, H))
        finish(pg, small, grains[f % 4], vignette)
        if ff:
            ff.stdin.write(pg.image.tobytes(small, "RGB"))
        else:
            pg.image.save(small, str(out))
    if ff:
        ff.stdin.close()
        ff.wait()
    return out


if __name__ == "__main__":
    import datetime
    import sys
    from pathlib import Path
    base = Path(__file__).resolve().parents[2] / "out" / datetime.date.today().isoformat() / "toon_test"
    if "--still" in sys.argv:
        print(render_test(base / "toon_still.png", still=1.0))
    else:
        print(render_test(base / "toon_test.mp4"))
