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


def mix(events: Sequence[Event], bank: SoundBank, duration: float) -> np.ndarray:
    """Mix the events into int16 PCM of the given duration, soft-clipped with tanh."""
    audio = np.zeros(int(SR * duration) + SR * 2, dtype=np.float32)
    for t, kind, idx in events:
        entry = bank[kind]
        s = entry[idx % len(entry)] if isinstance(entry, list) else entry
        a = int(t * SR)
        b = min(len(audio), a + len(s))
        audio[a:b] += s[: b - a]
    audio = np.tanh(audio * 1.3) * 0.85
    return (audio[: int(SR * duration)] * 32767).astype(np.int16)


def write_wav(pcm: np.ndarray, path: str) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
