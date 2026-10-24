#!/usr/bin/env python3
"""
brickreel.py — auto-playing 2D brick-breaker reels in four formats, rendered as 9:16 MP4.

Modes
  classic  1 ball vs a brick shape (heart, star, a word...); power-up bricks spawn more balls
  escape   the ball starts trapped inside a carved maze lined with unbreakable grey bricks;
           the hook is whether, and where, it breaks out to the top
  boss     a giant block with a big HP counter, ringed by power-up bricks
  wars     colour territories battle it out, each ball converts the other teams' bricks;
           "which colour wins?"

Every run is seeded, so each reel gets a fresh layout, palette and outcome.

Requirements:  pip install pygame numpy      (plus ffmpeg on PATH)

Usage:
    python brickreel.py                              # random mode and layout
    python brickreel.py --mode escape --shape spiral
    python brickreel.py --mode wars --teams 4
    python brickreel.py --mode boss --boss-hp 999
    python brickreel.py --mode classic --shape text --text 2026
    python brickreel.py --batch 8                    # eight different reels
    python brickreel.py --mode escape --preview      # watch it live, no file
"""
import argparse
import colorsys
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np

# ------------------------------------------------------------------ layout
W, H = 1080, 1920
FPS = 30
SUBSTEPS = 4

ARENA_L, ARENA_R = 40, W - 40
ARENA_T = 340
LOST_Y = H - 40

PADDLE_Y = 1700
PADDLE_W = 230
PADDLE_H = 24
PADDLE_SPEED = 1700.0

BALL_R = 10
MAX_BALLS = 220

INTRO_S = 1.2
OUTRO_S = 2.8
SR = 44100

WALL = (172, 174, 184)
WALL_HI = (215, 217, 226)

SHAPES = ["heart", "circle", "diamond", "star", "ring", "text"]
TEXT_WORDS = ["2026", "WIN", "GO", "BOOM", "LOL", "OK"]

TEAM_COLOURS = [("PINK", (255, 80, 160)), ("CYAN", (40, 200, 255)), ("LIME", (140, 230, 60)),
                ("ORANGE", (255, 150, 40)), ("PURPLE", (160, 100, 255)), ("YELLOW", (250, 215, 40))]
ESCAPE_FILLS = [(250, 215, 40), (60, 220, 255), (255, 110, 170), (150, 235, 80),
                (255, 160, 60), (190, 140, 255)]


def _font_path():
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/Library/Fonts/Arial Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(p):
            return p
    return None   # pygame's default font


# ------------------------------------------------------------------ classic shapes
def _uv(cols, rows):
    """Normalised cell centres: u to the right, v upwards, both in [-1, 1]."""
    cs = (np.arange(cols) + 0.5) / cols * 2 - 1
    rs = (np.arange(rows) + 0.5) / rows * 2 - 1
    u, v = np.meshgrid(cs, rs)
    return u, -v


def _poly_mask(u, v, pts):
    inside = np.zeros(u.shape, dtype=bool)
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        cond = (y1 > v) != (y2 > v)
        xcross = (x2 - x1) * (v - y1) / (y2 - y1 + 1e-12) + x1
        inside ^= cond & (u < xcross)
    return inside


def shape_mask(name, text, pg, cols, rows):
    u, v = _uv(cols, rows)
    if name == "heart":
        x, y = u * 1.25, v * 1.25 + 0.15
        return (x * x + y * y - 1) ** 3 - x * x * y ** 3 <= 0
    if name == "circle":
        return u * u + v * v <= 0.96 ** 2
    if name == "ring":
        r2 = u * u + v * v
        return (r2 <= 0.98 ** 2) & (r2 >= 0.48 ** 2)
    if name == "diamond":
        return np.abs(u) + np.abs(v) <= 1.0
    if name == "star":
        pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            r = 1.0 if k % 2 == 0 else 0.42
            pts.append((r * math.cos(a), r * math.sin(a) - 0.06))
        return _poly_mask(u, v, pts)
    if name == "text":
        font = pg.font.Font(_font_path(), 200)
        surf = font.render(text, True, (255, 255, 255))
        sw, sh = surf.get_size()
        scale = min(cols / sw, (rows * 0.7) / sh)
        tw, th = max(1, int(sw * scale)), max(1, int(sh * scale))
        small = pg.transform.smoothscale(surf, (tw, th))
        alpha = pg.surfarray.array_alpha(small).T > 110
        mask = np.zeros((rows, cols), dtype=bool)
        r0, c0 = (rows - th) // 2, (cols - tw) // 2
        mask[r0:r0 + th, c0:c0 + tw] = alpha
        return mask
    raise ValueError(f"unknown shape {name}")


# ------------------------------------------------------------------ escape mazes
# Each maze is a list of strokes (polylines in normalised u/v space) plus the
# point where the ball starts. Strokes reaching v < -1 open into the paddle area.
def _spiral():
    pts = [(0.0, -1.2), (0.0, -0.72)]
    turns, steps = 1.85, 90
    for i in range(1, steps + 1):
        k = i / steps
        a = -math.pi / 2 - k * turns * 2 * math.pi
        r = 0.72 - k * 0.58
        pts.append((r * math.cos(a), r * math.sin(a)))
    return [pts], pts[-1]


