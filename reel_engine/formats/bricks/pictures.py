"""Pictures for the mystery format: original drawings made in code, plus the user's own images.

Built-in pictures are simple, recognisable subjects drawn with pygame shapes, so there are no
licensing questions. The user can add images to assets/pictures/; the file name becomes the
answer (e.g. `taj_mahal.jpg` -> "TAJ MAHAL"). Only add images you own or that are public domain.
"""
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ...config import REPO_ROOT

USER_DIR = REPO_ROOT / "assets" / "pictures"
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


@dataclass
class Picture:
    answer: str
    hint: str | None
    draw: Callable                 # (pg, w, h, rng) -> Surface


def grad(pg, w, h, top, bot):
    s = pg.Surface((w, h))
    for y in range(h):
        k = y / max(1, h - 1)
        pg.draw.line(s, [int(top[i] + (bot[i] - top[i]) * k) for i in range(3)], (0, y), (w, y))
    return s


def glow(pg, s, centre, radius, colour, steps=14):
    layer = pg.Surface(s.get_size(), pg.SRCALPHA)
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        pg.draw.circle(layer, tuple(colour) + (int(110 / steps * (steps - i + 1) ** 0.7),), centre, r)
    s.blit(layer, (0, 0))


def petal(cx, cy, length, width, angle, n=24):
    """A pointed petal or leaf shape from (cx, cy) outwards at `angle` (radians)."""
    pts = []
    for i in range(n + 1):
        k = i / n
        along = length * k
        side = width * math.sin(math.pi * k) * (1 - 0.35 * k)
        pts.append((along, side))
    pts += [(a, -b) for a, b in reversed(pts)]
    ca, sa = math.cos(angle), math.sin(angle)
    return [(cx + a * ca - b * sa, cy + a * sa + b * ca) for a, b in pts]


def draw_kite(pg, w, h, rng):
    s = grad(pg, w, h, (90, 170, 245), (200, 232, 255))
    for _ in range(5):
        x, y = rng.uniform(0, w), rng.uniform(0, h * 0.8)
        for dx in (-50, 0, 50):
            pg.draw.ellipse(s, (250, 252, 255), (x + dx - 60, y - 30, 120, 60))
    cx, cy = w * 0.5, h * 0.4
    top, right, bottom, left, p = (cx, cy - 270), (cx + 200, cy - 40), (cx, cy + 310), (cx - 200, cy - 40), (cx, cy - 40)
    for tri, col in (((top, right, p), (255, 120, 30)), ((right, bottom, p), (230, 30, 110)),
                     ((bottom, left, p), (255, 120, 30)), ((left, top, p), (230, 30, 110))):
        pg.draw.polygon(s, col, tri)
    pg.draw.line(s, (90, 50, 20), top, bottom, 7)
    pg.draw.line(s, (90, 50, 20), left, right, 7)
    pts = [(bottom[0] + 40 * math.sin(i / 5), bottom[1] + i * 9) for i in range(40)]
    pg.draw.lines(s, (60, 60, 70), False, pts, 4)
    for i in range(6, 40, 8):
        x, y = pts[i]
        pg.draw.polygon(s, (255, 214, 40), [(x - 26, y - 14), (x, y), (x - 26, y + 14)])
        pg.draw.polygon(s, (255, 214, 40), [(x + 26, y - 14), (x, y), (x + 26, y + 14)])
    pg.draw.lines(s, (255, 255, 255), False, [p, (cx + 180, cy + 200), (w * 0.9, h)], 2)
    return s


def draw_diya(pg, w, h, rng):
    s = grad(pg, w, h, (30, 10, 50), (70, 20, 60))
    cx, base = w * 0.5, h * 0.62
    glow(pg, s, (int(cx), int(base - 230)), 380, (255, 160, 40))
    for ring, (r, col) in enumerate(((420, (255, 80, 120)), (470, (255, 200, 40)), (520, (80, 200, 255)))):
        for i in range(36 + ring * 6):
            a = 2 * math.pi * i / (36 + ring * 6)
            pg.draw.circle(s, col, (cx + r * math.cos(a), base + 120 + 0.35 * r * math.sin(a)), 12)
    pg.draw.ellipse(s, (120, 50, 20), (cx - 260, base - 60, 520, 260))
    pg.draw.rect(s, (30, 10, 50), (cx - 270, base - 70, 540, 120))
    pg.draw.ellipse(s, (200, 100, 40), (cx - 270, base - 40, 540, 90))
    pg.draw.ellipse(s, (70, 30, 10), (cx - 230, base - 25, 460, 60))
    pg.draw.polygon(s, (200, 100, 40), [(cx + 250, base), (cx + 340, base - 40), (cx + 250, base + 40)])
    pg.draw.line(s, (240, 230, 200), (cx + 300, base - 20), (cx + 330, base - 60), 6)
    fx, fy = cx + 330, base - 60
    pg.draw.polygon(s, (255, 170, 30), petal(fx, fy + 10, 210, 60, -math.pi / 2))
    pg.draw.polygon(s, (255, 245, 180), petal(fx, fy, 120, 28, -math.pi / 2))
    return s


