"""Sound synthesis and mixing.

Formats log sound events as (time, sound name, index) while they play. After the last frame the
events are mixed into a mono 16-bit WAV using the format's sound bank. A bank maps a name to one
sound, or to a list of pitched variants picked by index (wrapping round).
"""
import wave
from typing import Sequence, Union

import numpy as np

SR = 44100

SoundBank = dict[str, Union[np.ndarray, list[np.ndarray]]]
Event = tuple[float, str, int]


def tone(freq: float, dur: float, decay: float, harm: float = 0.3, noise: float = 0.0,
         chirp: float = 0.0) -> np.ndarray:
    """A short decaying tone with an optional second harmonic, noise and pitch sweep."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = freq * (1 + chirp * t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    w = np.sin(phase) + harm * np.sin(2 * phase)
    if noise:
        w += noise * np.random.default_rng(1).uniform(-1, 1, n)
    env = np.exp(-t * decay)
    att = min(n, int(0.003 * SR))
    env[:att] *= np.linspace(0, 1, att)
    return (w * env).astype(np.float32)


def overlay(*parts: tuple[float, np.ndarray]) -> np.ndarray:
    """Sum sounds that start at the given offsets (seconds) into one sound."""
    n = max(int(SR * off) + len(s) for off, s in parts)
    out = np.zeros(n, dtype=np.float32)
    for off, s in parts:
        a = int(SR * off)
        out[a:a + len(s)] += s
    return out


_common: SoundBank | None = None


def common_sounds() -> SoundBank:
    """Sounds the shared layer uses: hook whoosh, twist impact and slow-motion drop."""
    global _common
    if _common is None:
        _common = {
            "hook": tone(700, 0.55, 5, harm=0.2, noise=0.5, chirp=-0.75)[::-1].copy() * 0.28,
            "twist": overlay((0, tone(55, 0.8, 4.5, harm=0.9, noise=0.25) * 0.65),
                             (0.02, tone(1760, 0.45, 9, harm=0.1) * 0.22)),
            "slowmo": tone(420, 0.7, 3.5, harm=0.4, chirp=-0.6) * 0.3,
        }
    return _common


def place(events: Sequence[Event], bank: SoundBank, duration: float) -> np.ndarray:
    """The sound effects alone, as a float32 buffer of the given duration."""
    audio = np.zeros(int(SR * duration) + SR * 2, dtype=np.float32)
    for t, kind, idx in events:
        entry = bank[kind]
        s = entry[idx % len(entry)] if isinstance(entry, list) else entry
        a = int(t * SR)
        b = min(len(audio), a + len(s))
        audio[a:b] += s[: b - a]
    return audio[: int(SR * duration)]


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0


def mix(events: Sequence[Event], bank: SoundBank, duration: float, bed: np.ndarray | None = None,
        bed_level: float = 0.55, speech: Sequence[tuple[float, np.ndarray]] = ()) -> np.ndarray:
    """Effects over an optional music bed, plus spoken lines, as int16 PCM soft-clipped with tanh.

    The bed is scaled so its loudness is bed_level times the effects' loudness, so music stays
    audible under busy formats and never swamps quiet ones. While a line is spoken the music dips
    and the effects are lowered, so the words stay clear.
    """
    audio = place(events, bank, duration)
    duck = np.ones(len(audio), dtype=np.float32)
    for t, clip in speech:
        a, b = int(t * SR), min(len(audio), int(t * SR) + len(clip) + SR // 5)
        duck[a:b] = 0.45
    if len(speech):
        k = SR // 20                                   # smooth the dips over 50 ms
        duck = np.convolve(duck, np.ones(k, dtype=np.float32) / k, mode="same")
    level = max(rms(audio), 0.04)
    audio *= 0.5 + 0.5 * duck
    if bed is not None and rms(bed) > 0:
        n = min(len(bed), len(audio))
        audio[:n] += bed[:n] * (bed_level * level / rms(bed)) * duck[:n]
    for t, clip in speech:
        a = int(t * SR)
        b = min(len(audio), a + len(clip))
        if a < b:
            audio[a:b] += clip[: b - a] * max(1.0, 2.2 * level / 0.6)
    audio = np.tanh(audio * 1.3) * 0.85
    return (audio * 32767).astype(np.int16)


def write_wav(pcm: np.ndarray, path: str) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
