"""mystery: a picture hidden under the bricks. Every broken brick uncovers a little more.

"Guess the picture before it's revealed". Viewers are invited to comment their guess, a hint
appears part-way through, and at the end the remaining bricks shatter to show the answer.
"""
import random

import numpy as np

from ...core.canvas import ARENA_T, H, W
from ...core.text import outlined
from .. import EndCard, Option, register
from .classic import ClassicGame
from .pictures import BUILT_IN, Picture, image_picture, user_pictures

COVER = (24, 24, 32)        # what shows between bricks, so the gaps never leak the picture
PROMPT_AT = 0.2             # progress at which "Comment your guess" pops up
HINT_AT = 0.45              # progress at which the hint pops up
REVEAL_S = 0.8              # how long the final reveal takes
POWER_SHARE = 0.09
MESSAGE_Y = 1560            # prompts and hints sit in the clear space under the board


@register
class MysteryGame(ClassicGame):
    name = "mystery"
    order = 50
    default_duration = 25.0
    options = (Option("--picture", "mystery: image file to hide (default: a built-in or assets/pictures/)",
                      {"default": None}),
               Option("--answer", "mystery: answer shown at the reveal (default: from the file name)",
                      {"default": None}))
    end_veil = False
    card_y = H - 300
    cta = "Did you guess it?"

    def setup(self) -> None:
        path = getattr(self.opts, "picture", None)
        if path:
            self.pic: Picture = image_picture(path, getattr(self.opts, "answer", None))
        else:
            self.pic = self.rng.choice(BUILT_IN + user_pictures())
        self.grid(40, 4, 26, ARENA_T + 50)
        mask = np.ones((self.rows, self.cols), dtype=bool)
        self.hp[:] = self.nrng.choice([1, 2], size=mask.shape, p=[0.85, 0.15])
        self.place_powers(mask, POWER_SHARE)
        self.total = self.left = int(mask.sum())
        self.hp0 = self.hp.copy()
        self.make_palette()
        self.shape, self.text = "mystery", ""
        self.prompted = self.hinted = self.shattered = False
        self.message: tuple[float, object] | None = None    # (video time shown, surface)

    def title_hooks(self) -> list[str]:
        return ["Guess the picture before it's revealed", "What's hiding behind the bricks?",
                "Can you guess it before 50%?", "Guess it before the last brick breaks"]

    def _build_bg(self) -> None:
        super()._build_bg()
        w, h = self.cols * self.cell, self.rows * self.cell
        self.picture = self.pic.draw(self.pg, w, h, random.Random(f"pic:{self.seed}"))
        self.bg.blit(self.picture, (self.bx0, self.by0))

    def backdrop(self, r, c, x, y) -> None:
        if self.hp[r, c] != 0:
            self.field.fill(COVER, (x, y, self.cell, self.cell))
        else:
            super().backdrop(r, c, x, y)

    def cell_colour(self, r, c, hp):
        # muted bricks, so the cover never hints at the picture's colours
        return tuple(int(0.45 * v + 0.55 * 95) for v in self.colours[(r, c, min(hp, 3))])

    def step(self, dt: float, t: float) -> None:
        super().step(dt, t)
        p = self.progress()
        if not self.prompted and p >= PROMPT_AT:
            self.prompted = True
            self.show(t, "Comment your guess!", (255, 214, 64))
        if not self.hinted and self.pic.hint and p >= HINT_AT:
            self.hinted = True
            self.show(t, f"HINT: {self.pic.hint}", (255, 255, 255))

    def show(self, t: float, text: str, colour) -> None:
        """Put a message on the line under the board (visual only)."""
        if self.fx.enabled:
            self.message = (t, outlined(self.pg, self.fonts.cta, text, colour, 4))

    def end_sound(self, why: str) -> str:
        return "clear"

    def draw_world(self, screen, t: float) -> None:
        super().draw_world(screen, t)
        if self.message and not self.done:
            shown, surf = self.message
            surf.set_alpha(int(255 * min(1.0, (t - shown) / 0.3)))
            screen.blit(surf, surf.get_rect(center=(W / 2, MESSAGE_Y)))
        if not self.done:
            return
        if not self.shattered:
            self.shattered = True
            for r, c in np.argwhere(self.hp != 0)[::3]:
                cx, cy = self.centre(r, c)
                self.fx.burst(cx, cy, self.cell_colour(r, c, 1), n=3, power=0.8)
        k = min(1.0, (t - self.end_t) / REVEAL_S)
        self.picture.set_alpha(int(255 * k))
        screen.blit(self.picture, (self.bx0, self.by0))
        self.picture.set_alpha(None)

    def drama_score(self, trace) -> float:
        """Best when most, but not quite all, of the picture shows by the end, or it clears late."""
        shown = trace.outcome.get("revealed_pct", 0) / 100
        s = 4 * (1 - abs(shown - 0.88) / 0.88)
        if trace.done == "clear" and trace.decisive_t is not None:
            s += 2 - 3 * abs(trace.decisive_t / self.max_play - 0.85)
        if trace.done == "fail":
            s -= 2
        return s + (0.5 if trace.twist else 0.0)

    def stats(self) -> list[str]:
        return [f"REVEALED {round(100 * self.progress())}%", f"BALLS {len(self.balls)}", self.clock(self.play_t)]

    def end_card(self) -> EndCard:
        article = "AN" if self.pic.answer[:1] in "AEIOU" else "A"
        pct = round(100 * self.progress())
        sub = f"fully revealed in {self.play_t:.1f}s" if self.left == 0 else f"you only saw {pct}% of it"
        return EndCard(f"IT'S {article} {self.pic.answer}!", sub)

    def outcome(self):
        return {"result": self.done, "play_time": round(self.play_t, 1), "twist": self.twist_fired,
                "answer": self.pic.answer, "revealed_pct": round(100 * self.progress())}
