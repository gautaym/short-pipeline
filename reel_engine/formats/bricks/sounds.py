"""Brick-breaker sound bank: pentatonic hits that climb with each brick, plus paddle, wall and fanfares."""
from functools import lru_cache

import numpy as np

from ...core.audio import SR, SoundBank, tone

PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28]


@lru_cache(maxsize=1)
def brick_sounds() -> SoundBank:
    bank: SoundBank = {"hit": [], "break": []}
    for k in PENTA:
        f = 523.25 * 2 ** (k / 12)
        bank["hit"].append(tone(f, 0.09, 45) * 0.35)
        bank["break"].append(tone(f * 1.5, 0.14, 30, harm=0.5, noise=0.15) * 0.4)
    bank["paddle"] = tone(196, 0.12, 25, harm=0.6) * 0.5
    bank["wall"] = tone(1480, 0.05, 70, harm=0.1) * 0.18
    bank["boss"] = tone(98, 0.16, 22, harm=0.8, noise=0.1) * 0.45
    bank["power"] = tone(440, 0.35, 8, harm=0.4, chirp=1.5) * 0.55
    bank["lost"] = tone(150, 0.25, 12, chirp=-0.5) * 0.3
    clear = np.zeros(int(SR * 1.7), dtype=np.float32)
    for s, d in ((0, 0), (4, 0.08), (7, 0.16), (12, 0.24)):
        note = tone(523.25 * 2 ** (s / 12), 1.4, 3)
        a = int(SR * d)
        clear[a:a + len(note)] += note
    bank["clear"] = clear * 0.35
    bank["fail"] = tone(220, 1.0, 3, chirp=-0.4) * 0.4
    return bank
