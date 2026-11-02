"""Painted backdrops for story reels, in a paper-cut theatre style.

A Stage builds its layers once (sky, stars, paper clouds) and draws a scene by name:

    cosmos    warm glowing sky with stars and drifting paper clouds
    ocean     night sky over layered paper waves
    churning  the ocean with a mountain churning in it, a serpent rope and two teams pulling
    poison    the ocean under a darkened sky, with poison smoke rising
    kailash   snowy peaks under a cold sky
    forest    layered trees at dusk
    palace    arches and pillars in warm light
    space     planets and a starfield

Clouds and stars drift with time; nothing here changes how a story plays.
"""
import math
import random

import numpy as np

from ..core.canvas import H, W

SKIES = {
    "cosmos": ((46, 34, 40), (150, 110, 70), (255, 220, 150)),
    "ocean": ((10, 16, 34), (24, 50, 74), (120, 170, 190)),
    "churning": ((12, 16, 34), (34, 50, 76), (150, 180, 200)),
    "poison": ((14, 8, 22), (46, 20, 52), (120, 60, 150)),
    "kailash": ((14, 22, 44), (60, 90, 130), (220, 230, 250)),
    "forest": ((20, 18, 30), (70, 50, 60), (230, 160, 110)),
    "palace": ((40, 24, 22), (120, 70, 50), (250, 200, 140)),
    "space": ((4, 4, 12), (12, 10, 30), (80, 60, 140)),
}


def gradient_glow(pg, top, mid, glow, centre=(W / 2, H * 0.42)):
    """Sky that fades from top to mid with a soft warm glow around centre."""
    y = np.linspace(0, 1, H)[None, :, None]
    base = np.array(top)[None, None, :] * (1 - y) + np.array(mid)[None, None, :] * y
    xx = (np.arange(W) - centre[0])[:, None]
    yy = (np.arange(H) - centre[1])[None, :]
    d = np.sqrt(xx * xx + yy * yy) / 900
    g = np.clip(1 - d, 0, 1)[..., None] ** 2.2
    arr = np.clip(base * (1 - 0.6 * g) + np.array(glow)[None, None, :] * g * 0.75, 0, 255)
    return pg.surfarray.make_surface(np.broadcast_to(arr, (W, H, 3)).astype(np.uint8).copy())


def paper_cloud(pg, w: int, rng, tint=(150, 138, 128)):
    """A puffy paper cloud with white arc patterns and a dotted line along its base."""
    h = int(w * 0.5)
    s = pg.Surface((w, h), pg.SRCALPHA)
    bumps = [(w * 0.22, h * 0.62, w * 0.2), (w * 0.42, h * 0.45, w * 0.24), (w * 0.64, h * 0.5, w * 0.22),
             (w * 0.82, h * 0.66, w * 0.16), (w * 0.5, h * 0.72, w * 0.3)]
    for x, y, r in bumps:
        pg.draw.circle(s, (70, 60, 60, 230), (x, y), r + 5)
    for x, y, r in bumps:
        pg.draw.circle(s, tint + (235,), (x, y), r)
    hi = tuple(min(255, c + 30) for c in tint)
    for x, y, r in bumps[:4]:
        pg.draw.circle(s, hi + (235,), (x - r * 0.15, y - r * 0.2), r * 0.6)
    for x, y, r in bumps[:3]:                                     # the white arcs
        for k in range(3):
            rr = r * (0.75 - k * 0.2)
            pg.draw.arc(s, (250, 248, 240, 220), (x - rr, y - rr * 0.6, 2 * rr, 2 * rr), 0.15, math.pi - 0.15, 3)
    for k in range(int(w / 18)):
        pg.draw.circle(s, (250, 245, 230, 200), (w * 0.12 + k * 16, h * 0.86), 2.5)
    return s


