"""tower3d: a wrecking ball swings into a 3D tower of blocks, rendered by Blender (Eevee, on the GPU).

"Will the tower survive the wrecking ball?" Blender simulates the rigid bodies (a few seconds)
and renders the frames (about 0.6 s each on an RTX 3060); this format plays those frames and adds
the shared layer on top: hook card, title, HUD, voice, music, impact sounds and the end card.
Scouting only bakes the physics, so trying several seeds stays cheap; frames are rendered once,
for the chosen seed, and cached in out/blender/.

Not in the --mode random rotation, because each reel takes minutes rather than seconds.
"""
import json
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..core import blender
from ..core.audio import SR, SoundBank, overlay, tone
from ..core.canvas import FPS, H, W
from . import EndCard, Format, Option, register

CACHE = REPO_ROOT / "out" / "blender"
FELL_LINE = 0.6           # share of blocks that must come down for "the tower fell"


@register
class Tower3D(Format):
    name = "tower3d"
    order = 130
    default_duration = 20.0
    in_random_pool = False
    heavy = True                 # minutes per reel: kept out of the quick per-format tests
    options = (Option("--samples", "tower3d: Eevee render samples (quality vs speed)", {"type": int, "default": None}),)
    music = "tense"
    cta = "Did you think it would fall?"
    series = "Tower Demolition 3D"
    tags = ("3d", "simulation", "destruction", "physics", "satisfying", "blender")
    hashtags = ("3d", "destruction", "satisfying")

    @classmethod
    def titles(cls, o):
        f, b = o["fell"], o["blocks"]
        if o["result"] == "fell":
            return [f"{f} of {b} blocks came down", "1 wrecking ball vs a 3D tower", f"The tower lost {f} blocks",
                    "Will the tower survive? No."]
        return [f"Still standing after {len(o['hits'])} hits", f"Only {f} of {b} blocks fell",
                "The tower survived the wrecking ball", "1 wrecking ball, 1 stubborn tower"]

    @classmethod
    def describe(cls, o):
        return f"A rigid-body simulation in Blender: {o['fell']} of {o['blocks']} blocks fell."

    # ---------------------------------------------------------- setup
    def params(self, render: bool) -> dict:
        return {"seed": self.seed, "out_dir": str(self.dir), "frames": self.n_frames, "fps": FPS, "width": W,
                "height": H, "samples": getattr(self.opts, "samples", None) or 24, "swing_start": 75,
                "render": render}

    def setup(self) -> None:
        self.n_frames = int(round(self.max_play * FPS))
        self.dir = CACHE / f"tower_{self.seed}_{self.n_frames}"
        cached = self.dir / "result.json"
        if cached.exists():
            self.res = json.loads(cached.read_text(encoding="utf-8"))
        else:
            self.res = blender.run("tower", self.params(render=False))
        self.hit_times = [(f - 1) / FPS for f in self.res["hits"]]
        self.hits_done = 0
        self.frame_cache: tuple[int, object] | None = None

    def title_hooks(self) -> list[str]:
        b = self.res["blocks"]
        return ["Will the tower survive the wrecking ball?", f"{b} blocks vs 1 wrecking ball",
                "How many blocks will fall?"]

    # ---------------------------------------------------------- simulation
    def step(self, dt: float, t: float) -> None:
        while self.hits_done < len(self.hit_times) and self.play_t >= self.hit_times[self.hits_done]:
            self.hits_done += 1
            self.sfx(t, "boom", force=True)
            self.sfx(t, "rubble", self.hits_done, force=True)
            self.fx.shake(14 if self.hits_done == 1 else 8, 0.5)

    def check_end(self, t: float):
        if self.play_t >= self.max_play:
            return "fell" if self.res["fell"] >= FELL_LINE * self.res["blocks"] else "stood"
        return None

    def stats(self) -> list[str]:
        return [f"BLOCKS {self.res['blocks']}", f"HITS {self.hits_done}", f"0:{int(self.play_t):02d}"]

    def progress(self) -> float:
        return min(1.0, self.play_t / self.max_play)

    def drama_score(self, trace) -> float:
        share = trace.outcome["fell"] / trace.outcome["blocks"]
        return 4 * (1 - min(1.0, abs(share - FELL_LINE) / FELL_LINE))      # closest to the line wins

    def end_card(self) -> EndCard:
        f, b = self.res["fell"], self.res["blocks"]
        if self.done == "fell":
            return EndCard("THE TOWER FELL!", f"{f} of {b} blocks came down")
        return EndCard("STILL STANDING!", f"only {f} of {b} blocks fell")

    def outcome(self):
        return {**super().outcome(), "blocks": self.res["blocks"], "fell": self.res["fell"], "hits": self.res["hits"]}

    def sounds(self) -> SoundBank:
        rubble = []
        for k in range(4):
            n = int(SR * 1.6)
            t = np.arange(n) / SR
            noise = np.random.default_rng(k).uniform(-1, 1, n).astype(np.float32)
            rubble.append((noise * np.exp(-t * 2.2) * (0.5 + 0.5 * np.sin(t * 40 + k)) * 0.22).astype(np.float32))
        return {"boom": overlay((0, tone(48, 1.2, 3, harm=0.9, noise=0.3) * 0.7), (0, tone(120, 0.3, 14, noise=1.0) * 0.4)),
                "rubble": rubble, "clear": tone(392, 1.2, 3, harm=0.3) * 0.3, "fail": tone(220, 1.0, 3, chirp=-0.4) * 0.3}

    # ---------------------------------------------------------- drawing
    def frame_path(self, i: int) -> Path:
        return self.dir / "frames" / f"f_{i:04d}.png"

    def ensure_frames(self) -> None:
        if not self.frame_path(self.n_frames).exists():
            print(f"[tower3d {self.seed}] rendering {self.n_frames} frames in Blender (Eevee)...", flush=True)
            self.res = blender.run("tower", self.params(render=True), timeout=4 * 3600)

    def draw_world(self, screen, t: float) -> None:
        self.ensure_frames()
        i = min(self.n_frames, 1 + int(self.play_t * FPS))
        if self.frame_cache is None or self.frame_cache[0] != i:
            img = self.pg.image.load(str(self.frame_path(i)))
            self.frame_cache = (i, img)
        screen.blit(self.frame_cache[1], (0, 0))
        self.fx.draw_particles(screen)
