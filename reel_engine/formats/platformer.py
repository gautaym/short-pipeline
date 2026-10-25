"""platformer: a retro pixel-art runner on a freshly generated level. "1 life left. Can he make it?"

Every seed builds a new level (gaps over spike pits, steps, floating platforms, walking crabs,
coins, a flag at the end). The hero runs right and jumps with human-like timing: sometimes
early, sometimes late, sometimes pixel-perfect. Falling in a pit or touching a crab costs a life;
reaching the flag before the clock runs out wins.

The world is drawn on a 135x240 canvas and scaled up 8x for the chunky 90s look.
"""
import math

import numpy as np

from ..core.audio import SR, SoundBank
from ..core.canvas import H, W
from ..core.text import outlined
from . import EndCard, Format, Option, Twist, register

LW, LH, SCALE = 135, 240, 8
T = 10                            # tile size (low-res pixels)
GROUND_ROW = 18                   # default ground height (tile row of the top surface)
RUN = 62.0                        # running speed, low-res px/s
GRAVITY = 620.0
JUMP_V = 235.0
HERO_W, HERO_H = 7, 12
CRAB_W, CRAB_H, CRAB_SPEED = 8, 6, 18.0
RESPAWN_S = 0.9
CAMERA_LEAD = 44

SKY = [(38, 26, 84), (64, 34, 104), (102, 44, 116), (150, 60, 120), (200, 86, 112), (236, 124, 100),
       (250, 164, 96), (252, 200, 120)]
HERO = ["..hhhh..", ".hhhhhh.", ".hsssss.", ".hsesse.", "..ssss..", "..oooo..", ".oooooo.",
        "s.oooo.s", "..oooo..", "..w..w..", "..w..w..", ".bb..bb."]
HERO_RUN2 = HERO[:9] + ["...ww...", "..w..w..", ".bb...bb"]
HERO_JUMP = HERO[:7] + ["..oooo..", "s.oooo.s", ".w....w.", "w......w", "b......b"]
CRAB = ["..rrrr..", ".rwkrwk.", "rrrrrrrr", ".r.r.r.r"]
CRAB2 = ["..rrrr..", ".rwkrwk.", "rrrrrrrr", "r.r.r.r."]
PAL = {"h": (30, 20, 20), "s": (222, 162, 112), "e": (0, 0, 0), "o": (252, 132, 40), "w": (240, 240, 240),
       "b": (90, 50, 30), "r": (210, 50, 60), "k": (0, 0, 0)}


class Crab:
    __slots__ = ("x", "y", "lo", "hi", "dir", "alive")

    def __init__(self, x, y, lo, hi):
        self.x, self.y, self.lo, self.hi, self.dir, self.alive = x, y, lo, hi, -1, True


def sprite(pg, rows):
    s = pg.Surface((len(rows[0]), len(rows)), pg.SRCALPHA)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                s.set_at((i, j), PAL[ch])
    return s