class Stage:
    def __init__(self, pg, seed: int):
        self.pg = pg
        rng = random.Random(f"stage:{seed}")
        self.skies = {}
        self.stars = [(rng.uniform(0, W), rng.uniform(0, H * 0.75), rng.uniform(1, 2.6), rng.uniform(0, 6.28))
                      for _ in range(220)]
        self.clouds = [paper_cloud(pg, w, rng) for w in (420, 340, 500, 300)]
        self.cloud_slots = [(rng.uniform(-200, W - 100), rng.uniform(H * 0.55, H * 0.9), rng.randrange(4),
                             rng.uniform(4, 12) * rng.choice([-1, 1])) for _ in range(6)]
        self.lines = [rng.uniform(40, W - 40) for _ in range(9)]
        self.particles = [(rng.uniform(-1, 1), rng.uniform(0, 1), rng.uniform(0.5, 1.5)) for _ in range(160)]
        self.trees = [(rng.uniform(0, W), rng.uniform(0.8, 1.3), rng.randrange(3)) for _ in range(14)]

    def sky(self, name: str):
        if name not in self.skies:
            top, mid, glow = SKIES.get(name, SKIES["cosmos"])
            self.skies[name] = gradient_glow(self.pg, top, mid, glow)
        return self.skies[name]

    def draw(self, surf, name: str, t: float) -> None:
        pg = self.pg
        surf.blit(self.sky(name), (0, 0))
        if name not in ("palace",):
            for x, y, r, ph in self.stars:
                a = 0.5 + 0.5 * math.sin(t * 2.2 + ph)
                c = int(150 + 100 * a)
                pg.draw.circle(surf, (c, c, min(255, c + 20)), (x, y), r)
        for x in self.lines:                                       # the theatre's hanging threads
            pg.draw.line(surf, (64, 56, 60), (x, 0), (x, H * 0.62), 1)
        if name == "kailash":
            self.mountains(surf, (225, 232, 245), (150, 170, 200), H * 0.62)
        if name == "forest":
            self.forest(surf, t)
        if name == "palace":
            self.palace(surf)
        if name == "space":
            self.planets(surf, t)
        if name in ("ocean", "churning", "poison"):
            if name == "churning":
                self.churn(surf, t)
            self.waves(surf, t, dark=name == "poison")
        if name == "poison":
            self.smoke(surf, t)
        if name not in ("ocean", "churning", "poison", "space"):
            self.draw_clouds(surf, t)

    def draw_clouds(self, surf, t: float) -> None:
        for x, y, k, v in self.cloud_slots:
            img = self.clouds[k]
            xx = (x + v * t) % (W + img.get_width()) - img.get_width() / 2
            surf.blit(img, (xx, y))

    def waves(self, surf, t: float, dark: bool) -> None:
        pg = self.pg
        top = H * 0.66
        for row in range(7):
            y0 = top + row * 70
            col = (20, 70 + row * 6, 100 + row * 10) if not dark else (40, 20 + row * 4, 60 + row * 8)
            pts = [(x, y0 + 14 * math.sin(x / 70 + t * 1.2 + row)) for x in range(0, W + 30, 30)]
            pg.draw.polygon(surf, col, pts + [(W, H), (0, H)])
            pg.draw.lines(surf, (200, 230, 240) if not dark else (170, 120, 200), False, pts, 3)
            for x in range(15 + row * 23 % 60, W, 120):                        # paper swirls
                pg.draw.arc(surf, (230, 245, 250) if not dark else (190, 150, 220),
                            (x, y0 + 10 * math.sin(x / 70 + t * 1.2 + row), 40, 30), 0.2, math.pi - 0.2, 2)

    def churn(self, surf, t: float) -> None:
        pg = self.pg
        cx, base = W / 2, H * 0.72
        mountain = [(cx - 150, base), (cx - 70, base - 520), (cx - 20, base - 600), (cx + 30, base - 560),
                    (cx + 90, base - 470), (cx + 160, base)]
        pg.draw.polygon(surf, (60, 50, 50), [(x, y + 6) for x, y in mountain])
        pg.draw.polygon(surf, (120, 100, 90), mountain)
        for k in range(8):                                                   # turning bands
            y = base - 60 - k * 62
            off = 40 * math.sin(t * 2.5 + k * 0.7)
            pg.draw.line(surf, (160, 140, 120), (cx - 110 + k * 8 + off * 0.3, y), (cx + 110 - k * 10 + off * 0.3, y - 14), 6)
        coil_top = base - 380
        pts = []
        for k in range(160):                                                 # the serpent rope
            u = k / 159
            y = coil_top + u * 300
            ang = u * 6 * math.pi + t * 2.5
            x = cx + math.cos(ang) * (120 + 20 * u)
            pts.append((x, y))
        pg.draw.lines(surf, (30, 60, 40), False, pts, 26)
        pg.draw.lines(surf, (80, 160, 100), False, pts, 18)
        pg.draw.line(surf, (30, 60, 40), pts[0], (60, coil_top + 120), 22)
        pg.draw.line(surf, (80, 160, 100), pts[0], (60, coil_top + 120), 14)
        pg.draw.line(surf, (30, 60, 40), pts[-1], (W - 60, coil_top + 260), 22)
        pg.draw.line(surf, (80, 160, 100), pts[-1], (W - 60, coil_top + 260), 14)
        pg.draw.circle(surf, (80, 160, 100), (52, coil_top + 116), 26)

    def smoke(self, surf, t: float) -> None:
        pg = self.pg
        layer = pg.Surface((W, H), pg.SRCALPHA)
        for dx, ph, sp in self.particles:
            u = (ph + t * 0.12 * sp) % 1.0
            x = W / 2 + dx * (80 + 380 * u) + 40 * math.sin(t * sp + ph * 10)
            y = H * 0.72 - u * 1100
            r = 40 + 120 * u
            pg.draw.circle(layer, (80, 30, 110, int(150 * (1 - u))), (x, y), r)
            pg.draw.circle(layer, (130, 60, 170, int(70 * (1 - u))), (x - r * 0.2, y - r * 0.2), r * 0.5)
        surf.blit(layer, (0, 0))

    def mountains(self, surf, snow, rock, base) -> None:
        pg = self.pg
        peaks = [(-100, 520), (220, 760), (540, 900), (820, 700), (1180, 560)]
        for x, h in peaks:
            pg.draw.polygon(surf, rock, [(x - 360, base + 300), (x, base - h + 300), (x + 360, base + 300)])
            pg.draw.polygon(surf, snow, [(x - 110, base - h + 300 + 140), (x, base - h + 300), (x + 110, base - h + 300 + 140),
                                         (x + 40, base - h + 300 + 110), (x - 30, base - h + 300 + 150)])
        pg.draw.rect(surf, rock, (0, base + 300, W, H))

    def forest(self, surf, t: float) -> None:
        pg = self.pg
        for x, sc, kind in self.trees:
            y = H * 0.8
            col = (30, 50 + kind * 12, 40)
            pg.draw.rect(surf, (50, 34, 30), (x - 10 * sc, y - 220 * sc, 20 * sc, 240 * sc))
            for k in range(3):
                pg.draw.circle(surf, col, (x + (k - 1) * 50 * sc, y - (240 + k % 2 * 40) * sc), 90 * sc)
        pg.draw.rect(surf, (36, 40, 30), (0, H * 0.8, W, H))

    def palace(self, surf) -> None:
        pg = self.pg
        for k in range(4):
            x = 60 + k * 300
            pg.draw.rect(surf, (200, 150, 100), (x, H * 0.3, 60, H * 0.5))
            pg.draw.arc(surf, (230, 180, 110), (x + 30, H * 0.22, 300, 300), 0, math.pi, 14)
        pg.draw.rect(surf, (110, 60, 50), (0, H * 0.8, W, H))

    def planets(self, surf, t: float) -> None:
        pg = self.pg
        pg.draw.circle(surf, (200, 120, 70), (W * 0.75, H * 0.28), 120)
        pg.draw.ellipse(surf, (230, 200, 160), (W * 0.75 - 200, H * 0.28 - 22, 400, 44), 6)
        pg.draw.circle(surf, (90, 140, 220), (W * 0.22, H * 0.62), 70)


_halos: dict = {}


def glow(pg, surf, centre, radius: int, colour, strength: float = 1.0) -> None:
    """A soft additive halo (an aura behind a character)."""
    r = int(radius)
    key = (r, tuple(colour), round(strength, 2))
    if key not in _halos:
        yy, xx = np.mgrid[-r:r, -r:r]
        i = np.clip(1 - np.sqrt(xx * xx + yy * yy) / r, 0, 1) ** 2 * strength
        arr = (np.array(colour)[None, None, :] * i[..., None]).clip(0, 255).astype(np.uint8)
        _halos[key] = pg.surfarray.make_surface(arr.transpose(1, 0, 2).copy())
    surf.blit(_halos[key], (centre[0] - r, centre[1] - r), special_flags=pg.BLEND_ADD)