MAZES = {
    "trident": lambda: ([[(-0.72, 0.55), (0.72, 0.55)], [(0, 0.55), (0, -1.2)],
                         [(-0.1, 0.45), (-0.72, -0.2)], [(0.1, 0.45), (0.72, -0.2)]], (0, 0.55)),
    "arrow": lambda: ([[(0, -1.2), (0, 0.6)], [(-0.55, 0.05), (0, 0.62), (0.55, 0.05)]], (0, 0.5)),
    "zigzag": lambda: ([[(0, -1.2), (0, -0.65), (-0.65, -0.3), (0.65, 0.05), (-0.65, 0.4), (0.45, 0.68)]],
                       (0.45, 0.68)),
    "tree": lambda: ([[(0, -1.2), (0, 0.62)], [(0, -0.15), (-0.62, 0.3)], [(0, -0.15), (0.62, 0.3)],
                      [(0, 0.25), (-0.42, 0.6)], [(0, 0.25), (0.42, 0.6)]], (0, 0.62)),
    "lightning": lambda: ([[(0, -1.2), (0.05, -0.55), (-0.38, -0.2), (0.32, 0.18), (-0.12, 0.66)]],
                          (-0.12, 0.66)),
    "plus": lambda: ([[(0, -1.2), (0, 0.65)], [(-0.68, 0.12), (0.68, 0.12)]], (0, 0.65)),
    "box": lambda: ([[(0, -1.2), (0, -0.45)],
                     [(-0.58, -0.45), (0.58, -0.45), (0.58, 0.55), (-0.58, 0.55), (-0.58, -0.45)]],
                    (0, 0.55)),
    "spiral": _spiral,
}


# ------------------------------------------------------------------ sound
PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28]


