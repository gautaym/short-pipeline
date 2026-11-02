"""Story scripts and the story format."""
from argparse import Namespace

import pytest

from reel_engine import formats
from reel_engine.formats.story import load_story, story_ids
from reel_engine.story.puppet import POSES, PRESETS


@pytest.mark.parametrize("sid", story_ids())
def test_scripts_are_complete(sid):
    sc = load_story(sid)
    assert sc["title"]["en"] and sc["title"]["hi"]
    for name, spec in sc["cast"].items():
        assert spec["preset"] in PRESETS, f"{sid}: unknown preset for {name}"
    for i, b in enumerate(sc["beats"]):
        assert b["en"] and b["hi"] and b["caption"], f"{sid}: beat {i + 1} is missing text"
        for name, spec in (b.get("actors") or {}).items():
            assert name in sc["cast"], f"{sid}: beat {i + 1} uses {name}, who is not in the cast"
            assert spec.get("pose", "stand") in POSES, f"{sid}: beat {i + 1} has an unknown pose"


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_story_timeline_and_frames(pg, lang, tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("render:\n  voice: false\n", encoding="utf-8")
    sid = story_ids()[0]
    game = formats.get("story")(pg, 1, Namespace(story=sid, lang=lang, config=str(cfg), title=None, max_play=None,
                                                  twist="none", min_length=0))
    assert game.starts == sorted(game.starts) and game.max_play > 20
    assert len(game.narration()) == len(game.beats) + 1
    screen = pg.Surface((1080, 1920))
    for f in range(0, int(game.max_play * 30), 90):             # every third second draws without error
        game.update(1 / 30, f / 30)
        game.draw(screen, f / 30)


@pytest.mark.parametrize("sid", [s for s in story_ids() if "art" in load_story(s)])
def test_stages_use_defined_art(sid):
    from reel_engine.story.art import prompts
    sc = load_story(sid)
    made = prompts(sc)                                   # fails if a prompt names someone not in art.cast
    shared = {k for k in prompts(load_story("_library")) if k.startswith("puppet_")}
    assert all("{" not in text for text, _ in made.values())
    for i, b in enumerate(sc["beats"]):
        stage = b["stage"]
        assert f"backdrop_{stage['backdrop']}" in made, f"{sid}: beat {i + 1} uses an undefined backdrop"
        for name, actor in stage.get("actors", {}).items():
            key = f"puppet_{actor['puppet']}"
            assert key in made or key in shared, f"{sid}: beat {i + 1}: {name} uses an undefined puppet"


def test_art_prompts_fill_in_the_cast():
    from reel_engine.story.art import BACKDROP_SIZE, PUPPET_SIZE, prompts
    sc = {"art": {"puppet_style": "Flat   puppet.", "backdrop_style": "Painted cloth.",
                  "cast": {"hero": "a blue   hero"},
                  "puppets": {"hero": "The puppet is {hero}."}, "backdrops": {"sea": "Waves."}}}
    assert prompts(sc) == {"puppet_hero": ("Flat puppet. The puppet is a blue hero.", PUPPET_SIZE),
                           "backdrop_sea": ("Painted cloth. The scene: Waves.", BACKDROP_SIZE)}


def test_cut_out_keeps_dark_paint_inside_the_puppet():
    import numpy as np
    from reel_engine.story.art import cut_out
    rgb = np.zeros((40, 40, 3), np.uint8)
    rgb[10:30, 10:30] = 200                              # a puppet ...
    rgb[15:25, 15:25] = 5                                # ... with black paint in the middle
    alpha = cut_out(rgb)
    assert alpha[0, 0] == 0 and alpha[20, 20] == 255 and alpha[12, 12] == 255
