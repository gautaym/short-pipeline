"""Spoken lines (the hook, the result) with Kokoro, an open text-to-speech model (Apache 2.0).

The model files live in models/ (git-ignored): kokoro-v1.0.onnx and voices-v1.0.bin from the
kokoro-onnx releases. If they are missing, reels render without a voice.
"""
import re

import numpy as np

from ..config import REPO_ROOT
from .audio import SR

MODEL = REPO_ROOT / "models" / "kokoro-v1.0.onnx"
VOICES = REPO_ROOT / "models" / "voices-v1.0.bin"
KEEP_CAPS = {"BFS", "DFS", "HP"}          # read letter by letter
_engine = None
_cache: dict[tuple, np.ndarray] = {}


def available() -> bool:
    if not (MODEL.exists() and VOICES.exists()):
        return False
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        return False
    return True


def speakable(text: str) -> str:
    """Turn on-screen text (often in capitals) into something that reads naturally aloud."""
    text = text.replace("A*", "A star").replace(" vs ", " versus ").replace("%", " percent")
    words = []
    for w in text.split():
        core = re.sub(r"[^A-Za-z]", "", w)
        words.append(w if core in KEEP_CAPS else w.lower())
    out = " ".join(words)
    out = re.sub(r"([.!?:]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out[:1].upper() + out[1:]


def language(voice: str) -> str:
    """Kokoro voice names start with a language letter: a = US, b = UK English, h = Hindi."""
    return {"b": "en-gb", "h": "hi"}.get(voice[:1], "en-us")


def say(text: str, voice: str = "am_michael", speed: float = 1.05) -> np.ndarray:
    """Speech for the text as float32 at the engine's sample rate, peak-normalised to 0.6.

    Results are cached for the life of the process, so a story's narration is synthesised once
    for timing and reused for the final mix.
    """
    global _engine
    key = (text, voice, speed)
    if key in _cache:
        return _cache[key]
    if _engine is None:
        from kokoro_onnx import Kokoro
        _engine = Kokoro(str(MODEL), str(VOICES))
    lang = language(voice)
    spoken = text if lang == "hi" else speakable(text)
    samples, rate = _engine.create(spoken, voice=voice, speed=speed, lang=lang)
    samples = np.asarray(samples, dtype=np.float32)
    if rate != SR:
        t_out = np.arange(int(len(samples) * SR / rate)) / SR
        samples = np.interp(t_out, np.arange(len(samples)) / rate, samples).astype(np.float32)
    peak = float(np.abs(samples).max()) or 1.0
    _cache[key] = samples * (0.6 / peak)
    return _cache[key]
