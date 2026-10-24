"""Fonts, line wrapping and fitting text to a width."""
import os


def font_path() -> str | None:
    """First bold system font found, or None for pygame's built-in font."""
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/Library/Fonts/Arial Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(p):
            return p
    return None


class Fonts:
    """The standard set of font sizes used by titles, HUDs, floaters and end cards."""

    def __init__(self, pg):
        fp = font_path()
        self.title = pg.font.Font(fp, 66)
        self.stat = pg.font.Font(fp, 40)
        self.mid = pg.font.Font(fp, 32)
        self.small = pg.font.Font(fp, 22)
        self.floater = pg.font.Font(fp, 46)
        self.big = pg.font.Font(fp, 110)
        self.huge = pg.font.Font(fp, 150)


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
