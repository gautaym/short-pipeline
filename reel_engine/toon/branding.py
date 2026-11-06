"""Channel art for "Bhess ki Eyes" (a dark-comedy joke channel, 2026-11-06), drawn in the chibi look.
Run: python -m reel_engine.toon.branding   -> out/channel_bhess_ki_eyes/

    banner.png      2048 x 1152; the title sits inside YouTube's safe area (1235 x 338 in the middle),
                    so it shows on phones, desktops and TVs alike
    profile.png     800 x 800; reads in YouTube's circle crop down to about 98 px
    watermark.png   150 x 150 with a transparent background, for the video watermark

The mascot is a chibi bhains (water buffalo) with huge shiny, sly eyes: the channel's name made literal.
Night colours with neon accents, for dark comedy rather than a kids' channel.
"""
import math
import os
import random
from pathlib import Path

from .chibi import CHIBI, Act, Painter, Z, dark, ease, ell, light, man, mix, spline

INK = (40, 28, 40)


def buffalo(p, cx, cy, s, look=0.0, wink=False, sly=True):
    """The mascot's face, centred on (cx, cy): curved horns, leafy ears, a charcoal face, a pink muzzle,
    big shiny eyes with lashes, rosy cheeks and a grin."""
    face = (74, 70, 84)
    horn = (240, 226, 200)
    for side in (-1, 1):                                                  # horns, curving up and out
        h = spline([(cx + side * 70 * s, cy - 108 * s), (cx + side * 190 * s, cy - 180 * s), (cx + side * 268 * s, cy - 120 * s),
                    (cx + side * 262 * s, cy - 52 * s), (cx + side * 222 * s, cy - 110 * s), (cx + side * 128 * s, cy - 86 * s)], 8)
        p.fill(h, horn)
        p.stroke([(cx + side * 240 * s, cy - 136 * s), (cx + side * 262 * s, cy - 70 * s)], 6 * s, dark(horn, 0.8), closed=False)
    for side in (-1, 1):                                                  # ears, out to the sides
        p.fill(ell(cx + side * 165 * s, cy - 18 * s, 66 * s, 30 * s, 36, rot=side * 0.35), face)
        p.fill(ell(cx + side * 170 * s, cy - 16 * s, 42 * s, 15 * s, 30, rot=side * 0.35), (236, 150, 160), shade=False, ink=False)
    head = spline([(cx - 112 * s, cy - 118 * s), (cx, cy - 132 * s), (cx + 112 * s, cy - 118 * s), (cx + 152 * s, cy - 10 * s),
                   (cx + 138 * s, cy + 92 * s), (cx + 92 * s, cy + 158 * s), (cx - 92 * s, cy + 158 * s), (cx - 138 * s, cy + 92 * s),
                   (cx - 152 * s, cy - 10 * s)], 8)
    p.fill(head, face)
    for dx in (-26, 0, 26):                                               # a little tuft on the forehead
        p.fill([(cx + dx * s - 20 * s, cy - 118 * s), (cx + dx * s + 6 * s, cy - 165 * s), (cx + dx * s + 20 * s, cy - 116 * s)], dark(face, 0.8), shade=False)
    p.fill(ell(cx, cy + 98 * s, 118 * s, 78 * s, 60), (214, 170, 170))   # the muzzle
    for side in (-1, 1):
        p.fill(ell(cx + side * 44 * s, cy + 86 * s, 15 * s, 22 * s, 30, rot=side * 0.4), (90, 50, 60), shade=False)
    if sly:                                                               # a lopsided smirk
        p.stroke(spline([(cx - 40 * s, cy + 128 * s), (cx + 10 * s, cy + 134 * s), (cx + 46 * s, cy + 116 * s), (cx + 58 * s, cy + 104 * s)], 8, closed=False),
                 7 * s, (110, 50, 60), closed=False)
    else:
        p.stroke(ell(cx, cy + 118 * s, 46 * s, 26 * s, 30, 0.2, math.pi - 0.2), 6 * s, (110, 50, 60), closed=False)   # grin
    for side in (-1, 1):                                                  # rosy cheeks
        p.glow((cx + side * 112 * s, cy + 34 * s), 34 * s, 18 * s, (250, 120, 140), 150)
    for side in (-1, 1):                                                  # the eyes: the whole point
        ex, ey, r = cx + side * 64 * s, cy - 22 * s, 58 * s
        if wink and side > 0:
            p.stroke(ell(ex, ey + r * 0.2, r * 0.8, r * 0.55, 24, math.pi * 1.1, math.pi * 1.9), 8 * s, INK, closed=False)
            continue
        p.fill(ell(ex, ey, r * 0.86, r, 48), (255, 255, 255), shade=False, grad=False)
        p.fill(ell(ex + look * r * 0.2, ey + r * 0.14, r * 0.66, r * 0.78, 48), (150, 92, 40), shade=False, grad=True, ink=False)
        p.fill(ell(ex + look * r * 0.2, ey + r * 0.2, r * 0.4, r * 0.46, 36), (24, 16, 14), shade=False, grad=False, ink=False)
        p.dot((ex + look * r * 0.2 - r * 0.26, ey - r * 0.18), r * 0.22, (255, 255, 255))
        p.dot((ex + look * r * 0.2 + r * 0.22, ey + r * 0.42), r * 0.11, (255, 255, 255))
        if sly:                                                           # heavy lids: up to something
            lid_y = ey - r * (0.12 if side < 0 else 0.3)
            line_ = lambda x_: lid_y + side * r * 0.08 * (ex - x_) / r       # the lid's edge, tilted a little
            top = [(ex + math.cos(a) * r * 0.9, ey + math.sin(a) * r * 1.04) for a in [math.pi * (1 + k / 30) for k in range(31)]]
            top = [q for q in top if q[1] < line_(q[0])]
            if top:                                                       # the lid follows the eye's curve
                p.fill(top + [(x_, line_(x_)) for x_, _ in reversed(top)], dark(face, 0.85), shade=False, grad=False, ink=False)
            p.stroke([(top[0][0] if top else ex - r * 0.88, line_(top[0][0] if top else ex - r * 0.88)),
                      (top[-1][0] if top else ex + r * 0.88, line_(top[-1][0] if top else ex + r * 0.88))], 8 * s, INK, closed=False)
            p.stroke(ell(ex, ey, r * 0.9, r * 1.04, 30, math.pi * 1.0, math.pi * 2.0), 6 * s, INK, closed=False)
            by = ey - r * (1.25 if side > 0 else 1.0)                     # the right brow up, the left one down
            p.stroke([(ex - r * 0.6, by + side * r * 0.12), (ex + r * 0.6, by - side * r * 0.12)], 9 * s, (34, 30, 40), closed=False)
        else:
            p.stroke(ell(ex, ey + 2 * s, r * 0.95, r * 1.08, 30, math.pi * 1.05, math.pi * 1.95), 7 * s, INK, closed=False)
            for k in range(3):                                            # lashes
                a = math.pi * (1.2 + 0.18 * k) if side < 0 else math.pi * (1.8 - 0.18 * k)
                x0, y0 = ex + math.cos(a) * r * 0.95, ey + math.sin(a) * r * 1.05
                p.stroke([(x0, y0), (x0 + math.cos(a) * r * 0.32, y0 + math.sin(a) * r * 0.32)], 6 * s, INK, closed=False)


