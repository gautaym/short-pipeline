"""A puppet theatre for story reels: cut-out puppets moved on a painted stage.

Each beat's `stage` names a backdrop, the puppets on stage and the effects:

    stage:
      backdrop: ocean
      fx: [waves, spray]
      actors:
        deva: {puppet: deva_pull, x: 200, y: 1560, h: 700, face: right, motion: pull, enter: left}

x is the puppet's centre, y the bottom of its stick, h its height in pixels. An actor that was on
stage in the last beat glides to its new mark (and turns, squashing through edge-on like a puppet
being flipped, when its facing changes); a new one enters (left, right, bottom or fade); one that is
gone fades away, unless it was given `exit: left|right|fade`, in which case it leaves during its
own beat. Motions are what the puppeteer's hand does: sway, pull, churn, tremble, run, walk_in,
drink, breathe. Everything is a function of time, so any frame can be drawn on its own.

Story-level `art.anchors` mark points on a puppet picture as fractions of its width and height,
e.g. {shiva_blue: {throat: [0.56, 0.17]}}; the throat glow and the poison that flows into the
bowl use them.
"""
import math
import random

import numpy as np

from ..core.canvas import H, W
from . import art

MOVE_S = 1.0          # gliding to a new mark
ENTER_S = 1.3         # sliding on stage
FADE_S = 0.8          # fading in or out
TURN_S = 0.45         # flipping to face the other way
BACKDROP_ROOM = 1.08  # backdrops are scaled past the frame so they can drift
PIVOT = 0.62          # puppets rock about the hand that holds them, this far down from the top


def ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def soft_blob(pg, radius: int, colour) -> object:
    """A round sprite fading from `colour` at the centre to clear at the edge."""
    size = radius * 2
    x = (np.arange(size) - radius + 0.5) / radius
    d = np.sqrt(x[:, None] ** 2 + x[None, :] ** 2)
    surf = pg.Surface((size, size), pg.SRCALPHA)
    surf.fill(colour[:3])
    pg.surfarray.pixels_alpha(surf)[:] = (np.clip(1 - d, 0, 1) ** 1.8 * colour[3]).astype(np.uint8)
    return surf


def light(pg, radius: int, colour, strength: float = 1.0) -> object:
    """A round light for additive blending: colour at the centre falling to black (no alpha)."""
    size = radius * 2
    x = (np.arange(size) - radius + 0.5) / radius
    d = np.sqrt(x[:, None] ** 2 + x[None, :] ** 2)
    fall = np.clip(1 - d, 0, 1) ** 2 * strength
    surf = pg.Surface((size, size))
    pg.surfarray.pixels3d(surf)[:] = (fall[..., None] * np.array(colour[:3])).astype(np.uint8)
    return surf


def dimmed(pg, surf, level: float):
    """A copy of an additive light at `level` (0-1) of its brightness."""
    v = max(0, min(255, int(255 * level)))
    out = surf.copy()
    out.fill((v, v, v), special_flags=pg.BLEND_RGB_MULT)
    return out


