"""Frame-by-frame comparison of reel_engine against the original single-file brickreel.py.

Both versions are stepped side by side in one process. Every frame's pixels must match,
both must end on the same frame, and the sound events and mixed audio must be identical.
"""
import importlib.util
import tempfile
from argparse import Namespace
from pathlib import Path

from ..config import REPO_ROOT
from .. import formats
from ..core.audio import mix, write_wav
from ..core.canvas import FPS, H, W
from ..core.render import init_pygame

LEGACY_PATH = REPO_ROOT / "legacy" / "brickreel_v0.py"
_legacy = None


def legacy_module():
    global _legacy
    if _legacy is None:
        spec = importlib.util.spec_from_file_location("brickreel_v0", LEGACY_PATH)
        _legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_legacy)
    return _legacy


def make_opts(**kw) -> Namespace:
    base = dict(shape=None, text=None, teams=None, boss_hp=None, title=None, max_play=None)
    base.update(kw)
    return Namespace(**base)


def compare(mode: str, seed: int, **kw) -> tuple[bool, str]:
    """Run one case. Returns (ok, message)."""
    pg = init_pygame()
    L = legacy_module()
    opts = make_opts(**kw)
    old = L.MODES[mode](pg, seed, opts)
    new = formats.get(mode)(pg, seed, opts)
    if old.title != new.title:
        return False, f"title differs: {old.title!r} vs {new.title!r}"
    s_old, s_new = pg.Surface((W, H)), pg.Surface((W, H))
    frame = 0
    while True:
        t = frame / FPS
        old.update(1 / FPS, t)
        old.draw(s_old, t)
        new.update(1 / FPS, t)
        new.draw(s_new, t)
        if pg.image.tobytes(s_old, "RGB") != pg.image.tobytes(s_new, "RGB"):
            return False, f"frame {frame} differs"
        frame += 1
        old_end = bool(old.done) and t >= old.end_t + L.OUTRO_S
        new_end = new.finished(t)
        if old_end != new_end:
            return False, f"end differs at frame {frame - 1}: legacy {old_end}, new {new_end}"
        if old_end:
            break
    if old.events != new.events:
        return False, f"sound events differ ({len(old.events)} vs {len(new.events)})"
    duration = frame / FPS
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "old.wav", Path(d) / "new.wav"
        L.render_audio(old.events, duration, str(a))
        write_wav(mix(new.events, new.sounds(), duration), str(b))
        if a.read_bytes() != b.read_bytes():
            return False, "mixed audio differs"
    return True, f"{frame} frames, {len(new.events)} sounds, ended '{new.done}'"
