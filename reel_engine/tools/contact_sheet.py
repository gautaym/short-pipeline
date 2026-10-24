"""Contact sheets: evenly spaced frames from one or more videos in a single image.

One video gives a grid of frames; several videos give one labelled row each, which makes
side-by-side review of a batch quick.
"""
import os

from ..core.render import init_pygame
from ..core.text import font_path
from ..core.video import grab_frame, probe

PAD = 10
LABEL_H = 26
HEADER_H = 34
BG = (18, 18, 24)


def _frames(pg, path: str, n: int, width: int):
    info = probe(path)
    height = round(width * info["height"] / info["width"] / 2) * 2
    times = [(i + 0.5) * info["duration"] / n for i in range(n)]
    imgs = [pg.image.frombuffer(grab_frame(path, t, (width, height)), (width, height), "RGB").copy()
            for t in times]
    return imgs, times, height


def contact_sheet(videos: list[str], out: str, n: int = 10, cols: int = 5, width: int = 216) -> str:
    """Write a PNG contact sheet of the videos to `out` and return its path."""
    pg = init_pygame()
    font = pg.font.Font(font_path(), 18)
    head_font = pg.font.Font(font_path(), 22)
    rows = []                                 # (header or None, [(img, time), ...])
    height = 0
    for v in videos:
        imgs, times, height = _frames(pg, v, n, width)
        pairs = list(zip(imgs, times))
        if len(videos) == 1:
            rows += [(None, pairs[i:i + cols]) for i in range(0, len(pairs), cols)]
        else:
            rows.append((os.path.basename(v), pairs))
    per_row = max(len(r[1]) for r in rows)
    cell_h = height + LABEL_H
    sheet_w = PAD + per_row * (width + PAD)
    sheet_h = PAD + sum((HEADER_H if head else 0) + cell_h + PAD for head, _ in rows)
    sheet = pg.Surface((sheet_w, sheet_h))
    sheet.fill(BG)
    y = PAD
    for head, pairs in rows:
        if head:
            sheet.blit(head_font.render(head, True, (235, 235, 245)), (PAD, y + 4))
            y += HEADER_H
        for i, (img, t) in enumerate(pairs):
            x = PAD + i * (width + PAD)
            sheet.blit(img, (x, y))
            lab = font.render(f"{t:.1f}s", True, (200, 200, 210))
            sheet.blit(lab, lab.get_rect(center=(x + width / 2, y + height + LABEL_H / 2)))
        y += cell_h + PAD
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    pg.image.save(sheet, out)
    return out