def _tone(freq, dur, decay, harm=0.3, noise=0.0, chirp=0.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = freq * (1 + chirp * t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    w = np.sin(phase) + harm * np.sin(2 * phase)
    if noise:
        w += noise * np.random.default_rng(1).uniform(-1, 1, n)
    env = np.exp(-t * decay)
    att = min(n, int(0.003 * SR))
    env[:att] *= np.linspace(0, 1, att)
    return (w * env).astype(np.float32)


def build_sound_bank():
    bank = {}
    for i, k in enumerate(PENTA):
        f = 523.25 * 2 ** (k / 12)
        bank[("hit", i)] = _tone(f, 0.09, 45) * 0.35
        bank[("break", i)] = _tone(f * 1.5, 0.14, 30, harm=0.5, noise=0.15) * 0.4
    bank[("paddle", 0)] = _tone(196, 0.12, 25, harm=0.6) * 0.5
    bank[("wall", 0)] = _tone(1480, 0.05, 70, harm=0.1) * 0.18
    bank[("boss", 0)] = _tone(98, 0.16, 22, harm=0.8, noise=0.1) * 0.45
    bank[("power", 0)] = _tone(440, 0.35, 8, harm=0.4, chirp=1.5) * 0.55
    bank[("lost", 0)] = _tone(150, 0.25, 12, chirp=-0.5) * 0.3
    clear = np.zeros(int(SR * 1.7), dtype=np.float32)
    for s, d in ((0, 0), (4, 0.08), (7, 0.16), (12, 0.24)):
        note = _tone(523.25 * 2 ** (s / 12), 1.4, 3)
        a = int(SR * d)
        clear[a:a + len(note)] += note
    bank[("clear", 0)] = clear * 0.35
    bank[("fail", 0)] = _tone(220, 1.0, 3, chirp=-0.4) * 0.4
    return bank


def render_audio(events, duration, path):
    bank = build_sound_bank()
    audio = np.zeros(int(SR * duration) + SR * 2, dtype=np.float32)
    for t, kind, idx in events:
        s = bank[(kind, idx % len(PENTA) if kind in ("hit", "break") else 0)]
        a = int(t * SR)
        b = min(len(audio), a + len(s))
        audio[a:b] += s[: b - a]
    audio = np.tanh(audio * 1.3) * 0.85
    pcm = (audio[: int(SR * duration)] * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# ------------------------------------------------------------------ core game
class Ball:
    __slots__ = ("x", "y", "vx", "vy", "team", "speed")

    def __init__(self, x, y, angle, speed, team=0):
        self.x, self.y = x, y
        self.speed, self.team = speed, team
        self.vx = speed * math.sin(angle)
        self.vy = -speed * math.cos(angle)
        self.renormalise()

    def renormalise(self):
        # constant speed, and no near-horizontal or near-vertical loops that drag on
        sp = math.hypot(self.vx, self.vy) or 1.0
        vx, vy = self.vx / sp, self.vy / sp
        if abs(vy) < 0.3:
            vy = math.copysign(0.3, vy or 1)
            vx = math.copysign(math.sqrt(1 - vy * vy), vx or 1)
        if abs(vx) < 0.08:
            vx = math.copysign(0.08, vx or 1)
            vy = math.copysign(math.sqrt(1 - vx * vx), vy)
        self.vx, self.vy = vx * self.speed, vy * self.speed


class Game:
    has_paddle = True
    ball_speed = 1250.0
    fancy_bricks = True
    default_play = 40.0
    wins = ("clear", "escape", "win", "wars")

    def __init__(self, pg, seed, opts):
        self.pg, self.seed, self.opts = pg, seed, opts
        self.rng = random.Random(seed)
        self.nrng = np.random.default_rng(seed)
        self.max_play = opts.max_play or self.default_play
        self.balls, self.particles, self.floaters, self.events = [], [], [], []
        self.frame_events = 0
        self.note = 0
        self.flash = 0.0
        self.done = self.end_t = None
        self.play_t = 0.0
        self.launched = False
        self.paddle_x, self.aim_off = W / 2, 0.0
        self.hue = self.rng.random()
        fp = _font_path()
        self.f_title = pg.font.Font(fp, 66)
        self.f_stat = pg.font.Font(fp, 40)
        self.f_mid = pg.font.Font(fp, 32)
        self.f_small = pg.font.Font(fp, 22)
        self.f_float = pg.font.Font(fp, 46)
        self.f_big = pg.font.Font(fp, 110)
        self.f_huge = pg.font.Font(fp, 150)
        self.setup()
        self.title = opts.title or self.rng.choice(self.hooks())
        self._build_bg()
        self._build_sprites()
        self._build_field()
        self._wrap_title()

    # ---------------------------------------------------------- hooks for modes
    def setup(self): ...
    def hooks(self): return ["Watch this"]
    def launch(self, t): ...
    def idle_ball(self): return None
    def check_end(self, t): return None
    def stats(self): return ["", "", ""]
    def progress(self): return 0.0
    def end_text(self): return "DONE", ""
    def cell_colour(self, r, c, hp): return (255, 255, 255)
    def on_destroy(self, r, c, t): ...
    def extra_collide(self, b, t): ...
    def draw_extra(self, screen, t): ...

    def solid(self, r, c, b):
        return self.hp[r, c] != 0

    # ---------------------------------------------------------- grid helpers
    def grid(self, cell, gap, rows, top):
        self.cell, self.gap = cell, gap
        self.cols = (ARENA_R - ARENA_L) // cell
        self.rows = rows
        self.bx0 = ARENA_L + ((ARENA_R - ARENA_L) - self.cols * cell) // 2
        self.by0 = top
        self.hp = np.zeros((rows, self.cols), dtype=np.int32)
        self.power = np.zeros((rows, self.cols), dtype=np.int8)

    def centre(self, r, c):
        return self.bx0 + c * self.cell + self.cell / 2, self.by0 + r * self.cell + self.cell / 2

    def place_powers(self, mask, frac, big_chance=0.08):
        cells = np.argwhere(mask)
        if len(cells) == 0:
            return
        n = max(4, int(len(cells) * frac))
        for r, c in cells[self.nrng.choice(len(cells), min(n, len(cells)), replace=False)]:
            self.power[r, c] = 10 if self.nrng.random() < big_chance else 3
            self.hp[r, c] = 1

    def make_palette(self):
        self.colours = {}
        for r in range(self.rows):
            for c in range(self.cols):
                h = (self.hue + 0.22 * r / self.rows + 0.06 * c / self.cols) % 1
                for hp, val in ((1, 1.0), (2, 0.78), (3, 0.58)):
                    rgb = colorsys.hsv_to_rgb(h, 0.72, val)
                    self.colours[(r, c, hp)] = tuple(int(255 * x) for x in rgb)

    # ---------------------------------------------------------- graphics setup
    def _build_bg(self):
        pg = self.pg
        top = colorsys.hsv_to_rgb((self.hue + 0.55) % 1, 0.55, 0.16)
        bot = colorsys.hsv_to_rgb((self.hue + 0.65) % 1, 0.65, 0.05)
        self.bg = pg.Surface((W, H))
        for y in range(H):
            k = y / H
            col = tuple(int(255 * (top[i] * (1 - k) + bot[i] * k)) for i in range(3))
            pg.draw.line(self.bg, col, (0, y), (W, y))
        self._arena_outline()

    def _flat_bg(self, colour):
        self.bg = self.pg.Surface((W, H))
        self.bg.fill(colour)
        self._arena_outline()

    def _arena_outline(self):
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

    def _build_sprites(self):
        pg = self.pg
        self.ball_sprites = {0: self._glow_ball()}
        bw = self.cell - self.gap
        self.power_sprites = {}
        for val in (3, 10):
            s = pg.Surface((bw, bw), pg.SRCALPHA)
            colour = (255, 255, 255) if val == 3 else (255, 214, 64)
            pg.draw.rect(s, colour, (0, 0, bw, bw), border_radius=6)
            lab = self.f_small.render(f"+{val}", True, (30, 30, 40))
            s.blit(lab, lab.get_rect(center=(bw / 2, bw / 2)))
            self.power_sprites[val] = s

    def _build_field(self):
        self.field = self.bg.copy()
        for r in range(self.rows):
            for c in range(self.cols):
                self._paint(r, c)

    def _paint(self, r, c):
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

    def _wrap_title(self):
        words, lines, cur = self.title.split(), [], ""
        for w_ in words:
            trial = (cur + " " + w_).strip()
            if self.f_title.size(trial)[0] > W - 80 and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = trial
        lines.append(cur)
        self.title_surfs = [self.f_title.render(l, True, (255, 255, 255)) for l in lines[:2]]

    # ---------------------------------------------------------- effects
    def sfx(self, t, kind, idx=0, force=False):
        if force or self.frame_events < 4:
            self.events.append((t, kind, idx))
            self.frame_events += 1

    def burst(self, x, y, colour, n=7, power=1.0):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(120, 420) * power
            self.particles.append([x, y, sp * math.cos(a), sp * math.sin(a) - 150,
                                   self.rng.uniform(0.4, 0.9), colour])

    def floater(self, x, y, text, colour=(255, 236, 120), font=None, life=1.0):
        surf = (font or self.f_float).render(text, True, colour)
        self.floaters.append([x, y, surf, life])

    def spawn(self, x, y, count, t, team=0):
        spawned = 0
        for _ in range(count):
            if len(self.balls) >= MAX_BALLS:
                break
            self.balls.append(Ball(x, y, self.rng.uniform(-math.pi, math.pi), self.ball_speed, team))
            spawned += 1
        return spawned

    # ---------------------------------------------------------- physics
    def _bounce_rect(self, b, x0, y0, x1, y1):
        nx = min(max(b.x, x0), x1)
        ny = min(max(b.y, y0), y1)
        dx, dy = b.x - nx, b.y - ny
        if dx * dx + dy * dy > BALL_R * BALL_R:
            return False
        if dx == 0 and dy == 0:
            b.vy = -b.vy
        elif abs(dx) > abs(dy):
            b.vx = math.copysign(abs(b.vx), dx)
            b.x = nx + math.copysign(BALL_R + 0.5, dx)
        else:
            b.vy = math.copysign(abs(b.vy), dy)
            b.y = ny + math.copysign(BALL_R + 0.5, dy)
        b.renormalise()
        return True

    def _hit_cells(self, b, t):
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
                if self._bounce_rect(b, x0, y0, x0 + cell - 2 * half, y0 + cell - 2 * half):
                    self.on_hit(r, c, b, t)
                    return

    def on_hit(self, r, c, b, t):
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
        self.burst(cx, cy, colour, n=7 if self.fancy_bricks else 4)
        val = int(self.power[r, c])
        if val:
            self.power[r, c] = 0
            self.sfx(t, "power", force=True)
            n = self.spawn(cx, cy, val, t)
            if n:
                self.floater(cx, cy, f"+{n} BALLS")
        else:
            self.sfx(t, "break", self.note)
        self.on_destroy(r, c, t)

    def _predict_x(self, b):
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

    def _move_paddle(self, dt):
        best, best_t = None, 1e9
        for b in self.balls:
            x, t = self._predict_x(b)
            if x is not None and t < best_t:
                best, best_t = x, t
        target = (best if best is not None else W / 2) - self.aim_off
        step = PADDLE_SPEED * dt
        self.paddle_x += max(-step, min(step, target - self.paddle_x))
        self.paddle_x = max(ARENA_L + PADDLE_W / 2, min(ARENA_R - PADDLE_W / 2, self.paddle_x))

    def _step(self, dt, t):
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

    def update(self, dt, t):
        self.frame_events = 0
        if self.done is None and t >= INTRO_S:
            if not self.launched:
                self.launched = True
                self.launch(t)
            for _ in range(SUBSTEPS):
                self._step(dt / SUBSTEPS, t)
            self.play_t += dt
            why = self.check_end(t)
            if why:
                self.done, self.end_t = why, t
                self.sfx(t, "clear" if why in self.wins else "fail", force=True)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 900 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[1] -= 70 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        self.flash = max(0.0, self.flash - dt * 2.5)

    # ---------------------------------------------------------- drawing
    def draw_power(self, screen, t):
        pulse = 0.5 + 0.5 * math.sin(t * 8)
        g = self.gap // 2
        for r, c in np.argwhere(self.power > 0):
            spr = self.power_sprites[int(self.power[r, c])]
            spr.set_alpha(int(170 + 85 * pulse))
            screen.blit(spr, (self.bx0 + c * self.cell + g, self.by0 + r * self.cell + g))

    def draw_stats(self, screen):
        for i, txt in enumerate(self.stats()):
            s = self.f_stat.render(txt, True, (235, 235, 245))
            x = [ARENA_L + 10, W / 2, ARENA_R - 10][i]
            anchor = ["midleft", "center", "midright"][i]
            screen.blit(s, s.get_rect(**{anchor: (x, 252)}))
        frac = self.progress()
        self.pg.draw.rect(screen, (70, 70, 85), (ARENA_L, 290, ARENA_R - ARENA_L, 16), border_radius=8)
        if frac > 0:
            rgb = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(self.hue, 0.6, 1.0))
            self.pg.draw.rect(screen, rgb, (ARENA_L, 290, int((ARENA_R - ARENA_L) * frac), 16), border_radius=8)

    def draw(self, screen, t):
        pg = self.pg
        screen.blit(self.field, (0, 0))
        self.draw_power(screen, t)
        self.draw_extra(screen, t)
        for p in self.particles:
            size = max(2, int(10 * p[4]))
            pg.draw.rect(screen, p[5], (p[0], p[1], size, size))
        if self.has_paddle:
            pr = pg.Rect(0, 0, PADDLE_W, PADDLE_H)
            pr.midtop = (self.paddle_x, PADDLE_Y)
            pg.draw.rect(screen, (245, 245, 255), pr, border_radius=12)
        if not self.launched and self.idle_ball():
            x, y = self.idle_ball()
            spr = self.ball_sprites[0]
            screen.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2))
        for b in self.balls:
            spr = self.ball_sprites.get(b.team, self.ball_sprites[0])
            screen.blit(spr, (b.x - spr.get_width() / 2, b.y - spr.get_height() / 2))
        for f in self.floaters:
            f[2].set_alpha(int(255 * min(1, f[3] * 1.6)))
            screen.blit(f[2], f[2].get_rect(center=(f[0], f[1])))

        y = 60
        for s in self.title_surfs:
            screen.blit(s, s.get_rect(midtop=(W / 2, y)))
            y += s.get_height() + 4
        self.draw_stats(screen)

        if self.flash > 0:
            veil = pg.Surface((W, H), pg.SRCALPHA)
            veil.fill((255, 255, 255, int(150 * self.flash)))
            screen.blit(veil, (0, 0))

        if self.done:
            k = min(1.0, (t - self.end_t) / 0.4)
            veil = pg.Surface((W, H - ARENA_T), pg.SRCALPHA)
            veil.fill((0, 0, 0, int(150 * k)))
            screen.blit(veil, (0, ARENA_T))
            head, sub = self.end_text()
            hs = self.f_big.render(head, True, (255, 255, 255))
            if hs.get_width() > W - 60:
                hs = pg.transform.smoothscale(hs, (W - 60, int(hs.get_height() * (W - 60) / hs.get_width())))
            ss = self.f_stat.render(sub, True, (230, 230, 240))
            hs.set_alpha(int(255 * k))
            ss.set_alpha(int(255 * k))
            screen.blit(hs, hs.get_rect(center=(W / 2, H * 0.5)))
            screen.blit(ss, ss.get_rect(center=(W / 2, H * 0.5 + 100)))


