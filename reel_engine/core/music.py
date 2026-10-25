"""Background music generated from the seed: copyright-free by construction.

Each reel gets its own short track: a tempo, a chord progression (common progressions are not
copyrightable) and a style that suits the format. The key defaults to C major / A minor so the
formats' pentatonic sound effects always sit in tune on top.
"""
import random

import numpy as np

from .audio import SR

STYLES = ("upbeat", "chill", "tense", "festive", "chiptune")

PROGRESSIONS = {                      # scale degrees (0 = I) of one chord per bar
    "major": [[0, 4, 5, 3], [5, 3, 0, 4], [0, 5, 3, 4], [3, 0, 4, 5], [0, 3, 5, 4]],
    "minor": [[0, 5, 2, 6], [0, 3, 4, 0], [0, 6, 5, 6], [0, 5, 3, 4]],
}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]

SETTINGS = {   # bpm range, mode, kick pattern (beats), snare, arp step (beats, 0 = off), level
    "upbeat":   ((112, 126), "major", [0, 1, 2, 3], True, 0.5, 1.0),
    "chill":    ((80, 94), "major", [0, 2], False, 1.0, 0.9),
    "tense":    ((96, 110), "minor", [0, 1.5, 2, 3.5], False, 0.25, 0.9),
    "festive":  ((104, 116), "major", [0, 2, 2.5], True, 0.5, 1.0),
    "chiptune": ((128, 142), "major", [0, 2], True, 0.25, 0.8),
}


def midi_hz(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


class Track:
    """A mono float32 buffer that notes are written into."""

    def __init__(self, seconds: float, noise_seed: int):
        self.buf = np.zeros(int(SR * seconds) + SR, dtype=np.float32)
        self.noise = np.random.default_rng(noise_seed)

    def add(self, start: float, wave: np.ndarray) -> None:
        a = int(start * SR)
        if a >= len(self.buf):
            return
        b = min(len(self.buf), a + len(wave))
        self.buf[a:b] += wave[: b - a]

    def tone(self, freq, dur, decay, vol, harm=0.0, attack=0.004, square=False, detune=0.0):
        n = max(1, int(SR * dur))
        t = np.arange(n) / SR
        ph = 2 * np.pi * freq * t
        if square:
            w = np.sign(np.sin(ph)) * 0.6
        else:
            w = np.sin(ph) + harm * np.sin(2 * ph)
            if detune:
                w = 0.5 * (w + np.sin(ph * (1 + detune)))
        env = np.exp(-t * decay)
        att = min(n, max(1, int(attack * SR)))
        env[:att] *= np.linspace(0, 1, att)
        rel = min(n, int(0.03 * SR))
        env[-rel:] *= np.linspace(1, 0, rel)
        return (w * env * vol).astype(np.float32)

    def kick(self, vol):
        n = int(SR * 0.3)
        t = np.arange(n) / SR
        f = 45 + 75 * np.exp(-t * 28)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * vol).astype(np.float32)

    def hiss(self, dur, decay, vol, tone_hz=0.0):
        n = int(SR * dur)
        t = np.arange(n) / SR
        w = np.diff(self.noise.uniform(-1, 1, n + 1))          # crude high-pass
        if tone_hz:
            w = 0.6 * w + 0.4 * np.sin(2 * np.pi * tone_hz * t)
        return (w * np.exp(-t * decay) * vol).astype(np.float32)


def compose(seconds: float, seed: int, style: str = "upbeat", key: int = 60) -> np.ndarray:
    """A track of the given length, fading in briefly and out over the last 1.5 s."""
    if style not in SETTINGS:
        raise ValueError(f"unknown music style {style}; choose from {', '.join(STYLES)}")
    rng = random.Random(f"music:{seed}")
    (lo, hi), mode, kicks, snare, arp_step, level = SETTINGS[style]
    bpm = rng.uniform(lo, hi)
    beat = 60 / bpm
    bar = 4 * beat
    scale = MAJOR if mode == "major" else MINOR
    root = key if mode == "major" else key - 3            # A minor shares C major's notes
    prog = rng.choice(PROGRESSIONS[mode])
    chip = style == "chiptune"
    tr = Track(seconds, rng.randrange(1 << 30))
    arp_shape = rng.choice([[0, 1, 2, 1], [0, 1, 2, 3], [2, 1, 0, 1], [0, 2, 1, 2]])

    def chord(degree: int) -> list[int]:
        return [root + scale[(degree + k) % 7] + 12 * ((degree + k) // 7) for k in (0, 2, 4)]

    t0, i = 0.0, 0
    while t0 < seconds:
        notes = chord(prog[i % len(prog)])
        for n in notes:                                       # pad
            if chip:
                tr.add(t0, tr.tone(midi_hz(n), bar, 1.2, 0.035, square=True))
            else:
                tr.add(t0, tr.tone(midi_hz(n), bar * 1.02, 0.5, 0.05, attack=0.25, detune=0.004))
        for b in range(4):                                    # bass on every beat (root, fifth)
            n = notes[0] - 24 + (7 if b == 2 and style != "chill" else 0)
            tr.add(t0 + b * beat, tr.tone(midi_hz(n), beat * 0.95, 4, 0.16, harm=0.4, square=chip))
        if arp_step:                                          # arpeggio
            steps = int(4 / arp_step)
            for s in range(steps):
                n = notes[arp_shape[s % 4] % 3] + 12 + (12 if style == "festive" and s % 2 else 0)
                tr.add(t0 + s * arp_step * beat, tr.tone(midi_hz(n), arp_step * beat * 1.6, 9, 0.045,
                                                         harm=0.2, square=chip))
        for k in kicks:
            tr.add(t0 + k * beat, tr.kick(0.32))
        if snare:
            for k in (1, 3):
                tr.add(t0 + k * beat, tr.hiss(0.18, 22, 0.12, tone_hz=190))
        for h in range(8):                                    # off-beat hats
            if h % 2 == 1 or style in ("upbeat", "chiptune"):
                tr.add(t0 + h * beat / 2, tr.hiss(0.05, 70, 0.05 if h % 2 else 0.025))
        t0 += bar
        i += 1
    out = tr.buf[: int(SR * seconds)] * level
    fade_in, fade_out = int(0.25 * SR), int(1.5 * SR)
    out[:fade_in] *= np.linspace(0, 1, fade_in)
    out[-fade_out:] *= np.linspace(1, 0, fade_out)
    return out.astype(np.float32)
