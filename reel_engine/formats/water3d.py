"""water3d: water pours over planks and pegs into three glasses. "Which glass fills first?"

A Blender liquid simulation (Mantaflow), rendered with Eevee on the GPU. Blender bakes the fluid
and measures how full each glass is over time; this format shows live A/B/C percentages, labels
over the glasses, and the shared layer: hook card, title, voice, music, pouring sound, end card.
Only the frames up to shortly after the first glass is full are rendered.

Not in the --mode random rotation, because each reel takes minutes rather than seconds.
"""
import json

import numpy as np

from ..config import REPO_ROOT
from ..core import blender
from ..core.audio import SR, SoundBank, tone
from ..core.canvas import FPS, H, W
from ..core.text import outlined
from . import EndCard, Format, register

CACHE = REPO_ROOT / "out" / "blender"
BAKE_FRAMES = 600                    # simulated; only the needed part is rendered
LINGER_FRAMES = 75                   # keep playing this long after the first glass is full
NAMES = "ABC"


@register
class Water3D(Format):
    name = "water3d"
    order = 140
    default_duration = 20.0
    in_random_pool = False
    heavy = True
    max_scout = 3                    # each pre-pass bakes a fluid (about 40 s)
    music = "chill"
    cta = "Did you pick the right glass?"
    series = "Which Glass Fills First?"
    tags = ("3d", "fluid simulation", "water", "satisfying", "physics", "blender")
    hashtags = ("satisfying", "fluidsimulation", "3d")

    @classmethod
    def titles(cls, o):
        w, t = NAMES[o["winner"]], o["full_s"]
        return [f"Glass {w} filled first ({t}s)", "Which glass fills first?", f"Did you pick glass {w}?",
                f"Water race: glass {w} wins"]

    @classmethod
    def describe(cls, o):
        return f"A liquid simulation in Blender: glass {NAMES[o['winner']]} filled first, after {o['full_s']} seconds."

    def params(self, render: bool, end: int | None = None) -> dict:
        p = {"seed": self.seed, "out_dir": str(self.dir), "frames": BAKE_FRAMES, "fps": FPS, "width": W, "height": H,
             "samples": 24, "resolution": 96, "inflow_frames": BAKE_FRAMES, "render": render}
        if end:
            p.update(start=1, end=end)
        return p

    def setup(self) -> None:
        self.dir = CACHE / f"water_{self.seed}"
        cached = self.dir / "result.json"
        self.res = json.loads(cached.read_text(encoding="utf-8")) if cached.exists() else \
            blender.run("water", self.params(render=False))
        done = [f for f in self.res["full_at"] if f is not None]
        self.end_frame = min(BAKE_FRAMES, (min(done) if done else BAKE_FRAMES - LINGER_FRAMES) + LINGER_FRAMES)
        self.max_play = self.end_frame / FPS
        self.full_frame = min(done) if done else None
        self.announced = False
        self.frame_cache = None
        self.label_surfs = [outlined(self.pg, self.fonts.big, n, (255, 255, 255), 5) for n in NAMES]

    def title_hooks(self) -> list[str]:
        return ["Which glass fills first?", "Pick a glass: A, B or C!", "Watch where the water goes",
                "One tap, three glasses. Which wins?"]

    def fill(self, i: int) -> float:
        rows, every = self.res["timeline"], self.res["every"]
        k = min(len(rows) - 1, int(self.play_t * FPS / every))
        return rows[k][i]

    def step(self, dt: float, t: float) -> None:
        if not self.announced and self.full_frame and self.play_t * FPS >= self.full_frame:
            self.announced = True
            self.mark("decisive")
            self.sfx(t, "ding", force=True)
            self.fx.shake(6, 0.3)

    def check_end(self, t: float):
        return "filled" if self.play_t >= self.max_play else None

    def stats(self) -> list[str]:
        return [f"{n} {round(100 * self.fill(i))}%" for i, n in enumerate(NAMES)]

    def progress(self) -> float:
        return max(self.fill(i) for i in range(3))

    def drama_score(self, trace) -> float:
        if max(self.res["final"]) < 0.3:
            return -10.0                                      # the water never reached a glass
        full = sorted(f for f in self.res["full_at"] if f is not None)
        if len(full) < 2:
            return 1.0
        gap = (full[1] - full[0]) / FPS                       # a close race scores best
        late = min(1.0, full[0] / FPS / 12)
        return 4 * (1 - min(1.0, gap / 6)) + 2 * late

    def end_card(self) -> EndCard:
        w = NAMES[self.res["winner"]]
        if self.full_frame:
            return EndCard(f"GLASS {w} WINS!", f"full after {self.full_frame / FPS:.1f} seconds")
        return EndCard(f"GLASS {w} WINS!", "the fullest when the tap ran dry")

    def outcome(self):
        return {**super().outcome(), "winner": self.res["winner"], "full_at": self.res["full_at"],
                "full_s": round((self.full_frame or self.end_frame) / FPS, 1)}

    def sounds(self) -> SoundBank:
        n = int(SR * 30)
        noise = np.random.default_rng(7).uniform(-1, 1, n)
        pour = np.convolve(noise, np.ones(40) / 40, mode="same") * 1.6           # soft, low rush of water
        pour *= 0.8 + 0.2 * np.sin(np.arange(n) / SR * 2 * np.pi * 0.7)
        pour[: SR // 2] *= np.linspace(0, 1, SR // 2)
        return {"pour": (pour * 0.25).astype(np.float32),
                "ding": tone(1046.5, 0.8, 4, harm=0.2) * 0.35, "clear": tone(784, 1.2, 3) * 0.3,
                "fail": tone(220, 1.0, 3, chirp=-0.4) * 0.3}

    def update(self, dt: float, t: float) -> None:
        if self.frame_no == 0:
            self.sfx(t + self.intro_s, "pour", force=True)
        super().update(dt, t)

    def ensure_frames(self) -> None:
        last = self.dir / "frames" / f"f_{self.end_frame:04d}.png"
        if not last.exists():
            print(f"[water3d {self.seed}] rendering {self.end_frame} frames in Blender (Eevee)...", flush=True)
            blender.run("water", self.params(render=True, end=self.end_frame), timeout=4 * 3600)

    def draw_world(self, screen, t: float) -> None:
        self.ensure_frames()
        i = min(self.end_frame, 1 + int(self.play_t * FPS))
        if self.frame_cache is None or self.frame_cache[0] != i:
            self.frame_cache = (i, self.pg.image.load(str(self.dir / "frames" / f"f_{i:04d}.png")))
        screen.blit(self.frame_cache[1], (0, 0))
        for k, (lx, ly) in enumerate(self.res["labels"]):
            lab = self.label_surfs[k]
            screen.blit(lab, lab.get_rect(center=(lx * W, ly * H)))
        self.fx.draw_particles(screen)
