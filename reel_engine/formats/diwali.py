"""diwali: one spark, a field of crackers, a chain reaction. "How far will the chain go?"

Each cracker type spreads the fire differently: an anar lights its four neighbours, a chakri
all eight, a sutli bomb everything within a big radius, a rocket flies along its row. Duds
fizzle and stop the fire, so whether the chain reaches every cracker is genuinely uncertain.
"""
import math

import numpy as np

from ..core.audio import SR, SoundBank, overlay, tone
from ..core.canvas import FPS, H, W
from ..core.palette import hsv255
from ..core.text import outlined
from . import EndCard, Format, Option, Twist, register

EMPTY, ANAR, CHAKRI, BOMB, ROCKET, DUD = range(6)
IDLE, LIT, GONE = range(3)

CELL = 60
COLS, ROWS = 16, 17
X0, Y0 = (W - COLS * CELL) // 2, 480
FUSE = (0.55, 1.1)                 # seconds between catching fire and exploding
DUDS = (0.16, 0.3)                 # seeded share of duds
EMPTY_SHARE = 0.08
MIX = {ANAR: 0.72, CHAKRI: 0.14, BOMB: 0.05, ROCKET: 0.09}   # how the rest splits
ROCKET_RANGE = 7
ROCKET_CELL_S = 0.07               # rocket flight time per cell
MAX_SPARKS = 1600

KINDS = [ANAR, CHAKRI, BOMB, ROCKET, DUD]
SPARK_COLOURS = [(255, 210, 80), (255, 90, 170), (90, 220, 255), (255, 255, 255), (140, 255, 120),
                 (255, 140, 40)]


