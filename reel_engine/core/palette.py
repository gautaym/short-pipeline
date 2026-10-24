"""Colour helpers."""
import colorsys


def hsv255(h: float, s: float, v: float) -> tuple[int, int, int]:
    """HSV in 0..1 to an 8-bit RGB tuple."""
    return tuple(int(255 * x) for x in colorsys.hsv_to_rgb(h, s, v))


def vertical_gradient(pg, size: tuple[int, int], top, bot):
    """A surface fading from colour `top` to `bot` (RGB floats in 0..1), one row at a time."""
    w, h = size
    surf = pg.Surface((w, h))
    for y in range(h):
        k = y / h
        col = tuple(int(255 * (top[i] * (1 - k) + bot[i] * k)) for i in range(3))
        pg.draw.line(surf, col, (0, y), (w, y))
    return surf
