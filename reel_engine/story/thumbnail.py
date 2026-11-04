"""Click-worthy thumbnails for a story reel, built from the story's own art.

A 9:16 picture (Shorts thumbnail, Instagram cover) and a 16:9 one (YouTube search and home feed),
written beside the reel by `reel make` or `reel thumb <story>`. One face with a strong emotion is the
hero, large in the middle with a coloured halo; an optional dilemma puts one figure on each side under
a big label; the hook sits at the top in gold, with an optional red mark ("?") by the hero's head.

A story may describe its thumbnail (every key optional):

    thumbnail:
      title: "POV: TUM KARNA HO"     # default: the story's English title
      backdrop: void                 # default: the cold open's backdrop
      hero: karna_shock              # default: the cold open's first actor
      hero_crop: 1.0                 # share of the hero's picture kept from the top (default 0.62:
                                     #   a full-body puppet becomes waist-up; 1.0 for close-ups)
      mark: "?"                      # default "?" when the title is a question
      left: {puppet: duryodhana, label: DOSTI, colour: [170, 90, 255]}
      right: {puppet: kunti, label: DHARMA, colour: [255, 210, 120], flip: true}
      join: "ya"                     # a small word between the two labels (9:16 only)

Text is Latin script only: the bundled fonts have no Devanagari.
"""
import os
from pathlib import Path

import numpy as np

TALL = (1080, 1920)
WIDE = (1280, 720)
SIDE_CROP = 0.6           # the side figures are shown from the head down to about the waist
HERO_CROP = 0.62
HERO_GLOW = (255, 120, 40)
LEFT_TINT = (120, 40, 200)
RIGHT_TINT = (255, 190, 80)


def spec(sc: dict) -> dict:
    """The story's thumbnail block with its defaults filled in from the cold open."""
    th = dict(sc.get("thumbnail") or {})
    beats = sc["beats"]
    opening = sc.get("opening") or {}
    beat = beats[int(opening.get("beat", 1)) - 1]
    th.setdefault("backdrop", beat.get("stage", {}).get("backdrop"))
    if "hero" not in th and not (th.get("left") or th.get("right")):   # a dilemma needs no hero
        actors = list((opening.get("actors") or {}).values()) + list(beat.get("stage", {}).get("actors", {}).values())
        th["hero"] = next((a["puppet"] for a in actors if a.get("puppet") and "narrator" not in str(a["puppet"])), None)
    title = th.get("title") or sc["title"]["en"]
    th["title"] = title.upper()
    th.setdefault("mark", "?" if title.rstrip().endswith("?") else None)
    th.setdefault("hero_crop", HERO_CROP)
    return th


