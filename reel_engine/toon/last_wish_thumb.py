"""The Last Wish: a 9:16 Shorts thumbnail from the slap frame, plus the upload folder.

Run: python -m reel_engine.toon.last_wish_thumb
"""
import os
import shutil
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame as pg

from ..core.text import font_file, gold_text, outlined

SRC = Path("out/2026-11-07/last_wish/last_wish_hi")
DEST = Path("out/2026-11-07/last_wish_upload")
FRAME = SRC / "frames" / "f_0868.png"      # mid-slap: 102's hand on 420's squashed red cheek
W, H = 1080, 1920
ZOOM, FOCUS = 1.22, (560, 1000)              # push in on 420 and the slapper


def shade(surf, top, rows, alpha):
    """A dark band fading out from one edge, so the lettering reads over the yard."""
    for i in range(rows):
        a = int(alpha * (1 - i / rows) ** 1.6)
        y = i if top else H - 1 - i
        pg.draw.line(surf, (12, 6, 20, a), (0, y), (W, y))


def draw() -> pg.Surface:
    pg.init()
    shot = pg.image.load(str(FRAME))
    big = pg.transform.smoothscale(shot, (int(W * ZOOM), int(H * ZOOM)))
    x = min(max(int(FOCUS[0] * ZOOM - W / 2), 0), big.get_width() - W)
    y = min(max(int(FOCUS[1] * ZOOM - H / 2), 0), big.get_height() - H)
    out = pg.Surface((W, H))
    out.blit(big, (-x, -y))

    veil = pg.Surface((W, H), pg.SRCALPHA)
    shade(veil, True, 560, 230)
    shade(veil, False, 520, 230)
    out.blit(veil, (0, 0))

    head = pg.font.Font(font_file("Poppins-ExtraBold"), 112)
    for i, line in enumerate(("SIR, UN DONO KO", "WAPAS BULA LO!")):
        s = gold_text(pg, head, line, outline=9)
        out.blit(s, ((W - s.get_width()) // 2, 70 + i * 150))

    pop = pg.font.Font(font_file("Poppins-ExtraBold"), 128)
    s = pg.transform.rotozoom(outlined(pg, pop, "THAPPAD!", (255, 150, 30), 10, (60, 10, 10)), 9, 1)
    out.blit(s, (W - s.get_width() - 10, 395))

    tag = pg.font.Font(font_file("Poppins-ExtraBold"), 96)
    for i, (line, col) in enumerate((("AAKHRI ICHHA", (255, 255, 255)), ("ULTI PAD GAYI!", (255, 70, 60)))):
        s = outlined(pg, tag, line, col, 9, (20, 6, 10))
        out.blit(s, ((W - s.get_width()) // 2, H - 330 + i * 125))
    return out


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    pg.image.save(draw(), str(DEST / "thumbnail.png"))
    for name in ("last_wish_hi.mp4", "preview_phone.mp4"):
        shutil.copy2(SRC / name, DEST / name)
    print(DEST.resolve())


if __name__ == "__main__":
    main()
