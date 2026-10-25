"""physics: plays a physics scene file (scenes/*.yaml). "Will Earth survive the black hole?"

The scene describes bodies, forces, the camera, on-screen readouts and how the run can end; this
format simulates it with reel_engine.physics, draws it and turns the outcome into the end card.
Outcome conditions (checked in order, first match wins):

    time                         the scene's duration has run out
    swallowed(NAME | any)        a black hole swallowed the body
    merged(NAME | any)           the body merged into another
    landed(NAME | all)           the body (or every body) reached the ground
    ejected(NAME | any, R)       the body is further than R from the others' centre of mass
    escaped(NAME, R, FROM)       the body is further than R from body FROM (or from "origin")

Readouts: speed(NAME), distance(A, B), height(NAME), time, energy, or a text template.
"""
import math
import random
import re

import numpy as np

from ..core.audio import SR, SoundBank, overlay, tone
from ..core.canvas import ARENA_L, ARENA_R, H, SAFE_BOTTOM, W
from ..core.text import outlined
from ..physics.scene import Scene, load, scene_names
from ..physics.world import World
from . import EndCard, Format, Option, register

VIEW_TOP, VIEW_BOTTOM = 430, SAFE_BOTTOM          # screen band the scene is framed into
CALL = re.compile(r"^\s*(\w+)\s*(?:\((.*)\))?\s*$")


def parse(expr: str) -> tuple[str, list[str]]:
    m = CALL.match(expr)
    if not m:
        raise SystemExit(f"cannot read physics expression {expr!r}")
    args = [a.strip() for a in m.group(2).split(",")] if m.group(2) else []
    return m.group(1), args


