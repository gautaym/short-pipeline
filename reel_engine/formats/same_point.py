"""same_point: balls fired from one point bounce once off a closed shape. Do they all meet?

Round 1 fires two mirror-image balls; they must meet on the axis, and that meeting point becomes
the target. Later rounds fire 4, 8, 16 balls. In an ellipse fired from one focus, every ball
reflects through the other focus and they all arrive at the same instant (the reflection property
of the ellipse). In a circle, a stadium, a blob, or an ellipse fired slightly off its focus, they
do not, so the run fails at some round. Which shape you get is seeded.
"""
import math

import numpy as np

from ..core.audio import SR, SoundBank, overlay, tone
from ..core.canvas import W
from ..core.palette import hsv255
from ..core.text import outlined
from . import EndCard, Format, Option, register

CX, CY = W / 2, 980
SPEED = 330.0                        # px per second of play
SEGMENTS = 1440                      # polygon resolution of the wall
ROUNDS = [2, 4, 8, 16]
HIT_TOL = 7.0                        # px: how close to the target counts as a hit
PAUSE_S = 1.6                        # between rounds
SPREADS = [None, 60, 105, 150]       # degrees either side of the axis, per round (round 1 is a narrow pair)

SHAPES = {   # name: (weight, label)
    "ellipse": (4, "ellipse"),
    "off_focus": (2, "ellipse"),
    "circle": (1, "circle"),
    "stadium": (1, "stadium"),
    "blob": (1, "blob"),
    "rounded_box": (1, "rounded box"),
}


def wall(shape: str, rng) -> tuple[np.ndarray, dict]:
    """Closed polygon (SEGMENTS points, counter-clockwise) and facts about the shape."""
    a, b = rng.uniform(250, 320), rng.uniform(400, 470)          # half width, half height
    th = np.linspace(0, 2 * np.pi, SEGMENTS, endpoint=False)
    if shape in ("ellipse", "off_focus"):
        x, y = a * np.cos(th), b * np.sin(th)
    elif shape == "circle":
        x, y = a * 1.2 * np.cos(th), a * 1.2 * np.sin(th)
    elif shape == "stadium":
        x, y = a * np.cos(th), np.sign(np.sin(th)) * (b - a) + a * np.sin(th)
    elif shape == "blob":
        k, amp = rng.choice([5, 6, 7]), rng.uniform(0.06, 0.1)
        r = 1 + amp * np.cos(k * (th - np.pi / 2))
        x, y = a * 1.15 * r * np.cos(th), b * 0.9 * r * np.sin(th)
    else:                                                         # rounded box (superellipse)
        n = 4.0
        x = a * np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / n)
        y = b * 0.85 * np.sign(np.sin(th)) * np.abs(np.sin(th)) ** (2 / n)
    pts = np.stack([CX + x, CY - y], axis=1)
    c = math.sqrt(max(b * b - a * a, 0))
    return pts, {"a": a, "b": b, "focus": c}


