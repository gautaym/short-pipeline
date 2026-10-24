"""Brick shapes for the classic format, as boolean masks over the brick grid."""
import math

import numpy as np

from ...core.text import font_path

SHAPES = ["heart", "circle", "diamond", "star", "ring", "text"]
TEXT_WORDS = ["2026", "WIN", "GO", "BOOM", "LOL", "OK"]


def uv(cols: int, rows: int):
    """Normalised cell centres: u to the right, v upwards, both in [-1, 1]."""
    cs = (np.arange(cols) + 0.5) / cols * 2 - 1
    rs = (np.arange(rows) + 0.5) / rows * 2 - 1
    u, v = np.meshgrid(cs, rs)
    return u, -v


def poly_mask(u, v, pts):
    inside = np.zeros(u.shape, dtype=bool)
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        cond = (y1 > v) != (y2 > v)
        xcross = (x2 - x1) * (v - y1) / (y2 - y1 + 1e-12) + x1
        inside ^= cond & (u < xcross)
    return inside


def shape_mask(name: str, text: str, pg, cols: int, rows: int):
    u, v = uv(cols, rows)
    if name == "heart":
        x, y = u * 1.25, v * 1.25 + 0.15
        return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0
    if name == "circle":
        return u * u + v * v <= 0.96 ** 2
    if name == "ring":
        r2 = u * u + v * v
        return (r2 <= 0.98 ** 2) & (r2 >= 0.48 ** 2)
    if name == "diamond":
        return np.abs(u) + np.abs(v) <= 1.0
    if name == "star":
        pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            r = 1.0 if k % 2 == 0 else 0.42
            pts.append((r * math.cos(a), r * math.sin(a) - 0.06))
        return poly_mask(u, v, pts)
    if name == "text":
        font = pg.font.Font(font_path(), 200)
        surf = font.render(text, True, (255, 255, 255))
        sw, sh = surf.get_size()
        scale = min(cols / sw, (rows * 0.7) / sh)
        tw, th = max(1, int(sw * scale)), max(1, int(sh * scale))
        small = pg.transform.smoothscale(surf, (tw, th))
        alpha = pg.surfarray.array_alpha(small).T > 110
        mask = np.zeros((rows, cols), dtype=bool)
        r0, c0 = (rows - th) // 2, (cols - tw) // 2
        mask[r0:r0 + th, c0:c0 + tw] = alpha
        return mask
    raise ValueError(f"unknown shape {name}")