def draw_rocket(pg, w, h, rng):
    s = grad(pg, w, h, (5, 5, 25), (25, 15, 60))
    for _ in range(160):
        pg.draw.circle(s, (230, 230, 255), (rng.uniform(0, w), rng.uniform(0, h)), rng.choice([1, 1, 2, 3]))
    pg.draw.circle(s, (200, 120, 80), (w - 120, 140), 110)
    pg.draw.ellipse(s, (240, 200, 160), (w - 290, 110, 340, 60), 6)
    cx = w * 0.5
    for i, col in enumerate(((255, 80, 30), (255, 170, 30), (255, 240, 160))):
        pg.draw.polygon(s, col, petal(cx, 760, 300 - i * 80, 90 - i * 25, math.pi / 2))
    pg.draw.polygon(s, (220, 40, 50), [(cx - 95, 560), (cx - 200, 760), (cx - 95, 700)])
    pg.draw.polygon(s, (220, 40, 50), [(cx + 95, 560), (cx + 200, 760), (cx + 95, 700)])
    pg.draw.rect(s, (235, 235, 245), (cx - 95, 260, 190, 480), border_radius=40)
    pg.draw.rect(s, (190, 195, 210), (cx + 40, 260, 55, 480), border_radius=30)
    pg.draw.polygon(s, (220, 40, 50), [(cx - 95, 300), (cx, 90), (cx + 95, 300)])
    pg.draw.circle(s, (120, 125, 140), (cx, 420), 62)
    pg.draw.circle(s, (70, 170, 255), (cx, 420), 48)
    pg.draw.circle(s, (200, 235, 255), (cx - 15, 405), 14)
    pg.draw.rect(s, (220, 40, 50), (cx - 95, 640, 190, 30))
    return s


def draw_lotus(pg, w, h, rng):
    s = grad(pg, w, h, (20, 110, 120), (5, 40, 60))
    for x, y, r in ((160, 820, 170), (820, 760, 150), (520, 960, 140)):
        pg.draw.circle(s, (40, 150, 70), (x, y), r)
        pg.draw.polygon(s, (20, 110, 120), [(x, y), (x + r + 5, y - 40), (x + r + 5, y + 10)])
    cx, cy = w * 0.5, h * 0.52
    for k in range(9):
        a = math.pi + k * math.pi / 8
        pg.draw.polygon(s, (220, 90, 150), petal(cx, cy, 300, 85, a))
    for k in range(7):
        a = math.pi * 1.08 + k * math.pi * 0.84 / 6
        pg.draw.polygon(s, (255, 150, 195), petal(cx, cy + 10, 250, 70, a))
        pg.draw.polygon(s, (255, 205, 225), petal(cx, cy + 10, 150, 26, a))
    pg.draw.ellipse(s, (250, 210, 60), (cx - 70, cy - 40, 140, 70))
    return s


def draw_watermelon(pg, w, h, rng):
    s = grad(pg, w, h, (255, 245, 200), (255, 220, 150))
    cx, cy, R = w * 0.5, h * 0.92, 760

    def wedge(r):
        return [(cx, cy)] + [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                             for a in range(-128, -51)]

    pg.draw.polygon(s, (40, 130, 50), wedge(R))
    pg.draw.polygon(s, (170, 220, 120), wedge(R - 40))
    pg.draw.polygon(s, (240, 60, 70), wedge(R - 65))
    for _ in range(26):
        a = math.radians(rng.uniform(-120, -60))
        r = rng.uniform(180, R - 130)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        pg.draw.polygon(s, (30, 20, 20), petal(x, y, 34, 10, a + math.pi))
    return s


def draw_sunflower(pg, w, h, rng):
    s = grad(pg, w, h, (110, 190, 250), (190, 230, 255))
    cx, cy = w * 0.5, h * 0.38
    pg.draw.line(s, (50, 140, 50), (cx, cy), (cx - 40, h), 34)
    pg.draw.polygon(s, (60, 160, 60), petal(cx - 30, h * 0.75, 260, 80, -0.5))
    pg.draw.polygon(s, (60, 160, 60), petal(cx - 30, h * 0.85, 240, 70, math.pi + 0.5))
    for k in range(24):
        a = 2 * math.pi * k / 24
        pg.draw.polygon(s, (255, 200, 20) if k % 2 else (250, 180, 10), petal(cx, cy, 340, 70, a))
    pg.draw.circle(s, (110, 60, 20), (cx, cy), 170)
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(260):
        r = 10 * math.sqrt(i)
        a = i * golden
        pg.draw.circle(s, (70, 35, 10), (cx + r * math.cos(a), cy + r * math.sin(a)), 5)
    return s


