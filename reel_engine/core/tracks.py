"""Background music from royalty-free tracks you download into assets/music/<mood>/.

Put tracks (mp3, wav, ogg, m4a, flac) in mood folders, e.g. assets/music/mythic/, calm/, tense/,
festive/, upbeat/. A reel picks one track from the folder named by its format's music style
(seeded, so the same seed picks the same track), takes the length it needs and fades it out.
If a track needs attribution, put the credit line in a text file with the same name
(e.g. "Song.mp3" and "Song.txt"); it is added to the reel's description.

Only use tracks whose licence allows use in monetised videos (e.g. Pixabay Music, or YouTube
Audio Library tracks marked for use in your videos).
"""
import random
import subprocess
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from .audio import SR
from .video import find_tool

MUSIC = REPO_ROOT / "assets" / "music"
TYPES = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
FADE_IN_S, FADE_OUT_S = 0.4, 2.0


def tracks(mood: str) -> list[Path]:
    folder = MUSIC / mood
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in TYPES) if folder.is_dir() else []


def pick(mood: str, seed: int) -> Path | None:
    found = tracks(mood)
    return random.Random(f"track:{seed}").choice(found) if found else None


def credit(track: Path) -> str | None:
    note = track.with_suffix(".txt")
    return note.read_text(encoding="utf-8").strip() if note.exists() else None


def load(track: Path, seconds: float) -> np.ndarray:
    """The first `seconds` of the track as mono float32 at the engine's rate, looped if short."""
    raw = subprocess.run([find_tool(), "-v", "error", "-i", str(track), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).copy()
    n = int(seconds * SR)
    if len(audio) == 0:
        return np.zeros(n, dtype=np.float32)
    while len(audio) < n:
        audio = np.concatenate([audio, audio])
    audio = audio[:n]
    fi, fo = min(n, int(FADE_IN_S * SR)), min(n, int(FADE_OUT_S * SR))
    audio[:fi] *= np.linspace(0, 1, fi)
    audio[-fo:] *= np.linspace(1, 0, fo)
    return audio