# ------------------------------------------------------------------ mode: classic
class ClassicGame(Game):
    def setup(self):
        o = self.opts
        self.shape = o.shape or self.rng.choice(SHAPES)
        if self.shape not in SHAPES:
            raise SystemExit(f"classic shapes: {', '.join(SHAPES)}")
        self.text = (o.text or self.rng.choice(TEXT_WORDS)).upper()
        self.grid(40, 4, 26, ARENA_T + 50)
        mask = shape_mask(self.shape, self.text, self.pg, self.cols, self.rows)
        self.hp[:] = np.where(mask, self.nrng.choice([1, 2, 3], size=mask.shape, p=[0.8, 0.16, 0.04]), 0)
        self.place_powers(mask, 0.075)
        self.total = self.left = int(mask.sum())
        self.make_palette()

    def hooks(self):
        name = self.text if self.shape == "text" else self.shape.upper()
        return [f"Can 1 ball clear the {name}?", f"1 ball vs {self.total} bricks",
                f"Will the {name} break in {int(self.max_play)} seconds?"]

    def cell_colour(self, r, c, hp):
        return self.colours[(r, c, min(hp, 3))]

    def launch(self, t):
        self.balls.append(Ball(self.paddle_x, PADDLE_Y - BALL_R - 1, self.rng.uniform(-0.45, 0.45),
                               self.ball_speed))
        self.sfx(t, "paddle")

    def idle_ball(self):
        return self.paddle_x, PADDLE_Y - BALL_R - 1

    def check_end(self, t):
        if self.left == 0:
            return "clear"
        if not self.balls:
            return "fail"
        if self.play_t >= self.max_play:
            return "time"

    def stats(self):
        s = int(self.play_t)
        return [f"BRICKS {self.left}", f"BALLS {len(self.balls)}", f"{s // 60}:{s % 60:02d}"]

    def progress(self):
        return 1 - self.left / max(1, self.total)

    def end_text(self):
        if self.done == "clear":
            return "CLEARED!", f"in {self.play_t:.1f} seconds"
        if self.done == "fail":
            return "OUT OF BALLS", f"only {self.left} bricks left..."
        return "TIME UP!", f"{self.left} bricks survived"


