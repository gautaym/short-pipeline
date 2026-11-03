"""Puppets and backdrops for puppet-theatre stories, drawn locally with an image model
(ai/imagegen.py in aienv), then cut out so the reel can move the puppets on stage.

A story's `art` block holds two locked styles, a fixed description of each character, and the
puppets and backdrops the story needs, with characters named as {shiva}, {deva}, ...:

    art:
      puppet_style: "A single flat painted leather shadow puppet ... against a plain pure black backdrop"
      prop_style: "A single flat painted leather shadow puppet scenery piece ..."
      backdrop_style: "The painted cloth backdrop of a traditional Indian shadow puppet theatre ..."
      cast: {shiva: "Lord Shiva with blue skin ...", ...}
      puppets: {shiva: "The puppet is {shiva}, standing calmly, side view facing right.", ...}
      props: {mandara: "The prop is a tall rocky mountain ..."}    (prop_style; moved like puppets;
              a puppet or prop may be {style: "...", text: "..."} to use its own style)
      backdrops: {ocean: "A vast white ocean of milk ...", ...}

Characters used across stories (the Sutradhar host, gods drawn once and approved once) live in
the shared library, stories/_library.yaml, drawn with `reel story-art _library`; a story's stage can
use any library puppet it does not draw itself.

Files go in stories/art/<id>/ (git-ignored): puppet_<name>.png and backdrop_<name>.png, extra
takes as puppet_<name>_<take>.png. Copy the best take over puppet_<name>.png to choose it. Puppets
face right; the reel mirrors them. Each puppet is cut out of its black background into
puppet_<name>_cut.png, made again whenever the picture is newer.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT

ART = REPO_ROOT / "stories" / "art"
LIBRARY = "_library"                         # stories/_library.yaml: characters shared by every story
PYTHON = REPO_ROOT / "aienv" / "Scripts" / "python.exe"
SCRIPT = REPO_ROOT / "ai" / "imagegen.py"
MODEL = "Tongyi-MAI/Z-Image-Turbo"           # Apache 2.0; weights held in 8-bit to fit a 12 GB card
PUPPET_SIZE = (832, 1216)
BACKDROP_SIZE = (864, 1536)                  # 9:16, scaled up to the reel's 1080 x 1920
BLACK = 34                                   # background pixels are darker than this on every channel


def folder(story_id: str) -> Path:
    return ART / story_id


def puppet_file(story_id: str, name: str) -> Path:
    """The story's own picture of a puppet, or the shared library's if the story has none."""
    own = folder(story_id) / f"puppet_{name}.png"
    shared = folder(LIBRARY) / f"puppet_{name}.png"
    return shared if not own.exists() and shared.exists() else own


def cut_file(story_id: str, name: str) -> Path:
    src = puppet_file(story_id, name)
    return src.with_name(f"{src.stem}_cut.png")


def facing(sc: dict, name: str) -> str:
    """Which way the puppet's picture faces, "right" unless the art says otherwise (`facing: {name: left}`).
    The model does not always draw the side it was asked for, so this is set after looking at the picture."""
    own = sc.get("art", {}).get("facing", {})
    if name in own:
        return own[name]
    from ..formats.story import load_story
    return load_story(LIBRARY).get("art", {}).get("facing", {}).get(name, "right")


def backdrop_file(story_id: str, name: str) -> Path:
    return folder(story_id) / f"backdrop_{name}.png"


def segment(sc: dict) -> dict | None:
    """The story's segment from the library: {"narrator": name, "asker": name}, or None."""
    name = sc.get("segment")
    if not name:
        return None
    from ..formats.story import load_story
    return load_story(LIBRARY)["segments"][name]


def cast_segment(sc: dict) -> None:
    """Put the segment's pair on stage, facing each other: in the cold open the asker walks in and
    asks the question and the narrator joins to answer; in the last beat the narrator closes, the asker
    beside them."""
    pair = segment(sc)
    if not pair:
        return
    opening = sc.setdefault("opening", {})
    opening.setdefault("beat", 1)
    if sc.get("ask", True) is False:                     # told straight: the narrator opens and closes alone
        opening["actors"] = {"narrator": {"puppet": pair["narrator"], "x": 540, "y": 2010, "h": 780, "z": 11,
                                          "face": "left", "motion": "talk", "enter": "right"},
                             **opening.get("actors", {})}
        sc["beats"][-1]["stage"].setdefault("actors", {}).setdefault(
            "narrator", {"puppet": pair["narrator"], "x": 600, "y": 2150, "h": 780, "z": 11,
                         "face": "left", "motion": "talk", "enter": "right"})
        return
    opening["actors"] = {
        "asker": {"puppet": pair["asker"], "x": 310, "y": 2000, "h": 720, "z": 10, "face": "right",
                  "motion": "talk", "enter": "left"},
        "narrator": {"puppet": pair["narrator"], "x": 770, "y": 2010, "h": 780, "z": 11, "face": "left",
                     "motion": "talk", "enter": "right", "delay": 1.2},
        **opening.get("actors", {})}
    last = sc["beats"][-1]["stage"].setdefault("actors", {})
    last.setdefault("narrator", {"puppet": pair["narrator"], "x": 600, "y": 2150, "h": 780, "z": 11,
                                 "face": "left", "motion": "talk", "enter": "right"})
    last.setdefault("asker", {"puppet": pair["asker"], "x": 230, "y": 2140, "h": 720, "z": 10,
                              "face": "right", "motion": "breathe", "enter": "left"})


