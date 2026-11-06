"""Stick Katha, episode 2 "Sheru", redrawn in the toon look. Run: python -m reel_engine.toon.sheru

Same script, voices, sounds and timing as pressure_cooker.py; only the drawing changes. The set and the
figures are drawn at twice the size (toon.S) and scaled down; text, the phone, the khaata and other overlays
are drawn on top at full size afterwards.
"""
import math
import random
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..stick import pressure_cooker as base
from ..stick.durvasa import RED, ease
from ..stick.pressure_cooker import (CUTS, EPISODE, HOOK, KHAATA, LABELS, LINES, MUSIC_SEED, SPEAKER_COLOUR,  # noqa: F401
                              VOICE_FX, VOICES, COMMENT, render as run)
from .kit import (H, INK, P, S, W, Bean, bean, finish, line, mix, poly, shade, shaded_ellipse, soft_shadow)

NAME = "stick_sheru_toon_hi"
FEET = 1262
BX = 300
BOY = Bean(shirt=(232, 84, 64), hair=(52, 34, 30), skin=(246, 206, 170))
FRIEND = Bean(shirt=(46, 184, 140), hair=(30, 24, 24), skin=(204, 150, 110), size=0.55)
VISHNU = Bean(shirt=(252, 196, 50), hair=(34, 30, 70), skin=(96, 150, 232), size=0.72, buttons=0)
CHITRAGUPT = Bean(shirt=(168, 36, 64), hair=(40, 30, 30), skin=(236, 190, 150), size=0.9, buttons=0)
VX, CX = 640, 885
WALL_TOP, WALL_BOTTOM = (54, 132, 152), (118, 192, 188)
FLOOR_TOP, FLOOR_BOTTOM = (206, 132, 78), (150, 86, 48)


def vgrad(pg, surf, rect, top, bottom, step=2):
    x, y, w, h = rect
    for k in range(0, int(h), step):
        pg.draw.rect(surf, mix(top, bottom, k / max(1, h)), (x, y + k, w, step))


