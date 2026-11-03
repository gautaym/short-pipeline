"""Fonts, line wrapping, outlined text and fitting text to a width.

All text uses FreeSans Bold, which ships inside pygame-ce (GNU FreeFont: GPL with the font
exception). Using a bundled font keeps the same seed pixel-identical on every OS.
"""
import os


def font_path() -> str:
    import pygame
    return os.path.join(os.path.dirname(pygame.__file__), "freesansbold.ttf")


def serif_path(weight: str = "SemiBold") -> str:
    """Cormorant Garamond (SIL Open Font Licence) from assets/fonts, falling back to the default font."""
    from ..config import REPO_ROOT
    p = REPO_ROOT / "assets" / "fonts" / f"CormorantGaramond-{weight}.ttf"
    return str(p) if p.exists() else font_path()


def font_file(name: str) -> str:
    """A font from assets/fonts (all SIL Open Font Licence), e.g. "Poppins-ExtraBold"."""
    from ..config import REPO_ROOT
    p = REPO_ROOT / "assets" / "fonts" / f"{name}.ttf"
    return str(p) if p.exists() else font_path()


def soft_text(pg, font, text: str, colour, shadow: int = 150, offset: int = 5):
    """Text with a soft blurred drop shadow (no hard outline), as in polished video captions."""
    face = font.render(text, True, colour)
    w, h = face.get_size()
    pad = 14
    dark = font.render(text, True, (0, 0, 0))
    halo = pg.Surface((w + pad * 2, h + pad * 2), pg.SRCALPHA)
    for dx, dy in ((0, 0), (2, 0), (-2, 0), (0, 2), (0, -2)):
        halo.blit(dark, (pad + dx, pad + dy))
    small = pg.transform.smoothscale(halo, (max(1, halo.get_width() // 5), max(1, halo.get_height() // 5)))
    halo = pg.transform.smoothscale(small, halo.get_size())               # blurred by scaling down and up
    halo.fill((255, 255, 255, shadow), special_flags=pg.BLEND_RGBA_MULT)
    out = pg.Surface((w + pad * 2, h + pad * 2 + offset), pg.SRCALPHA)
    out.blit(halo, (0, offset))
    out.blit(halo, (0, offset))
    out.blit(face, (pad, pad))
    return out


class Fonts:
    """The standard set of font sizes used by titles, HUDs, floaters, banners and end cards."""

    def __init__(self, pg):
        fp = font_path()
        self.title = pg.font.Font(fp, 60)
        self.stat = pg.font.Font(fp, 40)
        self.mid = pg.font.Font(fp, 32)
        self.small = pg.font.Font(fp, 22)
        self.floater = pg.font.Font(fp, 46)
        self.big = pg.font.Font(fp, 110)
        self.huge = pg.font.Font(fp, 150)
        self.hook = pg.font.Font(fp, 96)
        self.banner = pg.font.Font(fp, 130)
        self.cta = pg.font.Font(fp, 44)


def wrap(font, text: str, max_w: int) -> list[str]:
    """Greedy word wrap so that no line is wider than max_w pixels (unless one word is)."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.size(trial)[0] > max_w and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


def fit_width(pg, surf, max_w: int):
    """Scale a rendered surface down, keeping its aspect ratio, if it is wider than max_w."""
    if surf.get_width() > max_w:
        surf = pg.transform.smoothscale(surf, (max_w, int(surf.get_height() * max_w / surf.get_width())))
    return surf


def outlined(pg, font, text: str, colour, outline: int = 5, outline_colour=(0, 0, 0)):
    """Text with a solid outline, readable over any background."""
    base = font.render(text, True, colour)
    edge = font.render(text, True, outline_colour)
    w, h = base.get_size()
    surf = pg.Surface((w + 2 * outline, h + 2 * outline), pg.SRCALPHA)
    for dx in range(-outline, outline + 1):
        for dy in range(-outline, outline + 1):
            if (dx or dy) and dx * dx + dy * dy <= outline * outline:
                surf.blit(edge, (dx + outline, dy + outline))
    surf.blit(base, (outline, outline))
    return surf


def text_block(pg, font, text: str, colour, max_w: int, max_lines: int = 4, outline: int = 5,
               line_gap: int = 6):
    """Wrapped, outlined, centred lines stacked into one transparent surface."""
    lines = [outlined(pg, font, line, colour, outline) for line in wrap(font, text, max_w)[:max_lines]]
    w = max(s.get_width() for s in lines)
    h = sum(s.get_height() for s in lines) + line_gap * (len(lines) - 1)
    block = pg.Surface((w, h), pg.SRCALPHA)
    y = 0
    for s in lines:
        block.blit(s, ((w - s.get_width()) // 2, y))
        y += s.get_height() + line_gap
    return block
