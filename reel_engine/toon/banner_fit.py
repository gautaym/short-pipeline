"""Fit a finished 3:1 picture to YouTube's channel banner.

Run: python -m reel_engine.toon.banner_fit [source.png]   -> out/channel_bhess_ki_eyes/

YouTube asks for 2560 x 1440. TVs show all of it, desktops a 2560 x 423 strip through the middle,
and phones only the 1546 x 423 safe area in the centre. The picture is scaled so its title block
(the buffalo, the name and the ribbon) fits that safe area, and placed in the middle over a blurred,
darkened copy of itself so the TV edges are filled without seams.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import numpy as np
import pygame as pg

OUT = Path("out/channel_bhess_ki_eyes")
W, H = 2560, 1440
SAFE = (1546, 423)
TITLE_Y = (140, 535)        # title block's top and bottom in the 2000 x 667 source
FEATHER = 90                # px of soft edge where the picture meets the blurred fill


def blurred_cover(src):
    k = max(W / src.get_width(), H / src.get_height())
    small = pg.transform.smoothscale(src, (int(src.get_width() * k / 48), int(src.get_height() * k / 48)))
    for _ in range(3):
        small = pg.transform.smoothscale(pg.transform.smoothscale(small, (small.get_width() // 2, small.get_height() // 2)),
                                         small.get_size())
    big = pg.transform.smoothscale(small, (int(src.get_width() * k), int(src.get_height() * k)))
    out = pg.Surface((W, H))
    out.blit(big, ((W - big.get_width()) // 2, (H - big.get_height()) // 2))
    shade = pg.Surface((W, H), pg.SRCALPHA)
    shade.fill((10, 0, 30, 90))
    out.blit(shade, (0, 0))
    return out


def feathered(pic):
    w, h = pic.get_size()
    out = pg.Surface((w, h), pg.SRCALPHA)
    out.blit(pic, (0, 0))
    pic = out
    ramp = lambda n: np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / FEATHER, 0, 1)
    a = (np.outer(ramp(w), ramp(h)) * 255).astype(np.uint8)
    pg.surfarray.pixels_alpha(pic)[:] = a
    return pic


def main(src_path=OUT / "banner_source.png"):
    pg.init()
    src = pg.image.load(str(src_path))
    sw, sh = src.get_size()
    title_h = (TITLE_Y[1] - TITLE_Y[0]) * sw / 2000
    k = min(SAFE[1] * 0.97 / title_h, W / sw)
    pic = pg.transform.smoothscale(src, (int(sw * k), int(sh * k)))
    mid = (TITLE_Y[0] + TITLE_Y[1]) / 2 * sw / 2000 * k               # title block centre in the scaled picture
    canvas = blurred_cover(src)
    canvas.blit(feathered(pic), ((W - pic.get_width()) // 2, int(H / 2 - mid)))
    pg.image.save(canvas, str(OUT / "banner.png"))

    guide = canvas.copy()
    for (bw, bh), col in (((W, 423), (80, 200, 255)), (SAFE, (255, 60, 60))):
        pg.draw.rect(guide, col, ((W - bw) // 2, (H - bh) // 2, bw, bh), 6)
    pg.image.save(guide, str(OUT / "banner_safe_area_check.png"))
    pg.image.save(canvas.subsurface(((W - SAFE[0]) // 2, (H - SAFE[1]) // 2, *SAFE)), str(OUT / "banner_as_on_phone.png"))
    pg.image.save(canvas.subsurface((0, (H - 423) // 2, W, 423)), str(OUT / "banner_as_on_desktop.png"))
    print(f"scale {k:.3f}, picture {pic.get_size()}, {OUT.resolve()}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
