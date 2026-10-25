"""End-to-end smoke tests: CLI rendering, parallel batches and contact sheets (need ffmpeg)."""
import re

import pytest

from reel_engine import formats
from reel_engine.cli import main
from reel_engine.core.video import probe
from tests.conftest import needs_ffmpeg


@needs_ffmpeg
@pytest.mark.parametrize("mode", formats.names())
def test_each_format_renders_a_3_second_reel(tmp_path, mode):
    out = tmp_path / f"{mode}.mp4"
    assert main(["render", "--mode", mode, "--seed", "1", "--max-play", "3", "--out", str(out), "--no-ledger", "--no-voice"]) == 0
    info = probe(str(out))
    assert (info["width"], info["height"]) == (1080, 1920)
    assert info["duration"] > 3


@needs_ffmpeg
def test_parallel_batch_with_even_mix_renders_every_format(tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(f"render:\n  output_dir: '{tmp_path.as_posix()}'\n", encoding="utf-8")
    n = len(formats.random_pool())
    assert main(["--mode", "random", "--mix", "even", "--batch", str(n), "--seed", "40",
                 "--max-play", "1", "--workers", "2", "--config", str(cfg), "--no-voice"]) == 0
    tags = [re.fullmatch(r"reel_(.+)_\d+\.mp4", p.name).group(1) for p in tmp_path.glob("reel_*.mp4")]
    made = sorted(max((n for n in formats.random_pool() if t == n or t.startswith(n + "_")), key=len) for t in tags)
    assert made == sorted(formats.random_pool())


@needs_ffmpeg
def test_contact_sheet(tmp_path, pg):
    video = tmp_path / "v.mp4"
    main(["render", "--mode", "wars", "--seed", "2", "--max-play", "1", "--out", str(video), "--no-ledger", "--no-voice"])
    sheet = tmp_path / "sheet.png"
    assert main(["contact-sheet", str(video), "-n", "4", "--cols", "2", "-o", str(sheet)]) == 0
    img = pg.image.load(str(sheet))
    assert img.get_width() > 2 * 216 and img.get_height() > 2 * 384


@needs_ffmpeg
def test_voice_lines_are_spoken(tmp_path, pg):
    from reel_engine.core import voice
    if not voice.available():
        pytest.skip("Kokoro model files not in models/")
    clip = voice.say("Can one ball escape the spiral?")
    assert 1.0 < len(clip) / 44100 < 6.0 and abs(clip).max() > 0.5
