"""Maths Test: a 9:16 Shorts thumbnail (the two cackling, Golu's blank sheet with a red 0/20) and the upload folder.

Run: python -m reel_engine.toon.maths_test_thumb
"""
import os
import shutil
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame as pg

from ..core.text import font_file, gold_text, outlined

ROOT = Path("out/2026-11-08/maths_test")
SRC = ROOT / "maths_test_hi"
DEST = Path("out/2026-11-08/maths_test_upload")
FRAME = SRC / "frames" / "f_0605.png"       # both cackling, eyes squeezed shut
W, H = 1080, 1920
ZOOM, FOCUS = 1.0, (540, 960)


def shade(surf, top, rows, alpha):
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
    shade(veil, False, 700, 200)
    out.blit(veil, (0, 0))

    head = pg.font.Font(font_file("Poppins-ExtraBold"), 104)
    for i, line in enumerate(("WO DOST JO TUMSE", "BHI FISSADI HAI!")):
        s = gold_text(pg, head, line, outline=9)
        out.blit(s, ((W - s.get_width()) // 2, 70 + i * 140))

    sheet = pg.image.load(str(ROOT / "papers" / "golu.png"))           # Golu's blank sheet, with a red 0/20
    sheet = pg.transform.smoothscale(sheet, (470, int(470 * sheet.get_height() / sheet.get_width())))
    sheet = pg.transform.rotozoom(sheet, 8, 1)
    out.blit(sheet, (60, H - sheet.get_height() - 60))
    stamp = pg.font.Font(font_file("Poppins-ExtraBold"), 150)
    s = pg.transform.rotozoom(outlined(pg, stamp, "0/20", (230, 30, 40), 9, (255, 255, 255)), 14, 1)
    out.blit(s, (300, H - 520))
    tag = pg.font.Font(font_file("Poppins-ExtraBold"), 84)
    for i, (line, col) in enumerate((("MATHS", (255, 255, 255)), ("TEST", (255, 200, 60)))):
        t = outlined(pg, tag, line, col, 8, (20, 6, 10))
        out.blit(t, (W - t.get_width() - 50, H - 330 + i * 110))
    return out


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    pg.image.save(draw(), str(DEST / "thumbnail.png"))
    for name in ("maths_test_hi.mp4", "preview_phone.mp4"):
        shutil.copy2(SRC / name, DEST / name)
    print(DEST.resolve())


if __name__ == "__main__":
    main()