@register
class PhysicsLab(Format):
    name = "physics"
    order = 110
    default_duration = 30.0
    options = (Option("--scene", "physics: scene name from scenes/ or a .yaml path", {"default": None}),)
    wins = ()
    cta = "Did you predict it?"
    series = "Physics Lab"
    tags = ("physics", "simulation", "science", "space", "gravity", "satisfying")
    hashtags = ("physics", "science", "simulation")

    @classmethod
    def titles(cls, o):
        head, sub = o.get("head", "").title(), o.get("sub", "")
        hook = o.get("hook", "")
        return [f"{head} ({sub})" if sub else head, f"{hook} {head.capitalize()}", f"{head}: {o.get('scene', '')} simulation"]

    @classmethod
    def describe(cls, o):
        return f"{o.get('head', '').capitalize()} {o.get('sub', '')}. A physics simulation ({o.get('scene', '')})."

    # ---------------------------------------------------------- setup
    def setup(self) -> None:
        name = getattr(self.opts, "scene", None) or self.rng.choice(scene_names())
        self.sc: Scene = load(name, self.rng)
        self.max_play = getattr(self.opts, "max_play", None) or self.sc.duration
        self.music = self.sc.music
        self.world = World(self.sc.bodies, self.sc.world)
        self.matched: dict | None = None
        self.match_ctx: dict = {}
        self.end_at: float | None = None
        self.seen_events = 0
        self.sweep_pts: list[tuple[float, np.ndarray, np.ndarray]] = []    # (time, body pos, centre pos)
        self.trails: list[list[tuple[float, float]]] = [[] for _ in self.sc.bodies]
        self.cam = None

    def title_hooks(self) -> list[str]:
        return [h.format(**self.sc.params) for h in self.sc.hooks]

    # ---------------------------------------------------------- simulation
    def step(self, dt: float, t: float) -> None:
        w = self.world
        w.step(dt)
        for e in w.events[self.seen_events:]:
            kind = {"swallowed": "swallow", "merged": "merge", "landed": "land"}[e.kind]
            self.sfx(t, kind, e.body, force=True)
            if e.kind == "swallowed":
                self.fx.shake(10, 0.4)
        self.seen_events = len(w.events)
        sw = self.sc.sweep
        if sw and self.tick % 6 == 0:
            self.sweep_pts.append((self.play_t, w.pos[w.index(sw["body"])].copy(), w.pos[w.index(sw["around"])].copy()))

    def subject(self, arg: str) -> list[int]:
        w = self.world
        return list(range(len(w.bodies))) if arg in ("any", "all") else [w.index(arg)]

    def condition(self, expr: str) -> tuple[bool, int]:
        """(true?, index of the body it is about, or -1)."""
        fn, args = parse(expr)
        w = self.world
        if fn == "time":
            return self.play_t >= self.max_play, -1
        if fn in ("swallowed", "merged"):
            kinds = {"swallowed": "swallowed", "merged": "merged"}[fn]
            who = set(self.subject(args[0]))
            for e in w.events:
                if e.kind == kinds and e.body in who:
                    return True, e.body
            return False, -1
        if fn == "landed":
            idx = self.subject(args[0])
            live = [i for i in idx if w.alive[i]]
            done = all(w.landed[i] for i in live) if args[0] == "all" else bool(w.landed[idx[0]])
            return done and bool(live), -1 if args[0] == "all" else idx[0]
        if fn == "ejected":
            for i in self.subject(args[0]):
                if w.alive[i] and not w.holes[i] and \
                        np.linalg.norm(w.pos[i] - w.centre_of_mass(exclude=i)) > float(args[1]):
                    return True, i
            return False, -1
        if fn == "escaped":
            i = w.index(args[0])
            ref = np.zeros(2) if args[2] == "origin" else w.pos[w.index(args[2])]
            return bool(w.alive[i] and np.linalg.norm(w.pos[i] - ref) > float(args[1])), i
        raise SystemExit(f"unknown condition {fn!r} in scene {self.sc.name}")

    def check_end(self, t: float):
        if self.matched is None:
            for oc in self.sc.outcomes:
                ok, who = self.condition(oc["when"])
                if ok:
                    self.matched = oc
                    self.match_ctx = self.context(oc, who)
                    if oc["when"].strip() != "time":
                        self.mark("decisive")
                    self.end_at = self.play_t + float(oc.get("linger", 0))
                    break
        if self.matched is not None and self.play_t >= self.end_at:
            return self.matched.get("result", "done")
        if self.play_t >= self.max_play + 15:                     # safety net for scenes without "time"
            return "time"
        return None

    def context(self, oc: dict, who: int) -> dict:
        w = self.world
        ctx = {**self.sc.params, "t": self.play_t, "name": w.bodies[who].name if who >= 0 else ""}
        if "rank" in oc:
            key = oc["rank"]
            live = [i for i in range(len(w.bodies)) if w.alive[i] and not w.fixed[i]]
            vals = sorted(((self.measure(key, i), i) for i in live), reverse=True)
            if vals:
                ctx.update(winner=w.bodies[vals[0][1]].name, value=vals[0][0],
                           margin=(vals[0][0] - vals[1][0]) if len(vals) > 1 else 0.0)
        return ctx

    def measure(self, key: str, i: int) -> float:
        w = self.world
        return {"x": w.pos[i, 0], "y": w.pos[i, 1], "speed": w.speed(i)}[key]

    def readout(self, r: dict) -> str:
        if "text" in r:
            return r["text"].format(**self.sc.params, t=self.play_t)
        fn, args = parse(r["value"])
        w = self.world
        val = {"speed": lambda: w.speed(w.index(args[0])),
               "distance": lambda: w.distance(w.index(args[0]), w.index(args[1])),
               "height": lambda: w.pos[w.index(args[0]), 1],
               "time": lambda: self.play_t,
               "energy": lambda: w.energy()}[fn]()
        return f"{r.get('label', fn).upper()} {val:.{int(r.get('digits', 0))}f}{r.get('unit', '')}"

    def stats(self) -> list[str]:
        out = [self.readout(r) for r in self.sc.readouts[:3]]
        return (out + ["", "", ""])[:3] if len(out) < 3 else out

    def progress(self) -> float:
        return min(1.0, self.play_t / self.max_play)

    def slug(self) -> str:
        return f"physics_{self.sc.name}"

    def end_sound(self, why: str) -> str:
        return "reveal"

    def end_card(self) -> EndCard:
        oc = self.matched or {"head": "TIME UP", "sub": ""}
        return EndCard(oc.get("head", "").format(**self.match_ctx), oc.get("sub", "").format(**self.match_ctx))

    def drama_score(self, trace) -> float:
        d = self.sc.drama
        s = 3.0 if trace.done in d.get("prefer", []) else 0.0
        if trace.decisive_t is not None:
            s += 3 - 4 * abs(trace.decisive_t / self.max_play - float(d.get("target", 0.7)))
        if "close" in d and "margin" in self.match_ctx:              # photo finishes
            s += 3 * (1 - min(1.0, self.match_ctx["margin"] / float(d["close"])))
        return s

    def outcome(self):
        card = self.end_card()
        return {**super().outcome(), "scene": self.sc.name, "head": card.head, "sub": card.sub,
                "hook": self.title, "winner": self.match_ctx.get("winner")}

    def sounds(self) -> SoundBank:
        lands = [tone(220 * 2 ** (k / 12), 0.25, 14, harm=0.5, noise=0.3) * 0.35 for k in (0, 3, 5, 7, 10, 12, 15, 17)]
        reveal = np.zeros(int(SR * 1.8), dtype=np.float32)
        for s, d in ((0, 0), (7, 0.1), (12, 0.2), (16, 0.3)):
            note = tone(392 * 2 ** (s / 12), 1.4, 3, harm=0.2)
            reveal[int(SR * d):int(SR * d) + len(note)] += note
        return {"swallow": overlay((0, tone(70, 1.2, 3, harm=0.8, noise=0.2, chirp=-0.5) * 0.6),
                                   (0, tone(900, 0.4, 8, chirp=-0.8) * 0.15)),
                "merge": tone(160, 0.35, 10, harm=0.6, noise=0.4) * 0.4,
                "land": lands, "reveal": reveal * 0.3}

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        pg = self.pg
        rng = random.Random(f"sky:{self.seed}")
        bg = pg.Surface((W, H))
        if self.sc.background == "sky":
            for y in range(H):
                k = y / H
                bg.fill((int(40 + 90 * k), int(90 + 100 * k), int(170 + 60 * k)), (0, y, W, 1))
        else:
            for y in range(H):
                k = y / H
                bg.fill((int(4 + 8 * k), int(5 + 6 * k), int(16 + 14 * k)), (0, y, W, 1))
            for _ in range(420):
                b = rng.choice([90, 140, 200, 255])
                pg.draw.circle(bg, (b, b, min(255, b + 20)), (rng.uniform(0, W), rng.uniform(0, H)),
                               rng.choice([1, 1, 1, 2]))
        self.bg = bg
        self.bg_arr = pg.surfarray.array3d(bg)
        self.glows: dict = {}
        self.disk = [(rng.uniform(0, 2 * math.pi), rng.uniform(1.6, 3.6), rng.choice([(255, 170, 60), (255, 220, 140),
                                                                                       (255, 120, 40)]))
                     for _ in range(160)]
        self.labels = [outlined(pg, self.fonts.small, b.name, b.colour, 2) for b in self.sc.bodies]
        self.eq = outlined(pg, self.fonts.mid, self.sc.equation, (230, 230, 245), 3) if self.sc.equation else None

    def glow_sprite(self, r: int, col):
        key = (r, col)
        if key not in self.glows:
            yy, xx = np.mgrid[-r:r, -r:r]
            i = np.clip(1 - np.sqrt(xx * xx + yy * yy) / max(r, 1), 0, 1) ** 2.2
            arr = (np.array(col)[None, None, :] * i[..., None] * 0.9).astype(np.uint8)
            self.glows[key] = self.pg.surfarray.make_surface(arr.transpose(1, 0, 2).copy())
        return self.glows[key]

    def camera(self) -> tuple[float, float, float]:
        """(centre x, centre y, pixels per unit), following the bodies if the scene asks."""
        v = self.sc.view
        band_h = VIEW_BOTTOM - VIEW_TOP
        if not v.get("follow"):
            scale = (ARENA_R - ARENA_L) / float(v.get("width", 1000))
            cx, cy = v.get("centre", (0, 0))
            return float(cx), float(cy), scale
        w = self.world
        live = w.alive & ~w.holes
        pts = w.pos[live] if live.any() else w.pos
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        width = max(float(v.get("min_width", 600)), (hi[0] - lo[0]) * 1.35, (hi[1] - lo[1]) * 1.35 *
                    (ARENA_R - ARENA_L) / band_h)
        width = min(width, float(v.get("max_width", 4000)))
        target = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, width])
        if w.s.ground is not None:                       # keep the ground near the bottom of the frame
            k = (ARENA_R - ARENA_L) / width
            target[1] = w.s.ground + (band_h / 2 - 90) / k
        self.cam = target if self.cam is None else self.cam + (target - self.cam) * 0.06
        return float(self.cam[0]), float(self.cam[1]), (ARENA_R - ARENA_L) / float(self.cam[2])

    def to_screen(self, p, cam) -> tuple[float, float]:
        cx, cy, k = cam
        return (W / 2 + (p[0] - cx) * k, (VIEW_TOP + VIEW_BOTTOM) / 2 - (p[1] - cy) * k)

    def lens(self, screen, centre, horizon_px: float) -> None:
        """Bend the starlight around a black hole and leave a dark shadow in the middle."""
        hx, hy = centre
        R = int(min(320, max(70, horizon_px * 9)))
        x0, x1 = max(0, int(hx - R)), min(W, int(hx + R))
        y0, y1 = max(0, int(hy - R)), min(H, int(hy + R))
        if x0 >= x1 or y0 >= y1:
            return
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        dx, dy = xs - hx, ys - hy
        d = np.sqrt(dx * dx + dy * dy) + 1e-6
        theta = horizon_px * 2.4
        fade = np.clip((R - d) / (0.35 * R), 0, 1)
        src = np.maximum(d - fade * theta * theta / d, 0)
        sx = np.clip((hx + dx * src / d).astype(int), 0, W - 1)
        sy = np.clip((hy + dy * src / d).astype(int), 0, H - 1)
        region = self.bg_arr[sx, sy]
        region[d < horizon_px * 1.15] = 0
        px = self.pg.surfarray.pixels3d(screen)
        px[x0:x1, y0:y1] = region
        del px

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        w = self.world
        screen.blit(self.bg, (0, 0))
        cam = self.camera()
        k = cam[2]
        if w.s.ground is not None:
            gy = self.to_screen((0, w.s.ground), cam)[1]
            pg.draw.rect(screen, (70, 120, 60), (0, gy, W, H - gy))
            pg.draw.rect(screen, (110, 170, 90), (0, gy, W, 6))
        for i in np.flatnonzero(w.holes & w.alive):
            self.lens(screen, self.to_screen(w.pos[i], cam), w.horizon[i] * k)
        self.draw_sweep(screen, cam)
        for i, b in enumerate(self.sc.bodies):
            if not b.trail:
                continue
            if w.alive[i]:
                self.trails[i].append(tuple(w.pos[i]))
                del self.trails[i][:-b.trail]
            pts = [self.to_screen(p, cam) for p in self.trails[i]]
            if len(pts) > 1:
                n = len(pts)
                for c in range(4):                                     # fade the tail in 4 chunks
                    seg = pts[c * n // 4: (c + 1) * n // 4 + 1]
                    if len(seg) > 1:
                        col = tuple(int(v * (0.25 + 0.2 * c)) for v in b.colour)
                        pg.draw.lines(screen, col, False, seg, 2 + c // 2)
        for i in np.flatnonzero(w.holes & w.alive):
            self.draw_hole(screen, self.to_screen(w.pos[i], cam), w.horizon[i] * k, t)
        for i, b in enumerate(self.sc.bodies):
            if not w.alive[i] or b.kind == "black_hole":
                continue
            x, y = self.to_screen(w.pos[i], cam)
            r = max(3, int(w.radius[i] * k))
            if b.glow:
                g = self.glow_sprite(int(r * (1 + b.glow)), b.colour)
                screen.blit(g, (x - g.get_width() / 2, y - g.get_height() / 2), special_flags=pg.BLEND_ADD)
            pg.draw.circle(screen, b.colour, (x, y), r)
            for j in np.flatnonzero(w.holes & w.alive):                # being pulled apart near a hole
                hd = w.distance(i, int(j))
                if hd < w.horizon[j] * 7 and self.fx.enabled:
                    hx, hy = self.to_screen(w.pos[j], cam)
                    for f in range(3):
                        u = self.fx.rng.random()
                        self.fx.particles.append([x + (hx - x) * u * 0.6, y + (hy - y) * u * 0.6, 0, 150,
                                                  0.25, b.colour])
            if b.label or w.landed[i]:
                lab = self.labels[i]
                screen.blit(lab, lab.get_rect(midbottom=(x, y - r - 6)))
            if w.landed[i]:
                pg.draw.line(screen, b.colour, (x, y), (x, y + 30), 3)
        if self.eq:
            screen.blit(self.eq, self.eq.get_rect(center=(W / 2, VIEW_TOP - 20)))
        self.fx.draw_particles(screen)

    def draw_hole(self, screen, centre, hpx: float, t: float) -> None:
        pg = self.pg
        hx, hy = centre
        g = self.glow_sprite(int(max(12, hpx * 3.2)), (255, 150, 60))
        screen.blit(g, (hx - g.get_width() / 2, hy - g.get_height() / 2), special_flags=pg.BLEND_ADD)
        for a0, rr, col in self.disk:                                  # accretion disc, tilted
            a = a0 + t * 3.0 / rr ** 1.5
            x = hx + math.cos(a) * rr * hpx
            y = hy + math.sin(a) * rr * hpx * 0.32
            pg.draw.circle(screen, col, (x, y), max(1, int(hpx * 0.12)))
        pg.draw.circle(screen, (0, 0, 0), (hx, hy), max(3, int(hpx)))
        pg.draw.circle(screen, (255, 210, 150), (hx, hy), max(4, int(hpx * 1.12)), max(1, int(hpx * 0.12)))

    def draw_sweep(self, screen, cam) -> None:
        sw = self.sc.sweep
        if not sw or len(self.sweep_pts) < 2:
            return
        every = float(sw.get("every", 3))
        layer = self.pg.Surface((W, H), self.pg.SRCALPHA)
        groups: dict[int, list] = {}
        for tt, p, c in self.sweep_pts:
            groups.setdefault(int(tt // every), []).append((p, c))
        for n, pts in groups.items():
            if len(pts) < 2 or n % 2:
                continue
            poly = [self.to_screen(pts[0][1], cam)] + [self.to_screen(p, cam) for p, _ in pts]
            col = (255, 214, 64, 70) if (n // 2) % 2 else (90, 200, 255, 70)
            self.pg.draw.polygon(layer, col, poly)
        screen.blit(layer, (0, 0))