def _clean(text: str) -> str:
    return " ".join(text.split())


def prompts(sc: dict) -> dict[str, tuple[str, tuple[int, int]]]:
    """Every picture the story needs: {"puppet_shiva": (prompt, size), "backdrop_ocean": ...}."""
    art = sc["art"]
    cast = {k: _clean(v) for k, v in art.get("cast", {}).items()}
    out = {}
    for name, text in art.get("puppets", {}).items():
        style = art["puppet_style"]
        if isinstance(text, dict):                                   # a puppet with its own style
            style, text = text["style"], text["text"]
        out[f"puppet_{name}"] = (f"{_clean(style)} {text.format(**cast)}", PUPPET_SIZE)
    for name, text in art.get("props", {}).items():                # scenery pieces moved like puppets
        style = art["prop_style"]
        if isinstance(text, dict):                                   # a prop with its own style
            style, text = text["style"], text["text"]
        out[f"puppet_{name}"] = (f"{_clean(style)} {text.format(**cast)}", PUPPET_SIZE)
    for name, text in art.get("backdrops", {}).items():
        out[f"backdrop_{name}"] = (f"{_clean(art['backdrop_style'])} The scene: {text.format(**cast)}", BACKDROP_SIZE)
    return out


def generate(sc: dict, takes: int = 2, only: list[str] | None = None, redo: bool = False) -> list[Path]:
    """Draw the pictures a story is missing (or those named in `only`, with redo) in one batch.

    Puppets get `takes` versions each to choose from; backdrops get one.
    """
    out = folder(sc["id"])
    jobs = []
    for n, (key, (prompt, (w, h))) in enumerate(sorted(prompts(sc).items())):
        if only and key.split("_", 1)[1] not in only and key not in only:
            continue
        for take in range(takes if key.startswith("puppet_") else 1):
            path = out / (f"{key}.png" if take == 0 else f"{key}_{take + 1}.png")
            if path.exists() and not redo:
                continue
            seed = sum(map(ord, key)) * 100 + take
            jobs.append({"prompt": prompt, "seed": seed, "width": w, "height": h, "out": str(path)})
    if jobs:
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "jobs.json"
            spec.write_text(json.dumps({"model": MODEL, "jobs": jobs}), encoding="utf-8")
            print(f"drawing {len(jobs)} picture(s) for {sc['id']} with {MODEL} ...", flush=True)
            subprocess.run([str(PYTHON), str(SCRIPT), str(spec)], check=True, cwd=REPO_ROOT)
    return [Path(j["out"]) for j in jobs]


def cut_out(rgb: np.ndarray) -> np.ndarray:
    """Alpha (0-255) for a puppet photographed on black: the background is the near-black region
    reachable from the picture's edges, so dark paint inside the puppet stays solid."""
    level = rgb.max(axis=2)
    border = np.concatenate([level[:6].ravel(), level[-6:].ravel(), level[:, :6].ravel(), level[:, -6:].ravel()])
    dark = level < max(BLACK, float(np.percentile(border, 80)) + 14)    # some "black" backdrops are textured grey;
                                                                        # a stick touching the edge is a few percent
    bg = np.zeros_like(dark)
    bg[0, :], bg[-1, :], bg[:, 0], bg[:, -1] = dark[0, :], dark[-1, :], dark[:, 0], dark[:, -1]
    while True:                                                  # grow from the edges through dark pixels
        grown = bg.copy()
        grown[1:] |= bg[:-1]
        grown[:-1] |= bg[1:]
        grown[:, 1:] |= bg[:, :-1]
        grown[:, :-1] |= bg[:, 1:]
        grown &= dark
        if (grown == bg).all():
            break
        bg = grown
    alpha = (~bg).astype(np.float32)
    soft = alpha.copy()                                          # feather the edge by a pixel
    soft[1:-1, 1:-1] = sum(alpha[1 + dy:alpha.shape[0] - 1 + dy, 1 + dx:alpha.shape[1] - 1 + dx]
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
    return (np.minimum(alpha, soft) * 255).astype(np.uint8)


def outline(pg, rgb: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int] | None]:
    """The puppet's alpha mask on its black backdrop, and the rectangle it fills (None if empty)."""
    alpha = cut_out(rgb)
    size = rgb.shape[:2]
    pocket = pg.Surface(size, pg.SRCALPHA)                            # background trapped inside the outline,
    pg.surfarray.pixels_alpha(pocket)[:] = np.where((rgb.max(axis=2) < BLACK) & (alpha > 0), 255, 0)  # e.g.
    for p in pg.mask.from_surface(pocket, 127).connected_components():  # between an arm and the body
        if p.count() >= 0.002 * rgb.shape[0] * rgb.shape[1]:          # big enough not to be paint or outline
            hole = pg.surfarray.array_alpha(p.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)))
            alpha = np.where(hole > 0, 0, alpha)
    surf = pg.Surface(size, pg.SRCALPHA)
    pg.surfarray.pixels_alpha(surf)[:] = alpha
    pieces = pg.mask.from_surface(surf, 127).connected_components()   # drop specks of textured background
    if pieces:
        biggest = max(p.count() for p in pieces)
        keep = pg.mask.Mask(size)
        for p in pieces:
            if p.count() >= 0.1 * biggest:
                keep.draw(p, (0, 0))
        alpha = np.where(pg.surfarray.array_alpha(keep.to_surface(setcolor=(255, 255, 255, 255),
                                                                  unsetcolor=(0, 0, 0, 0))) > 0, alpha, 0)
    cols, rows = np.flatnonzero(alpha.max(axis=1) > 0), np.flatnonzero(alpha.max(axis=0) > 0)
    if not (len(cols) and len(rows)):
        return alpha, None
    return alpha, (cols[0], rows[0], cols[-1] - cols[0] + 1, rows[-1] - rows[0] + 1)


