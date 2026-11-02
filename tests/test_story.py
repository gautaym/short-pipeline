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
