"""Registry, determinism and parity with the original brickreel.py."""
import hashlib

import pytest

from reel_engine import formats
from reel_engine.core.canvas import H, W
from reel_engine.core.render import frames
from reel_engine.tools.parity import compare, make_opts

BRICK_FORMATS = ["classic", "escape", "boss", "wars"]


def frame_hashes(pg, mode: str, seed: int, **kw) -> list[str]:
    game = formats.get(mode)(pg, seed, make_opts(**kw))
    screen = pg.Surface((W, H))
    return [hashlib.md5(pg.image.tobytes(screen, "RGB")).hexdigest() for _ in frames(game, screen)]


def test_registry_lists_brick_formats_in_rotation_order():
    assert formats.names()[:4] == BRICK_FORMATS


def test_every_format_declares_the_plugin_interface():
    for fmt in formats.all_formats():
        assert fmt.name and fmt.default_duration > 0
        for opt in fmt.options:
            assert opt.flag.startswith("--") and opt.help


@pytest.mark.parametrize("mode", BRICK_FORMATS)
def test_same_seed_gives_identical_frames(pg, mode):
    assert frame_hashes(pg, mode, 5, max_play=1.5) == frame_hashes(pg, mode, 5, max_play=1.5)


@pytest.mark.parametrize("mode", BRICK_FORMATS)
def test_different_seeds_differ(pg, mode):
    assert frame_hashes(pg, mode, 5, max_play=1) != frame_hashes(pg, mode, 6, max_play=1)


@pytest.mark.parametrize("mode", BRICK_FORMATS)
def test_matches_original_script(pg, mode):
    ok, msg = compare(mode, 3, max_play=2)
    assert ok, msg