# ------------------------------------------------------------------ mode: escape
class EscapeGame(Game):
    ball_speed = 1100.0
    fancy_bricks = False

    def setup(self):
        o = self.opts
        self.maze = o.shape or self.rng.choice(list(MAZES))
        if self.maze not in MAZES:
            raise SystemExit(f"escape shapes: {', '.join(MAZES)}")
        self.grid(18, 2, 55, ARENA_T)
        strokes, start = MAZES[self.maze]()
        if self.rng.random() < 0.5:                     # mirror for extra variety
            strokes = [[(-x, y) for x, y in s] for s in strokes]
            start = (-start[0], start[1])

        def to_cells(p):
            return (p[0] + 1) / 2 * self.cols, (1 - p[1]) / 2 * self.rows

        cx = np.arange(self.cols) + 0.5
        cy = np.arange(self.rows) + 0.5
        px, py = np.meshgrid(cx, cy)
        dist = np.full(px.shape, 1e9)
        segs = []
        for s in strokes:
            for a, b in zip(s, s[1:]):
                ax, ay = to_cells(a)
                bx, by = to_cells(b)
                segs.append((ax, ay, bx, by))
                vx, vy = bx - ax, by - ay
                k = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
                dist = np.minimum(dist, np.hypot(px - (ax + k * vx), py - (ay + k * vy)))

        hw = 1.45
        channel = dist <= hw
        band = (dist > hw) & (dist <= hw + 1.15)

        # weak spots: short stretches of wall left breakable, so there is a way out
        weak = np.zeros(px.shape, dtype=bool)
        cands = [s for s in segs if min(s[1], s[3]) < self.rows * 0.75]
        lengths = np.array([math.hypot(s[2] - s[0], s[3] - s[1]) for s in cands])
        for _ in range(self.rng.randint(2, 4)):
            ax, ay, bx, by = cands[self.nrng.choice(len(cands), p=lengths / lengths.sum())]
            k = self.rng.uniform(0.2, 0.8)
            wx, wy = ax + k * (bx - ax), ay + k * (by - ay)
            if wy > self.rows * 0.8:
                continue
            weak |= np.hypot(px - wx, py - wy) <= 2.8

        self.hp[:] = 1
        self.hp[channel] = 0
        self.hp[band & ~weak] = -1
        self.total = self.left = int((self.hp > 0).sum())
        self.fill = self.rng.choice(ESCAPE_FILLS)
        sx, sy = to_cells(start)
        self.start = (self.bx0 + sx * self.cell, self.by0 + sy * self.cell)
        self.escaped_t = None
        self.escape_play = 0.0

    def _build_bg(self):
        self._flat_bg((32, 32, 38))

    def hooks(self):
        name = self.maze.upper()
        return [f"Can the ball escape the {name}?", "Where will it break out?",
                f"Will it escape in {int(self.max_play)} seconds?", "Trapped ball. Will it get out?"]

    def cell_colour(self, r, c, hp):
        return self.fill

    def launch(self, t):
        self.balls.append(Ball(*self.start, self.rng.uniform(-math.pi, math.pi), self.ball_speed))
        self.sfx(t, "paddle")

    def idle_ball(self):
        return self.start

    def on_destroy(self, r, c, t):
        if r == 0 and self.escaped_t is None:
            self.escaped_t = t
            self.escape_play = self.play_t
            self.flash = 1.0
            cx, cy = self.centre(r, c)
            self.floater(W / 2, ARENA_T + 220, "ESCAPED!", (255, 255, 255), self.f_big, 1.6)
            self.sfx(t, "clear", force=True)

    def check_end(self, t):
        if self.escaped_t is not None and t - self.escaped_t >= 6.0:
            return "escape"
        if self.left == 0:
            return "clear"
        if not self.balls:
            return "fail"
        if self.play_t >= self.max_play:
            return "escape" if self.escaped_t is not None else "trapped"

    def stats(self):
        s = int(self.play_t)
        state = "FREE!" if self.escaped_t is not None else "TRAPPED"
        return [f"BROKEN {self.total - self.left}", state, f"{s // 60}:{s % 60:02d}"]

    def progress(self):
        return 1 - self.left / max(1, self.total)

    def end_text(self):
        if self.done == "escape":
            return "ESCAPED!", f"broke out in {self.escape_play:.1f} seconds"
        if self.done == "trapped":
            return "TRAPPED!", f"still stuck after {int(self.max_play)} seconds"
        if self.done == "clear":
            return "CLEARED!", f"in {self.play_t:.1f} seconds"
        return "OUT OF BALLS", f"{self.total - self.left} bricks broken"


