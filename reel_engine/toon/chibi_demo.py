"""Chibi animation test: the aunty, the Dost and Positive Bhai chatting in a breezy garden.
Run: python -m reel_engine.toon.chibi_demo   (or --still for a few frames, no voices)

Shows what the chibi kit can do in motion: mouths driven by the loudness of each voice line (real
lip-sync), hand gestures while talking and idle moves when quiet, blinks, breathing, eyes that look at
whoever is speaking, a saree pallu, a lock of hair and jhumkas swaying in the breeze, drifting leaves, and
a camera that eases into a sharp close-up on each speaker (everything is drawn in code, so zooming loses
nothing). Voices, timing and the mix come from the shared skit renderer.
"""
import math
import random
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..stick.durvasa import Episode
from ..stick.pressure_cooker import render as run
from .chibi import CHIBI, FEET, Act, Painter, Z, dark, ease, ell, lady, light, man, mix, spline
from .kit import finish

W, H = 1080, 1920
EPISODE, NAME, MUSIC_SEED = 1, "chibi_demo_hi", 33
SERIES, END_SUB, TAGLINE = "CHIBI TEST", "All drawn in code", ""
VOICES = {
    "aunty": "maya:hi:Ishwari@-1~1.0",
    "dost": "maya:hi:Ritvik@+2~1.15",
    "bhai": "maya:hi:Shaunak@+1~1.15",
}
LINES = [
    ("aunty", "अरे बच्चों, आज हवा कितनी अच्छी चल रही है ना?", ""),
    ("dost", "हाँ आंटी! पर उड़-उड़ के मेरे बाल, बिल्कुल झाड़ू बन गए हैं।", ""),
    ("bhai", "[excited] अरे positive सोचो! Free में नया hairstyle मिल गया!", ""),
    ("aunty", "[laughs] तुम दोनों भी ना!", ""),
]
HOOK = "CHIBI STYLE TEST"
COMMENT = {}
CUTS = (1, 2, 3)
LABELS = {"aunty": "AUNTY", "dost": "DOST", "bhai": "POSITIVE BHAI"}
SPEAKER_COLOUR = {"aunty": (255, 190, 220), "dost": (255, 226, 120), "bhai": (170, 220, 255)}
VOICE_FX = {}

X = {"dost": 215, "aunty": 500, "bhai": 785}
HEAD_Y = {"dost": FEET - CHIBI.m_legs - CHIBI.m_torso - CHIBI.neck - CHIBI.hr * 0.95,
          "bhai": FEET - CHIBI.m_legs - CHIBI.m_torso - CHIBI.neck - CHIBI.hr * 0.95,
          "aunty": FEET - CHIBI.f_skirt - CHIBI.f_torso - CHIBI.neck - CHIBI.hr * 0.95}
WIDE = (1.2, 500.0, 470.0)                    # (zoom, focus x, focus y) in world units
SHOTS = ["wide", "dost", "bhai", "wide"]      # the camera for each line


IDLE = {"dost": ("scratch", "rest"), "bhai": ("thumb", "rest"), "aunty": ("rest", "hip")}   # (right, left)
TALK = {"dost": [("explain", "rest"), ("chest", "rest"), ("shrug", "shrug")],
        "bhai": [("up", "up"), ("present", "rest"), ("thumb", "thumb")],
        "aunty": [("explain", "hip"), ("present", "hip"), ("chest", "hip")]}
LAUGH = {"dost": ("chest", "rest"), "bhai": ("chest", "rest"), "aunty": ("chest", "hip")}
MOVE_S = 0.32                                  # how long a hand takes to reach its next pose


def gust(t):
    return max(0.0, min(1.0, 0.5 + 0.5 * math.sin(t * 0.9) * (0.6 + 0.4 * math.sin(t * 2.3))))


def shot(name):
    if name == "wide":
        return WIDE
    return (1.95, float(X[name]), HEAD_Y[name] + 110)


