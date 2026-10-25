"""ring_escape: balls bounce inside spinning rings with gaps; every escape spawns 2 more balls.

"Every escape = 2 more balls. Can it reach 100?" Balls fall under gravity and bounce off the
rings elastically; a ball can only pass a ring through its gap, which keeps rotating. Each bounce
plays the next note of a rising pentatonic scale.
"""
import math

import numpy as np

from ..core.audio import SR, SoundBank, overlay, tone
from ..core.canvas import H, W
from ..core.palette import hsv255
from . import EndCard, Format, Option, Twist, register

CX, CY = W / 2, 1000
OUTER_R = 470
BALL_R = 12
RING_W = 16
MAX_BALLS = 400
TRAIL_N = 6
SPAWN_SPEED = (420, 820)
BOUNCE_GAIN = 1.02          # each bounce adds a little energy, so balls stay lively...
MAX_SPEED = 1500.0          # ...up to this speed
GAP_DEG = (45, 70)
GOALS = [30, 40, 60, 80]
PENTA = [0, 2, 4, 7, 9]
NOTES = [PENTA[i % 5] + 12 * (i // 5) for i in range(15)]
HUES = 12


class RBall:
    __slots__ = ("x", "y", "vx", "vy", "hue", "trail")

    def __init__(self, x, y, vx, vy, hue):
        self.x, self.y, self.vx, self.vy, self.hue = x, y, vx, vy, hue
        self.trail: list[tuple[float, float]] = []


class Ring:
    __slots__ = ("radius", "angle", "gap_half", "speed", "colour", "alive")

    def __init__(self, radius, angle, gap_half, speed, colour):
        self.radius, self.angle, self.gap_half, self.speed, self.colour = radius, angle, gap_half, speed, colour
        self.alive = True

    def in_gap(self, theta: float) -> bool:
        diff = (theta - self.angle + math.pi) % (2 * math.pi) - math.pi
        return abs(diff) < self.gap_half - BALL_R / self.radius


@register
class RingEscape(Format):
    name = "ring_escape"
    order = 60
    default_duration = 35.0
    options = (Option("--rings", "ring_escape: number of rings", {"type": int, "choices": [1, 2, 3, 4],
                                                                   "default": None}),
               Option("--goal", "ring_escape: balls needed to win", {"type": int, "default": None}))
    wins = ("goal",)
    cta = "Comment your prediction!"

    def setup(self) -> None:
        rng = self.rng
        n = getattr(self.opts, "rings", None) or rng.choice([1, 2, 2])
        self.gravity = rng.uniform(450, 750)
        radii = [OUTER_R] if n == 1 else np.linspace(rng.uniform(260, 320), OUTER_R, n)
        self.hue0 = rng.random()
        self.rings = [Ring(float(r), rng.uniform(0, 2 * math.pi), math.radians(rng.uniform(*GAP_DEG)) / 2,
                           rng.uniform(0.9, 2.0) * rng.choice([-1, 1]),
                           hsv255((self.hue0 + 0.13 * i) % 1, 0.75, 1.0)) for i, r in enumerate(radii)]
        self.goal = getattr(self.opts, "goal", None) or rng.choice(GOALS)
        self.balls: list[RBall] = []
        self.escaped = 0
        self.note = 0
        self.flying: list[list] = []          # escaped balls drifting away (visual only)
        self.spawn(1)

    def title_hooks(self) -> list[str]:
        return ["Every escape = 2 more balls", f"Can it reach {self.goal} balls?",
                f"1 ball. {len(self.rings)} ring{'s' if len(self.rings) > 1 else ''}. {self.goal} to win.",
                f"{self.goal} balls in {int(self.max_play)} seconds?"]

    def twists(self) -> list[Twist]:
        return [Twist("shatter", "a ring just shattered", self._shatter,
                      lambda: sum(r.alive for r in self.rings) >= 2),
                Twist("reverse", "every ring reversed its spin", self._reverse)]

    def _shatter(self, t: float) -> None:
        ring = next(r for r in self.rings if r.alive)
        ring.alive = False
        self.sfx(t, "shatter", force=True)
        for k in range(24):
            a = 2 * math.pi * k / 24
            self.fx.burst(CX + ring.radius * math.cos(a), CY + ring.radius * math.sin(a), ring.colour, 3, 0.8)
        return None

    def _reverse(self, t: float) -> None:
        for r in self.rings:
            r.speed *= -1.3
        return None

    def spawn(self, count: int) -> int:
        n = max(0, min(count, MAX_BALLS - len(self.balls)))
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(*SPAWN_SPEED)
            self.balls.append(RBall(CX, CY, sp * math.cos(a), sp * math.sin(a), self.rng.randrange(HUES)))
        return n

    def outer_radius(self) -> float:
        alive = [r.radius for r in self.rings if r.alive]
        return max(alive) if alive else 0.0

    # ---------------------------------------------------------- simulation
    def step(self, dt: float, t: float) -> None:
        for ring in self.rings:
            ring.angle = (ring.angle + ring.speed * dt) % (2 * math.pi)
        rings = [r for r in self.rings if r.alive]
        exit_r = self.outer_radius() + RING_W + BALL_R
        keep, born = [], 0
        for b in self.balls:
            b.vy += self.gravity * dt
            b.x += b.vx * dt
            b.y += b.vy * dt
            dx, dy = b.x - CX, b.y - CY
            d = math.hypot(dx, dy) or 1e-6
            if d > exit_r:
                self.escaped += 1
                born += 2
                self.sfx(t, "escape")
                if self.fx.enabled:
                    self.flying.append([b.x, b.y, b.vx, b.vy, b.hue, 1.2])
                continue
            nx, ny = dx / d, dy / d
            theta = math.atan2(dy, dx)
            for ring in rings:
                vn = b.vx * nx + b.vy * ny
                if d < ring.radius:
                    limit = ring.radius - RING_W / 2 - BALL_R
                    hit = d > limit and vn > 0
                else:
                    limit = ring.radius + RING_W / 2 + BALL_R
                    hit = d < limit and vn < 0
                if hit and not ring.in_gap(theta):
                    k = min(BOUNCE_GAIN, MAX_SPEED / (math.hypot(b.vx, b.vy) or 1.0))
                    b.vx = (b.vx - 2 * vn * nx) * k
                    b.vy = (b.vy - 2 * vn * ny) * k
                    b.x, b.y = CX + nx * limit, CY + ny * limit
                    d = limit
                    self.sfx(t, "note", self.note)
                    self.note = (self.note + 1) % len(NOTES)
                    break
            keep.append(b)
        self.balls = keep
        if born:
            got = self.spawn(born)
            if got and self.fx.enabled:
                self.fx.floater(CX, CY - 40, f"+{got}", (255, 255, 255), self.fonts.mid, 0.6)
        for f in self.flying:
            f[3] += self.gravity * dt
            f[0] += f[2] * dt
            f[1] += f[3] * dt
            f[5] -= dt
        self.flying = [f for f in self.flying if f[5] > 0 and -50 < f[1] < H + 50]

    def check_end(self, t: float):
        if len(self.balls) >= self.goal:
            self.mark("decisive")
            return "goal"
        if self.play_t >= self.max_play:
            return "time"
        return None

    def stats(self) -> list[str]:
        return [f"BALLS {len(self.balls)}", f"GOAL {self.goal}", f"ESCAPES {self.escaped}"]

    def progress(self) -> float:
        return min(1.0, len(self.balls) / self.goal)

    def hud_accent(self):
        return hsv255(self.hue0, 0.6, 1.0)

    def end_card(self) -> EndCard:
        if self.done == "goal":
            return EndCard(f"{self.goal} BALLS!", f"reached in {self.play_t:.1f} seconds")
        return EndCard("TIME UP!", f"stopped at {len(self.balls)} of {self.goal}")

    def outcome(self):
        return {**super().outcome(), "goal": self.goal, "balls": len(self.balls), "escapes": self.escaped,
                "rings": len(self.rings)}

    def sounds(self) -> SoundBank:
        clear = np.zeros(int(SR * 1.7), dtype=np.float32)
        for s, d in ((0, 0), (4, 0.08), (7, 0.16), (12, 0.24)):
            note = tone(523.25 * 2 ** (s / 12), 1.4, 3)
            a = int(SR * d)
            clear[a:a + len(note)] += note
        return {
            "note": [tone(392.0 * 2 ** (k / 12), 0.22, 16, harm=0.25) * 0.3 for k in NOTES],
            "escape": overlay((0, tone(1318.5, 0.25, 14) * 0.22), (0.06, tone(1760, 0.3, 12) * 0.22)),
            "shatter": tone(90, 0.6, 6, harm=0.6, noise=0.6) * 0.5,
            "clear": clear * 0.35,
            "fail": tone(220, 1.0, 3, chirp=-0.4) * 0.4,
        }

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        pg = self.pg
        x = (np.arange(W) - CX)[:, None]
        y = (np.arange(H) - CY)[None, :]
        k = np.clip(np.sqrt(x * x + y * y) / 1300, 0, 1)[..., None]
        inner = np.array(hsv255((self.hue0 + 0.5) % 1, 0.6, 0.18), dtype=float)
        outer = np.array((6, 6, 12), dtype=float)
        self.bg = pg.surfarray.make_surface((inner * (1 - k) + outer * k).astype(np.uint8))
        self.ball_sprites, self.trail_sprites = [], []
        for i in range(HUES):
            col = hsv255(self.hue0 + i / HUES, 0.55, 1.0)
            s = pg.Surface((BALL_R * 4, BALL_R * 4), pg.SRCALPHA)
            for j, a in enumerate((25, 45, 70)):
                pg.draw.circle(s, col + (a,), (BALL_R * 2, BALL_R * 2), BALL_R * (2 - j * 0.3))
            pg.draw.circle(s, (255, 255, 255), (BALL_R * 2, BALL_R * 2), BALL_R - 2)
            self.ball_sprites.append(s)
            dots = []
            for k2 in range(TRAIL_N - 1):
                f = (k2 + 1) / (TRAIL_N - 1)
                r = max(2, int(BALL_R * (0.3 + 0.55 * f)))
                d = pg.Surface((2 * r + 2, 2 * r + 2), pg.SRCALPHA)
                pg.draw.circle(d, col + (int(30 + 100 * f),), (r + 1, r + 1), r)
                dots.append(d)
            self.trail_sprites.append(dots)

    def _ring_poly(self, ring: Ring, half_width: float) -> list[tuple[float, float]]:
        a0 = ring.angle + ring.gap_half
        span = 2 * math.pi - 2 * ring.gap_half
        steps = max(48, int(ring.radius / 4))
        outer = [(CX + (ring.radius + half_width) * math.cos(a0 + span * i / steps),
                  CY + (ring.radius + half_width) * math.sin(a0 + span * i / steps)) for i in range(steps + 1)]
        inner = [(CX + (ring.radius - half_width) * math.cos(a0 + span * i / steps),
                  CY + (ring.radius - half_width) * math.sin(a0 + span * i / steps)) for i in range(steps, -1, -1)]
        return outer + inner

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        screen.blit(self.bg, (0, 0))
        for ring in self.rings:
            if not ring.alive:
                continue
            glow = tuple(int(c * 0.3) for c in ring.colour)
            pg.draw.polygon(screen, glow, self._ring_poly(ring, RING_W / 2 + 7))
            pg.draw.polygon(screen, ring.colour, self._ring_poly(ring, RING_W / 2))
        for f in self.flying:
            spr = self.ball_sprites[f[4]]
            spr.set_alpha(int(255 * min(1.0, f[5])))
            screen.blit(spr, (f[0] - BALL_R * 2, f[1] - BALL_R * 2))
            spr.set_alpha(None)
        self.fx.draw_particles(screen)
        for b in self.balls:
            b.trail.append((b.x, b.y))
            del b.trail[:-TRAIL_N]
            dots = self.trail_sprites[b.hue]
            off = TRAIL_N - len(b.trail)
            for i, (x, y) in enumerate(b.trail[:-1]):
                d = dots[i + off]
                screen.blit(d, (x - d.get_width() / 2, y - d.get_height() / 2))
        for b in self.balls:
            screen.blit(self.ball_sprites[b.hue], (b.x - BALL_R * 2, b.y - BALL_R * 2))