def cut_with(pg, rgb: np.ndarray, alpha: np.ndarray, rect):
    surf = pg.Surface(rgb.shape[:2], pg.SRCALPHA)
    pg.surfarray.pixels3d(surf)[:] = rgb
    pg.surfarray.pixels_alpha(surf)[:] = alpha
    return surf.subsurface(rect).copy() if rect else surf


def cut(pg, story_id: str, name: str):
    """The puppet cut out of its background and cropped to it, cached as puppet_<name>_cut.png."""
    src, dst = puppet_file(story_id, name), cut_file(story_id, name)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return pg.image.load(str(dst))
    rgb = pg.surfarray.array3d(pg.image.load(str(src)))             # (w, h, 3)
    alpha, rect = outline(pg, rgb)
    surf = cut_with(pg, rgb, alpha, rect)
    pg.image.save(surf, str(dst))
    return surf


def live_face(sc: dict, name: str) -> list[float] | None:
    """The face box [cx, cy, width] (fractions of the picture) of a puppet that comes alive, from the
    story's `art.live` or the library's; None for a puppet that stays still."""
    own = sc.get("art", {}).get("live", {})
    if name in own:
        return own[name]
    from ..formats.story import load_story
    return load_story(LIBRARY).get("art", {}).get("live", {}).get(name)


def live_dir(story_id: str, name: str) -> Path:
    """Where a puppet's living-face frames are kept, next to its picture: raw frames 0000.png ...,
    cut-out frames c0000.png ..."""
    src = puppet_file(story_id, name)
    return src.with_name(f"{src.stem}_live")


def live_frames(pg, story_id: str, name: str) -> list:
    """The puppet's living-face loop, cut out with the still picture's own outline (cached)."""
    folder = live_dir(story_id, name)
    raw = sorted(folder.glob("[0-9][0-9][0-9][0-9].png")) if folder.is_dir() else []
    if not raw:
        return []
    cuts = [folder / f"c{f.name}" for f in raw]
    if all(c.exists() and c.stat().st_mtime >= f.stat().st_mtime for c, f in zip(cuts, raw)):
        return [pg.image.load(str(c)) for c in cuts]
    alpha, rect = outline(pg, pg.surfarray.array3d(pg.image.load(str(puppet_file(story_id, name)))))
    frames = []
    for f, c in zip(raw, cuts):
        surf = cut_with(pg, pg.surfarray.array3d(pg.image.load(str(f))), alpha, rect)
        pg.image.save(surf, str(c))
        frames.append(surf)
    return frames


def make_live(sc: dict) -> list[str]:
    """Make the living-face loops a story needs that are missing or older than their picture (lpenv)."""
    names = {a["puppet"] for b in sc["beats"] for a in b["stage"].get("actors", {}).values()}
    names |= {a["puppet"] for a in (sc.get("opening") or {}).get("actors", {}).values()}
    seg = segment(sc)
    if seg:
        names |= {seg["narrator"], seg["asker"]}
    jobs = []
    for name in sorted(names):
        face = live_face(sc, name)
        src = puppet_file(sc["id"], name)
        if not face or not src.exists():
            continue
        folder = live_dir(sc["id"], name)
        first = folder / "0000.png"
        if first.exists() and first.stat().st_mtime >= src.stat().st_mtime:
            continue
        jobs.append({"src": str(src.relative_to(REPO_ROOT)), "face": face,
                     "out": str(folder.relative_to(REPO_ROOT))})
    if not jobs:
        return []
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(jobs, f)
    python = REPO_ROOT / "lpenv" / "Scripts" / "python.exe"
    subprocess.run([str(python), str(REPO_ROOT / "ai" / "liveface.py"), f.name], check=True, cwd=REPO_ROOT,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return [j["out"] for j in jobs]
