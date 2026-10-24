"""Registry, determinism, the draw-independence rule, scouting and twists."""
import hashlib
from argparse import Namespace

import pytest

from reel_engine import formats
from reel_engine.core.canvas import H, W
from reel_engine.core.drama import scout, simulate
from reel_engine.core.render import frames

BRICK_FORMATS = ["classic", "escape", "boss", "wars"]


def make_opts(**kw) -> Namespace:
    base = dict(shape=None, text=None, teams=None, boss_hp=None, title=None, max_play=None, twist="auto",
                min_length=0)
    base.update(kw)
    return Namespace(**base)


def render_run(pg, mode: str, seed: int, **kw):
    """Render every frame in memory; return (frame hashes, game)."""
    game = formats.get(mode)(pg, seed, make_opts(**kw))
    game.plan = simulate(pg, mode, seed, make_opts(**kw)).plan()
    screen = pg.Surface((W, H))
    hashes = [hashlib.md5(pg.image.tobytes(screen, "RGB")).hexdigest() for _ in frames(game, screen)]
    return hashes, game


def test_registry_lists_formats_in_rotation_order():
    assert formats.names()[:4] == BRICK_FORMATS


def test_every_format_declares_the_plugin_interface():
    for fmt in formats.all_formats():
        assert fmt.name and fmt.default_duration > 0
        for opt in fmt.options:
            assert opt.flag.startswith("--") and opt.help


@pytest.mark.parametrize("mode", formats.names())
def test_same_seed_gives_identical_frames(pg, mode):
    a, _ = render_run(pg, mode, 5, max_play=2)
    b, _ = render_run(pg, mode, 5, max_play=2)
    assert a == b


@pytest.mark.parametrize("mode", formats.names())
def test_different_seeds_differ(pg, mode):
    a, _ = render_run(pg, mode, 5, max_play=1)
    b, _ = render_run(pg, mode, 6, max_play=1)
    assert a != b


@pytest.mark.parametrize("mode", formats.names())
@pytest.mark.parametrize("seed", [1, 2])
def test_simulation_without_drawing_matches_render(pg, mode, seed):
    """Seed scouting relies on this: gameplay must not depend on drawing or effects."""
    kw = dict(max_play=6, twist="auto")
    trace = simulate(pg, mode, seed, make_opts(**kw))
    _, game = render_run(pg, mode, seed, **kw)
    assert (game.done, game.play_t, game.twist_fired) == (trace.done, trace.play_t, trace.twist)


def test_scouting_is_deterministic_and_picks_the_top_score(pg):
    best1, traces = scout(pg, "wars", 3, 4, make_opts(max_play=5))
    best2, _ = scout(pg, "wars", 3, 4, make_opts(max_play=5))
    assert best1.seed == best2.seed
    assert best1.score == max(t.score for t in traces)
    assert {t.seed for t in traces} == {3000, 3001, 3002, 3003}


@pytest.mark.parametrize("mode", BRICK_FORMATS)
def test_named_twist_fires(pg, mode):
    fmt = formats.get(mode)
    game = fmt(pg, 1, make_opts())
    for tw in game.twists():
        kw = {"boss_hp": 60} if mode == "boss" else {}
        fired = [simulate(pg, mode, s, make_opts(twist=tw.name, max_play=20, **kw)).twist for s in range(6)]
        assert tw.name in fired, f"{mode}: twist {tw.name} never fired"


def test_short_run_is_padded_to_min_length(pg):
    n, _ = render_run(pg, "wars", 1, max_play=1, min_length=20)
    assert len(n) == 20 * 30


@pytest.mark.parametrize("mode,seed,kw", [("classic", 0, {"shape": "text", "text": "OK"}),
                                          ("boss", 2, {"boss_hp": 15}), ("escape", 3, {})])
def test_length_estimate_matches_render(pg, mode, seed, kw):
    trace = simulate(pg, mode, seed, make_opts(**kw))
    frames_rendered, _ = render_run(pg, mode, seed, **kw)
    assert trace.decisive_tick is not None
    assert abs(trace.natural_s - len(frames_rendered) / 30) <= 2 / 30
