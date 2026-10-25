"""escape: the ball starts trapped in a carved maze lined with unbreakable grey bricks.

The hook is whether, and where, it breaks out to the top.
"""
import math

import numpy as np

from ...core.canvas import ARENA_T, W
from ...core.physics import Ball
from .. import EndCard, Twist, register
from .classic import SHAPE_OPTION
from .engine import BrickGame
from .mazes import MAZES

ESCAPE_FILLS = [(250, 215, 40), (60, 220, 255), (255, 110, 170), (150, 235, 80),
                (255, 160, 60), (190, 140, 255)]
POWER_SHARE = 0.03
AFTERMATH_S = 6.0     # play continues this long after the breakout...
MIN_PLAY_S = 16.0     # ...and at least until this much play, so the smash-out gets screen time


@register
class EscapeGame(BrickGame):
    name = "escape"
    order = 20
    options = (SHAPE_OPTION,)
    ball_speed = 1100.0
    fancy_bricks = False

    series = "Brick Escape"
    tags = ("brick breaker", "maze escape", "satisfying", "simulation", "can it escape")
    hashtags = ("satisfying", "maze", "simulation")

    @classmethod
    def titles(cls, o):
        m = str(o["maze"]).upper()
        if o["escaped"]:
            t = o["escape_time"]
            return [f"Broke out of the {m} in {t}s", f"Trapped in the {m}... for {t} seconds",
                    f"Escaped the {m} at {t}s", f"Can the ball escape the {m}? ({t}s)"]
        return [f"Still trapped in the {m}", f"The {m} won this time", f"No way out of the {m}",
                f"40 seconds in the {m}: no escape"]

    @classmethod
    def describe(cls, o):
        if o["escaped"]:
            return f"The ball broke out of the {str(o['maze']).upper()} maze after {o['escape_time']} seconds."
        return f"The ball never escaped the {str(o['maze']).upper()} maze."

    def setup(self) -> None:
        self.maze = getattr(self.opts, "shape", None) or self.rng.choice(list(MAZES))
        if self.maze not in MAZES:
            raise SystemExit(f"escape shapes: {', '.join(MAZES)}")
        self.grid(18, 2, 55, ARENA_T)
        strokes, start = MAZES[self.maze]()
        if self.rng.random() < 0.5:                     # mirror for extra variety
            strokes = [[(-x, y) for x, y in s] for s in strokes]
            start = (-start[0], start[1])

        def to_cells(p):
            return (p[0] + 1) / 2 * self.cols, (1 - p[1]) / 2 * self.rows

        cx = np.arange(self.cols) + 0.5
        cy = np.arange(self.rows) + 0.5
        px, py = np.meshgrid(cx, cy)
        dist = np.full(px.shape, 1e9)
        segs = []
        for s in strokes:
            for a, b in zip(s, s[1:]):
                ax, ay = to_cells(a)
                bx, by = to_cells(b)
                segs.append((ax, ay, bx, by))
                vx, vy = bx - ax, by - ay
                k = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
                dist = np.minimum(dist, np.hypot(px - (ax + k * vx), py - (ay + k * vy)))

        hw = 1.45
        channel = dist <= hw
        band = (dist > hw) & (dist <= hw + 1.15)

        # weak spots: short stretches of wall left breakable, so there is a way out
        weak = np.zeros(px.shape, dtype=bool)
        cands = [s for s in segs if min(s[1], s[3]) < self.rows * 0.75]
        lengths = np.array([math.hypot(s[2] - s[0], s[3] - s[1]) for s in cands])
        for _ in range(self.rng.randint(2, 4)):
            ax, ay, bx, by = cands[self.nrng.choice(len(cands), p=lengths / lengths.sum())]
            k = self.rng.uniform(0.2, 0.8)
            wx, wy = ax + k * (bx - ax), ay + k * (by - ay)
            if wy > self.rows * 0.8:
                continue
            weak |= np.hypot(px - wx, py - wy) <= 2.8

        self.hp[:] = 1
        self.hp[channel] = 0
        self.hp[band & ~weak] = -1
        # power bricks out in the field: once the ball is through a wall, the escape can snowball
        self.place_powers((self.hp > 0) & (dist > hw + 4), POWER_SHARE, big_chance=0.0)
        self.total = self.left = int((self.hp > 0).sum())
        self.fill = self.rng.choice(ESCAPE_FILLS)
        sx, sy = to_cells(start)
        self.start = (self.bx0 + sx * self.cell, self.by0 + sy * self.cell)
        self.escaped_t = None
        self.escape_play = 0.0

    def twists(self) -> list[Twist]:
        def free() -> bool:
            return self.escaped_t is None
        return [Twist("earthquake", "the walls are cracking", self._quake, free),
                Twist("split", "the ball split into 3!", self._split,
                      lambda: free() and 1 <= len(self.balls) <= 2)]

    def _quake(self, t: float) -> None:
        walls = np.argwhere(self.hp[: int(self.rows * 0.7)] < 0)
        if len(walls) == 0:
            return None
        rr, cc = np.mgrid[0:self.rows, 0:self.cols]
        crack = np.zeros(self.hp.shape, dtype=bool)
        for r, c in walls[self.nrng.choice(len(walls), min(3, len(walls)), replace=False)]:
            crack |= np.hypot(rr - r, cc - c) <= 2.2
        crack &= self.hp < 0
        self.hp[crack] = 1
        n = int(crack.sum())
        self.left += n
        self.total += n
        for r, c in np.argwhere(crack):
            self._paint(r, c)
        return None

    def _split(self, t: float) -> None:
        for b in list(self.balls):
            for _ in range(2):
                self.balls.append(Ball(b.x, b.y, self.rng.uniform(-math.pi, math.pi), self.ball_speed))
        return None

    def drama_score(self, trace) -> float:
        bonus = 0.5 if trace.twist else 0.0
        if not trace.outcome.get("escaped"):
            return -2.0 + bonus
        f = trace.outcome["escape_time"] / self.max_play
        return 5 - 4 * abs(f - 0.45) + bonus

    def _build_bg(self) -> None:
        self._flat_bg((32, 32, 38))

    def title_hooks(self) -> list[str]:
        name = self.maze.upper()
        return [f"Can the ball escape the {name}?", "Where will it break out?",
                f"Will it escape in {int(self.max_play)} seconds?", "Trapped ball. Will it get out?"]

    def cell_colour(self, r, c, hp):
        return self.fill

    def launch(self, t: float) -> None:
        self.balls.append(Ball(*self.start, self.rng.uniform(-math.pi, math.pi), self.ball_speed))
        self.sfx(t, "paddle")

    def idle_ball(self):
        return self.start

    def on_destroy(self, r, c, t: float) -> None:
        if r == 0 and self.escaped_t is None:
            self.escaped_t = t
            self.escape_play = self.play_t
            self.mark("decisive")
            self.fx.flash = 1.0
            self.fx.shake(16, 0.6)
            self.fx.floater(W / 2, ARENA_T + 220, "ESCAPED!", (255, 255, 255), self.fonts.big, 1.6)
            self.sfx(t, "clear", force=True)

    def check_end(self, t: float):
        if (self.escaped_t is not None and self.play_t - self.escape_play >= AFTERMATH_S
                and self.play_t >= MIN_PLAY_S):
            return "escape"
        if self.left == 0:
            return "clear"
        if not self.balls:
            return "fail"
        if self.play_t >= self.max_play:
            return "escape" if self.escaped_t is not None else "trapped"
        return None

    def stats(self) -> list[str]:
        state = "FREE!" if self.escaped_t is not None else "TRAPPED"
        return [f"BROKEN {self.total - self.left}", state, self.clock(self.play_t)]

    def progress(self) -> float:
        return 1 - self.left / max(1, self.total)

    def end_card(self) -> EndCard:
        if self.done == "escape":
            return EndCard("ESCAPED!", f"broke out in {self.escape_play:.1f} seconds")
        if self.done == "trapped":
            return EndCard("TRAPPED!", f"still stuck after {int(self.max_play)} seconds")
        if self.done == "clear":
            return EndCard("CLEARED!", f"in {self.play_t:.1f} seconds")
        return EndCard("OUT OF BALLS", f"{self.total - self.left} bricks broken")

    def outcome(self):
        return {**super().outcome(), "maze": self.maze, "escaped": self.escaped_t is not None,
                "escape_time": round(self.escape_play, 1) if self.escaped_t is not None else None}