class Skit(Episode):
    def __init__(self, pg):
        super().__init__(pg)
        from ..core import voice as tts
        from ..core.audio import SR
        self.env = []                                                     # per line: mouth opening per frame
        hop = SR // 30
        for who, line, _ in LINES:
            c = tts.say(line, VOICES[who])
            n = len(c) // hop + 1
            rms = np.array([math.sqrt(float(np.mean(c[k * hop:(k + 1) * hop] ** 2)) if len(c[k * hop:(k + 1) * hop]) else 0.0)
                            for k in range(n)])
            top = float(np.percentile(rms, 95)) or 1.0
            e, out = 0.0, []
            for v in np.clip(rms / top, 0, 1):
                e = v if v > e else e * 0.6 + v * 0.4                     # snap open, close a little slower
                out.append(e)
            self.env.append(out)
        self.plan()
        self.big = pg.Surface((W * Z, H * Z))
        self.sky = pg.Surface((W * Z, H * Z))
        for yy in range(0, H * Z, 4):
            pg.draw.rect(self.sky, mix((150, 206, 240), (255, 236, 214), yy / (H * Z)), (0, yy, W * Z, 4))
        xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H), indexing="ij")
        self.vignette = (1 - 0.22 * np.clip((xs ** 2 * 0.8 + ys ** 2 * 0.6) - 0.3, 0, None)).astype(np.float32)
        rng = np.random.default_rng(4)
        self.grains = [rng.normal(0, 2.5, (W, H)).astype(np.float32) for _ in range(4)]
        self.frame_no = 0

    def plan(self):
        """Arm keyframes per line and character: the speaker moves to a new gesture on stressed beats
        (peaks in the voice's loudness, at least 0.6 s apart) and returns to idle before the line ends;
        listeners hold their idle pose; on the laugh everyone clutches their chest."""
        self.keys = []
        for i, (speaker, _, _) in enumerate(LINES):
            env = self.env[i]
            dur = len(env) / 30
            per = {}
            for who in X:
                if i == 3:
                    per[who] = [(0.0,) + IDLE[who], (0.15,) + LAUGH[who]]
                    continue
                keys = [(0.0,) + IDLE[who]]
                if who == speaker:
                    keys.append((0.1,) + TALK[who][0])
                    n, last = 1, 0.1
                    for f in range(1, len(env) - 1):
                        tt = f / 30
                        if env[f] > 0.7 and env[f] >= env[f - 1] and env[f] > env[f + 1] and tt - last >= 0.6 and tt < dur - 0.7:
                            keys.append((tt,) + TALK[who][n % len(TALK[who])])
                            n, last = n + 1, tt
                    keys.append((max(last + 0.4, dur - 0.35),) + IDLE[who])
                per[who] = keys
            self.keys.append(per)

    def arms(self, i, who, since):
        keys = self.keys[i][who]
        since = max(0.0, since)                                           # the lead-in before line 0
        j = max(n for n, k in enumerate(keys) if k[0] <= since)
        cur, prev = keys[j], keys[j - 1] if j else keys[j]
        u = min(1.0, (since - cur[0]) / MOVE_S)
        return (prev[1], cur[1], u), (prev[2], cur[2], u)

    def room(self, surf, dim=0.0):
        surf.fill((200, 226, 240))

    # ------------------------------------------------------------ drawing
    def world(self, p, t):
        """Clouds, hills, two trees and a lawn with flowers, in world units (so the camera moves them)."""
        w = gust(t)
        for k, (cx, cy, s) in enumerate(((-100, -380, 1.0), (420, -520, 0.8), (900, -330, 1.1), (1300, -470, 0.9))):
            x = (cx + t * 14 + 400) % 1700 - 400
            for dx, dy, r in ((-60, 10, 50), (0, -20, 70), (70, 0, 55), (130, 15, 40)):
                p.oval((x + dx * s, cy + dy * s), r * s, r * s * 0.8, (255, 255, 255), shade=False, ink=False, grad=False)
        p.fill(spline([(-700, 560), (-200, 470), (300, 540), (800, 450), (1400, 530), (1700, 700), (1700, 900), (-700, 900)], 8),
               (150, 196, 120), shade=False, ink=False)
        p.fill([(-700, 740), (1700, 740), (1700, 1500), (-700, 1500)], (140, 200, 100), shade=False, ink=False)
        p.fill(spline([(330, 1500), (430, 900), (470, 745), (530, 745), (570, 900), (670, 1500)], 6), (236, 214, 170), shade=False, ink=False)
        rng = random.Random(9)
        for _ in range(40):                                               # flowers on the lawn
            fx, fy = rng.uniform(-300, 1300), rng.uniform(760, 1250)
            if 380 < fx < 620:
                continue
            c = rng.choice(((255, 120, 150), (255, 220, 90), (255, 255, 255), (200, 130, 230)))
            for a in range(5):
                p.dot((fx + 7 * math.cos(a * 1.257), fy + 5 * math.sin(a * 1.257)), 4.5, c)
            p.dot((fx, fy), 3, (250, 190, 60))
        for tx in (-130, 1130):                                           # trees, canopies swaying
            p.fill([(tx - 22, 760), (tx + 22, 760), (tx + 16, 420), (tx - 16, 420)], (130, 86, 56))
            sway = w * 14 + math.sin(t * 2) * 4
            for dx, dy, r in ((-90, 330, 110), (80, 320, 115), (0, 230, 130), (-40, 400, 100), (60, 400, 100)):
                p.oval((tx + dx + sway * (1 - dy / 450), dy), r, r * 0.9, (70, 150, 80))

    def overlay(self, surf, t):
        """Leaves and petals riding the breeze, and a few soft breeze streaks (screen space)."""
        pg = self.pg
        w = gust(t)
        lay = pg.Surface((W, H), pg.SRCALPHA)
        rng = random.Random(3)
        for n in range(18):
            x0, y0, ph, sp = rng.uniform(0, 1300), rng.uniform(150, 1500), rng.uniform(0, 6.28), rng.uniform(50, 110)
            x = (x0 + t * sp * (0.6 + w)) % 1300 - 110
            y = y0 + math.sin(t * 1.6 + ph) * 40 + (t * 25) % 60
            rot = t * 2.5 + ph
            col = (110, 180, 90) if n % 3 else (255, 150, 180)
            pts = ell(x, y, 13, 6, 16, rot=rot)
            pg.draw.polygon(lay, col + (230,), pts)
            pg.draw.line(lay, dark(col, 0.7) + (230,), pts[0], pts[8], 2)
        for n in range(4):
            x0, y0 = rng.uniform(0, W), rng.uniform(300, 1300)
            x = (x0 + t * 260) % (W + 400) - 200
            a = int(90 * w)
            pts = [(x + k * 30, y0 + math.sin(k * 0.5 + t * 3) * 10) for k in range(8)]
            pg.draw.lines(lay, (255, 255, 255, a), False, pts, 4)
        surf.blit(lay, (0, 0))

    def draw(self, surf, cam, acts, t):
        pg = self.pg
        k, fx, fy = cam
        big = self.big
        big.blit(self.sky, (0, 0))
        p = Painter(pg, big, CHIBI, seed=1, k=k, ox=W * Z / 2 - fx * Z * k, oy=0.42 * H * Z - fy * Z * k)
        self.world(p, t)
        heads = {"dost": man(p, CHIBI, X["dost"], "dost", acts["dost"]),
                 "aunty": lady(p, CHIBI, X["aunty"], acts["aunty"]),
                 "bhai": man(p, CHIBI, X["bhai"], "bhai", acts["bhai"])}
        surf.blit(pg.transform.smoothscale(big, (W, H)), (0, 0))
        self.frame_no += 1
        finish(pg, surf, self.grains[self.frame_no % 4], self.vignette)
        self.overlay(surf, t)
        return heads

    def acts(self, i, since, length, t, laugh=False):
        speaker = LINES[i][0]
        out = {}
        for who, ph, per in (("dost", 0.0, 3.4), ("aunty", 1.1, 4.1), ("bhai", 2.3, 3.7)):
            talking = who == speaker
            env = self.env[i]
            f = int(since * 30)
            talk = env[f] if talking and f < len(env) else 0.0
            g = ease(since / 0.4) * ease((length - since) / 0.5) if talking else 0.0
            look = 0.0 if talking else (0.6 if X[speaker] > X[who] else -0.6)
            mood = "goofy" if who == "dost" else "happy"
            if laugh and since > 0.15:
                mood = "laugh"
            arm_r, arm_l = self.arms(i, who, since)
            out[who] = Act(t=t, talk=talk if mood != "laugh" or talking else 0.5 + 0.3 * abs(math.sin(t * 9)),
                           gesture=g, blink=((t + ph) % per) < 0.13, look=look, wind=gust(t), mood=mood,
                           arm_r=arm_r, arm_l=arm_l)
        return out

    def scene(self, surf, i, since, length, t):
        cur = shot(SHOTS[i])
        prev = shot(SHOTS[i - 1]) if i else cur
        q = ease(since / 0.6)
        cam = tuple(prev[j] + (cur[j] - prev[j]) * q for j in range(3))
        self.draw(surf, cam, self.acts(i, since, length, t, laugh=i == 3), t)
        if i == 3 and "laugh" not in self.cache:
            self.cache["laugh"] = 1
            self.events.append((t, "ding"))
        return (1.0, W / 2, H / 2)