def draw_umbrella(pg, w, h, rng):
    s = grad(pg, w, h, (90, 100, 130), (150, 160, 185))
    for _ in range(140):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        pg.draw.line(s, (200, 210, 235), (x, y), (x - 12, y + 40), 2)
    cx, cy, R = w * 0.5, h * 0.5, 420
    cols = [(230, 40, 60), (255, 200, 30), (40, 160, 230), (60, 190, 90), (240, 120, 30), (160, 70, 210)]
    for i in range(6):
        a0, a1 = math.pi + i * math.pi / 6, math.pi + (i + 1) * math.pi / 6
        arc = [(cx + R * math.cos(a0 + (a1 - a0) * k / 20), cy + R * math.sin(a0 + (a1 - a0) * k / 20))
               for k in range(21)]
        pg.draw.polygon(s, cols[i], [(cx, cy)] + arc)
        pg.draw.line(s, (40, 40, 50), (cx, cy), arc[0], 3)
    pg.draw.line(s, (60, 40, 30), (cx, cy - R - 30), (cx, cy + 380), 14)
    pg.draw.arc(s, (60, 40, 30), (cx - 90, cy + 320, 90, 120), math.pi, 2 * math.pi, 14)
    pg.draw.ellipse(s, (120, 135, 170), (cx - 330, h - 130, 660, 90))
    return s


def draw_icecream(pg, w, h, rng):
    s = grad(pg, w, h, (255, 200, 225), (255, 160, 200))
    cx = w * 0.5
    A, B, C = (cx - 190, 520), (cx + 190, 520), (cx, 1000)
    pg.draw.polygon(s, (215, 160, 90), [A, B, C])

    def on(p, q, u):
        return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)

    for i in range(1, 9):
        u = i / 9
        pg.draw.line(s, (170, 115, 60), on(A, B, u), on(A, C, u), 4)
        pg.draw.line(s, (170, 115, 60), on(B, A, u), on(B, C, u), 4)
    pg.draw.circle(s, (150, 220, 140), (cx, 470), 200)
    for dx in (-140, -40, 70, 150):
        pg.draw.ellipse(s, (150, 220, 140), (cx + dx - 25, 520, 50, 90))
    pg.draw.circle(s, (255, 120, 160), (cx, 290), 170)
    pg.draw.circle(s, (210, 20, 40), (cx + 20, 115), 45)
    pg.draw.line(s, (60, 120, 40), (cx + 25, 75), (cx + 70, 20), 6)
    return s


BUILT_IN = [
    Picture("KITE", "it flies on Makar Sankranti", draw_kite),
    Picture("DIYA", "you light it on Diwali", draw_diya),
    Picture("ROCKET", "3, 2, 1...", draw_rocket),
    Picture("LOTUS", "India's national flower", draw_lotus),
    Picture("WATERMELON", "red inside, green outside", draw_watermelon),
    Picture("SUNFLOWER", "it follows the sun", draw_sunflower),
    Picture("UMBRELLA", "you need it in the monsoon", draw_umbrella),
    Picture("ICE CREAM", "best on a hot day", draw_icecream),
]


def user_pictures() -> list[Picture]:
    """Images in assets/pictures/, in a stable order. The file name is the answer."""
    if not USER_DIR.is_dir():
        return []
    files = sorted(p for p in USER_DIR.iterdir() if p.suffix.lower() in IMAGE_TYPES)
    return [image_picture(str(p)) for p in files]


def image_picture(path: str, answer: str | None = None) -> Picture:
    name = answer or Path(path).stem.replace("_", " ").replace("-", " ")
    return Picture(name.upper(), None, lambda pg, w, h, rng: load_cover(pg, path, w, h))


def load_cover(pg, path: str, w: int, h: int):
    """Load an image and scale/crop it to fill w x h, like CSS object-fit: cover."""
    if not os.path.exists(path):
        raise SystemExit(f"picture not found: {path}")
    img = pg.image.load(path)
    iw, ih = img.get_size()
    k = max(w / iw, h / ih)
    img = pg.transform.smoothscale(img, (max(w, round(iw * k)), max(h, round(ih * k))))
    x, y = (img.get_width() - w) // 2, (img.get_height() - h) // 2
    return img.subsurface((x, y, w, h)).copy()