# ------------------------------------------------------------------ mode: boss
class BossGame(ClassicGame):
    def setup(self):
        o = self.opts
        self.grid(40, 4, 26, ARENA_T + 50)
        self.boss_hp0 = self.boss_hp = o.boss_hp or self.rng.choice([300, 500, 777, 999])
        c0, c1 = self.cols // 2 - 4, self.cols // 2 + 4
        r0, r1 = 7, 15
        self.boss_cells = (r0, r1, c0, c1)
        self.boss_rect = (self.bx0 + c0 * self.cell + 2, self.by0 + r0 * self.cell + 2,
                          self.bx0 + (c1 + 1) * self.cell - 2, self.by0 + (r1 + 1) * self.cell - 2)
        u, v = _uv(self.cols, self.rows)
        mask = u * u + v * v <= 0.97 ** 2
        mask[r0:r1 + 1, c0:c1 + 1] = False
        self.hp[:] = np.where(mask, self.nrng.choice([1, 2], size=mask.shape, p=[0.75, 0.25]), 0)
        self.place_powers(mask, 0.09)
        self.total = self.left = int(mask.sum())
        self.make_palette()
        self.boss_col = tuple(int(255 * x) for x in colorsys.hsv_to_rgb((self.hue + 0.5) % 1, 0.75, 0.85))
        self.shake = 0.0
        self.shape, self.text = "boss", ""

    def hooks(self):
        hp = self.boss_hp0
        return [f"1 ball vs a {hp} HP block", f"Can it break the {hp} HP boss?",
                f"{hp} HP. {int(self.max_play)} seconds. Go."]

    def extra_collide(self, b, t):
        if self.boss_hp <= 0:
            return
        if self._bounce_rect(b, *self.boss_rect):
            self.boss_hp -= 1
            self.shake = 0.12
            self.sfx(t, "boss")
            if self.boss_hp <= 0:
                x0, y0, x1, y1 = self.boss_rect
                for _ in range(10):
                    self.burst(self.rng.uniform(x0, x1), self.rng.uniform(y0, y1), self.boss_col, 8, 1.6)
                self.flash = 1.0

    def draw_extra(self, screen, t):
        if self.boss_hp <= 0:
            return
        pg = self.pg
        x0, y0, x1, y1 = self.boss_rect
        self.shake = max(0.0, self.shake - 1 / FPS)
        j = 6 if self.shake > 0 else 0
        ox, oy = self.rng.randint(-j, j), self.rng.randint(-j, j)
        frac = self.boss_hp / self.boss_hp0
        col = tuple(int(c * (0.45 + 0.55 * frac)) for c in self.boss_col)
        rect = pg.Rect(x0 + ox, y0 + oy, x1 - x0, y1 - y0)
        pg.draw.rect(screen, col, rect, border_radius=14)
        pg.draw.rect(screen, (255, 255, 255), rect, 4, border_radius=14)
        num = self.f_huge.render(str(self.boss_hp), True, (255, 255, 255))
        if num.get_width() > rect.width - 30:
            num = pg.transform.smoothscale(num, (rect.width - 30, int(num.get_height() * (rect.width - 30)
                                                                      / num.get_width())))
        screen.blit(num, num.get_rect(center=rect.center))
        lab = self.f_mid.render("HP", True, (255, 255, 255))
        screen.blit(lab, lab.get_rect(midtop=(rect.centerx, rect.centery + 70)))
        bar = pg.Rect(rect.x + 20, rect.bottom - 30, rect.width - 40, 12)
        pg.draw.rect(screen, (40, 40, 50), bar, border_radius=6)
        pg.draw.rect(screen, (255, 90, 90), (bar.x, bar.y, int(bar.width * frac), bar.height), border_radius=6)

    def check_end(self, t):
        if self.boss_hp <= 0:
            return "win"
        if not self.balls:
            return "fail"
        if self.play_t >= self.max_play:
            return "time"

    def stats(self):
        s = int(self.play_t)
        return [f"BOSS HP {max(0, self.boss_hp)}", f"BALLS {len(self.balls)}", f"{s // 60}:{s % 60:02d}"]

    def progress(self):
        return 1 - max(0, self.boss_hp) / self.boss_hp0

    def end_text(self):
        if self.done == "win":
            return "BOSS DOWN!", f"in {self.play_t:.1f} seconds"
        if self.done == "fail":
            return "OUT OF BALLS", f"boss had {self.boss_hp} HP left"
        return "TIME UP!", f"boss survived with {self.boss_hp} HP"