def blurred(pg, layer, factor):
    w, h = layer.get_size()
    return pg.transform.smoothscale(pg.transform.smoothscale(layer, (max(1, w // factor), max(1, h // factor))), (w, h))


def build_room(pg):
    """The bedroom, at 2x: teal wallpapered wall, a sunset window with mustard curtains, a poster, a bed,
    a plant, a rug on a plank floor, with the window's warm light falling on the floor."""
    surf = pg.Surface((W * S, H * S))
    vgrad(pg, surf, (0, 0, W * S, 1160 * S), WALL_TOP, WALL_BOTTOM)
    for yy in range(60, 1100, 120):                                       # wallpaper diamonds
        for xx in range((yy // 120 % 2) * 60, W + 60, 120):
            pg.draw.polygon(surf, mix(WALL_TOP, WALL_BOTTOM, yy / 1160 + 0.25),
                            [P(xx, yy - 18), P(xx + 14, yy), P(xx, yy + 18), P(xx - 14, yy)])
    shadows = []
    # the floor: planks converging on a vanishing point behind the wall
    vgrad(pg, surf, (0, 1160 * S, W * S, (H - 1160) * S), FLOOR_TOP, FLOOR_BOTTOM)
    vx, vy = 540, 300
    for xb in range(-1400, W + 1500, 170):
        k = (1160 - vy) / (H - vy)
        pg.draw.line(surf, shade(FLOOR_TOP, 0.78), P(vx + (xb - vx) * k, 1160), P(xb, H), 3 * S)
    yy, gap = 1175, 22
    while yy < H:
        pg.draw.line(surf, shade(FLOOR_TOP, 0.82), P(0, yy), P(W, yy), 2 * S)
        yy += gap
        gap *= 1.35
    poly(pg, surf, [(0, 1100), (W, 1100), (W, 1160), (0, 1160)], (236, 222, 190), edge=4)   # skirting
    line(pg, surf, (0, 1106), (W, 1106), (252, 244, 222), 4)
    # window
    wx, wy, ww, wh = 640, 330, 300, 360
    shadows.append([(wx + 20, wy + 16), (wx + ww + 34, wy + 16), (wx + ww + 34, wy + wh + 40), (wx + 20, wy + wh + 40)])
    poly(pg, surf, [(wx - 16, wy - 16), (wx + ww + 16, wy - 16), (wx + ww + 16, wy + wh + 16), (wx - 16, wy + wh + 16)], (250, 246, 236), edge=4)
    vgrad(pg, surf, (wx * S, wy * S, ww * S, wh * S), (255, 128, 92), (255, 214, 130))
    shaded_ellipse(pg, surf, 840, 600, 58, 58, (255, 240, 170), ink=(255, 240, 170), edge=0, gloss=False, dark=0.97)
    for hx, hh in ((650, 80), (712, 124), (784, 70), (850, 140), (900, 92)):
        poly(pg, surf, [(hx, wy + wh - hh), (hx + 52, wy + wh - hh), (hx + 52, wy + wh), (hx, wy + wh)], (118, 66, 110), edge=0)
        for wy2 in range(wy + wh - hh + 14, wy + wh - 10, 26):
            pg.draw.rect(surf, (255, 214, 120), (*P(hx + 12, wy2), 10 * S, 10 * S))
    line(pg, surf, (wx + ww / 2, wy), (wx + ww / 2, wy + wh), (250, 246, 236), 10)
    line(pg, surf, (wx, wy + wh / 2), (wx + ww, wy + wh / 2), (250, 246, 236), 10)
    pg.draw.rect(surf, INK, (*P(wx, wy), ww * S, wh * S), 4 * S)
    poly(pg, surf, [(wx - 34, wy + wh + 16), (wx + ww + 34, wy + wh + 16), (wx + ww + 34, wy + wh + 38), (wx - 34, wy + wh + 38)], (226, 220, 206), edge=3)
    shadows.append([(wx - 28, wy + wh + 38), (wx + ww + 40, wy + wh + 38), (wx + ww + 54, wy + wh + 74), (wx - 14, wy + wh + 74)])
    # curtains with folds, and the rod
    for cx in (590, 990):
        pts = [(cx - 34, 300), (cx + 34, 300), (cx + 50, 740), (cx - 50, 740)]
        shadows.append([(p[0] + 26, p[1] + 20) for p in pts])
        poly(pg, surf, pts, (242, 182, 52), edge=5)
        for f in (-0.5, 0.0, 0.5):
            line(pg, surf, (cx + f * 34, 312), (cx + f * 50, 730), (212, 146, 34), 7)
            line(pg, surf, (cx + f * 34 + 9, 312), (cx + f * 50 + 11, 730), (255, 214, 110), 3)
    line(pg, surf, (540, 300), (1040, 300), (120, 76, 50), 12)
    for cx in (540, 1040):
        shaded_ellipse(pg, surf, cx, 300, 13, 13, (190, 130, 70), edge=3, gloss=False)
    # poster: a planet
    px, py, pw, ph = 110, 380, 220, 300
    shadows.append([(px + 18, py + 18), (px + pw + 26, py + 18), (px + pw + 26, py + ph + 26), (px + 18, py + ph + 26)])
    poly(pg, surf, [(px - 10, py - 10), (px + pw + 10, py - 10), (px + pw + 10, py + ph + 10), (px - 10, py + ph + 10)], (250, 246, 236), edge=4)
    vgrad(pg, surf, (px * S, py * S, pw * S, ph * S), (40, 30, 84), (90, 50, 120))
    pg.draw.ellipse(surf, (255, 220, 100), (*P(130, 505), 180 * S, 30 * S), 6 * S)
    shaded_ellipse(pg, surf, 220, 520, 66, 66, (250, 120, 160), edge=4)
    pg.draw.arc(surf, (255, 220, 100), (*P(130, 505), 180 * S, 30 * S), math.pi, 2 * math.pi, 6 * S)
    for sx, sy in ((150, 420), (290, 440), (170, 640), (280, 620), (300, 560)):
        pg.draw.circle(surf, (255, 255, 255), P(sx, sy), 4 * S)
    # the window's light on the floor
    q = 4
    lay = pg.Surface((W // q, H // q), pg.SRCALPHA)
    pg.draw.polygon(lay, (255, 190, 120, 90), [(x // q, y // q) for x, y in ((560, 1170), (900, 1170), (760, 1560), (300, 1560))])
    surf.blit(pg.transform.smoothscale(blurred(pg, lay, 6), (W * S, H * S)), (0, 0))
    # the rug
    soft_shadow(pg, surf, 580, 1372, 280, 70, 90)
    for k_, c in ((1.0, (200, 60, 90)), (0.75, (250, 200, 70)), (0.5, (60, 170, 160)), (0.25, (250, 250, 240))):
        shaded_ellipse(pg, surf, 560, 1360, 260 * k_, 62 * k_, c, edge=5 if k_ == 1.0 else 0, ink=INK, gloss=False, dark=0.9)
    # the bed: headboard, a box with a top and a front, blanket stripes, a pillow
    shadows.append([(70, 1200), (470, 1200), (560, 1250), (150, 1250)])
    poly(pg, surf, [(28, 880), (78, 880), (78, 1210), (28, 1210)], (150, 92, 58), edge=5)
    poly(pg, surf, [(40, 1030), (430, 1030), (462, 1000), (72, 1000)], (84, 104, 196), edge=5)
    poly(pg, surf, [(40, 1030), (430, 1030), (430, 1200), (40, 1200)], (62, 80, 170), edge=5)
    poly(pg, surf, [(430, 1030), (462, 1000), (462, 1170), (430, 1200)], (46, 60, 140), edge=5)
    for xx in range(70, 420, 50):
        line(pg, surf, (xx, 1045), (xx + 20, 1188), (130, 156, 230), 7)
    poly(pg, surf, [(90, 950), (210, 950), (222, 1004), (80, 1004)], (255, 246, 222), edge=5)
    line(pg, surf, (110, 965), (180, 962), (255, 255, 255), 5)
    # the plant
    shadows.append([(1000, 1180), (1060, 1180), (1100, 1210), (1030, 1214)])
    for a in (-0.7, -0.3, 0.1, 0.5, 0.85):
        tip = (1020 + 130 * math.sin(a), 1060 - 160 * math.cos(a))
        line(pg, surf, (1020, 1060), tip, (40, 140, 70), 10)
        shaded_ellipse(pg, surf, tip[0], tip[1], 34, 20, (70, 190, 96), edge=4, gloss=False)
    poly(pg, surf, [(984, 1060), (1056, 1060), (1046, 1184), (994, 1184)], (186, 100, 70), edge=5)
    poly(pg, surf, [(978, 1050), (1062, 1050), (1062, 1072), (978, 1072)], (206, 120, 86), edge=4)
    # shadows: one layer, softened, multiplied in; then a contact shadow along the wall's foot
    lay = pg.Surface((W // q, H // q), pg.SRCALPHA)
    for pts in shadows:
        pg.draw.polygon(lay, (40, 30, 60, 80), [(x // q, y // q) for x, y in pts])
    pg.draw.rect(lay, (40, 30, 50, 90), (0, 1160 // q, W // q, 4))
    surf.blit(pg.transform.smoothscale(blurred(pg, lay, 3), (W * S, H * S)), (0, 0))
    top = pg.Surface((W // 8, H // 8), pg.SRCALPHA)                       # cooler at the top of the wall
    for yy in range(0, 60):
        pg.draw.line(top, (20, 30, 60, int(70 * (1 - yy / 60))), (0, yy), (W // 8, yy))
    surf.blit(pg.transform.smoothscale(top, (W * S, H * S)), (0, 0))
    return surf


def cloud(pg, surf, cx, cy, s=1.0):
    puffs = ((-200, 25, 55), (-150, 10, 70), (-70, -30, 90), (30, -40, 100), (130, -5, 80), (200, 20, 60))
    soft_shadow(pg, surf, cx, cy + 70 * s, 240 * s, 30 * s, 60)
    for dx, dy, r in puffs:
        shaded_ellipse(pg, surf, cx + dx * s, cy + dy * s, r * s, r * s, (255, 255, 255), edge=6, dark=0.86, gloss=False)
    poly(pg, surf, [(cx - 230 * s, cy + 10 * s), (cx + 240 * s, cy + 10 * s), (cx + 230 * s, cy + 70 * s), (cx - 220 * s, cy + 70 * s)],
         (236, 222, 240), edge=0)
    line(pg, surf, (cx - 220 * s, cy + 72 * s), (cx + 230 * s, cy + 72 * s), INK, 6)


def chakra(pg, surf, at, t, r=24):
    shaded_ellipse(pg, surf, at[0], at[1], r, r, (255, 200, 60), edge=4)
    for j in range(6):
        a = t * 8 + j * math.pi / 3
        line(pg, surf, at, (at[0] + r * 0.85 * math.cos(a), at[1] + r * 0.85 * math.sin(a)), INK, 3)
    shaded_ellipse(pg, surf, at[0], at[1], 6, 6, (230, 60, 60), edge=2, gloss=False)


def conch(pg, surf, at):
    x, y = at
    shaded_ellipse(pg, surf, x, y - 18, 18, 26, (255, 250, 240), edge=4)
    pg.draw.arc(surf, INK, (*P(x - 9, y - 30), 18 * S, 20 * S), 0, 4.5, 3 * S)
    poly(pg, surf, [(x - 6, y + 6), (x + 6, y + 6), (x, y + 18)], (250, 236, 220), edge=3)


class Skit(base.Skit):
    def __init__(self, pg):
        super().__init__(pg)
        self.big_room = build_room(pg)
        xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H), indexing="ij")
        self.vignette = (1 - 0.28 * np.clip((xs ** 2 * 0.8 + ys ** 2 * 0.6) - 0.25, 0, None)).astype(np.float32)
        rng = np.random.default_rng(3)
        self.grains = [rng.normal(0, 3.5, (W, H)).astype(np.float32) for _ in range(4)]
        self.small_room = pg.transform.smoothscale(self.big_room, (W, H))
        finish(pg, self.small_room, self.grains[0], self.vignette)
        self.big = pg.Surface((W * S, H * S))
        self.layer = pg.Surface((W * S, H * S), pg.SRCALPHA)
        self.halo = pg.Surface((160, 160), pg.SRCALPHA)
        for r, a in ((80, 50), (60, 70), (40, 90)):
            pg.draw.circle(self.halo, (255, 220, 120, a), (80, 80), r)
        self.halo = pg.transform.smoothscale(blurred(pg, self.halo, 4), (int(560 * S), int(560 * S)))
        self.frame_no = 0

    # ------------------------------------------------------------ helpers
    def room(self, surf, dim=0.0):
        surf.blit(self.small_room, (0, 0))
        if dim:
            veil = self.pg.Surface((W, H), self.pg.SRCALPHA)
            veil.fill((255, 214, 120, int(50 * dim)))
            surf.blit(veil, (0, 0))

    def front(self, draw):
        """Draw a toon figure in front of the overlays: at 2x on a clear layer, scaled down onto the frame."""
        self.layer.fill((0, 0, 0, 0))
        out = draw(self.layer)
        self._front = self.pg.transform.smoothscale(self.layer, (W, H))
        return out

    def talk(self, i, who, since, length, t):
        if LINES[i][0] != who or since > length - base.GAP - 0.05:
            return 0.0
        return abs(math.sin(t * 13)) * (0.65 + 0.35 * math.sin(t * 4.1))

    def rays(self, big, k, t):
        pg = self.pg
        q = 4
        lay = pg.Surface((W // q, H // q), pg.SRCALPHA)
        cx, cy = VX / q, 380 / q
        for j in range(12):
            a = t * 0.15 + j * math.pi / 6
            pts = [(cx, cy), (cx + 500 * math.cos(a - 0.08), cy + 500 * math.sin(a - 0.08)),
                   (cx + 500 * math.cos(a + 0.08), cy + 500 * math.sin(a + 0.08))]
            pg.draw.polygon(lay, (255, 226, 120, int(55 * k)), pts)
        pg.draw.polygon(lay, (255, 236, 160, int(80 * k)), [(cx - 40, 0), (cx + 40, 0), (cx + 90, FEET / q), (cx - 90, FEET / q)])
        big.blit(pg.transform.smoothscale(blurred(pg, lay, 2), (W * S, H * S)), (0, 0))

    def sparkles(self, surf, k, t):
        pg = self.pg
        rng = random.Random(int(t * 6))
        for _ in range(int(14 * k)):
            x, y = rng.uniform(150, W - 100), rng.uniform(150, FEET - 200)
            pg.draw.line(surf, (255, 250, 200), (x - 10, y), (x + 10, y), 3)
            pg.draw.line(surf, (255, 250, 200), (x, y - 10), (x, y + 10), 3)

    def god(self, big, i, since, length, t, k_in=1.0, mood="happy", bless=False, palm=False):
        """Bhagwan Vishnu on his cloud, coming down as k_in goes 0 -> 1."""
        pg = self.pg
        fy = -320 + 1010 * ease(k_in)
        big.blit(self.halo, self.halo.get_rect(center=P(VX, fy - 330)))
        reach = [None, None]
        if bless:
            reach[1] = (VX + 150, fy - 330)
        if palm:
            reach[0] = (VX - 10, fy - 300)
        pts = bean(pg, big, VX, fy, VISHNU, mood, self.talk(i, "vishnu", since, length, t), (t % 3.9) < 0.1,
                   t=t, look=-0.4, extras=("mukut", "four_arms", "tilak"), reach=tuple(reach), lift=0)
        cloud(pg, big, VX, fy + 20, 0.85)
        if pts["upper"]:
            conch(pg, big, pts["upper"][0])
            chakra(pg, big, (pts["upper"][1][0], pts["upper"][1][1] - 24), t)
        return pts

    def scribe(self, big, i, since, length, t, arrive=9.0):
        """Chitragupt Ji, holding his scroll; the scroll itself is drawn later, over his hands."""
        if arrive < 0.15:
            return None
        return bean(self.pg, big, CX, FEET, CHITRAGUPT, "neutral" if i != 14 else "closed",
                    self.talk(i, "chitragupt", since, length, t), (t % 4.3) < 0.1, t=t + 2, look=-0.5,
                    extras=("crown", "mustache"), grip=(CX - 20, FEET - 330, 60))

    def scroll(self, surf, pts, k, t, writing=False):
        pg = self.pg
        if not pts:
            return
        hx = (pts["hands"][0][0] + pts["hands"][1][0]) / 2
        top = pts["hands"][0][1] - 30
        length = 60 + 300 * ease(k)
        pg.draw.rect(surf, (250, 236, 200), (hx - 70, top, 140, length))
        pg.draw.rect(surf, (226, 206, 160), (hx + 40, top, 30, length))
        pg.draw.rect(surf, INK, (hx - 70, top, 140, length), 4)
        rng = random.Random(4)
        for row in range(int(length / 26) - 1):
            w = rng.randint(50, 100)
            pg.draw.line(surf, (150, 120, 90), (hx - 56, top + 20 + row * 26), (hx - 56 + w, top + 20 + row * 26), 4)
        for y in (top - 14, top + length - 10):
            pg.draw.rect(surf, (176, 112, 60), (hx - 86, y, 172, 24), border_radius=10)
            pg.draw.rect(surf, INK, (hx - 86, y, 172, 24), 4, border_radius=10)
        if writing:
            qx, qy = hx - 20 + 20 * math.sin(t * 14), top + length * 0.6
            pg.draw.line(surf, INK, (qx, qy), (qx + 40, qy - 70), 5)
            pg.draw.polygon(surf, (240, 240, 240), [(qx + 40, qy - 70), (qx + 70, qy - 120), (qx + 30, qy - 60)])

    def poof(self, surf, since):
        if since >= 0.5:
            return
        pg = self.pg
        for j in range(9):
            a = j * 2 * math.pi / 9
            r = 60 + since * 400
            c = (int(CX + math.cos(a) * r * 0.6), int(FEET - 260 + math.sin(a) * r * 0.4))
            rad = int(70 * (1 - since / 0.5)) + 10
            pg.draw.circle(surf, INK, c, rad + 5)
            pg.draw.circle(surf, (214, 214, 226), c, rad)
            pg.draw.circle(surf, (240, 240, 248), (c[0] - rad // 4, c[1] - rad // 4), int(rad * 0.7))

    def packet(self, surf, k, t):
        """Episode 2's SHERU packet, moved down so it clears the call window's name bar."""
        lay = self.pg.Surface((W, H), self.pg.SRCALPHA)
        self.doggee(lay, k, t)
        surf.blit(lay, (30, 130))

    def boy(self, big, i, since, length, t, mood, x=BX, reach=(None, None), skin=None, lift=0.0, blush=0.0, arms=None):
        return bean(self.pg, big, x, FEET, BOY, mood, self.talk(i, "boy", since, length, t), (t % 3.3) < 0.12, t=t,
                    look=0.5, reach=reach, skin=skin, lift=lift, blush=blush, arms=arms)

    def khaata(self, surf, since, length, t):
        """The ledger close-up from episode 2, with the toon boy wilting in front of it."""
        pg = self.pg
        k = ease(since / 0.4)
        if k <= 0:
            return
        page = pg.Rect(0, 0, 940, 760)
        page.center = (W / 2, 745 + (1 - k) * 1100)
        veil = pg.Surface((W, H), pg.SRCALPHA)
        veil.fill((20, 10, 30, int(110 * k)))
        surf.blit(veil, (0, 0))
        sh = pg.Surface((page.width, page.height), pg.SRCALPHA)
        sh.fill((0, 0, 0, 70))
        surf.blit(sh, page.move(18, 22))
        pg.draw.rect(surf, (250, 236, 200), page, border_radius=18)
        for yy in range(page.top + 150, page.bottom - 20, 70):
            pg.draw.line(surf, (220, 196, 150), (page.left + 30, yy + 34), (page.right - 30, yy + 34), 3)
        pg.draw.rect(surf, INK, page, 7, border_radius=18)
        for y in (page.top - 14, page.bottom - 10):
            pg.draw.rect(surf, (170, 110, 60), (page.left - 20, y, page.width + 40, 26), border_radius=12)
            pg.draw.rect(surf, INK, (page.left - 20, y, page.width + 40, 26), 4, border_radius=12)
        head = self.text(self.f_mid, "KHAATA: LADKA (2026)", (150, 40, 50), 0)
        surf.blit(head, head.get_rect(midtop=(W / 2, page.top + 30)))
        total = sum(len(sp) + 1 for sp, _ in KHAATA)
        done = 0
        from ..core.text import fit_width
        for j, (spoken, entry) in enumerate(KHAATA):
            at = 0.15 + (length - 0.4) * done / total
            done += len(spoken) + 1
            if j == 0 or since < at:
                continue
            img = fit_width(pg, self.text(self.f_list, entry, (60, 40, 40) if j < 4 else (190, 40, 50), 0), page.width - 140)
            qk = ease((since - at) / 0.18)
            y = page.top + 150 + (j - 1) * 70
            sc = 1 + 0.4 * (1 - qk)
            im = pg.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
            im.set_alpha(int(255 * qk))
            surf.blit(im, im.get_rect(midleft=(page.left + 90, y + 4)))
            pg.draw.circle(surf, (190, 40, 50), (page.left + 52, int(y + 4)), 14)
            key = f"item{j}"
            if key not in self.cache:
                self.cache[key] = 1
                self.events.append((t, "ding"))
        late = since > length * 0.45
        palm = since > length * 0.7
        small = Bean(shirt=BOY.shirt, hair=BOY.hair, skin=BOY.skin, size=1.05)

        def draw(lay):
            hy = 1900 - 250 * 1.05 - 128 * 1.05 * 1.65 - 96 * 1.05 * 0.55
            reach = ((170, hy + 20), None) if palm else (None, None)
            arms = ((2.5, 0.4), (2.5, 0.4)) if since < length * 0.2 else None
            return bean(pg, lay, 210, 1900, small, "shy" if late else "shock", 0.0, False, t=t, look=0.5,
                        blush=1.0 if late else 0.0, reach=reach, arms=arms)
        self.front(draw)
        surf.blit(self._front, (0, 0))

    # ------------------------------------------------------------ the scenes
    def scene(self, surf, i, since, length, t):
        pg = self.pg
        self._t = t
        cam = (1.0, W / 2, H / 2)
        big = self.big
        big.blit(self.big_room, (0, 0))
        post = []                                                           # overlays, drawn at 1x afterwards
        divine = 2 <= i <= 8 or i == 14
        if divine:
            self.rays(big, min(1.0, since * 2) if i == 2 else 1.0, t)

        if i <= 1:                                                          # the angry call, then the throw
            red = mix(BOY.skin, (250, 120, 100), 0.5 if i == 0 else 0.7)
            ear = (BX + 108, FEET - 505)
            if i == 0:
                pts = self.boy(big, i, since, length, t, "angry", reach=(None, ear), skin=red)
                post.append(lambda s: self.phone(s, (pts["hands"][1][0] + 4, pts["hands"][1][1] + 4), angle=-15))
                post.append(lambda s: self.steam(s, (pts["head"][0], pts["top"]), t, 6, 0.9))
                if (since * 2) % 1 < 0.5:
                    post.append(lambda s: self.pop_text(s, self.f_mid, "!!", RED, (pts["head"][0] + 150, pts["top"] - 30), 1.0, 10))
            else:
                tk = max(0.0, (since - (length - 1.1)) / 0.7)
                if tk <= 0:
                    hand = ear
                else:
                    a = -2.6 + 4.5 * ease(min(1.0, tk / 0.75))
                    sx, sy = BX + 70, FEET - 520
                    hand = (sx + math.sin(a) * 205, sy + math.cos(a) * 205)
                pts = self.boy(big, i, since, length, t, "angry", reach=(None, hand), skin=red)
                post.append(lambda s: self.steam(s, (pts["head"][0], pts["top"]), t, 3, 1.3))
                if tk <= 0.75:
                    post.append(lambda s: self.phone(s, (pts["hands"][1][0] + 4, pts["hands"][1][1] + 4), angle=-15 - tk * 300))
                else:
                    qk = min(1.0, (tk - 0.75) / 0.25)
                    sx, sy = pts["hands"][1]
                    post.append(lambda s: self.phone(s, (sx + (640 - sx) * qk, sy + (FEET - 50 - sy) * qk), cracked=qk >= 1, angle=qk * 400))
                    if qk >= 1:
                        post.append(lambda s: self.pop_text(s, self.f_big, "CRASH!", RED, (660, FEET - 280), (tk - 1.0) * 4 + 0.3, -8))
                        cam = (1.04, 620, FEET - 220)
                        if "crash" not in self.cache:
                            self.cache["crash"] = 1
                            self.events.append((t, "crash"))
        elif i in (2, 3, 4):                                                # a voice from the clouds
            post.append(lambda s: self.phone(s, (640, FEET - 50), cracked=True, angle=40))
            gp = self.god(big, i, since, length, t, since / 0.9 if i == 2 else 1.0, bless=i == 4 and since > length * 0.5)
            up = i == 2 and since < 1.0
            pts = self.boy(big, i, since, length, t, "shock" if i == 2 else "worried",
                           arms=((2.6, 0.3), (2.6, 0.3)) if up else None)
            if i == 2:
                post.append(lambda s: self.tag(s, "BHAGWAN VISHNU", "Customer support, live", (40, 1480), (since - 0.6) / 0.6))
                if since < 0.15 and "chime" not in self.cache:
                    self.cache["chime"] = 1
                    self.events.append((t, "chime"))
            if i == 4 and since > length * 0.6:
                post.append(lambda s: self.pop_text(s, self.f_big, "?!", RED, (pts["head"][0] + 130, pts["top"] - 40), (since - length * 0.6) / 0.3))
        elif i in (5, 6, 7):                                                # Chitragupt Ji and the khaata
            post.append(lambda s: self.phone(s, (640, FEET - 50), cracked=True, angle=40))
            self.god(big, i, since, length, t)
            arrive = since if i == 5 else 9.0
            if i == 5 and since < 0.1 and "poof" not in self.cache:
                self.cache["poof"] = 1
                self.events.append((t, "poof"))
            roll = 0.0 if i == 5 and since < 0.9 else (min(1.0, (since - 0.9) / 0.8) if i == 5 else 1.0)
            if i == 5 and roll > 0 and "unroll" not in self.cache:
                self.cache["unroll"] = 1
                self.events.append((t, "unroll"))
            cp = self.scribe(big, i, since, length, t, arrive)
            post.append(lambda s: self.scroll(s, cp, roll, t))
            if i == 5:
                post.append(lambda s: self.poof(s, since))
                post.append(lambda s: self.tag(s, "CHITRAGUPT JI", "Head of Accounts, Yamlok", (40, 1480), (since - 0.5) / 0.6))
            if i != 7:
                self.boy(big, i, since, length, t, "shock" if i == 6 else "worried")
            else:
                post.append(lambda s: self.khaata(s, since, length, t))
        elif i in (8, 9):                                                   # the promise, then the apology
            if i == 8:
                self.god(big, i, since, length, t)
                cp = self.scribe(big, i, since, length, t)
                post.append(lambda s: self.scroll(s, cp, 1.0, t))
                chest = (BX + 6, FEET - 560)
                self.boy(big, i, since, length, t, "worried", reach=((chest[0] - 4, chest[1]), (chest[0] + 4, chest[1])))
                post.append(lambda s: self.phone(s, (640, FEET - 50), cracked=True, angle=40))
            else:
                pick = ease(since / 0.8)
                x = BX + 120 * pick
                ear = (x + 108, FEET - 505)
                target = (640, FEET - 50) if pick < 0.5 else ear
                pts = self.boy(big, i, since, length, t, "neutral", x=x, reach=(None, target))
                hx, hy = pts["hands"][1]
                at = (640 + (hx - 640) * pick, FEET - 50 + (hy - FEET + 50) * pick)
                post.append(lambda s: self.phone(s, at, cracked=True, angle=40 * (1 - pick) - 15 * pick))
                if pick >= 1:
                    post.append(lambda s: self.pop_text(s, self.f_mid, "CALLING...", INK, (W / 2 + 160, 520), (since - 0.8) / 0.3, 0, outline=0))
        elif i in (10, 11, 12, 13):                                         # the call: the friend in a window
            x = BX + 120
            mood = {10: "worried", 11: "neutral", 12: "shock", 13: "angry"}[i]
            pts = self.boy(big, i, since, length, t, mood, x=x, reach=(None, (x + 108, FEET - 505)),
                           skin=mix(BOY.skin, (250, 120, 100), 0.5) if i == 13 else None)
            post.append(lambda s: self.phone(s, (pts["hands"][1][0] + 4, pts["hands"][1][1] + 4), cracked=True, angle=-15))
            win = pg.Rect(560, 230, 470, 560)
            soft_shadow(pg, big, win.centerx + 20, win.bottom + 30, 240, 30, 70)
            vgrad(pg, big, (win.left * S, win.top * S, win.width * S, win.height * S), (120, 90, 200), (240, 140, 176))
            shaded_ellipse(pg, big, win.left + 380, win.top + 130, 44, 44, (255, 220, 120), edge=0, gloss=False, dark=0.95)
            poly(pg, big, [(win.left, win.bottom - 90), (win.right, win.bottom - 90), (win.right, win.bottom), (win.left, win.bottom)], (110, 70, 120), edge=0)
            fx = win.centerx - 30
            bean(pg, big, fx, win.bottom - 40, FRIEND, "happy", self.talk(i, "friend", since, length, t), (t % 3.6) < 0.1,
                 t=t + 1, look=-0.5, reach=((fx - 58, win.bottom - 40 - 280), None))
            post.append(lambda s: self.phone(s, (fx - 60, win.bottom - 40 - 285), angle=15))
            hx_, hy_ = fx + 100, win.top + 90 + 8 * math.sin(t * 4)       # his girlfriend's heart sticker
            for dx in (-14, 14):
                shaded_ellipse(pg, big, hx_ + dx, hy_, 19, 19, (240, 80, 110), edge=0, gloss=False, dark=0.9)
            poly(pg, big, [(hx_ - 32, hy_ + 6), (hx_ + 32, hy_ + 6), (hx_, hy_ + 46)], (240, 80, 110), edge=0)
            pg.draw.rect(big, INK, (*P(win.left, win.top), win.width * S, win.height * S), 8 * S, border_radius=30 * S)

            def bar(s):
                name = self.text(self.f_small, "BHAI (ON CALL)", (255, 255, 255), 0)
                r = pg.Rect(win.left, win.bottom - 4, win.width, 56)
                pg.draw.rect(s, (40, 40, 60), r, border_radius=16)
                s.blit(name, name.get_rect(center=r.center))
            post.append(bar)
            if i == 12:
                post.append(lambda s: self.pop_text(s, self.f_big, "?", RED, (pts["head"][0] + 130, pts["top"] - 30), since / 0.3, 10))
            if i == 13 and since > 0.4:
                post.append(lambda s: self.packet(s, ease((since - 0.4) / 0.3), t))
        elif i == 14:                                                       # whistle!
            self.god(big, i, since, length, t, mood="closed", palm=True)
            cp = self.scribe(big, i, since, length, t)
            post.append(lambda s: self.scroll(s, cp, 1.0, t, writing=True))
            heat = min(1.0, since / 0.5)
            pts = self.boy(big, i, since, length, t, "angry", skin=mix(BOY.skin, (240, 70, 60), heat),
                           lift=abs(6 * math.sin(t * 40)) * heat, reach=((BX - 80, FEET - 300), (BX + 80, FEET - 300)))

            def jet(s):
                hx, hy = pts["head"][0], pts["top"]
                for j in range(4):
                    y = hy - 20 - j * 70 - (since * 400) % 70
                    r = 22 + j * 12
                    c = (int(hx + math.sin(t * 20 + j) * 10), int(y))
                    pg.draw.circle(s, (150, 150, 160), c, r + 4)
                    pg.draw.circle(s, (255, 255, 255), c, r)
            post.append(jet)
            if "whistle" not in self.cache:
                self.cache["whistle"] = 1
                self.events.append((t, "whistle"))
            post.append(lambda s: self.pop_text(s, self.f_big, "SEETI!", RED, (300, 470), since / 0.3, 8))
            cam = (1.0 + 0.02 * math.sin(since * 50), W / 2, H / 2)

        surf.blit(self.pg.transform.smoothscale(big, (W, H)), (0, 0))
        self.frame_no += 1
        finish(pg, surf, self.grains[self.frame_no % 4], self.vignette)
        if divine:
            self.sparkles(surf, 1.0, t)
        for draw in post:
            draw(surf)
        self.draw_puffs(surf)
        return cam


def end_card(sk, frame, t, e):
    pts = sk.front(lambda lay: bean(sk.pg, lay, 300, FEET, BOY, "angry", 0.0, False, t=t, look=0.5,
                                    skin=mix(BOY.skin, (240, 90, 80), 0.6)))
    frame.blit(sk._front, (0, 0))
    sk.steam(frame, (pts["head"][0], pts["top"]), t, 3, 1.0)


def render(out_dir: Path) -> Path:
    import sys
    return run(out_dir, sys.modules[__name__])


if __name__ == "__main__":
    import datetime
    import sys
    if "--still" in sys.argv:                                               # one frame per scene, no voices
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame as pg
        pg.init()
        sk = Skit(pg)
        out = REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME / "stills"
        out.mkdir(parents=True, exist_ok=True)
        surf = pg.Surface((W, H))
        for i in [int(a) for a in sys.argv[sys.argv.index("--still") + 1:]] or range(len(LINES)):
            sk.cache = {k: v for k, v in sk.cache.items() if not isinstance(v, int)}
            sk.scene(surf, i, 1.6, 4.0, 10.0 + i)
            pg.image.save(surf, str(out / f"scene_{i:02d}.png"))
        print(out)
    else:
        render(REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME)