class Theatre:
    @classmethod
    def load(cls, pg, sc: dict, seed: int):
        """The theatre for a story, or None until every puppet and backdrop it uses is drawn."""
        if "art" not in sc or not all("stage" in b for b in sc["beats"]):
            return None
        sid = sc["id"]
        puppets = {a["puppet"] for b in sc["beats"] for a in b["stage"].get("actors", {}).values()}
        backdrops = {b["stage"]["backdrop"] for b in sc["beats"]}
        if not all(art.puppet_file(sid, p).exists() for p in puppets):
            return None
        if not all(art.backdrop_file(sid, b).exists() for b in backdrops):
            return None
        return cls(pg, sc, seed, puppets, backdrops)

    def __init__(self, pg, sc: dict, seed: int, puppets: set, backdrops: set):
        self.pg, self.sc, self.seed = pg, sc, seed
        self.beats = [b["stage"] for b in sc["beats"]]
        self.anchors = sc["art"].get("anchors", {})
        self.puppets = {p: art.cut(pg, sc["id"], p) for p in puppets}
        size = (int(W * BACKDROP_ROOM), int(H * BACKDROP_ROOM))
        self.backdrops = {b: pg.transform.smoothscale(pg.image.load(str(art.backdrop_file(sc["id"], b))), size)
                          for b in backdrops}
        self.sized: dict[tuple, tuple] = {}
        r = random.Random(f"theatre:{seed}")
        self.phase = {name: r.uniform(0, 6.3) for b in self.beats for name in b.get("actors", {})}
        self.smoke = [soft_blob(pg, 120, c) for c in ((90, 40, 130, 150), (40, 16, 60, 170), (150, 80, 200, 110))]
        self.foam = soft_blob(pg, 26, (250, 248, 236, 200))
        self.glow_blue = light(pg, 120, (90, 200, 255), 1.5)       # cyan: plain blue would vanish on blue skin
        self.mote = soft_blob(pg, 6, (255, 220, 160, 200))
        self.motes = [(r.uniform(0, W), r.uniform(0, H), r.uniform(10, 34), r.uniform(0, 6.3)) for _ in range(40)]
        self.rays = self.make_rays()
        self.lamp = light(pg, 900, (255, 200, 130), 0.16)

    # ---------------------------------------------------------- pictures
    def sized_puppet(self, name: str, h: int):
        """The puppet scaled to height h, with its soft shadow; cached by size."""
        key = (name, h)
        if key not in self.sized:
            src = self.puppets[name]
            w = max(1, round(src.get_width() * h / src.get_height()))
            img = self.pg.transform.smoothscale(src, (w, h))
            shadow = img.copy()
            shadow.fill((0, 0, 0, 255), special_flags=self.pg.BLEND_RGBA_MIN)
            shadow.fill((255, 255, 255, 110), special_flags=self.pg.BLEND_RGBA_MULT)
            small = self.pg.transform.smoothscale(shadow, (max(1, w // 8), max(1, h // 8)))
            shadow = self.pg.transform.smoothscale(small, (w, h))          # blurred by scaling down and up
            self.sized[key] = (img, shadow)
        if len(self.sized) > 40:                                           # keep memory bounded
            self.sized.pop(next(iter(self.sized)))
        return self.sized[key]

    def make_rays(self):
        surf = self.pg.Surface((W, H))                                    # black: drawn additively
        for k in range(7):
            a = math.radians(-35 + k * 11)
            top = (W * 0.5 + 60 * math.sin(k), -200)
            length = H * 1.4
            spread = math.radians(2.6)
            pts = [top, (top[0] + length * math.sin(a - spread), top[1] + length * math.cos(a - spread)),
                   (top[0] + length * math.sin(a + spread), top[1] + length * math.cos(a + spread))]
            self.pg.draw.polygon(surf, (40, 32, 20), pts)
        return surf

    # ---------------------------------------------------------- where each puppet is
    def mark(self, beat: int, name: str) -> dict | None:
        spec = self.beats[beat].get("actors", {}).get(name) if 0 <= beat < len(self.beats) else None
        if spec is None:
            return None
        return {"puppet": spec["puppet"], "x": float(spec.get("x", W / 2)), "y": float(spec.get("y", 1560)),
                "h": float(spec.get("h", 900)), "face": 1 if spec.get("face", "right") == "right" else -1,
                "motion": spec.get("motion", "sway"), "enter": spec.get("enter", "fade"),
                "exit": spec.get("exit")}

    def actor_state(self, beat: int, name: str, since: float, length: float) -> dict | None:
        """Where the actor is `since` seconds into the beat: position, size, facing, opacity."""
        now, before = self.mark(beat, name), self.mark(beat - 1, name)
        if now is None:                                          # gone: fade out where it was
            if before is None or before["exit"] or since > FADE_S:
                return None
            return {**before, "alpha": 1 - since / FADE_S, "sx": float(before["face"]), "old": None, "mix": 1.0}
        s = dict(now, alpha=1.0, old=None, mix=1.0)
        if before is not None and not before["exit"]:            # glide from the last mark
            k = ease(since / MOVE_S)
            for key in ("x", "y", "h"):
                s[key] = before[key] + (now[key] - before[key]) * k
            if before["puppet"] != now["puppet"]:
                s["old"], s["mix"] = before["puppet"], ease(since / 0.5)
            turn = ease(since / TURN_S) if before["face"] != now["face"] else 1.0
            s["sx"] = before["face"] + (now["face"] - before["face"]) * turn
        else:                                                    # enter
            s["sx"] = float(now["face"])
            k = ease(since / (ENTER_S if now["enter"] in ("left", "right", "bottom") else FADE_S))
            if now["enter"] == "left":
                s["x"] = -now["h"] * 0.4 + (now["x"] + now["h"] * 0.4) * k
            elif now["enter"] == "right":
                s["x"] = W + now["h"] * 0.4 + (now["x"] - W - now["h"] * 0.4) * k
            elif now["enter"] == "bottom":
                s["y"] = now["y"] + now["h"] * (1 - k)
            else:
                s["alpha"] = k
            s["moving"] = k < 1
        if now["exit"]:                                          # leave during this beat
            k = ease((since / max(0.1, length) - 0.35) / 0.6)
            if now["exit"] == "left":
                s["x"] += (-now["h"] * 0.5 - s["x"]) * k
            elif now["exit"] == "right":
                s["x"] += (W + now["h"] * 0.5 - s["x"]) * k
            else:
                s["alpha"] *= 1 - k
            s["moving"] = s.get("moving") or 0 < k < 1
        return s

    def motion(self, s: dict, name: str, since: float, length: float, t: float) -> tuple[float, float, float, float]:
        """The puppeteer's hand: (dx, dy, degrees of tilt, extra scale)."""
        ph = self.phase.get(name, 0.0)
        face = 1 if s["sx"] >= 0 else -1
        dx, dy = 0.0, 3 * math.sin(t * 1.9 + ph)
        rot = 1.2 * math.sin(t * 1.3 + ph)                       # a hand is never quite still
        scale = 1.0
        m = s["motion"]
        if m == "pull":                                          # heave on the rope, ease off, heave again
            heave = 0.5 + 0.5 * math.sin(t * 2.6 + ph)
            rot += face * 9 * heave
            dx -= face * 26 * heave
        elif m == "churn":                                       # the mountain rocks and spins
            rot += 4 * math.sin(t * 1.5)
            dx += 24 * math.sin(t * 1.5)
            s["sx"] *= 0.86 + 0.14 * math.cos(t * 2.2)
        elif m == "tremble":
            rot += 2.2 * math.sin(t * 27 + ph)
            dx += 5 * math.sin(t * 33 + ph)
        elif m == "run":
            rot -= face * 8 - 4 * math.sin(t * 9 + ph)
            dy -= abs(math.sin(t * 9 + ph)) * 30
        elif m == "walk_in":
            if s.get("moving"):
                dy -= abs(math.sin(t * 6.5 + ph)) * 20
                rot += 3 * math.sin(t * 6.5 + ph)
        elif m == "drink":                                       # tip the head back as he drinks
            k = ease(since / max(0.5, length * 0.7))
            rot += face * 7 * k
            dy -= 18 * k
        elif m == "breathe":
            scale += 0.014 * math.sin(t * 1.4 + ph)
        return dx, dy, rot, scale

    def anchor(self, s: dict, puppet: str, point: str, t: float, since: float, length: float, name: str):
        """A marked point on an actor's puppet, in screen pixels (None if not marked)."""
        frac = self.anchors.get(puppet, {}).get(point)
        if frac is None or s is None:
            return None
        dx, dy, rot, scale = self.motion(dict(s), name, since, length, t)
        h = s["h"] * scale
        src = self.puppets[puppet]
        w = src.get_width() * h / src.get_height()
        px, py = s["x"] + dx, s["y"] + dy - h * (1 - PIVOT)      # the pivot
        ax = (frac[0] - 0.5) * w * (1 if s["sx"] >= 0 else -1) * abs(s["sx"])
        ay = frac[1] * h - h * PIVOT
        a = math.radians(rot)
        return px + ax * math.cos(a) + ay * math.sin(a), py - ax * math.sin(a) + ay * math.cos(a)

    # ---------------------------------------------------------- drawing
    def draw_puppet(self, screen, puppet: str, s: dict, dx: float, dy: float, rot: float, scale: float, alpha: float):
        pg = self.pg
        h = max(8, int(s["h"] * scale))
        img, shadow = self.sized_puppet(puppet, h)
        sx = s["sx"]
        w = max(2, int(img.get_width() * abs(sx)))
        if w != img.get_width():
            img, shadow = pg.transform.smoothscale(img, (w, h)), pg.transform.smoothscale(shadow, (w, h))
        if sx < 0:
            img, shadow = pg.transform.flip(img, True, False), pg.transform.flip(shadow, True, False)
        if abs(rot) > 0.05:
            img, shadow = pg.transform.rotozoom(img, -rot, 1.0), pg.transform.rotozoom(shadow, -rot, 1.0)
        px, py = s["x"] + dx, s["y"] + dy - h * (1 - PIVOT)      # rotate about the hand holding the stick
        off = h * PIVOT - h / 2
        a = math.radians(rot)
        cx, cy = px - off * math.sin(a), py - off * math.cos(a)
        if alpha < 0.99:
            img, shadow = img.copy(), shadow.copy()
            img.set_alpha(int(255 * alpha))
            shadow.set_alpha(int(255 * alpha))
        screen.blit(shadow, shadow.get_rect(center=(cx + 22, cy + 14)))
        screen.blit(img, img.get_rect(center=(cx, cy)))

    def draw_backdrop(self, screen, beat: int, since: float, t: float, shake: tuple[float, float]) -> None:
        def place(name, alpha):
            img = self.backdrops[name]
            ox = (img.get_width() - W) / 2 + 22 * math.sin(t * 0.11) + shake[0] * 0.5
            oy = (img.get_height() - H) / 2 + 14 * math.sin(t * 0.07) + shake[1] * 0.5
            if alpha < 0.99:
                img = img.copy()
                img.set_alpha(int(255 * alpha))
            screen.blit(img, (-ox, -oy))
        now = self.beats[beat]["backdrop"]
        place(now, 1.0)
        if beat > 0 and self.beats[beat - 1]["backdrop"] != now and since < 0.9:
            place(self.beats[beat - 1]["backdrop"], 1 - ease(since / 0.9))

    def fx(self, beat: int) -> list[str]:
        return list(self.beats[beat].get("fx", []))

    def draw(self, screen, beat: int, since: float, length: float, t: float, opening: bool = False) -> None:
        pg = self.pg
        fx = self.fx(beat)
        shake = (0.0, 0.0)
        if "shake" in fx and not opening:
            amp = 18 * max(0.15, 1 - since / 1.6)
            shake = (amp * math.sin(t * 41), amp * math.cos(t * 37))
        self.draw_backdrop(screen, beat, since, t, shake)
        screen.blit(self.lamp, self.lamp.get_rect(center=(W / 2, H * 0.36)), special_flags=pg.BLEND_RGB_ADD)
        if "rays" in fx:
            rays = dimmed(pg, self.rays, 0.75 + 0.25 * math.sin(t * 0.8))
            screen.blit(rays, (0, 0), special_flags=pg.BLEND_RGB_ADD)
        if "smoke_far" in fx:
            self.draw_smoke(screen, t, base=1100, spread=520, rise=700, n=14, strength=0.55)
        if "smoke" in fx:
            self.draw_smoke(screen, t, base=1380, spread=380, rise=1100, n=26, strength=1.0,
                            grow=ease(since / 2.5) if beat == 0 or "smoke" not in self.fx(beat - 1) else 1.0)
        if "waves" in fx:
            self.draw_waves(screen, t, back=True)
        names = list(dict.fromkeys(list(self.beats[beat].get("actors", {}))
                                   + (list(self.beats[beat - 1].get("actors", {})) if beat > 0 else [])))
        states = {}
        if not opening:
            for name in names:
                s = self.actor_state(beat, name, since, length)
                if s is not None:
                    states[name] = s
        for name in sorted(states, key=lambda n: states[n]["h"]):    # bigger puppets nearer the screen
            s = states[name]
            dx, dy, rot, scale = self.motion(s, name, since, length, t)
            dx, dy = dx + shake[0], dy + shake[1]
            if s["old"] and s["mix"] < 1:
                self.draw_puppet(screen, s["old"], s, dx, dy, rot, scale, s["alpha"] * (1 - s["mix"]))
            self.draw_puppet(screen, s["puppet"], s, dx, dy, rot, scale, s["alpha"] * (s["mix"] if s["old"] else 1))
        if "smoke_in" in fx and "shiva" in states:
            to = self.anchor(states["shiva"], states["shiva"]["puppet"], "bowl", t, since, length, "shiva")
            if to:
                self.draw_inflow(screen, t, to, strength=1 - ease((since - length * 0.6) / (length * 0.3)))
        if "throat_glow" in fx and "shiva" in states:
            at = self.anchor(states["shiva"], states["shiva"]["puppet"], "throat", t, since, length, "shiva")
            if at:
                g = dimmed(pg, self.glow_blue, 0.65 + 0.35 * math.sin(t * 2.4))
                screen.blit(g, g.get_rect(center=at), special_flags=pg.BLEND_RGB_ADD)
        if "waves" in fx:
            self.draw_waves(screen, t, back=False)
        if "spray" in fx:
            self.draw_spray(screen, t)
        for x, y, speed, ph in self.motes:                            # dust in the lamp light
            m = self.mote.copy()
            m.set_alpha(int(90 + 80 * math.sin(t * 1.7 + ph)))
            screen.blit(m, (x + 14 * math.sin(t * 0.6 + ph), (y - speed * t) % H))
        dim = pg.Surface((W, H))
        lamp = 0.5 + 0.5 * math.sin(t * 2.3) * math.sin(t * 0.7 + 1.3)  # an oil lamp's slow flicker
        dim.set_alpha(int(8 + 20 * lamp + (110 if opening else 0)))
        screen.blit(dim, (0, 0))

    # ---------------------------------------------------------- effects
    def draw_smoke(self, screen, t: float, base: float, spread: float, rise: float, n: int, strength: float,
                   grow: float = 1.0) -> None:
        """Poison billowing up from the water: n puffs, each rising, swelling and thinning in turn."""
        for k in range(n):
            p = (t / 7.0 + k / n) % 1.0
            x = W / 2 + spread * math.sin(k * 12.9898) * (0.4 + 0.6 * p) + 40 * math.sin(t * 0.5 + k)
            y = base - rise * p * grow
            size = int(140 + 330 * p)
            puff = self.pg.transform.smoothscale(self.smoke[k % 3], (size, size))
            puff.set_alpha(int(255 * strength * grow * math.sin(math.pi * p) ** 0.8))
            screen.blit(puff, puff.get_rect(center=(x, y)))

    def draw_inflow(self, screen, t: float, to: tuple[float, float], strength: float) -> None:
        """Poison drawn in from all around into one point (the bowl)."""
        if strength <= 0:
            return
        for k in range(22):
            p = (t / 2.2 + k / 22) % 1.0
            a = k * 2.399
            r = 620 * (1 - p)
            x, y = to[0] + r * math.cos(a + p * 1.5), to[1] + r * math.sin(a + p * 1.5) * 0.8
            size = int(40 + 170 * (1 - p))
            puff = self.pg.transform.smoothscale(self.smoke[k % 3], (size, size))
            puff.set_alpha(int(220 * strength * math.sin(math.pi * p)))
            screen.blit(puff, puff.get_rect(center=(x, y)))

    def draw_waves(self, screen, t: float, back: bool) -> None:
        """Rolling bands of milk-white sea; the back ones behind the puppets, the front ones over them."""
        rows = (1300, 1380, 1460) if back else (1540, 1620)
        for r, y0 in enumerate(rows):
            amp, length, speed = 16 + 6 * r, 210 - 20 * r, (0.9 + 0.3 * r) * (1 if r % 2 else -1)
            pts = [(x, y0 + amp * math.sin(x / length * 6.283 + t * speed * 2 + r)) for x in range(-20, W + 41, 20)]
            body = pts + [(W + 40, H), (-20, H)]
            shade = 228 - 26 * r if back else 196 - 20 * r
            layer = self.pg.Surface((W, H), self.pg.SRCALPHA)
            self.pg.draw.polygon(layer, (shade, shade, shade - 14, 200 if back else 235), body)
            self.pg.draw.lines(layer, (255, 255, 250, 255), False, pts, 5)
            screen.blit(layer, (0, 0))

    def draw_spray(self, screen, t: float) -> None:
        for k in range(28):
            p = (t / 1.4 + k / 28) % 1.0
            side = -1 if k % 2 else 1
            x = W / 2 + side * (60 + 260 * p + 30 * math.sin(k))
            y = 1420 - 380 * p + 520 * p * p
            f = self.foam.copy()
            f.set_alpha(int(230 * (1 - p)))
            screen.blit(f, f.get_rect(center=(x, y)))
