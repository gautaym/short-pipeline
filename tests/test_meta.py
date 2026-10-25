"""Titles, descriptions and the ledger."""
import json

from reel_engine import formats
from reel_engine.meta.generate import record
from reel_engine.meta.ledger import Ledger

CHANNEL = {"made_for_kids": None, "tags": ["simulation"], "hashtags": []}


def summary(tmp_path, mode, i, outcome):
    return {"mode": mode, "seed": i, "out": str(tmp_path / f"reel_{mode}_{i}.mp4"), "title": "Hook line",
            "duration": 25.0, "score": 1.0, "outcome": outcome}


def test_titles_never_repeat_even_for_identical_outcomes(tmp_path):
    ledger = Ledger(str(tmp_path / "ledger.sqlite"))
    outcome = {"result": "clear", "play_time": 21.3, "twist": None, "shape": "heart",
               "bricks_total": 300, "bricks_left": 0}
    titles = [record(summary(tmp_path, "classic", i, outcome), ledger, CHANNEL).title for i in range(150)]
    assert len(set(titles)) == len(titles)
    cores = [t.split(" | ")[0] for t in titles]
    assert all(a != b for a, b in zip(cores, cores[1:]))          # consecutive reels read differently
    assert titles[13].endswith("| 1 Ball Challenge #14")
    ledger.close()


def test_every_format_produces_titles_within_youtube_limit(tmp_path, pg):
    from reel_engine.core.drama import simulate
    from tests.test_formats import make_opts
    ledger = Ledger(str(tmp_path / "ledger.sqlite"))
    for fmt in [f for f in formats.all_formats() if not f.heavy]:
        trace = simulate(pg, fmt.name, 3, make_opts(max_play=4))
        meta = record(summary(tmp_path, fmt.name, 3, trace.outcome), ledger, CHANNEL)
        assert 0 < len(meta.title) <= 100 and "#shorts" in meta.description
    ledger.close()


def test_sidecar_files(tmp_path):
    ledger = Ledger(str(tmp_path / "ledger.sqlite"))
    o = {"result": "wars", "play_time": 30.0, "twist": "underdog", "teams": ["PINK", "CYAN"], "winner": "CYAN",
         "shares": {"PINK": 45, "CYAN": 55}}
    record(summary(tmp_path, "wars", 1, o), ledger, CHANNEL)
    data = json.loads((tmp_path / "reel_wars_1.json").read_text(encoding="utf-8"))
    assert data["made_for_kids"] is None and "CYAN" in data["title"]
    assert "underdog" in (tmp_path / "reel_wars_1.txt").read_text(encoding="utf-8")
    ledger.close()