def first_hit(pts: np.ndarray, o: np.ndarray, d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Where a ray from o along unit d first meets the wall, and the reflected direction."""
    a, b = pts, np.roll(pts, -1, axis=0)
    e = b - a
    denom = d[0] * e[:, 1] - d[1] * e[:, 0]
    ao = a - o
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (ao[:, 0] * e[:, 1] - ao[:, 1] * e[:, 0]) / denom
        u = (ao[:, 0] * d[1] - ao[:, 1] * d[0]) / denom
    ok = (np.abs(denom) > 1e-12) & (t > 1e-6) & (u >= 0) & (u <= 1)
    i = int(np.argmin(np.where(ok, t, np.inf)))
    hit = o + t[i] * d
    n = np.array([e[i, 1], -e[i, 0]])
    n /= np.linalg.norm(n)
    return hit, d - 2 * np.dot(d, n) * n


@register
class SamePoint(Format):
    name = "same_point"
    order = 120
    default_duration = 40.0
    options = (Option("--shape-kind", "same_point: " + ", ".join(SHAPES), {"default": None}),)
    wins = ("all",)
    cta = "Did you guess right?"
    music = "chill"
    series = "Same Point?"
    tags = ("ellipse", "geometry", "maths", "reflection", "satisfying", "physics")
    hashtags = ("maths", "geometry", "satisfying")

    @classmethod
    def titles(cls, o):
        shape, n, hits = o["shape"], o["balls"], o["hits"]
        if o["result"] == "all":
            return [f"All {n} balls hit the same point", f"Why do they all meet? ({shape})",
                    f"{n} balls, 1 bounce, 1 point", f"The {shape} trick: all {n} meet at once"]
        return [f"It worked with 2... then only {hits} of {n}", f"The {shape} broke at {n} balls",
                f"Will they all hit the same point? Not in a {shape}", f"{hits} of {n} hit the spot"]

    @classmethod
    def describe(cls, o):
        if o["result"] == "all":
            return (f"Every ball fired from one focus of an ellipse reflects through the other focus, and they "
                    f"all arrive together: {o['balls']} balls, one point.")
        return f"In a {o['shape']} there is no second focus: only {o['hits']} of {o['balls']} balls hit the point."

    # ---------------------------------------------------------- setup
    def setup(self) -> None:
        rng = self.rng
        kind = getattr(self.opts, "shape_kind", None)
        if kind is None:
            names = list(SHAPES)
            kind = rng.choices(names, [SHAPES[n][0] for n in names])[0]
        if kind not in SHAPES:
            raise SystemExit(f"same_point shapes: {', '.join(SHAPES)}")
        self.kind, self.label = kind, SHAPES[kind][1]
        self.pts, info = wall(kind, rng)
        if kind == "ellipse":
            launch_y = CY + info["focus"]
        elif kind == "off_focus":
            launch_y = CY + info["focus"] + rng.choice([-1, 1]) * rng.uniform(8, 20)
        else:
            launch_y = CY + rng.uniform(0.25, 0.6) * info["b"]
        self.launch = np.array([CX, launch_y])
        self.jitter = rng.uniform(0.85, 1.0)
        self.first_phi = math.radians(rng.uniform(25, 45))     # round 1's pair: narrow, so it meets inside
        self.hue = rng.random()
        self.round = 0
        self.round_t = 0.0
        self.pause = 0.6
        self.target: np.ndarray | None = None
        self.results: list[tuple[int, int]] = []        # (hits, balls) per finished round
        self.failed = False
        self.new_round()

    def title_hooks(self) -> list[str]:
        return ["Will they all hit the same point?", "It works with 2 balls. Will it work with 16?",
                "One bounce. Do they all meet?", "Will every ball find the same spot?"]

    def directions(self, n: int) -> list[np.ndarray]:
        out = []
        for i in range(n // 2):
            spread = math.radians(SPREADS[self.round]) if self.round else 0.0
            phi = self.first_phi if n == 2 else spread * self.jitter * (i + 0.5) / (n // 2)   # from straight up
            for s in (-1, 1):
                out.append(np.array([s * math.sin(phi), -math.cos(phi)]))
        return out

    def new_round(self) -> None:
        if self.round == 0:                                           # narrow the pair until it meets inside
            while self.first_phi > math.radians(8) and not self.pair_meets_inside():
                self.first_phi *= 0.85
        n = ROUNDS[self.round]
        self.paths = []
        for d in self.directions(n):
            h1, r1 = first_hit(self.pts, self.launch, d)
            h2, _ = first_hit(self.pts, h1 + r1 * 1e-3, r1)
            self.paths.append((self.launch.copy(), h1, h2))
        if self.target is None:                                       # where the first pair meets
            (_, a1, a2), (_, b1, b2) = self.paths[0], self.paths[1]
            da, db = a2 - a1, b2 - b1
            m = np.array([[da[0], -db[0]], [da[1], -db[1]]])
            s = np.linalg.solve(m, b1 - a1)[0]
            self.target = a1 + s * da
        self.passes = []                                              # distance along path at closest approach
        self.hit = []
        for p0, h1, h2 in self.paths:
            leg1 = np.linalg.norm(h1 - p0)
            seg = h2 - h1
            u = np.clip(np.dot(self.target - h1, seg) / np.dot(seg, seg), 0, 1)
            closest = h1 + u * seg
            self.passes.append(leg1 + u * np.linalg.norm(seg))
            self.hit.append(bool(np.linalg.norm(closest - self.target) <= HIT_TOL))
        self.round_len = max(self.passes) + 90
        self.arrived = [False] * len(self.paths)
        self.round_t = 0.0

    def pair_meets_inside(self) -> bool:
        legs = []
        for d in self.directions(2):
            h1, r1 = first_hit(self.pts, self.launch, d)
            h2, _ = first_hit(self.pts, h1 + r1 * 1e-3, r1)
            legs.append((h1, h2))
        (a1, a2), (b1, b2) = legs
        da, db = a2 - a1, b2 - b1
        m = np.array([[da[0], -db[0]], [da[1], -db[1]]])
        if abs(np.linalg.det(m)) < 1e-9:
            return False
        s, u = np.linalg.solve(m, b1 - a1)
        return 0.02 < s < 0.98 and 0.02 < u < 0.98

    # ---------------------------------------------------------- simulation
    def step(self, dt: float, t: float) -> None:
        if self.pause > 0:
            self.pause -= dt
            if self.pause <= 0:
                self.sfx(t, "launch", force=True)
            return
        if self.round_t == 0.0:
            self.bounced = [False] * len(self.paths)
        self.round_t += dt
        dist = self.round_t * SPEED
        for i, (p0, h1, _) in enumerate(self.paths):
            if not self.bounced[i] and dist >= np.linalg.norm(h1 - p0):
                self.bounced[i] = True
                self.sfx(t, "ping", i)
            if not self.arrived[i] and dist >= self.passes[i]:
                self.arrived[i] = True
                if self.hit[i]:
                    self.sfx(t, "hit", i)
        if dist >= self.round_len:
            n, hits = len(self.paths), sum(self.hit)
            self.results.append((hits, n))
            ok = hits == n
            self.sfx(t, "yes" if ok else "no", force=True)
            if self.fx.enabled:
                self.fx.floater(W / 2, 520, f"{hits}/{n} HIT" if not ok else f"ALL {n} HIT!",
                                (120, 255, 140) if ok else (255, 90, 90), self.fonts.big, 1.2)
            if not ok:
                self.failed = True
                self.mark("decisive")
                return
            if self.round + 1 < len(ROUNDS):
                self.round += 1
                self.new_round()
                self.pause = PAUSE_S
            else:
                self.mark("decisive")

    def check_end(self, t: float):
        if self.failed:
            return "missed"
        if len(self.results) == len(ROUNDS):
            return "all"
        if self.play_t >= self.max_play:
            return "time"
        return None

    def stats(self) -> list[str]:
        n = ROUNDS[self.round]
        return [f"ROUND {self.round + 1}/{len(ROUNDS)}", f"BALLS {n}", self.label.upper()]

    def progress(self) -> float:
        return len(self.results) / len(ROUNDS)

    def drama_score(self, trace) -> float:
        rounds = len(trace.outcome.get("rounds", []))
        s = 4.0 if trace.done == "all" else 1.5 * rounds          # failing late beats failing early
        return s

    def end_card(self) -> EndCard:
        hits, n = self.results[-1] if self.results else (0, ROUNDS[self.round])
        if self.done == "all":
            return EndCard(f"ALL {n} HIT IT!", "an ellipse sends everything from one focus to the other")
        if self.kind == "off_focus":
            return EndCard(f"ONLY {hits} OF {n}!", "so close: the launch point was just off the focus")
        return EndCard(f"ONLY {hits} OF {n}!", f"a {self.label} has no second focus")

    def outcome(self):
        hits, n = self.results[-1] if self.results else (0, ROUNDS[self.round])
        return {**super().outcome(), "shape": self.label, "kind": self.kind, "hits": hits, "balls": n,
                "rounds": self.results}

    def sounds(self) -> SoundBank:
        pent = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36]
        yes = overlay(*[(0.07 * i, tone(523.25 * 2 ** (s / 12), 0.9, 4) * 0.25) for i, s in enumerate((0, 4, 7, 12))])
        return {"ping": [tone(523.25 * 2 ** (k / 12), 0.25, 14, harm=0.2) * 0.22 for k in pent],
                "hit": [tone(1046.5 * 2 ** (k / 12), 0.4, 9) * 0.18 for k in pent],
                "launch": tone(300, 0.3, 8, harm=0.2, noise=0.4, chirp=1.0) * 0.25,
                "yes": yes, "no": tone(180, 0.6, 5, harm=0.6, chirp=-0.3) * 0.4,
                "clear": yes, "fail": tone(180, 0.8, 4, harm=0.6, chirp=-0.4) * 0.4}

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        pg = self.pg
        self.bg = pg.Surface((W, 1920))
        for y in range(1920):
            k = y / 1920
            self.bg.fill((int(6 + 6 * k), int(7 + 5 * k), int(18 + 10 * k)), (0, y, W, 1))
        col = hsv255(self.hue, 0.65, 1.0)
        poly = [tuple(p) for p in self.pts]
        layer = pg.Surface((W, 1920), pg.SRCALPHA)
        for width, alpha in ((34, 40), (22, 80), (12, 160)):
            pg.draw.lines(layer, col + (alpha,), True, poly, width)
        pg.draw.lines(layer, (255, 255, 255, 230), True, poly, 3)
        self.bg.blit(layer, (0, 0))
        self.ball_cols = [hsv255(self.hue + 0.5 + i / 16, 0.6, 1.0) for i in range(16)]

    def position(self, path, dist: float) -> np.ndarray:
        p0, h1, h2 = path
        l1 = np.linalg.norm(h1 - p0)
        if dist <= l1:
            return p0 + (h1 - p0) * (dist / l1)
        return h1 + (h2 - h1) * min(1.0, (dist - l1) / max(np.linalg.norm(h2 - h1), 1e-6))

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        screen.blit(self.bg, (0, 0))
        tx, ty = self.target
        pg.draw.circle(screen, (255, 255, 255), (tx, ty), 14, 2)
        lx, ly = self.launch
        pg.draw.circle(screen, (200, 200, 220), (lx, ly), 10, 2)
        dist = max(0.0, self.round_t * SPEED) if self.pause <= 0 else 0.0
        for i, path in enumerate(self.paths):
            col = self.ball_cols[i % len(self.ball_cols)]
            p0, h1, _ = path
            pos = self.position(path, dist)
            line = [tuple(p0)] + ([tuple(h1)] if dist > np.linalg.norm(h1 - p0) else []) + [tuple(pos)]
            if len(line) > 1:
                pg.draw.lines(screen, tuple(int(c * 0.7) for c in col), False, line, 2)
            pg.draw.circle(screen, col, pos, 9)
            pg.draw.circle(screen, (255, 255, 255), pos, 4)
        if self.pause <= 0 and all(self.arrived) and all(self.hit):
            pg.draw.circle(screen, (255, 255, 200), (tx, ty), 26, 4)
        if self.results:
            x = W / 2 - 110 * (len(self.results) - 1) / 2
            for hits, n in self.results:
                col = (120, 255, 140) if hits == n else (255, 90, 90)
                lab = outlined(pg, self.fonts.mid, f"{hits}/{n}", col, 3)
                screen.blit(lab, lab.get_rect(center=(x, 1480)))
                x += 110
        self.fx.draw_particles(screen)
