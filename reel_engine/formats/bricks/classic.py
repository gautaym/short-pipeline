"""classic: 1 ball against a brick shape (heart, star, a word...); power-up bricks spawn more balls."""
import numpy as np

from ...core.canvas import ARENA_T
from ...core.physics import BALL_R, Ball
from .. import EndCard, Option, Twist, register
from .engine import PADDLE_Y, BrickGame
from .mazes import MAZES
from .shapes import SHAPES, TEXT_WORDS, shape_mask

SHAPE_OPTION = Option("--shape", f"classic: {', '.join(SHAPES)} | escape: {', '.join(MAZES)}",
                      {"default": None})


@register
class ClassicGame(BrickGame):
    name = "classic"
    order = 10
    default_duration = 25.0
    options = (SHAPE_OPTION,
               Option("--text", "word to build from bricks (classic, --shape text)", {"default": None}))

    def setup(self) -> None:
        o = self.opts
        self.shape = getattr(o, "shape", None) or self.rng.choice(SHAPES)
        if self.shape not in SHAPES:
            raise SystemExit(f"classic shapes: {', '.join(SHAPES)}")
        self.text = (getattr(o, "text", None) or self.rng.choice(TEXT_WORDS)).upper()
        self.grid(40, 4, 26, ARENA_T + 50)
        mask = shape_mask(self.shape, self.text, self.pg, self.cols, self.rows)
        self.hp[:] = np.where(mask, self.nrng.choice([1, 2, 3], size=mask.shape, p=[0.8, 0.16, 0.04]), 0)
        self.place_powers(mask, 0.075)
        self.total = self.left = int(mask.sum())
        self.hp0 = self.hp.copy()
        self.make_palette()

    def twists(self) -> list[Twist]:
        return [Twist("multiball", "+8 BALLS!", lambda t: f"+{self.multiball(8)} BALLS!",
                      lambda: len(self.balls) <= 3),
                Twist("regrow", "the bricks are growing back",
                      lambda t: f"{self.regrow(0.3)} bricks just grew back", lambda: self.progress() > 0.35)]

    def on_destroy(self, r, c, t: float) -> None:
        if self.left == 0:
            self.mark("decisive")

    def title_hooks(self) -> list[str]:
        name = self.text if self.shape == "text" else self.shape.upper()
        return [f"Can 1 ball clear the {name}?", f"1 ball vs {self.total} bricks",
                f"Will the {name} break in {int(self.max_play)} seconds?"]

    def cell_colour(self, r, c, hp):
        return self.colours[(r, c, min(hp, 3))]

    def launch(self, t: float) -> None:
        self.balls.append(Ball(self.paddle_x, PADDLE_Y - BALL_R - 1, self.rng.uniform(-0.45, 0.45),
                               self.ball_speed))
        self.sfx(t, "paddle")

    def idle_ball(self):
        return self.paddle_x, PADDLE_Y - BALL_R - 1

    def check_end(self, t: float):
        if self.left == 0:
            return "clear"
        if not self.balls:
            self.mark("decisive")
            return "fail"
        if self.play_t >= self.max_play:
            return "time"
        return None

    def stats(self) -> list[str]:
        return [f"BRICKS {self.left}", f"BALLS {len(self.balls)}", self.clock(self.play_t)]

    def progress(self) -> float:
        return 1 - self.left / max(1, self.total)

    def end_card(self) -> EndCard:
        if self.done == "clear":
            return EndCard("CLEARED!", f"in {self.play_t:.1f} seconds")
        if self.done == "fail":
            return EndCard("OUT OF BALLS", f"only {self.left} bricks left...")
        return EndCard("TIME UP!", f"{self.left} bricks survived")

    def outcome(self):
        return {**super().outcome(), "shape": self.shape if self.shape != "text" else self.text,
                "bricks_total": self.total, "bricks_left": self.left}
