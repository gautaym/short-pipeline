"""fire3d: a campfire, then a storm. "Will the fire survive the wind?"

A Blender smoke-and-fire simulation (Mantaflow), rendered with Eevee from the baked OpenVDB
volume. A gusting wind (seeded strength) rises after a calm start; Blender measures the flame
height throughout. The fire "holds on" if it never drops below half its calm height.

Not in the --mode random rotation, because each reel takes minutes rather than seconds.
"""
import json

import numpy as np

from ..config import REPO_ROOT
from ..core import blender
from ..core.audio import SR, SoundBank, tone
from ..core.canvas import FPS, H, W
from . import EndCard, Format, register

CACHE = REPO_ROOT / "out" / "blender"
FRAMES = 450
SPIN = 90
HOLD = 0.5                       # flame must stay above this share of its calm height


@register
class Fire3D(Format):
    name = "fire3d"
    order = 150
    default_duration = FRAMES / FPS
    in_random_pool = False
    heavy = True
    max_scout = 3
    music = "tense"
    cta = "Did you think it would survive?"
    series = "Fire vs Storm"
    tags = ("3d", "fire simulation", "satisfying", "physics", "blender", "storm")
    hashtags = ("fire", "simulation", "3d")

    @classmethod
    def titles(cls, o):
        if o["result"] == "held":
            return ["The fire held on through the storm", "Will the fire survive the wind? Yes",
                    f"Never below {o['storm_min']} m", "Fire vs storm: the fire wins"]
        return ["The storm flattened the fire", "Will the fire survive the wind? Barely...",
                f"From {o['calm']} m down to {o['storm_min']} m", "Fire vs storm: the storm wins"]

    @classmethod
    def describe(cls, o):
        return (f"A fire simulation in Blender: a {o['calm']} m campfire hit by a gusting storm "
                f"dropped to {o['storm_min']} m at its lowest.")

    def params(self, render: bool) -> dict:
        return {"seed": self.seed, "out_dir": str(self.dir), "frames": FRAMES, "fps": FPS, "width": W, "height": H,
                "samples": 24, "resolution": 96, "spin_frame": SPIN, "render": render}

    def setup(self) -> None:
        self.dir = CACHE / f"fire_{self.seed}"
        cached = self.dir / "result.json"
        self.res = json.loads(cached.read_text(encoding="utf-8")) if cached.exists() else \
            blender.run("fire", self.params(render=False))
        self.ratio = self.res["storm_min"] / max(self.res["calm"], 1e-6)
        self.frame_cache = None
        self.lowest_marked = False

    def title_hooks(self) -> list[str]:
        return ["Will the fire survive the storm?", "Campfire vs a storm. Who wins?", "Can the wind put it out?"]

    def at(self, key: str) -> float:
        rows = self.res[key]
        return rows[min(len(rows) - 1, int(self.play_t * FPS / self.res["every"]))]

    def step(self, dt: float, t: float) -> None:
        f = self.play_t * FPS
        if not self.lowest_marked and f >= SPIN + 60 and self.at("heights") <= self.res["storm_min"]:
            self.lowest_marked = True
            self.mark("decisive")

    def check_end(self, t: float):
        if self.play_t >= self.max_play:
            return "held" if self.ratio >= HOLD else "flattened"
        return None

    def stats(self) -> list[str]:
        return [f"FLAME {self.at('heights'):.1f} m", f"WIND {round(10 * self.at('wind'))}/10",
                f"0:{int(self.play_t):02d}"]

    def progress(self) -> float:
        return min(1.0, self.play_t / self.max_play)

    def hud_accent(self):
        return (255, 140, 40)

    def drama_score(self, trace) -> float:
        return 4 * (1 - min(1.0, abs(self.ratio - HOLD) / HOLD))           # a close call scores best

    def end_card(self) -> EndCard:
        lo, calm = self.res["storm_min"], self.res["calm"]
        if self.done == "held":
            return EndCard("THE FIRE HELD ON!", f"it never dropped below {lo:.1f} m")
        return EndCard("THE STORM WON!", f"flattened from {calm:.1f} m to {lo:.1f} m")

    def outcome(self):
        return {**super().outcome(), "calm": self.res["calm"], "storm_min": self.res["storm_min"]}

    def sounds(self) -> SoundBank:
        n = int(SR * (FRAMES / FPS + 6))
        rng = np.random.default_rng(self.seed)
        crackle = np.zeros(n, dtype=np.float32)
        for _ in range(int(n / SR * 14)):                                  # pops and crackles
            a = rng.integers(0, n - 2000)
            crackle[a:a + 1500] += (rng.uniform(-1, 1, 1500) * np.exp(-np.arange(1500) / 120) * rng.uniform(0.05, 0.3))
        noise = rng.uniform(-1, 1, n)
        rush = np.convolve(noise, np.ones(60) / 60, mode="same") * 3.0
        level = np.interp(np.arange(n) / SR - self.intro_s,
                          np.arange(len(self.res["wind"])) * self.res["every"] / FPS, self.res["wind"], left=0, right=0)
        bed = (crackle * 0.5 + rush * level * 0.35).astype(np.float32)
        return {"bed": bed, "clear": tone(392, 1.2, 3) * 0.3, "fail": tone(196, 1.2, 3, chirp=-0.3) * 0.3}

    def update(self, dt: float, t: float) -> None:
        if self.frame_no == 0:
            self.sfx(0.0, "bed", force=True)
        super().update(dt, t)

    def ensure_frames(self) -> None:
        if not (self.dir / "frames" / f"f_{FRAMES:04d}.png").exists():
            print(f"[fire3d {self.seed}] rendering {FRAMES} frames in Blender (Eevee)...", flush=True)
            self.res = blender.run("fire", self.params(render=True), timeout=4 * 3600)

    def draw_world(self, screen, t: float) -> None:
        self.ensure_frames()
        i = min(FRAMES, 1 + int(self.play_t * FPS))
        if self.frame_cache is None or self.frame_cache[0] != i:
            self.frame_cache = (i, self.pg.image.load(str(self.dir / "frames" / f"f_{i:04d}.png")))
        screen.blit(self.frame_cache[1], (0, 0))
        self.fx.draw_particles(screen)
