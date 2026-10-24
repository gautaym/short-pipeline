"""BrickGame: the shared grid, paddle and ball engine behind the brick-breaker formats.

Bricks live in a grid: hp > 0 is breakable (more hp takes more hits), hp < 0 is an
unbreakable wall, 0 is empty. `power` marks bricks that release extra balls. Static bricks
are painted once onto `field`, and only repainted when a brick changes.
"""
import colorsys
import math

import numpy as np

from ...core.canvas import ARENA_L, ARENA_R, ARENA_T, LOST_Y, H, W
from ...core.palette import hsv255, vertical_gradient
from ...core.physics import BALL_R, Ball, bounce_rect
from ..base import Format
from .sounds import PENTA, brick_sounds

TRAIL_N = 7          # positions kept per ball for its trail

PADDLE_Y = 1700
PADDLE_W = 230
PADDLE_H = 24
PADDLE_SPEED = 1700.0

MAX_BALLS = 220

WALL = (172, 174, 184)
WALL_HI = (215, 217, 226)


class BrickGame(Format):
    has_paddle = True
    ball_speed = 1250.0
    fancy_bricks = True
    wins = ("clear", "escape", "win", "wars")

    def init_state(self) -> None:
        self.balls: list[Ball] = []
        self.note = 0
        self.launched = False
        self.paddle_x, self.aim_off = W / 2, 0.0
        self.hue = self.rng.random()

    def build(self) -> None:
        self._build_bg()
        self._build_sprites()
        self._build_field()

    def sounds(self):
        return brick_sounds()

    # ---------------------------------------------------------- hooks for brick formats
    def launch(self, t: float) -> None: ...
    def idle_ball(self): return None
    def cell_colour(self, r, c, hp): return (255, 255, 255)
    def on_destroy(self, r, c, t): ...
    def extra_collide(self, b, t): ...
    def draw_extra(self, screen, t): ...

    def solid(self, r, c, b) -> bool:
        return self.hp[r, c] != 0

    def hud_accent(self):
        return hsv255(self.hue, 0.6, 1.0)

    # ---------------------------------------------------------- grid helpers
    def grid(self, cell: int, gap: int, rows: int, top: int) -> None:
        self.cell, self.gap = cell, gap
        self.cols = (ARENA_R - ARENA_L) // cell
        self.rows = rows
        self.bx0 = ARENA_L + ((ARENA_R - ARENA_L) - self.cols * cell) // 2
        self.by0 = top
        self.hp = np.zeros((rows, self.cols), dtype=np.int32)
        self.power = np.zeros((rows, self.cols), dtype=np.int8)

    def centre(self, r, c):
        return self.bx0 + c * self.cell + self.cell / 2, self.by0 + r * self.cell + self.cell / 2

    def place_powers(self, mask, frac: float, big_chance: float = 0.08) -> None:
        cells = np.argwhere(mask)
        if len(cells) == 0:
            return
        n = max(4, int(len(cells) * frac))
        for r, c in cells[self.nrng.choice(len(cells), min(n, len(cells)), replace=False)]:
            self.power[r, c] = 10 if self.nrng.random() < big_chance else 3
            self.hp[r, c] = 1

    def make_palette(self) -> None:
        self.colours = {}
        for r in range(self.rows):
            for c in range(self.cols):
                h = (self.hue + 0.22 * r / self.rows + 0.06 * c / self.cols) % 1
                for hp, val in ((1, 1.0), (2, 0.78), (3, 0.58)):
                    self.colours[(r, c, hp)] = hsv255(h, 0.72, val)

    # ---------------------------------------------------------- graphics setup
    def _build_bg(self) -> None:
        top = colorsys.hsv_to_rgb((self.hue + 0.55) % 1, 0.55, 0.16)
        bot = colorsys.hsv_to_rgb((self.hue + 0.65) % 1, 0.65, 0.05)
        self.bg = vertical_gradient(self.pg, (W, H), top, bot)
        self._arena_outline()

    def _flat_bg(self, colour) -> None:
        self.bg = self.pg.Surface((W, H))
        self.bg.fill(colour)
        self._arena_outline()

    def _arena_outline(self) -> None:
        self.pg.draw.rect(self.bg, (120, 120, 135), (ARENA_L - 4, ARENA_T - 4, ARENA_R - ARENA_L + 8,
                                                     LOST_Y - ARENA_T + 4), 2, border_radius=10)

    def _glow_ball(self, core=(255, 255, 255), glow=(255, 255, 230)):
        pg = self.pg
        s = pg.Surface((BALL_R * 6, BALL_R * 6), pg.SRCALPHA)
        cx = BALL_R * 3
        for i, a in enumerate((18, 30, 50)):
            pg.draw.circle(s, glow + (a,), (cx, cx), BALL_R * (3 - i * 0.6))
        pg.draw.circle(s, core, (cx, cx), BALL_R)
        return s

    def _trail_set(self, colour) -> list:
        """Trail dots from oldest (small, faint) to newest (larger, stronger)."""
        pg, sprites = self.pg, []
        for i in range(TRAIL_N - 1):
            k = (i + 1) / (TRAIL_N - 1)
            r = max(2, int(BALL_R * (0.3 + 0.6 * k)))
            s = pg.Surface((2 * r + 2, 2 * r + 2), pg.SRCALPHA)
            pg.draw.circle(s, tuple(colour) + (int(30 + 110 * k),), (r + 1, r + 1), r)
            sprites.append(s)
        return sprites

    def _build_sprites(self) -> None:
        pg = self.pg
        self.ball_sprites = {0: self._glow_ball()}
        self.trail_sprites = {0: self._trail_set((255, 255, 230))}
        bw = self.cell - self.gap
        self.power_sprites = {}
        for val in (3, 10):
            s = pg.Surface((bw, bw), pg.SRCALPHA)
            colour = (255, 255, 255) if val == 3 else (255, 214, 64)
            pg.draw.rect(s, colour, (0, 0, bw, bw), border_radius=6)
            lab = self.fonts.small.render(f"+{val}", True, (30, 30, 40))
            s.blit(lab, lab.get_rect(center=(bw / 2, bw / 2)))
            self.power_sprites[val] = s

    def _build_field(self) -> None:
        self.field = self.bg.copy()
        for r in range(self.rows):
            for c in range(self.cols):
                self._paint(r, c)

    def _paint(self, r, c) -> None:
        pg, cell, g = self.pg, self.cell, self.gap
        x, y = self.bx0 + c * cell, self.by0 + r * cell
        self.field.blit(self.bg, (x, y), (x, y, cell, cell))
        hp = int(self.hp[r, c])
        if hp == 0 or self.power[r, c]:
            return
        rect = (x + g // 2, y + g // 2, cell - g, cell - g)
        if hp < 0:
            pg.draw.rect(self.field, WALL, rect, border_radius=2)
            pg.draw.rect(self.field, WALL_HI, (rect[0], rect[1], rect[2], max(2, rect[3] // 5)))
            return
        col = self.cell_colour(r, c, hp)
        pg.draw.rect(self.field, col, rect, border_radius=5 if self.fancy_bricks else 2)
        if self.fancy_bricks:
            hi = tuple(min(255, int(v * 1.25) + 20) for v in col)
            pg.draw.rect(self.field, hi, (rect[0] + 3, rect[1] + 3, rect[2] - 6, 5), border_radius=3)
            if hp >= 2:
                pg.draw.circle(self.field, (255, 255, 255), (int(x + cell / 2), int(y + cell / 2 + 3)),
                               4 if hp == 2 else 6, 2)

    # ---------------------------------------------------------- balls
    def spawn(self, x, y, count: int, t: float, team: int = 0) -> int:
        spawned = 0
        for _ in range(count):
            if len(self.balls) >= MAX_BALLS:
                break
            self.balls.append(Ball(x, y, self.rng.uniform(-math.pi, math.pi), self.ball_speed, team))
            spawned += 1
        return spawned

    # ---------------------------------------------------------- physics
    def _hit_cells(self, b: Ball, t: float) -> None:
        cell, half = self.cell, self.gap / 2
        c0 = int((b.x - BALL_R - self.bx0) // cell)
        c1 = int((b.x + BALL_R - self.bx0) // cell)
        r0 = int((b.y - BALL_R - self.by0) // cell)
        r1 = int((b.y + BALL_R - self.by0) // cell)
        for r in range(max(r0, 0), min(r1, self.rows - 1) + 1):
            for c in range(max(c0, 0), min(c1, self.cols - 1) + 1):
                if not self.solid(r, c, b):
                    continue
                x0 = self.bx0 + c * cell + half
                y0 = self.by0 + r * cell + half
                if bounce_rect(b, x0, y0, x0 + cell - 2 * half, y0 + cell - 2 * half):
                    self.on_hit(r, c, b, t)
                    return

    def on_hit(self, r, c, b: Ball, t: float) -> None:
        hp = int(self.hp[r, c])
        if hp < 0:
            self.sfx(t, "wall")
            return
        colour = self.cell_colour(r, c, hp)
        self.hp[r, c] -= 1
        self.note = min(self.note + 1, len(PENTA) - 1)
        if self.hp[r, c] > 0:
            self.sfx(t, "hit", self.note)
            self._paint(r, c)
            return
        self.left -= 1
        self._paint(r, c)
        cx, cy = self.centre(r, c)
        self.fx.burst(cx, cy, colour, n=7 if self.fancy_bricks else 4)
        val = int(self.power[r, c])
        if val:
            self.power[r, c] = 0
            self.sfx(t, "power", force=True)
            n = self.spawn(cx, cy, val, t)
            if n:
                self.fx.floater(cx, cy, f"+{n} BALLS")
                if val >= 10:
                    self.fx.shake(6, 0.2)
        else:
            self.sfx(t, "break", self.note)
        self.on_destroy(r, c, t)

    def _predict_x(self, b: Ball):
        if b.vy <= 0:
            return None, None
        t = (PADDLE_Y - BALL_R - b.y) / b.vy
        if t < 0:
            return None, None
        lo, hi = ARENA_L + BALL_R, ARENA_R - BALL_R
        w = hi - lo
        m = (b.x + b.vx * t - lo) % (2 * w)
        if m > w:
            m = 2 * w - m
        return lo + m, t

    def _move_paddle(self, dt: float) -> None:
        best, best_t = None, 1e9
        for b in self.balls:
            x, t = self._predict_x(b)
            if x is not None and t < best_t:
                best, best_t = x, t
        target = (best if best is not None else W / 2) - self.aim_off
        step = PADDLE_SPEED * dt
        self.paddle_x += max(-step, min(step, target - self.paddle_x))
        self.paddle_x = max(ARENA_L + PADDLE_W / 2, min(ARENA_R - PADDLE_W / 2, self.paddle_x))

    def _substep(self, dt: float, t: float) -> None:
        if self.has_paddle:
            self._move_paddle(dt)
        lo, hi = ARENA_L + BALL_R, ARENA_R - BALL_R
        floor = LOST_Y - BALL_R
        keep = []
        for b in self.balls:
            b.x += b.vx * dt
            b.y += b.vy * dt
            if b.x < lo:
                b.x, b.vx = lo, abs(b.vx)
            elif b.x > hi:
                b.x, b.vx = hi, -abs(b.vx)
            if b.y < ARENA_T + BALL_R:
                b.y, b.vy = ARENA_T + BALL_R, abs(b.vy)
            if not self.has_paddle and b.y > floor:
                b.y, b.vy = floor, -abs(b.vy)
            if (self.has_paddle and b.vy > 0 and PADDLE_Y - BALL_R <= b.y <= PADDLE_Y + PADDLE_H
                    and abs(b.x - self.paddle_x) <= PADDLE_W / 2 + BALL_R):
                off = max(-1.0, min(1.0, (b.x - self.paddle_x) / (PADDLE_W / 2)))
                ang = off * math.radians(62)
                b.vx, b.vy = b.speed * math.sin(ang), -b.speed * math.cos(ang)
                b.y = PADDLE_Y - BALL_R
                self.aim_off = self.rng.uniform(-0.75, 0.75) * PADDLE_W / 2
                self.note = 0
                self.sfx(t, "paddle")
            self._hit_cells(b, t)
            self.extra_collide(b, t)
            if self.has_paddle and b.y > LOST_Y:
                self.sfx(t, "lost")
                continue
            keep.append(b)
        self.balls = keep

    def step(self, dt: float, t: float) -> None:
        if not self.launched:
            self.launched = True
            self.launch(t)
        self._substep(dt, t)

    def regrow(self, frac: float) -> int:
        """Bring back a share of the broken bricks (away from the balls). Returns how many."""
        cand = np.argwhere((self.hp0 > 0) & (self.hp == 0) & (self.power == 0))
        if len(cand) == 0:
            return 0
        near = np.zeros(len(cand), dtype=bool)
        for b in self.balls:
            bx, by = (b.x - self.bx0) / self.cell, (b.y - self.by0) / self.cell
            near |= np.hypot(cand[:, 1] + 0.5 - bx, cand[:, 0] + 0.5 - by) < 2.5
        cand = cand[~near]
        n = int(len(cand) * frac)
        if n == 0:
            return 0
        for r, c in cand[self.nrng.choice(len(cand), n, replace=False)]:
            self.hp[r, c] = 1
            self._paint(r, c)
            cx, cy = self.centre(r, c)
            self.fx.burst(cx, cy, self.cell_colour(r, c, 1), n=2, power=0.4)
        self.left += n
        return n

    def multiball(self, count: int) -> int:
        """Launch extra balls upwards from the paddle. Returns how many were added."""
        n = max(0, min(count, MAX_BALLS - len(self.balls)))
        for _ in range(n):
            self.balls.append(Ball(self.paddle_x, PADDLE_Y - BALL_R - 1, self.rng.uniform(-0.6, 0.6),
                                   self.ball_speed))
        return n

    # ---------------------------------------------------------- drawing
    def draw_power(self, screen, t: float) -> None:
        pulse = 0.5 + 0.5 * math.sin(t * 8)
        g = self.gap // 2
        for r, c in np.argwhere(self.power > 0):
            spr = self.power_sprites[int(self.power[r, c])]
            spr.set_alpha(int(170 + 85 * pulse))
            screen.blit(spr, (self.bx0 + c * self.cell + g, self.by0 + r * self.cell + g))

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        screen.blit(self.field, (0, 0))
        self.draw_power(screen, t)
        self.draw_extra(screen, t)
        self.fx.draw_particles(screen)
        if self.has_paddle:
            pr = pg.Rect(0, 0, PADDLE_W, PADDLE_H)
            pr.midtop = (self.paddle_x, PADDLE_Y)
            pg.draw.rect(screen, (245, 245, 255), pr, border_radius=12)
        if not self.launched and self.idle_ball():
            x, y = self.idle_ball()
            spr = self.ball_sprites[0]
            screen.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2))
        for b in self.balls:
            b.trail.append((b.x, b.y))
            del b.trail[:-TRAIL_N]
            dots = self.trail_sprites.get(b.team, self.trail_sprites[0])
            offset = TRAIL_N - len(b.trail)
            for i, (x, y) in enumerate(b.trail[:-1]):
                spr = dots[i + offset]
                screen.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2))
        for b in self.balls:
            spr = self.ball_sprites.get(b.team, self.ball_sprites[0])
            screen.blit(spr, (b.x - spr.get_width() / 2, b.y - spr.get_height() / 2))

    @staticmethod
    def clock(play_t: float) -> str:
        s = int(play_t)
        return f"{s // 60}:{s % 60:02d}"