@register
class Platformer(Format):
    name = "platformer"
    order = 100
    default_duration = 35.0
    options = (Option("--lives", "platformer: starting lives", {"type": int, "default": None}),)
    wins = ("flag",)
    cta = "Could you have done it?"
    music = "chiptune"

    # ---------------------------------------------------------- level generation
    series = "Pixel Run"
    tags = ("pixel art", "retro game", "platformer", "90s game", "8 bit", "level")
    hashtags = ("pixelart", "retrogaming", "8bit")

    @classmethod
    def titles(cls, o):
        lv, lives, t = o["level"], o["lives_left"], o["play_time"]
        if o["result"] == "flag":
            extra = "on the last life!" if lives == 1 else f"with {lives} lives left"
            return [f"Level {lv} cleared {extra}", f"Level {lv} in {t}s", f"He made it {extra}",
                    f"Level {lv}: {o['coins']} coins and the flag"]
        pct = round(100 * o["progress"])
        return [f"Level {lv}: game over at {pct}%", f"So close to the flag on level {lv}",
                f"Level {lv} wins this time", f"{pct}% of the way... then game over"]

    @classmethod
    def describe(cls, o):
        if o["result"] == "flag":
            return f"Level {o['level']} cleared in {o['play_time']} seconds with {o['coins']} coins."
        return f"Game over on level {o['level']}, {round(100 * o['progress'])}% of the way to the flag."

    def setup(self) -> None:
        rng = self.rng
        self.level_no = rng.randint(7, 99)
        self.sigma = rng.uniform(4.0, 8.0)             # how sloppy the jump timing is
        self.lives = getattr(self.opts, "lives", None) or rng.choice([2, 3])
        self.lives0 = self.lives
        self.generate(rng.randint(125, 150))
        self.hx, self.hy = 2 * T, (self.ground[2] * T) - HERO_H - 0.01
        self.vx, self.vy = 0.0, 0.0
        self.on_ground = True
        self.speed = RUN
        self.respawn_at: float | None = None
        self.checkpoint = self.hx
        self.triggers: dict = {}
        self.attempt = 0
        self.deaths = 0
        self.coins_got = 0
        self.near_misses = 0
        self.last_takeoff = self.hx
        self.flag_t = None
        self.dead_draw: tuple[float, float, float] | None = None   # (video time, x, y) of the last death

    def generate(self, length: int) -> None:
        rng = self.rng
        g: list[int | None] = [GROUND_ROW] * 10
        self.plats: set[tuple[int, int]] = set()
        self.crabs: list[Crab] = []
        coins: list[tuple[float, float]] = []
        row = GROUND_ROW
        while len(g) < length - 14:
            kind = rng.choices(["flat", "gap", "step", "float", "crab"], [2, 4, 2, 1.5, 2])[0]
            if kind == "flat":
                g += [row] * rng.randint(3, 6)
            elif kind == "gap":
                w = rng.randint(2, 4)
                x0 = len(g)
                g += [None] * w + [row] * rng.randint(3, 5)
                for i in range(1, 6):
                    k = i / 6
                    coins.append(((x0 + w * k) * T, row * T - 18 - 28 * 4 * k * (1 - k)))
            elif kind == "step":
                row = max(GROUND_ROW - 4, min(GROUND_ROW + 1, row + rng.choice([-2, -1, 1, 2])))
                g += [row] * rng.randint(4, 7)
            elif kind == "float":
                x0 = len(g)
                g += [None] * 7
                for c in range(x0 + 2, x0 + 5):
                    self.plats.add((c, row - 3))
                coins += [((c + 0.5) * T, (row - 4) * T - 2) for c in range(x0 + 2, x0 + 5)]
                g += [row] * rng.randint(3, 5)
            else:
                x0 = len(g)
                n = rng.randint(7, 10)
                g += [row] * n
                self.crabs.append(Crab((x0 + n - 3) * T, row * T - CRAB_H, (x0 + 1) * T, (x0 + n - 1) * T - CRAB_W))
        g += [row] * 14
        self.ground = g
        self.cols = len(g)
        self.flag_x = (self.cols - 6) * T
        self.coins = coins
        self.coin_alive = [True] * len(coins)
        self.level_w = self.cols * T

    def solid(self, col: int, row: int) -> bool:
        if col < 0 or col >= self.cols:
            return True
        top = self.ground[col]
        return (top is not None and row >= top) or (col, row) in self.plats

    def hits(self, x: float, y: float) -> bool:
        c0, c1 = int(x // T), int((x + HERO_W - 0.001) // T)
        r0, r1 = int(y // T), int((y + HERO_H - 0.001) // T)
        return any(self.solid(c, r) for c in range(c0, c1 + 1) for r in range(max(0, r0), r1 + 1))

    def title_hooks(self) -> list[str]:
        return [f"Level {self.level_no}. {self.lives} lives. Go.", "Can he reach the flag in time?",
                "This level was made 5 seconds ago", f"{self.lives} lives. {int(self.max_play)} seconds. 1 flag."]

    def twists(self) -> list[Twist]:
        return [Twist("turbo", "he's running 35% faster now", self._turbo, banner="TURBO!"),
                Twist("life", "+1 life!", self._life, lambda: self.lives == 1, banner="EXTRA LIFE!")]

    def _turbo(self, t: float) -> None:
        self.speed = RUN * 1.35
        return None

    def _life(self, t: float) -> None:
        self.lives += 1
        return None

    # ---------------------------------------------------------- simulation
    def hazard_ahead(self) -> tuple[str, int, float] | None:
        """Nearest thing to jump for: ('gap'|'wall'|'crab', id, distance from the hero's front)."""
        front = self.hx + HERO_W
        feet_row = int((self.hy + HERO_H + 0.5) // T)
        best = None
        for col in range(int(front // T), min(self.cols, int(front // T) + 8)):
            top = self.ground[col]
            if top is None:
                best = ("gap", col, col * T - front)
                break
            if top < feet_row:
                best = ("wall", col, col * T - front)
                break
        for i, crab in enumerate(self.crabs):
            d = crab.x - front
            if crab.alive and 0 <= d <= 45 and (best is None or d < best[2]):
                best = ("crab", i, d)
        return best

    def trigger(self, kind: str, ident: int) -> float:
        key = (kind, ident, self.attempt)
        if key not in self.triggers:
            ideal = {"gap": 4.0, "wall": 6.0, "crab": 16.0}[kind]
            spread = {"gap": self.sigma, "wall": 3.0, "crab": self.sigma * 1.2}[kind]
            self.triggers[key] = ideal + self.rng.gauss(0, spread)
        return self.triggers[key]

    def die(self, t: float) -> None:
        self.lives -= 1
        self.deaths += 1
        self.attempt += 1
        self.sfx(t, "die", force=True)
        self.fx.shake(10, 0.35)
        if self.fx.enabled:
            self.dead_draw = (t, self.hx, self.hy)
        if self.lives <= 0:
            self.mark("decisive")
            return
        self.respawn_at = self.play_t + RESPAWN_S
        self.hx = self.checkpoint
        col = int((self.hx + HERO_W / 2) // T)
        self.hy = self.ground[col] * T - HERO_H - 0.01 if self.ground[col] is not None else 0
        self.vx = self.vy = 0.0

    def step(self, dt: float, t: float) -> None:
        if self.respawn_at is not None:
            if self.play_t < self.respawn_at:
                return
            self.respawn_at = None
        for crab in self.crabs:
            if crab.alive:
                crab.x += crab.dir * CRAB_SPEED * dt
                if crab.x < crab.lo or crab.x > crab.hi:
                    crab.dir *= -1
                    crab.x = min(max(crab.x, crab.lo), crab.hi)
        if self.on_ground:
            hz = self.hazard_ahead()
            if hz and hz[2] <= self.trigger(hz[0], hz[1]):
                self.vy = -JUMP_V
                self.on_ground = False
                self.last_takeoff = self.hx
                self.sfx(t, "jump")
        self.vx = self.speed
        self.vy += GRAVITY * dt
        nx = self.hx + self.vx * dt
        if self.hits(nx, self.hy):
            nx = math.floor((nx + HERO_W) / T) * T - HERO_W - 0.01
        self.hx = nx
        ny = self.hy + self.vy * dt
        was_air = not self.on_ground
        if self.hits(self.hx, ny):
            if self.vy > 0:
                ny = math.floor((ny + HERO_H) / T) * T - HERO_H - 0.01
                self.on_ground = True
                if was_air:
                    self.landed(t)
            else:
                ny = (math.floor(ny / T) + 1) * T + 0.01
            self.vy = 0.0
        else:
            self.on_ground = False
        self.hy = ny
        if self.on_ground:
            self.checkpoint = max(self.checkpoint, self.hx - 14) if self.hazard_ahead() is None else self.checkpoint
        if self.hy > LH:
            self.die(t)
            return
        for crab in self.crabs:
            if crab.alive and self.hx < crab.x + CRAB_W and crab.x < self.hx + HERO_W \
                    and self.hy < crab.y + CRAB_H and crab.y < self.hy + HERO_H:
                if self.vy > 0 and self.hy + HERO_H < crab.y + 4:
                    crab.alive = False
                    self.vy = -JUMP_V * 0.6
                    self.sfx(t, "stomp")
                else:
                    self.die(t)
                    return
        for i, (cx, cy) in enumerate(self.coins):
            if self.coin_alive[i] and abs(cx - (self.hx + HERO_W / 2)) < 6 and abs(cy - (self.hy + HERO_H / 2)) < 8:
                self.coin_alive[i] = False
                self.coins_got += 1
                self.sfx(t, "coin")
        if self.hx + HERO_W >= self.flag_x and self.flag_t is None:
            self.flag_t = self.play_t
            self.mark("decisive")

    def landed(self, t: float) -> None:
        back = int(self.hx // T)
        overlap = self.hx + HERO_W - (back + 1) * T          # pixels of foot actually on the ledge
        if 0 <= back < self.cols and not self.solid(back, int((self.hy + HERO_H + 1) // T)) and overlap <= 3:
            self.near_misses += 1
            self.fx.floater(W / 2, 760, "PIXEL PERFECT!", (255, 230, 120), self.fonts.cta, 1.2)
            self.sfx(t, "close")

    def check_end(self, t: float):
        if self.flag_t is not None:
            return "flag"
        if self.lives <= 0:
            return "out"
        if self.play_t >= self.max_play:
            return "time"
        return None

    def stats(self) -> list[str]:
        return [f"COINS {self.coins_got}", f"LIVES {self.lives}", f"TIME {max(0, int(self.max_play - self.play_t))}"]

    def progress(self) -> float:
        return min(1.0, self.hx / self.flag_x)

    def hud_accent(self):
        return (255, 90, 90) if self.lives == 1 else (255, 214, 64)

    def drama_score(self, trace) -> float:
        """A late win on the last life is best; a loss right before the flag is next."""
        o = trace.outcome
        s = 0.0
        if trace.done == "flag":
            s += 3 + (2.0 if o["lives_left"] == 1 else 0.0) + 2 * min(1.0, trace.play_t / (0.8 * self.max_play))
        else:
            s += 4 * o["progress"] ** 2
        s += 0.7 * min(o["deaths"], 2) + 0.5 * min(o["near_misses"], 3)
        return s + (0.5 if trace.twist else 0.0)

    def end_card(self) -> EndCard:
        if self.done == "flag":
            return EndCard("LEVEL CLEAR!", f"{self.lives} {'life' if self.lives == 1 else 'lives'} left, "
                                           f"{self.coins_got} coins, {self.play_t:.1f}s")
        if self.done == "out":
            return EndCard("GAME OVER", f"{round(100 * self.progress())}% of the way to the flag")
        return EndCard("TIME UP!", f"{round(100 * self.progress())}% of the way to the flag")

    def outcome(self):
        return {**super().outcome(), "level": self.level_no, "lives_left": self.lives, "deaths": self.deaths,
                "coins": self.coins_got, "near_misses": self.near_misses, "progress": round(self.progress(), 3)}

    def sounds(self) -> SoundBank:
        def square(freq, dur, decay, sweep=0.0, vol=0.2):
            n = int(SR * dur)
            t = np.arange(n) / SR
            f = freq * (1 + sweep * t / dur)
            w = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
            return (w * np.exp(-t * decay) * vol).astype(np.float32)

        def seq(notes, each, vol=0.18):
            return np.concatenate([square(f, each, 4, vol=vol) for f in notes])

        return {"jump": square(330, 0.16, 12, sweep=1.2, vol=0.12),
                "coin": np.concatenate([square(988, 0.06, 8, vol=0.1), square(1319, 0.18, 10, vol=0.1)]),
                "stomp": square(110, 0.12, 20, sweep=-0.5, vol=0.25),
                "close": square(1568, 0.12, 14, vol=0.1),
                "die": seq([494, 466, 440, 415, 392, 370], 0.09, 0.16),
                "clear": seq([523, 659, 784, 1047, 784, 1047], 0.11),
                "fail": seq([392, 330, 262, 196], 0.18)}

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        pg = self.pg
        rng = __import__("random").Random(f"art:{self.seed}")
        sky = pg.Surface((LW, LH))
        bh = 30
        for i, col in enumerate(SKY):
            sky.fill(col, (0, i * bh, LW, bh))
            if i + 1 < len(SKY):
                for x in range(0, LW, 2):
                    sky.set_at((x, i * bh + bh - 1), SKY[i + 1])
                    sky.set_at((x + 1, i * bh + bh - 2), SKY[i + 1])
        sky.fill(SKY[-1], (0, len(SKY) * bh, LW, LH))
        pg.draw.circle(sky, (255, 232, 160), (96, 118), 22)
        for j, y in enumerate(range(121, 141, 5)):
            sky.fill(SKY[4], (70, y, 54, 1 + j // 2))
        self.sky = sky
        far_w = int(self.level_w * 0.3) + LW
        far = pg.Surface((far_w, LH), pg.SRCALPHA)
        for x0 in range(-6, far_w, 34):
            hgt = rng.randint(20, 44)
            col = (92, 46, 104)
            pg.draw.rect(far, col, (x0, 160 - hgt, 24, hgt + 100))
            pg.draw.circle(far, col, (x0 + 12, 160 - hgt), 9)
            pg.draw.rect(far, col, (x0 + 27, 160 - hgt - 20, 3, hgt + 120))
            pg.draw.circle(far, col, (x0 + 28, 160 - hgt - 21), 2)
        self.far = far
        mid_w = int(self.level_w * 0.6) + LW
        mid = pg.Surface((mid_w, LH), pg.SRCALPHA)
        x0 = 0
        while x0 < mid_w:
            bw, bh2 = rng.randint(16, 30), rng.randint(26, 60)
            pg.draw.rect(mid, (58, 28, 66), (x0, 190 - bh2, bw, bh2 + 80))
            for wy in range(190 - bh2 + 5, 186, 7):
                for wx in range(x0 + 3, x0 + bw - 3, 5):
                    if rng.random() < 0.35:
                        mid.fill((255, 206, 110), (wx, wy, 2, 2))
            x0 += bw + rng.randint(0, 3)
        self.mid = mid
        terrain = pg.Surface((self.level_w, LH), pg.SRCALPHA)
        for col, top in enumerate(self.ground):
            if top is None:
                for x in range(col * T, col * T + T, 5):
                    pg.draw.polygon(terrain, (200, 200, 212), [(x, LH - 2), (x + 2.5, LH - 12), (x + 5, LH - 2)])
                continue
            self._bricks(terrain, col * T, top * T, T, LH - top * T)
        for c, r in self.plats:
            self._bricks(terrain, c * T, r * T, T, T)
        fx = self.flag_x
        terrain.fill((60, 40, 30), (fx, (self.ground[self.cols - 6] or GROUND_ROW) * T - 60, 2, 60))
        pg.draw.polygon(terrain, (255, 214, 64), [(fx + 2, (self.ground[self.cols - 6] or GROUND_ROW) * T - 60),
                                                  (fx + 16, (self.ground[self.cols - 6] or GROUND_ROW) * T - 54),
                                                  (fx + 2, (self.ground[self.cols - 6] or GROUND_ROW) * T - 48)])
        self.terrain = terrain
        self.hero_frames = [sprite(pg, HERO), sprite(pg, HERO_RUN2), sprite(pg, HERO_JUMP)]
        self.crab_frames = [sprite(pg, CRAB), sprite(pg, CRAB2)]
        self.low = pg.Surface((LW, LH))
        self.lines = pg.Surface((W, H), pg.SRCALPHA)
        for y in range(0, H, SCALE):
            self.lines.fill((0, 0, 0, 50), (0, y, W, 1))
        self.level_tag = outlined(pg, self.fonts.mid, f"LEVEL {self.level_no}", (255, 255, 255), 3)

    def _bricks(self, surf, x0, y0, w, h) -> None:
        for ty in range(y0, y0 + h, 5):
            off = 5 if (ty // 5) % 2 else 0
            surf.fill((196, 120, 72), (x0, ty, w, 5))
            surf.fill((140, 80, 50), (x0, ty + 4, w, 1))
            surf.fill((140, 80, 50), (x0 + off, ty, 1, 5))
        surf.fill((244, 176, 104), (x0, y0, w, 2))

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        cam = int(min(max(0.0, self.hx - CAMERA_LEAD), self.level_w - LW))
        low = self.low
        low.blit(self.sky, (0, 0))
        low.blit(self.far, (-int(cam * 0.3), 0))
        low.blit(self.mid, (-int(cam * 0.6), 0))
        low.blit(self.terrain, (-cam, 0))
        spin = abs(math.sin(t * 6))
        for i, (cx, cy) in enumerate(self.coins):
            if self.coin_alive[i] and cam - 5 < cx < cam + LW + 5:
                w = max(1, int(5 * spin))
                pg.draw.ellipse(low, (250, 210, 60), (cx - cam - w / 2, cy - 3, w, 7))
        frame = int(t * 8) % 2
        for crab in self.crabs:
            if crab.alive and cam - 10 < crab.x < cam + LW:
                low.blit(self.crab_frames[frame], (int(crab.x - cam), int(crab.y + 2)))
        if self.respawn_at is None or int(t * 10) % 2:
            hero = self.hero_frames[2 if not self.on_ground else frame]
            if self.lives > 0 or self.done != "out":
                low.blit(hero, (int(self.hx - cam), int(self.hy)))
        pg.transform.scale(low, (W, H), screen)
        screen.blit(self.lines, (0, 0))
        if self.dead_draw and t - self.dead_draw[0] < 0.6:
            _, dx, dy = self.dead_draw
            self.fx.burst((dx - cam) * SCALE + 20, min(H - 80, dy * SCALE), (252, 132, 40), 12, 1.2)
            self.dead_draw = None
        screen.blit(self.level_tag, self.level_tag.get_rect(center=(W / 2, 400)))
        self.fx.draw_particles(screen)
