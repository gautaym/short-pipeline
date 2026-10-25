"""2D classical mechanics: point bodies under gravity, uniform fields and drag.

Bodies are stored as numpy arrays so many of them stay fast. Integration is leapfrog
(kick-drift-kick), which keeps orbits stable over long runs, with several substeps per tick
for close encounters. Everything is deterministic: the same scene and seed give the same run.

Events (a body swallowed, merged, landed, escaped) are recorded with their time so scenes can
end on them and the drama engine can find the decisive moment.
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Body:
    name: str
    mass: float
    radius: float
    pos: tuple[float, float]
    vel: tuple[float, float] = (0.0, 0.0)
    colour: tuple[int, int, int] = (255, 255, 255)
    fixed: bool = False
    kind: str = "body"            # "body" or "black_hole"
    glow: float = 0.0             # glow size, as a multiple of the radius
    trail: int = 0                # positions kept for the trail (0 = none)
    label: bool = False           # draw the name next to it
    horizon: float = 0.0          # black holes: anything closer than this is swallowed


@dataclass
class Event:
    t: float
    kind: str                     # swallowed, merged, landed
    body: int
    other: int = -1


@dataclass
class WorldSettings:
    G: float = 0.0
    softening: float = 2.0
    uniform: tuple[float, float] = (0.0, 0.0)   # e.g. (0, -9.8) for projectiles (y points up)
    drag: float = 0.0                           # quadratic drag: a = -drag * |v| * v
    ground: float | None = None                 # bodies stop when they reach this height
    merge: bool = False                         # bodies that touch merge into the heavier one
    substeps: int = 4
    time_scale: float = 1.0                     # simulated seconds per real second


class World:
    def __init__(self, bodies: list[Body], settings: WorldSettings):
        self.bodies = bodies
        self.s = settings
        n = len(bodies)
        self.pos = np.array([b.pos for b in bodies], dtype=float).reshape(n, 2)
        self.vel = np.array([b.vel for b in bodies], dtype=float).reshape(n, 2)
        self.mass = np.array([b.mass for b in bodies], dtype=float)
        self.radius = np.array([b.radius for b in bodies], dtype=float)
        self.fixed = np.array([b.fixed for b in bodies], dtype=bool)
        self.alive = np.ones(n, dtype=bool)
        self.landed = np.zeros(n, dtype=bool)
        self.holes = np.array([b.kind == "black_hole" for b in bodies], dtype=bool)
        self.horizon = np.array([b.horizon or b.radius for b in bodies], dtype=float)
        self.t = 0.0
        self.events: list[Event] = []
        self.acc = self.accelerations()

    def index(self, name: str) -> int:
        for i, b in enumerate(self.bodies):
            if b.name == name:
                return i
        raise KeyError(f"no body called {name!r}")

    # ---------------------------------------------------------- forces
    def accelerations(self) -> np.ndarray:
        s = self.s
        acc = np.zeros_like(self.pos)
        acc += np.array(s.uniform, dtype=float)
        if s.G:
            m = np.where(self.alive, self.mass, 0.0)
            d = self.pos[None, :, :] - self.pos[:, None, :]          # d[i, j] = pos[j] - pos[i]
            r2 = (d * d).sum(axis=2) + s.softening ** 2
            inv3 = r2 ** -1.5
            np.fill_diagonal(inv3, 0.0)
            acc += s.G * (d * (m[None, :] * inv3)[:, :, None]).sum(axis=1)
        if s.drag:
            speed = np.linalg.norm(self.vel, axis=1, keepdims=True)
            acc -= s.drag * speed * self.vel
        acc[self.fixed | ~self.alive | self.landed] = 0.0
        return acc

    # ---------------------------------------------------------- integration
    def step(self, dt: float) -> None:
        """Advance by dt real seconds (scaled by time_scale), in substeps."""
        h = dt * self.s.time_scale / self.s.substeps
        moving = ~(self.fixed | ~self.alive | self.landed)
        for _ in range(self.s.substeps):
            self.vel[moving] += 0.5 * h * self.acc[moving]
            self.pos[moving] += h * self.vel[moving]
            self.t += h
            self.collide()
            moving = ~(self.fixed | ~self.alive | self.landed)
            self.acc = self.accelerations()
            self.vel[moving] += 0.5 * h * self.acc[moving]

    def collide(self) -> None:
        s = self.s
        if s.ground is not None:
            hit = self.alive & ~self.fixed & ~self.landed & (self.pos[:, 1] - self.radius <= s.ground) \
                & (self.vel[:, 1] < 0)
            for i in np.flatnonzero(hit):
                self.pos[i, 1] = s.ground + self.radius[i]
                self.vel[i] = 0.0
                self.landed[i] = True
                self.events.append(Event(self.t, "landed", int(i)))
        holes = np.flatnonzero(self.holes & self.alive)
        for h in holes:
            d = np.linalg.norm(self.pos - self.pos[h], axis=1)
            eaten = self.alive & (d < self.horizon[h] + self.radius * 0.3)
            eaten[h] = False
            for i in np.flatnonzero(eaten):
                if self.holes[i] and self.mass[i] > self.mass[h]:
                    continue                                  # the bigger hole does the eating
                self.absorb(h, int(i), "swallowed")
        if s.merge:
            idx = np.flatnonzero(self.alive & ~self.holes)
            for a_pos, a in enumerate(idx):
                for b in idx[a_pos + 1:]:
                    if self.alive[a] and self.alive[b] and \
                            np.linalg.norm(self.pos[a] - self.pos[b]) < self.radius[a] + self.radius[b]:
                        big, small = (a, b) if self.mass[a] >= self.mass[b] else (b, a)
                        self.absorb(int(big), int(small), "merged")

    def absorb(self, big: int, small: int, kind: str) -> None:
        """Momentum-conserving merge of `small` into `big`."""
        m1, m2 = self.mass[big], self.mass[small]
        if not self.fixed[big]:
            self.vel[big] = (m1 * self.vel[big] + m2 * self.vel[small]) / (m1 + m2)
        self.mass[big] = m1 + m2
        if kind == "merged":
            self.radius[big] = (self.radius[big] ** 2 + self.radius[small] ** 2) ** 0.5
        self.alive[small] = False
        self.events.append(Event(self.t, kind, small, big))

    # ---------------------------------------------------------- measurements
    def speed(self, i: int) -> float:
        return float(np.linalg.norm(self.vel[i]))

    def distance(self, i: int, j: int) -> float:
        return float(np.linalg.norm(self.pos[i] - self.pos[j]))

    def centre_of_mass(self, exclude: int | None = None) -> np.ndarray:
        m = np.where(self.alive, self.mass, 0.0)
        if exclude is not None:
            m[exclude] = 0.0
        return (self.pos * m[:, None]).sum(axis=0) / max(m.sum(), 1e-12)

    def energy(self) -> float:
        m = np.where(self.alive, self.mass, 0.0)
        ke = 0.5 * (m * (self.vel ** 2).sum(axis=1)).sum()
        pe = 0.0
        if self.s.G:
            d = np.linalg.norm(self.pos[None] - self.pos[:, None], axis=2) + 1e-9
            pe = -0.5 * self.s.G * (m[None] * m[:, None] / d)[~np.eye(len(m), dtype=bool)].sum()
        return float(ke + pe)
