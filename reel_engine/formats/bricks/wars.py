"""wars: colour territories battle it out; each team's ball converts the other teams' bricks.

"Which colour wins?"
"""
import math

import numpy as np

from ...core.canvas import ARENA_L, ARENA_R, ARENA_T, LOST_Y, W
from ...core.physics import BALL_R, Ball
from .. import EndCard, Option, register
from .engine import BrickGame

TEAM_COLOURS = [("PINK", (255, 80, 160)), ("CYAN", (40, 200, 255)), ("LIME", (140, 230, 60)),
                ("ORANGE", (255, 150, 40)), ("PURPLE", (160, 100, 255)), ("YELLOW", (250, 215, 40))]


@register
class WarsGame(BrickGame):
    name = "wars"
    order = 40
    options = (Option("--teams", "wars mode team count", {"type": int, "choices": [2, 3, 4], "default": None}),)
    has_paddle = False
    ball_speed = 900.0
    fancy_bricks = False
    default_duration = 30.0
    MAX_PER_TEAM = 6

    def setup(self) -> None:
        self.n = getattr(self.opts, "teams", None) or self.rng.choice([2, 2, 3, 4])
        self.grid(30, 2, (LOST_Y - ARENA_T) // 30, ARENA_T)
        self.teams = self.rng.sample(TEAM_COLOURS, self.n)
        rows, cols = self.rows, self.cols
        rr, cc = np.mgrid[0:rows, 0:cols]
        if self.n == 2 and self.rng.random() < 0.5:
            if self.rng.random() < 0.5:
                self.owner = (cc >= cols // 2).astype(np.int32)
            else:
                self.owner = (rr >= rows // 2).astype(np.int32)
        else:
            seeds = [(self.rng.uniform(0.15, 0.85) * rows, self.rng.uniform(0.15, 0.85) * cols)
                     for _ in range(self.n)]
            d = np.stack([np.hypot((rr - sr) / rows, (cc - sc) / cols) for sr, sc in seeds])
            self.owner = d.argmin(axis=0).astype(np.int32)
        cells = np.argwhere(np.ones((rows, cols), dtype=bool))
        n_pow = max(self.n * 3, int(rows * cols * 0.012))
        for r, c in cells[self.nrng.choice(len(cells), n_pow, replace=False)]:
            self.power[r, c] = 1
        self.launched = True          # balls are on the board from the first frame
        for team in range(self.n):
            own = np.argwhere(self.owner == team)
            r, c = own[len(own) // 2]
            x, y = self.centre(r, c)
            self.balls.append(Ball(x, y, self.rng.uniform(-math.pi, math.pi), self.ball_speed, team))
        self.counts = np.bincount(self.owner.ravel(), minlength=self.n)

    def _build_bg(self) -> None:
        self._flat_bg((22, 22, 28))

    def _build_sprites(self) -> None:
        pg = self.pg
        self.ball_sprites = {}
        for i, (_, col) in enumerate(self.teams):
            s = pg.Surface((BALL_R * 3, BALL_R * 3), pg.SRCALPHA)
            cx = BALL_R * 1.5
            dark = tuple(int(v * 0.35) for v in col)
            pg.draw.circle(s, (255, 255, 255), (cx, cx), BALL_R + 3)
            pg.draw.circle(s, dark, (cx, cx), BALL_R)
            self.ball_sprites[i] = s

    def _paint(self, r, c) -> None:
        pg, cell, g = self.pg, self.cell, self.gap
        x, y = self.bx0 + c * cell, self.by0 + r * cell
        self.field.blit(self.bg, (x, y), (x, y, cell, cell))
        col = self.teams[int(self.owner[r, c])][1]
        pg.draw.rect(self.field, col, (x + g // 2, y + g // 2, cell - g, cell - g), border_radius=3)
        if self.power[r, c]:
            pg.draw.circle(self.field, (255, 255, 255), (x + cell // 2, y + cell // 2), 7)
            pg.draw.circle(self.field, col, (x + cell // 2, y + cell // 2), 3)

    def draw_power(self, screen, t: float) -> None:
        pass

    def title_hooks(self) -> list[str]:
        names = [n for n, _ in self.teams]
        if self.n == 2:
            return [f"{names[0]} vs {names[1]}: who takes the board?", "Which colour wins?",
                    "Pick your colour before it ends!"]
        return [f"{self.n} colours, 1 board. Who wins?", "Which colour wins?",
                "Pick your colour before it ends!"]

    def solid(self, r, c, b) -> bool:
        return self.owner[r, c] != b.team

    def on_hit(self, r, c, b, t: float) -> None:
        old = int(self.owner[r, c])
        self.owner[r, c] = b.team
        self.counts[old] -= 1
        self.counts[b.team] += 1
        cx, cy = self.centre(r, c)
        self.fx.burst(cx, cy, self.teams[old][1], n=3, power=0.6)
        self.sfx(t, "hit", b.team * 3 + self.rng.randint(0, 2))
        if self.power[r, c]:
            self.power[r, c] = 0
            mine = sum(1 for x in self.balls if x.team == b.team)
            if mine < self.MAX_PER_TEAM:
                self.spawn(cx, cy, 1, t, b.team)
                name, col = self.teams[b.team]
                self.fx.floater(cx, cy, f"+1 {name}", col)
                self.sfx(t, "power", force=True)
        self._paint(r, c)

    def check_end(self, t: float):
        if self.play_t >= self.max_play or self.counts.max() >= 0.97 * self.counts.sum():
            return "wars"
        return None

    def draw_hud(self, screen) -> None:
        pg = self.pg
        total = self.counts.sum()
        width = ARENA_R - ARENA_L
        font = self.fonts.stat if self.n <= 2 else self.fonts.mid
        for i, (name, col) in enumerate(self.teams):
            pct = round(100 * self.counts[i] / total)
            s = font.render(f"{name} {pct}%", True, col)
            screen.blit(s, s.get_rect(center=(ARENA_L + width * (i + 0.5) / self.n, 250)))
        x = ARENA_L
        for i, (_, col) in enumerate(self.teams):
            w = int(round(width * self.counts[i] / total))
            if i == self.n - 1:
                w = ARENA_R - x
            pg.draw.rect(screen, col, (x, 284, w, 22))
            x += w
        s = int(self.max_play - self.play_t + 0.999)
        ts = self.fonts.small.render(f"{s}s left", True, (200, 200, 210))
        screen.blit(ts, ts.get_rect(midtop=(W / 2, 312)))

    def winner(self) -> int:
        return int(self.counts.argmax())

    def end_card(self) -> EndCard:
        i = self.winner()
        pct = round(100 * self.counts[i] / self.counts.sum())
        return EndCard(f"{self.teams[i][0]} WINS!", f"took {pct}% of the board")

    def outcome(self):
        total = self.counts.sum()
        return {**super().outcome(), "teams": [n for n, _ in self.teams], "winner": self.teams[self.winner()][0],
                "shares": {n: round(100 * int(k) / total) for (n, _), k in zip(self.teams, self.counts)}}