def end_card(sk, frame, t, e):
    acts = {who: Act(t=t, talk=0.5 + 0.3 * abs(math.sin(t * 9)), gesture=1.0, blink=False, wind=gust(t), mood="laugh",
                     arm_r=(LAUGH[who][0],) * 2 + (1.0,), arm_l=(LAUGH[who][1],) * 2 + (1.0,))
            for who in ("dost", "aunty", "bhai")}
    sk.draw(frame, WIDE, acts, t)


def render(out_dir: Path) -> Path:
    import sys
    return run(out_dir, sys.modules[__name__])


if __name__ == "__main__":
    import datetime
    import os
    import sys
    out = REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME
    if "--still" in sys.argv:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame as pg
        pg.init()
        sk = Skit.__new__(Skit)                                           # no voices: a fake mouth envelope
        Episode.__init__(sk, pg)
        sk.env = [[0.2, 0.5, 0.9, 0.4, 0.2] * 20 for _ in LINES]
        sk.plan()
        sk.big = pg.Surface((W * Z, H * Z))
        sk.sky = pg.Surface((W * Z, H * Z))
        for yy in range(0, H * Z, 4):
            pg.draw.rect(sk.sky, mix((150, 206, 240), (255, 236, 214), yy / (H * Z)), (0, yy, W * Z, 4))
        xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H), indexing="ij")
        sk.vignette = (1 - 0.22 * np.clip((xs ** 2 * 0.8 + ys ** 2 * 0.6) - 0.3, 0, None)).astype(np.float32)
        sk.grains = [np.zeros((W, H), np.float32)] * 4
        sk.frame_no = 0
        (out / "stills").mkdir(parents=True, exist_ok=True)
        surf = pg.Surface((W, H))
        for n, (i, since) in enumerate(((0, 1.0), (1, 0.3), (1, 1.5), (2, 1.5), (3, 1.0))):
            sk.scene(surf, i, since, 3.0, 5.0 + n * 0.7)
            pg.image.save(surf, str(out / "stills" / f"demo_{n}.png"))
        print(out / "stills")
    else:
        render(out)