def make(sc: dict, out_dir: Path) -> list[Path]:
    """Draw both thumbnails into out_dir."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    th = spec(sc)
    out = []
    for size, name in ((TALL, "thumbnail.png"), (WIDE, "thumbnail_16x9.png")):
        path = Path(out_dir) / name
        pg.image.save(_draw(pg, sc, th, *size), str(path))
        out.append(path)
    return out


def _draw(pg, sc, th, W, H):
    from ..core.text import fit_width, font_file, gold_text
    from . import art
    wide = W > H
    screen = pg.Surface((W, H))
    if th.get("backdrop"):
        screen.blit(_cover(pg, pg.image.load(str(art.backdrop_file(sc["id"], th["backdrop"]))), W, H), (0, 0))
    _wash(pg, screen, (0, 0, 0), 70)
    left, right = th.get("left"), th.get("right")
    if left:
        screen.blit(_tint(pg, W, H, tuple(left.get("colour", LEFT_TINT)), True), (0, 0))
    if right:
        screen.blit(_tint(pg, W, H, tuple(right.get("colour", RIGHT_TINT)), False), (0, 0))

    def figure(name, flip=False):
        s = art.cut(pg, sc["id"], name)
        return pg.transform.flip(s, True, False) if flip else s

    placed = []                                                  # (surface, glow colour, rect anchor)
    hero = None
    if th.get("hero"):
        hero = _crop(pg, figure(th["hero"]), float(th["hero_crop"]))
        hero = _fit_h(pg, hero, int(H * (1.05 if wide else 0.62 if (left or right) else 0.72)))
        widest = W * (0.62 if wide else 0.98)
        if hero.get_width() > widest:
            hero = _fit_h(pg, hero, int(hero.get_height() * widest / hero.get_width()))
    sides = []
    for side, x in ((left, 0.15 if wide else 0.2), (right, 0.85 if wide else 0.8)):
        if side:
            s = _crop(pg, figure(side["puppet"], side.get("flip", False)), SIDE_CROP)
            alone = hero is None                                  # without a hero the pair fills the frame
            s = _fit_h(pg, s, int(H * (0.78 if wide else 0.56 if alone else 0.38)))
            top = H * (0.30 if wide else 0.40 if alone else 0.62)
            sides.append((s, tuple(side.get("colour", (255, 255, 255))), dict(midtop=(W * x, top))))
    hero_at = dict(midtop=(W / 2, H * (0.15 if wide else 0.2))) if (left or right) or wide else dict(midbottom=(W / 2, H * 0.86))
    if wide:
        placed = sides + ([(hero, HERO_GLOW, hero_at)] if hero else [])
    else:
        placed = ([(hero, HERO_GLOW, hero_at)] if hero else []) + sides
    hero_rect = None
    for surf, colour, at in placed:
        halo = _glow(pg, surf, colour)
        r = surf.get_rect(**at)
        screen.blit(halo, halo.get_rect(center=r.center))
        screen.blit(surf, r)
        if surf is hero:
            hero_rect = r

    def word(text, size, top, bottom, outline=10):
        return gold_text(pg, pg.font.Font(font_file("Poppins-ExtraBold"), size), text, top, bottom, outline, (20, 6, 6), 10)

    gold = ((255, 240, 150), (240, 150, 30))
    title = th["title"]
    if wide:
        t = fit_width(pg, word(title, 92, *gold), W - 80)
        screen.blit(t, t.get_rect(midtop=(W / 2, 8)))
    else:                                                        # "POV: ..." splits onto two lines at the colon
        head, sep, rest = title.partition(": ")
        rest_w = pg.font.Font(font_file("Poppins-ExtraBold"), 150).size(rest)[0] if sep else 0
        if sep and len(head) <= 8 and rest_w < (W - 70) * 1.25:     # "POV:" above, the rest big below
            a = word(head + ":", 100, (255, 255, 255), (225, 225, 235))
            screen.blit(a, a.get_rect(midtop=(W / 2, 110)))
            b = fit_width(pg, word(rest, 150, *gold), W - 70)
            screen.blit(b, b.get_rect(midtop=(W / 2, 215)))
        else:
            from ..core.text import wrap
            font = pg.font.Font(font_file("Poppins-ExtraBold"), 120)
            y = 120
            for line in wrap(font, title, W - 100)[:3]:
                b = fit_width(pg, word(line, 120, *gold), W - 70)
                screen.blit(b, b.get_rect(midtop=(W / 2, y)))
                y += b.get_height() - 20
    if left or right:
        size = 92 if wide else 104
        room = W * (0.44 if wide else 0.40) - 24                    # each label keeps to its own side
        labels = []
        if left and left.get("label"):
            s = fit_width(pg, word(left["label"].upper(), size, (226, 196, 255) if not left.get("colour")
                                   else _light(left["colour"]), tuple(left.get("colour", (150, 80, 255)))), room)
            labels.append(s.get_rect(**({"bottomleft": (24, H - 14)} if wide else {"midleft": (36, H * 0.875)})))
            screen.blit(s, labels[-1])
        if right and right.get("label"):
            s = fit_width(pg, word(right["label"].upper(), size, (255, 246, 200) if not right.get("colour")
                                   else _light(right["colour"]), tuple(right.get("colour", (255, 180, 50)))), room)
            labels.append(s.get_rect(**({"bottomright": (W - 24, H - 14)} if wide else {"midright": (W - 30, H * 0.875)})))
            screen.blit(s, labels[-1])
        if th.get("join") and len(labels) == 2 and not wide:
            j = word(th["join"], 76, (255, 255, 255), (220, 220, 230))
            screen.blit(j, j.get_rect(center=((labels[0].right + labels[1].left) / 2, H * 0.875 + 8)))
    if th.get("mark") and hero_rect is not None:
        m = word(th["mark"], 200 if wide else 250, (255, 90, 70), (200, 20, 20), 12)
        at = (min(W * 0.9, hero_rect.right - hero_rect.width * 0.12), hero_rect.top + hero_rect.height * 0.32)
        screen.blit(m, m.get_rect(center=at))
    _vignette(pg, screen)
    return screen


# ------------------------------------------------------------------ helpers
def _light(colour):
    return tuple(min(255, int(c * 0.45 + 255 * 0.55)) for c in colour)


def _fit_h(pg, s, h):
    return pg.transform.smoothscale(s, (max(1, int(s.get_width() * h / s.get_height())), h))


def _cover(pg, s, w, h):
    k = max(w / s.get_width(), h / s.get_height())
    s = pg.transform.smoothscale(s, (int(s.get_width() * k) + 1, int(s.get_height() * k) + 1))
    return s.subsurface(((s.get_width() - w) // 2, (s.get_height() - h) // 2, w, h)).copy()


def _crop(pg, s, keep):
    """The top `keep` of a cut-out, its lower edge fading away (no hard waist line)."""
    if keep < 1.0:
        s = s.subsurface((0, 0, s.get_width(), int(s.get_height() * keep))).copy()
    else:
        s = s.copy()
    h = s.get_height()
    a = pg.surfarray.pixels_alpha(s)
    a[:] = (a * np.clip((h - np.arange(h)) / (h * 0.25), 0, 1)[None, :]).astype(np.uint8)
    del a
    return s


def _wash(pg, screen, colour, alpha):
    veil = pg.Surface(screen.get_size(), pg.SRCALPHA)
    veil.fill((*colour, alpha))
    screen.blit(veil, (0, 0))


def _tint(pg, w, h, colour, left):
    """A soft colour wash from one side, fading out by the middle."""
    s = pg.Surface((w, h), pg.SRCALPHA)
    s.fill((*colour, 0))
    x = np.linspace(0, 1, w)
    a = (np.clip(1 - x / 0.55, 0, 1) if left else np.clip((x - 0.45) / 0.55, 0, 1)) ** 1.4 * 150
    pg.surfarray.pixels_alpha(s)[:] = np.broadcast_to(a[:, None], (w, h)).astype(np.uint8)
    return s


def _glow(pg, surf, colour, grow=30, strength=220):
    """A blurred coloured halo the shape of the cut-out."""
    halo = pg.Surface((surf.get_width() + grow * 2, surf.get_height() + grow * 2), pg.SRCALPHA)
    big = np.zeros(halo.get_size(), np.float32)
    big[grow:-grow, grow:-grow] = pg.surfarray.array_alpha(surf) / 255.0
    pg.surfarray.pixels_alpha(halo)[:] = (big * 255).astype(np.uint8)
    small = pg.transform.smoothscale(halo, (max(1, halo.get_width() // 8), max(1, halo.get_height() // 8)))
    halo = pg.transform.smoothscale(small, halo.get_size())
    pg.surfarray.pixels_alpha(halo)[:] = np.clip(pg.surfarray.array_alpha(halo).astype(np.float32) * 2.2,
                                                 0, strength).astype(np.uint8)
    pg.surfarray.pixels3d(halo)[:] = colour
    return halo


def _vignette(pg, screen):
    W, H = screen.get_size()
    v = pg.Surface((W, H), pg.SRCALPHA)
    x = (np.arange(W)[:, None] - W / 2) / (W / 2)
    y = (np.arange(H)[None, :] - H / 2) / (H / 2)
    r = np.sqrt(x * x * 0.8 + y * y * 0.8)
    pg.surfarray.pixels_alpha(v)[:] = (np.clip((r - 0.7) / 0.6, 0, 1) * 150).astype(np.uint8)
    screen.blit(v, (0, 0))