@register
class Diwali(Format):
    name = "diwali"
    order = 90
    default_duration = 40.0
    options = (Option("--duds", "diwali: share of dud crackers, e.g. 0.15", {"type": float, "default": None}),)
    wins = ("full",)
    cta = "Happy Diwali! Follow for more"
    music = "festive"

    series = "Diwali Chain"
    tags = ("diwali", "chain reaction", "crackers", "satisfying", "simulation", "happy diwali")
    hashtags = ("diwali", "chainreaction", "satisfying")

    @classmethod
    def titles(cls, o):
        n, left = o["crackers"], o["crackers"] - o["exploded"]
        if o["result"] == "full":
            return [f"1 spark lit all {n} crackers", f"Full chain: {n} crackers from 1 spark",
                    f"Can 1 spark light {n} crackers? Yes!", "Every single cracker went off"]
        return [f"{left} cracker{'s' if left != 1 else ''} survived the chain", f"1 spark, {n} crackers, {left} left",
                f"So close: {o['lit_pct']}% lit", f"The chain broke with {left} to go"]

    @classmethod
    def describe(cls, o):
        if o["result"] == "full":
            return f"One spark set off all {o['crackers']} crackers. Happy Diwali!"
        return f"The chain lit {o['exploded']} of {o['crackers']} crackers. Happy Diwali!"

    def setup(self) -> None:
        rng, nrng = self.rng, self.nrng
        duds = getattr(self.opts, "duds", None)
        self.dud_share = duds if duds is not None else rng.uniform(*DUDS)
        p_rest = 1 - self.dud_share - EMPTY_SHARE
        probs = [EMPTY_SHARE] + [MIX[k] * p_rest for k in (ANAR, CHAKRI, BOMB, ROCKET)] + [self.dud_share]
        self.kind = nrng.choice(6, size=(ROWS, COLS), p=probs)
        self.state = np.where(self.kind == EMPTY, GONE, IDLE)
        self.fuse = nrng.uniform(*FUSE, size=(ROWS, COLS))
        self.timer = np.zeros((ROWS, COLS))
        self.rocket_dir = nrng.choice([-1, 1], size=(ROWS, COLS))
        self.hue = nrng.random((ROWS, COLS))
        self.explodable = int(np.isin(self.kind, [ANAR, CHAKRI, BOMB, ROCKET]).sum())
        self.exploded = 0
        self.pending: list[tuple[float, int, int]] = []      # (play time, r, c) ignitions on their way
        start = np.argwhere(np.isin(self.kind, [ANAR, CHAKRI]))
        sr, sc = start[nrng.integers(len(start))]
        self.start_cell = (int(sr), int(sc))
        self.pending.append((0.0, int(sr), int(sc)))
        self.flights: list[list] = []                        # rockets in the air (visual)
        self.sparks: list[list] = []
        self.blasts: list[list] = []                         # expanding shock rings (visual)
        self.scorch: list[tuple[int, int]] = []
        self.last_draw_t = 0.0
        self.combo_shown = 0

    def title_hooks(self) -> list[str]:
        n = self.explodable
        return [f"1 spark. {n} crackers.", "How far will the chain go?", f"Can 1 spark light all {n}?",
                "Will every cracker go off?"]

    def twists(self) -> list[Twist]:
        return [Twist("spark", "another spark landed!", self._spark, self._dying, banner="ANOTHER SPARK!"),
                Twist("mega", "a mega bomb appeared", self._mega, banner="MEGA BOMB!")]

    def _dying(self) -> bool:
        lit = int((self.state == LIT).sum()) + len(self.pending)
        return lit <= 2 and self.exploded / self.explodable < 0.85

    def _spark(self, t: float) -> None:
        idle = np.argwhere((self.state == IDLE) & np.isin(self.kind, [ANAR, CHAKRI, BOMB]))
        if len(idle):
            r, c = idle[self.nrng.integers(len(idle))]
            self.pending.append((self.play_t, int(r), int(c)))
        return None

    def _mega(self, t: float) -> None:
        idle = np.argwhere(self.state == IDLE)
        if len(idle):
            r, c = idle[self.nrng.integers(len(idle))]
            if self.kind[r, c] == DUD:
                self.explodable += 1
            self.kind[r, c] = BOMB
            self.mega = (int(r), int(c))
        return None

    # ---------------------------------------------------------- simulation
    def ignite(self, r: int, c: int, delay: float = 0.0) -> None:
        if 0 <= r < ROWS and 0 <= c < COLS and self.state[r, c] == IDLE:
            self.pending.append((self.play_t + delay, r, c))

    def targets(self, r: int, c: int) -> list[tuple[int, int, float]]:
        k = self.kind[r, c]
        if k == ANAR:
            return [(r + dr, c + dc, 0.0) for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))]
        if k == CHAKRI:
            return [(r + dr, c + dc, 0.0) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]
        if k == BOMB:
            rad = 3.5 if getattr(self, "mega", None) == (r, c) else 2.3
            span = int(rad)
            return [(r + dr, c + dc, 0.04 * math.hypot(dr, dc)) for dr in range(-span, span + 1)
                    for dc in range(-span, span + 1) if (dr or dc) and math.hypot(dr, dc) <= rad]
        if k == ROCKET:
            d = int(self.rocket_dir[r, c])
            return [(r, c + d * i, ROCKET_CELL_S * i) for i in range(1, ROCKET_RANGE + 1)]
        return []

    def step(self, dt: float, t: float) -> None:
        if self.pending:
            due = [p for p in self.pending if p[0] <= self.play_t]
            self.pending = [p for p in self.pending if p[0] > self.play_t]
            for _, r, c in due:
                if self.state[r, c] == IDLE:
                    self.state[r, c] = LIT
                    self.timer[r, c] = self.fuse[r, c]
        lit = np.argwhere(self.state == LIT)
        for r, c in lit:
            self.timer[r, c] -= dt
            if self.timer[r, c] > 0:
                continue
            self.state[r, c] = GONE
            k = int(self.kind[r, c])
            if k == DUD:
                self.sfx(t, "fizz")
                continue
            self.exploded += 1
            for tr, tc, delay in self.targets(r, c):
                self.ignite(tr, tc, delay)
            self.sfx(t, {BOMB: "boom", ROCKET: "whoosh"}.get(k, "pop"), self.exploded % 6)
            if k == BOMB:
                self.fx.shake(10, 0.3)
            if self.exploded % 10 == 0:
                self.sfx(t, "combo", self.exploded // 10, force=True)
            if self.fx.enabled:
                self.boom_visual(int(r), int(c), k)

    def chain_alive(self) -> bool:
        return bool(self.pending) or bool((self.state == LIT).any())

    def check_end(self, t: float):
        if not self.chain_alive():
            self.mark("decisive")
            return "full" if self.exploded >= self.explodable else "broken"
        if self.play_t >= self.max_play:
            return "full" if self.exploded >= self.explodable else "broken"
        return None

    def progress(self) -> float:
        return self.exploded / max(1, self.explodable)

    def stats(self) -> list[str]:
        return [f"CHAIN x{self.exploded}", f"{math.floor(100 * self.progress())}% LIT", f"0:{int(self.play_t):02d}"]

    def hud_accent(self):
        return (255, 190, 60)

    def drama_score(self, trace) -> float:
        """Best: a long chain that lights every cracker, or one that leaves only a handful."""
        left = trace.outcome["crackers"] - trace.outcome["exploded"]
        s = 4 * (1 - min(1.0, left / 30)) + 2 * min(1.0, trace.play_t / 18)
        if trace.done == "full":
            s += 2.0
        elif left <= 5:
            s += 2.0                                         # so close
        return s + (0.5 if trace.twist else 0.0)

    def end_card(self) -> EndCard:
        pct = math.floor(100 * self.progress())
        left = self.explodable - self.exploded
        if self.done == "full":
            return EndCard("FULL CHAIN!", f"all {self.exploded} crackers from 1 spark")
        if left <= 5:
            return EndCard(f"{left} CRACKER{'S' if left > 1 else ''} SURVIVED!", f"so close: {pct}% lit")
        return EndCard("CHAIN BROKEN!", f"stopped at {pct}% ({self.exploded} crackers)")

    def outcome(self):
        return {**super().outcome(), "lit_pct": math.floor(100 * self.progress()), "crackers": self.explodable,
                "exploded": self.exploded}

    def sounds(self) -> SoundBank:
        pops = [tone(180 + 60 * i, 0.18, 22, harm=0.3, noise=0.9) * 0.35 for i in range(6)]
        combo = [tone(523.25 * 2 ** (k / 12), 0.35, 8, harm=0.3) * 0.25 for k in (0, 2, 4, 7, 9, 12, 14, 16, 19, 21)]
        clear = np.zeros(int(SR * 1.7), dtype=np.float32)
        for s, d in ((0, 0), (4, 0.08), (7, 0.16), (12, 0.24)):
            note = tone(523.25 * 2 ** (s / 12), 1.4, 3)
            clear[int(SR * d):int(SR * d) + len(note)] += note
        return {"pop": pops, "combo": combo,
                "boom": overlay((0, tone(60, 0.7, 5, harm=0.9, noise=0.6) * 0.6), (0, tone(140, 0.2, 18, noise=1.0) * 0.3)),
                "whoosh": tone(500, 0.45, 5, harm=0.2, noise=0.7, chirp=1.8) * 0.3,
                "fizz": tone(2400, 0.3, 9, harm=0.0, noise=1.0) * 0.12,
                "clear": clear * 0.35, "fail": tone(220, 1.0, 3, chirp=-0.4) * 0.4}

    # ---------------------------------------------------------- visuals (never touch gameplay)
    def centre(self, r: int, c: int) -> tuple[float, float]:
        return X0 + c * CELL + CELL / 2, Y0 + r * CELL + CELL / 2

    def boom_visual(self, r: int, c: int, k: int) -> None:
        x, y = self.centre(r, c)
        rng = self.fx.rng
        col = hsv255(float(self.hue[r, c]), 0.7, 1.0)
        self.scorch.append((r, c))
        n = {ANAR: 26, CHAKRI: 30, BOMB: 70, ROCKET: 14}[k]
        for _ in range(n):
            if len(self.sparks) >= MAX_SPARKS:
                break
            if k == ANAR:                                   # fountain: mostly upwards
                a = -math.pi / 2 + rng.uniform(-0.5, 0.5)
                sp = rng.uniform(250, 650)
            else:
                a = rng.uniform(0, 2 * math.pi)
                sp = rng.uniform(150, 520) * (1.6 if k == BOMB else 1.0)
            spin = 1.0 if k == CHAKRI else 0.0
            self.sparks.append([x, y, sp * math.cos(a), sp * math.sin(a), rng.uniform(0.5, 1.1),
                                rng.choice(SPARK_COLOURS) if rng.random() < 0.5 else col, spin])
        if k == BOMB:
            self.blasts.append([x, y, 0.0])
        if k == ROCKET:
            d = int(self.rocket_dir[r, c])
            self.flights.append([x, y, d, 0.0])

    def build(self) -> None:
        pg = self.pg
        bg = pg.Surface((W, H))
        for y in range(H):
            k = y / H
            bg.fill((int(6 + 38 * k), int(6 + 6 * k), int(30 + 22 * k)), (0, y, W, 1))
        rng = __import__("random").Random(f"sky:{self.seed}")
        for _ in range(170):
            pg.draw.circle(bg, (220, 220, 255), (rng.uniform(0, W), rng.uniform(0, H * 0.8)), rng.choice([1, 1, 2]))
        x = 0
        while x < W:                                            # rooftops and domes on the horizon
            bw, bh = rng.randint(60, 140), rng.randint(60, 200)
            pg.draw.rect(bg, (16, 10, 26), (x, H - 120 - bh, bw, bh + 120))
            if rng.random() < 0.3:
                pg.draw.circle(bg, (16, 10, 26), (x + bw // 2, H - 120 - bh), bw // 3)
            for wy in range(H - 110 - bh, H - 130, 24):
                for wx in range(x + 10, x + bw - 14, 22):
                    if rng.random() < 0.3:
                        bg.fill((255, 190, 90), (wx, wy, 8, 10))
            x += bw + rng.randint(0, 12)
        self.bg = bg
        self.sprites = {}
        for kind in KINDS:
            for hue_bin in range(8):
                self.sprites[(kind, hue_bin)] = self._cracker_sprite(kind, hue_bin / 8)
        self.glow = self._glow_sprite(26, (255, 200, 120))
        self.small_glow = self._glow_sprite(10, (255, 220, 160))
        self.diya_flame = self._glow_sprite(60, (255, 140, 30))
        self.combo_font = self.fonts.huge

    def _glow_sprite(self, r: int, col):
        yy, xx = np.mgrid[-r:r, -r:r]
        i = np.clip(1 - np.sqrt(xx * xx + yy * yy) / r, 0, 1) ** 2
        arr = (np.array(col)[None, None, :] * i[..., None]).astype(np.uint8)
        return self.pg.surfarray.make_surface(arr.transpose(1, 0, 2).copy())

    def _cracker_sprite(self, kind: int, hue: float):
        pg = self.pg
        s = pg.Surface((CELL, CELL), pg.SRCALPHA)
        col = hsv255(hue, 0.75, 0.95)
        dark = tuple(int(v * 0.55) for v in col)
        if kind == ANAR:
            pg.draw.polygon(s, col, [(14, 54), (46, 54), (34, 14), (26, 14)])
            pg.draw.rect(s, (250, 230, 160), (16, 36, 28, 7))
        elif kind == CHAKRI:
            pg.draw.circle(s, col, (30, 32), 22)
            for i in range(3):
                pg.draw.circle(s, dark, (30, 32), 18 - 6 * i, 3)
        elif kind == BOMB:
            pg.draw.circle(s, (170, 40, 40), (30, 36), 20)
            pg.draw.circle(s, (230, 200, 150), (30, 36), 20, 3)
            pg.draw.line(s, (230, 220, 200), (30, 16), (38, 6), 3)
        elif kind == ROCKET:
            pg.draw.line(s, (200, 170, 120), (30, 54), (30, 26), 3)
            pg.draw.rect(s, col, (24, 10, 12, 24), border_radius=3)
            pg.draw.polygon(s, (240, 240, 250), [(24, 10), (30, 2), (36, 10)])
        elif kind == DUD:
            pg.draw.polygon(s, (90, 90, 100), [(16, 54), (44, 54), (34, 16), (26, 16)])
        return s

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        dt = max(0.0, (t - self.last_draw_t)) * self.time_scale
        self.last_draw_t = t
        screen.blit(self.bg, (0, 0))
        for r, c in self.scorch:
            x, y = self.centre(r, c)
            pg.draw.circle(screen, (30, 20, 28), (x, y + 6), 20)
        flicker = 0.5 + 0.5 * math.sin(t * 30)
        for r in range(ROWS):
            for c in range(COLS):
                st = self.state[r, c]
                if st == GONE:
                    continue
                k = int(self.kind[r, c])
                x, y = X0 + c * CELL, Y0 + r * CELL
                screen.blit(self.sprites[(k, int(self.hue[r, c] * 8) % 8)], (x, y))
                if st == LIT:
                    screen.blit(self.glow, (x + CELL / 2 - 26, y + 4 - 26 + 6 * flicker), special_flags=pg.BLEND_ADD)
        if getattr(self, "mega", None) and self.state[self.mega] != GONE:
            x, y = self.centre(*self.mega)
            pg.draw.circle(screen, (255, 214, 64), (x, y), 30 + 4 * flicker, 3)
        for f in self.flights:
            f[3] += dt
            fx = f[0] + f[2] * f[3] / ROCKET_CELL_S * CELL
            for k2 in range(8):
                screen.blit(self.small_glow, (fx - f[2] * k2 * 10 - 10, f[1] - 10), special_flags=pg.BLEND_ADD)
        self.flights = [f for f in self.flights if f[3] < ROCKET_RANGE * ROCKET_CELL_S]
        for b in self.blasts:
            b[2] += dt
            rad = 40 + 520 * b[2]
            pg.draw.circle(screen, (255, 230, 180), (b[0], b[1]), rad, max(1, int(10 * (1 - b[2] / 0.4))))
        self.blasts = [b for b in self.blasts if b[2] < 0.4]
        keep = []
        for p in self.sparks:
            p[3] += 420 * dt
            if p[6]:
                p[2], p[3] = p[2] - p[3] * 2.5 * dt, p[3] + p[2] * 2.5 * dt
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] > 0:
                keep.append(p)
                pg.draw.circle(screen, p[5], (p[0], p[1]), 3)
                screen.blit(self.small_glow, (p[0] - 10, p[1] - 10), special_flags=pg.BLEND_ADD)
        self.sparks = keep
        for i in range(6):                                          # diyas along the bottom
            dx, dy = 120 + i * 168, H - 70
            screen.blit(self.diya_flame, (dx - 60, dy - 100), special_flags=pg.BLEND_ADD)
            pg.draw.polygon(screen, (150, 64, 24), [(dx - 50, dy), (dx + 50, dy), (dx + 32, dy + 28), (dx - 32, dy + 28)])
            pg.draw.ellipse(screen, (226, 120, 52), (dx - 52, dy - 9, 104, 18))
            h = 50 + 8 * math.sin(t * 9 + i)
            pg.draw.polygon(screen, (255, 190, 60), [(dx, dy - h), (dx + 13, dy - 22), (dx, dy - 6), (dx - 13, dy - 22)])
        if self.done == "broken":                                  # point out the survivors
            for r, c in np.argwhere((self.state == IDLE) & (self.kind != DUD)):
                x, y = self.centre(int(r), int(c))
                pg.draw.circle(screen, (255, 214, 64), (x, y), 30 + 6 * flicker, 4)
        if self.exploded >= 10 and not self.done:
            lab = outlined(pg, self.fonts.big, f"x{self.exploded}", (255, 214, 64), 5)
            screen.blit(lab, lab.get_rect(center=(W / 2, Y0 - 60)))
        self.fx.draw_particles(screen)