def placed(pg, surf, k, world, screen):
    """A painter that puts a world point (the chibi kit's units) at a screen pixel, at zoom k."""
    return Painter(pg, surf, CHIBI, k=k, ox=Z * (screen[0] - world[0] * k), oy=Z * (screen[1] - world[1] * k))


def burst(pg, surf, cx, cy, n, c1, c2):
    """Comic sunburst rays behind the title."""
    w, h = surf.get_size()
    surf.fill(c1)
    for j in range(n):
        a0, a1 = j * 2 * math.pi / n, (j + 0.5) * 2 * math.pi / n
        r = 4 * max(w, h)
        pg.draw.polygon(surf, c2, [(cx, cy), (cx + r * math.cos(a0), cy + r * math.sin(a0)), (cx + r * math.cos(a1), cy + r * math.sin(a1))])


def glow(pg, surf, cx, cy, r, col, strength=120):
    """A soft round neon glow."""
    lay = pg.Surface(surf.get_size(), pg.SRCALPHA)
    for k in range(24, 0, -1):
        pg.draw.circle(lay, col + (int(strength * (1 - k / 24) ** 1.5 / 6),), (cx, cy), int(r * k / 24))
    surf.blit(lay, (0, 0))


def sparkle(pg, surf, x, y, r, col):
    pts = []
    for j in range(8):
        rr = r if j % 2 == 0 else r * 0.3
        a = j * math.pi / 4 - math.pi / 2
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    pg.draw.polygon(surf, col, pts)