# ------------------------------------------------------------------ mode: wars
class WarsGame(Game):
    has_paddle = False
    ball_speed = 900.0
    fancy_bricks = False
    default_play = 30.0
    MAX_PER_TEAM = 6

    def setup(self):
        o = self.opts
        self.n = o.teams or self.rng.choice([2, 2, 3, 4])
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

    def _build_bg(self):
        self._flat_bg((22, 22, 28))

    def _build_sprites(self):
        pg = self.pg
        self.ball_sprites = {}
        for i, (_, col) in enumerate(self.teams):
            s = pg.Surface((BALL_R * 3, BALL_R * 3), pg.SRCALPHA)
            cx = BALL_R * 1.5
            dark = tuple(int(v * 0.35) for v in col)
            pg.draw.circle(s, (255, 255, 255), (cx, cx), BALL_R + 3)
            pg.draw.circle(s, dark, (cx, cx), BALL_R)
            self.ball_sprites[i] = s

    def _paint(self, r, c):
        pg, cell, g = self.pg, self.cell, self.gap
        x, y = self.bx0 + c * cell, self.by0 + r * cell
        self.field.blit(self.bg, (x, y), (x, y, cell, cell))
        col = self.teams[int(self.owner[r, c])][1]
        pg.draw.rect(self.field, col, (x + g // 2, y + g // 2, cell - g, cell - g), border_radius=3)
        if self.power[r, c]:
            pg.draw.circle(self.field, (255, 255, 255), (x + cell // 2, y + cell // 2), 7)
            pg.draw.circle(self.field, col, (x + cell // 2, y + cell // 2), 3)

    def draw_power(self, screen, t):
        pass

    def hooks(self):
        names = [n for n, _ in self.teams]
        if self.n == 2:
            return [f"{names[0]} vs {names[1]}: who takes the board?", "Which colour wins?",
                    "Pick your colour before it ends!"]
        return [f"{self.n} colours, 1 board. Who wins?", "Which colour wins?",
                "Pick your colour before it ends!"]

    def solid(self, r, c, b):
        return self.owner[r, c] != b.team

    def on_hit(self, r, c, b, t):
        old = int(self.owner[r, c])
        self.owner[r, c] = b.team
        self.counts[old] -= 1
        self.counts[b.team] += 1
        cx, cy = self.centre(r, c)
        self.burst(cx, cy, self.teams[old][1], n=3, power=0.6)
        self.sfx(t, "hit", b.team * 3 + self.rng.randint(0, 2))
        if self.power[r, c]:
            self.power[r, c] = 0
            mine = sum(1 for x in self.balls if x.team == b.team)
            if mine < self.MAX_PER_TEAM:
                self.spawn(cx, cy, 1, t, b.team)
                name, col = self.teams[b.team]
                self.floater(cx, cy, f"+1 {name}", col)
                self.sfx(t, "power", force=True)
        self._paint(r, c)

    def check_end(self, t):
        if self.play_t >= self.max_play or self.counts.max() >= 0.97 * self.counts.sum():
            return "wars"

    def draw_stats(self, screen):
        pg = self.pg
        total = self.counts.sum()
        width = ARENA_R - ARENA_L
        font = self.f_stat if self.n <= 2 else self.f_mid
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
        ts = self.f_small.render(f"{s}s left", True, (200, 200, 210))
        screen.blit(ts, ts.get_rect(midtop=(W / 2, 312)))

    def end_text(self):
        i = int(self.counts.argmax())
        pct = round(100 * self.counts[i] / self.counts.sum())
        return f"{self.teams[i][0]} WINS!", f"took {pct}% of the board"


MODES = {"classic": ClassicGame, "escape": EscapeGame, "boss": BossGame, "wars": WarsGame}


# ------------------------------------------------------------------ runner
def run(seed, opts, mode=None):
    if not opts.preview:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame as pg
    pg.init()

    if mode is None:
        mode = opts.mode if opts.mode != "random" else random.Random(seed * 7919).choice(list(MODES))
    game = MODES[mode](pg, seed, opts)
    screen = pg.Surface((W, H))
    out = opts.out if (opts.out and opts.batch == 1) else f"reel_{mode}_{seed}.mp4"
    print(f"[{mode} {seed}] title='{game.title}'")

    window = clock = ffmpeg = None
    if opts.preview:
        window = pg.display.set_mode((int(W * 0.45), int(H * 0.45)))
        pg.display.set_caption(f"brickreel preview: {mode}")
        clock = pg.time.Clock()
    else:
        tmp_video = out + ".video.mp4"
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp_video],
            stdin=subprocess.PIPE)

    frame = 0
    while True:
        t = frame / FPS
        game.update(1 / FPS, t)
        game.draw(screen, t)
        if opts.preview:
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    return
            window.blit(pg.transform.smoothscale(screen, window.get_size()), (0, 0))
            pg.display.flip()
            clock.tick(FPS)
        else:
            ffmpeg.stdin.write(pg.image.tobytes(screen, "RGB"))
        frame += 1
        if game.done and t >= game.end_t + OUTRO_S:
            break

    if opts.preview:
        return
    ffmpeg.stdin.close()
    ffmpeg.wait()
    duration = frame / FPS
    wav = out + ".wav"
    render_audio(game.events, duration, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_video, "-i", wav,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    os.remove(tmp_video)
    os.remove(wav)
    head, sub = game.end_text()
    print(f"[{mode} {seed}] {head} {sub} -> {out} ({duration:.1f}s)")


def main():
    ap = argparse.ArgumentParser(description="Render auto-playing brick-breaker reels.")
    ap.add_argument("--mode", choices=["random"] + list(MODES), default="random")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--shape", default=None,
                    help=f"classic: {', '.join(SHAPES)} | escape: {', '.join(MAZES)}")
    ap.add_argument("--text", default=None, help="word to build from bricks (classic, --shape text)")
    ap.add_argument("--teams", type=int, choices=[2, 3, 4], default=None, help="wars mode team count")
    ap.add_argument("--boss-hp", type=int, default=None, help="boss mode starting HP")
    ap.add_argument("--title", default=None, help="override the hook line at the top")
    ap.add_argument("--max-play", type=float, default=None, help="seconds of gameplay before time up")
    ap.add_argument("--out", default=None)
    ap.add_argument("--batch", type=int, default=1, help="render this many reels with consecutive seeds")
    ap.add_argument("--mix", choices=["random", "even"], default="random",
                    help="with --mode random: 'even' rotates through every format in turn")
    ap.add_argument("--preview", action="store_true", help="show a live window instead of rendering")
    opts = ap.parse_args()

    seed = opts.seed if opts.seed is not None else random.randrange(1_000_000)
    order = list(MODES)
    random.Random(seed).shuffle(order)      # rotation starts with a different format each batch
    for i in range(opts.batch):
        mode = order[i % len(order)] if (opts.mode == "random" and opts.mix == "even") else None
        run(seed + i, opts, mode)


if __name__ == "__main__":
    sys.exit(main())