def text(pg, size, s, colour, edge=INK, outline=0.08, shadow=True):
    from ..core.text import font_file, outlined
    f = pg.font.Font(font_file("Poppins-ExtraBold"), size)
    img = outlined(pg, f, s, colour, max(2, int(size * outline)), edge)
    if not shadow:
        return img
    out = pg.Surface((img.get_width() + size // 10, img.get_height() + size // 10), pg.SRCALPHA)
    sh = outlined(pg, f, s, (0, 0, 0), max(2, int(size * outline)), (0, 0, 0))
    sh.set_alpha(90)
    out.blit(sh, (size // 10, size // 10))
    out.blit(img, (0, 0))
    return out


def banner(pg, out: Path):
    BW, BH = 2048, 1152
    surf = pg.Surface((BW * Z, BH * Z))
    burst(pg, surf, 1100 * Z, 576 * Z, 28, (30, 20, 46), (46, 28, 66))
    glow(pg, surf, 1100 * Z, 576 * Z, 900 * Z, (150, 70, 230), 200)        # neon purple behind the title
    glow(pg, surf, 640 * Z, 590 * Z, 330 * Z, (255, 200, 60), 160)         # and a warm spot on the mascot
    rng = random.Random(7)
    for _ in range(26):
        x, y = rng.uniform(40, BW - 40), rng.uniform(40, BH - 40)
        if 380 < x < 1670 and 380 < y < 770:
            continue
        sparkle(pg, surf, x * Z, y * Z, rng.uniform(10, 26) * Z, rng.choice(((255, 226, 60), (255, 120, 170), (140, 230, 255))))
    # the two friends at the sides (seen on desktop and TV), laughing
    for who, sx, look in (("bhai", 215, 0.5), ("dost", 1835, -0.5)):
        hy = 800 - CHIBI.m_legs - CHIBI.m_torso - CHIBI.neck - CHIBI.hr * 0.95
        p = placed(pg, surf, 1.2, (500, hy), (sx, 560))
        if who == "bhai":
            man(p, CHIBI, 500, who, Act(t=0.4, mood="happy", look=look, arm_r=("thumb", "thumb", 1.0)))
        else:
            info = man(p, CHIBI, 500, who, Act(t=0.4, mood="goofy", look=look, arm_r=("hold", "hold", 1.0), arm_l=("hold", "hold", 1.0)))
            (lx, ly), (rx, ry) = info["hands"]
            bx, by = (lx + rx) / 2, (ly + ry) / 2 + 30
            for k in range(5):                                            # rockets poking out of the box
                x0 = bx - 80 + k * 40
                p.limb([(x0, by - 60), (x0 + 4, by - 130)], 6, (60, 40, 40))
                p.fill([(x0 - 12, by - 120), (x0 + 16, by - 120), (x0 + 2, by - 160)], (240, 70, 70) if k % 2 else (255, 200, 60), shade=False)
            p.fill([(bx - 110, by - 70), (bx + 110, by - 70), (bx + 110, by + 70), (bx - 110, by + 70)], (220, 50, 50))
            p.fill([(bx - 110, by - 22), (bx + 110, by - 22), (bx + 110, by + 22), (bx - 110, by + 22)], (255, 210, 70), shade=False)
            lbl = text(pg, int(30 * Z * 1.2), "PATAKHE", (200, 30, 30), outline=0.0, shadow=False)
            surf.blit(lbl, lbl.get_rect(center=(int(p.ox + bx * Z * p.k), int(p.oy + by * Z * p.k))))
    # the mascot and the title, inside the safe area (406..1641 x 407..745)
    p = Painter(pg, surf, CHIBI, k=1.0)
    buffalo(p, 640, 590, 0.8, look=0.25)
    t1 = text(pg, 118 * Z, "BHESS KI", (255, 255, 255))
    t2 = text(pg, 176 * Z, "EYES!", (255, 226, 60))
    surf.blit(t1, t1.get_rect(midleft=(905 * Z, 478 * Z)))
    surf.blit(t2, t2.get_rect(midleft=(895 * Z, 616 * Z)))
    tag = text(pg, 31 * Z, "DARK DESI COMEDY  •  CARTOON SKITS", (255, 255, 255), edge=INK, outline=0.0, shadow=False)
    pill = pg.Rect(0, 0, tag.get_width() + 60 * Z, tag.get_height() + 10 * Z)
    pill.midleft = (905 * Z, 718 * Z)
    pg.draw.rect(surf, (210, 40, 60), pill, border_radius=pill.height // 2)
    pg.draw.rect(surf, (20, 10, 20), pill, 4 * Z, border_radius=pill.height // 2)
    surf.blit(tag, tag.get_rect(center=pill.center))
    img = pg.transform.smoothscale(surf, (BW, BH))
    pg.image.save(img, str(out / "banner.png"))
    # previews of what each device shows
    guide = img.copy()
    for (w, h, c) in ((1235, 338, (255, 0, 0)), (2048, 423, (0, 120, 255))):
        r = pg.Rect(0, 0, w, h)
        r.center = (BW // 2, BH // 2)
        pg.draw.rect(guide, c, r, 4)
    pg.image.save(guide, str(out / "banner_safe_area_check.png"))
    mob = pg.Rect(0, 0, 1235, 338)
    mob.center = (BW // 2, BH // 2)
    pg.image.save(img.subsurface(mob), str(out / "banner_as_on_phone.png"))
    return img


def profile(pg, out: Path, size=800):
    surf = pg.Surface((size * Z, size * Z))
    burst(pg, surf, size * Z // 2, size * Z // 2, 20, (30, 20, 46), (50, 30, 72))
    glow(pg, surf, size * Z // 2, size * Z // 2, int(size * Z * 0.55), (255, 200, 60), 170)
    p = Painter(pg, surf, CHIBI, k=size / 800)
    buffalo(p, 400, 440, 1.25, look=0.0)
    img = pg.transform.smoothscale(surf, (size, size))
    pg.image.save(img, str(out / "profile.png"))
    circ = pg.Surface((size, size), pg.SRCALPHA)                          # how YouTube shows it
    pg.draw.circle(circ, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    shown = img.convert_alpha()
    shown.blit(circ, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
    pg.image.save(pg.transform.smoothscale(shown, (98, 98)), str(out / "profile_as_shown_98px.png"))
    return img


def watermark(pg, out: Path):
    n = 150
    surf = pg.Surface((n * Z, n * Z), pg.SRCALPHA)
    pg.draw.circle(surf, (40, 26, 60, 235), (n * Z // 2, n * Z // 2), n * Z // 2)
    pg.draw.circle(surf, (255, 210, 60, 255), (n * Z // 2, n * Z // 2), n * Z // 2, 4 * Z)
    p = Painter(pg, surf, CHIBI, k=n / 800)
    buffalo(p, 400, 440, 1.25)
    pg.image.save(pg.transform.smoothscale(surf, (n, n)), str(out / "watermark.png"))


def render(out: Path):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    pg.display.set_mode((1, 1))
    out.mkdir(parents=True, exist_ok=True)
    banner(pg, out)
    profile(pg, out)
    watermark(pg, out)
    return out


if __name__ == "__main__":
    from ..config import REPO_ROOT
    print(render(REPO_ROOT / "out" / "channel_bhess_ki_eyes"))
