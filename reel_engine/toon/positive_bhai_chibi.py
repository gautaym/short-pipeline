"""Positive Bhai, part 1, in the chibi look. Run: python -m reel_engine.toon.positive_bhai_chibi
(--still [line numbers] renders single frames with no voices).

Same script, voices, sounds and timing as positive_bhai.py; the drawing is the chibi kit (chibi.py):
the Dost and Positive Bhai in a courtyard, with mouths driven by each voice line's loudness, gestures on
the stressed beats, blinks, breathing, a breeze, and close-ups on the punchlines. The flashbacks are framed
chibi panels: the aunty in her saree in the sparks, her soul, the small uncle and the big car (BOOM), the
reunion on a cloud, and dadaji alone with dadi's soul waving.
"""
import math
import random
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..stick.durvasa import ORANGE, RED
from ..stick.pressure_cooker import render as run
from . import chibi_demo, positive_bhai as pb, sheru
from .chibi import CHIBI, FEET, Act, Painter, Z, dark, ease, ell, lady, light, man, mix, spline
from .kit import finish

# the episode, as in positive_bhai.py
LINES, STORY, VOICES, LINE_VOICE, LINE_FX, VOICE_FX = pb.LINES, pb.STORY, pb.VOICES, pb.LINE_VOICE, pb.LINE_FX, pb.VOICE_FX
HOOK, COMMENT, CUTS, LABELS, SPEAKER_COLOUR = pb.HOOK, pb.COMMENT, pb.CUTS, pb.LABELS, pb.SPEAKER_COLOUR
SERIES, END_SUB, TAGLINE, EPISODE, MUSIC_SEED = pb.SERIES, pb.END_SUB, pb.TAGLINE, pb.EPISODE, pb.MUSIC_SEED
NAME = "positive_bhai_chibi_hi"

W, H = 1080, 1920
X = {"p1": 300.0, "p2": 700.0}
WHO = {"p1": "dost", "p2": "bhai"}
HEAD_Y = FEET - CHIBI.m_legs - CHIBI.m_torso - CHIBI.neck - CHIBI.hr * 0.95
TWO = (1.5, 500.0, 151.0)                         # (zoom, focus x, focus y): both friends, feet near the bottom
PANEL = (110, 240, 860, 560)                      # the flashback frame, in screen pixels
AUNTY = dict(saree=(226, 70, 130), blouse=(120, 40, 90), grey=True)
DADI = dict(saree=(150, 40, 60), blouse=(60, 120, 90), grey=True)
MOVE_S = 0.32


def shot(n):
    """The camera for each line (n counts the intro as 0): close-ups on the punchlines, a two-shot otherwise."""
    s = n - 1
    if s == 7 or s == 9:
        return (2.3, X["p1"], HEAD_Y + 140)
    if s == 14:
        return (2.3, X["p2"], HEAD_Y + 140)
    return TWO


def panel_for(s):
    return s in (1, 2, 3, 4, 5, 6, 8, 13)


def mood1(s):
    """The Dost's face, line by line (s counts story lines; -1 is the intro)."""
    if s <= 8:
        return "sad"
    if s == 15:
        return "shock"
    return "goofy"


def idle(who, s):
    if who == "p2":
        return ("thumb", "rest") if s < 13 else ("rest", "rest")
    if s >= 13:
        return ("hold", "hold")
    return ("rest", "rest") if s <= 8 else ("scratch", "rest")


def talk_poses(who, s):
    if who == "p2":
        if s == 14:
            return [("explain", "explain")]
        if s == 15:
            return [("phone", "rest")]
        return [("present", "rest"), ("thumb", "rest"), ("explain", "explain"), ("up", "up")]
    if s == 7:
        return [("wipe", "wipe")]
    if s >= 13:
        return [("hold", "hold")]
    if s >= 9:
        return [("up", "up"), ("shrug", "shrug"), ("explain", "rest")]
    return [("chest", "rest"), ("explain", "rest")]


def gust(t):
    return chibi_demo.gust(t)


class Skit(pb.Skit):
    def __init__(self, pg):
        sheru.base.Skit.__init__(self, pg)                                 # fonts, text, phone, effects
        from ..core import voice as tts
        from ..core.audio import SR
        hop = SR // 30
        self.env = []
        for n, (who, line, _) in enumerate(LINES):
            c = tts.say(line, LINE_VOICE.get(n, VOICES[who]))
            frames = len(c) // hop + 1
            rms = np.array([math.sqrt(float(np.mean(c[k * hop:(k + 1) * hop] ** 2))) if len(c[k * hop:(k + 1) * hop]) else 0.0
                            for k in range(frames)])
            top = float(np.percentile(rms, 95)) or 1.0
            e, out = 0.0, []
            for v in np.clip(rms / top, 0, 1):
                e = v if v > e else e * 0.6 + v * 0.4
                out.append(e)
            self.env.append(out)
        self.setup(pg)

    def setup(self, pg):
        self.plan()
        self.big = pg.Surface((W * Z, H * Z))
        self.layer = pg.Surface((W * Z, H * Z), pg.SRCALPHA)
        self.sky = pg.Surface((W * Z, H * Z))
        for yy in range(0, H * Z, 4):
            self.pg.draw.rect(self.sky, mix((160, 210, 240), (255, 238, 214), yy / (H * Z)), (0, yy, W * Z, 4))
        xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H), indexing="ij")
        self.vignette = (1 - 0.22 * np.clip((xs ** 2 * 0.8 + ys ** 2 * 0.6) - 0.3, 0, None)).astype(np.float32)
        rng = np.random.default_rng(4)
        self.grains = [rng.normal(0, 2.5, (W, H)).astype(np.float32) for _ in range(4)]
        self.frame_no = 0

    def plan(self):
        """Arm keyframes: the speaker changes gesture on the stressed beats of the line, then returns to idle."""
        self.keys = []
        for n, (speaker, _, _) in enumerate(LINES):
            s = n - 1
            env = self.env[n]
            dur = len(env) / 30
            per = {}
            for who in X:
                rest = idle(who, s)
                keys = [(0.0,) + rest]
                if who == speaker:
                    poses = talk_poses(who, s)
                    keys.append((0.1,) + poses[0])
                    k, last = 1, 0.1
                    for f in range(1, len(env) - 1):
                        tt = f / 30
                        if env[f] > 0.7 and env[f] >= env[f - 1] and env[f] > env[f + 1] and tt - last >= 0.6 and tt < dur - 0.7:
                            keys.append((tt,) + poses[k % len(poses)])
                            k, last = k + 1, tt
                    if s not in (14, 15):                                 # the last two hold their pose
                        keys.append((max(last + 0.4, dur - 0.35),) + rest)
                per[who] = keys
            self.keys.append(per)

    def arms(self, n, who, since):
        keys = self.keys[n][who]
        since = max(0.0, since)
        j = max(k for k, key in enumerate(keys) if key[0] <= since)
        cur, prev = keys[j], keys[j - 1] if j else keys[j]
        u = min(1.0, (since - cur[0]) / MOVE_S)
        return (prev[1], cur[1], u), (prev[2], cur[2], u)

    def room(self, surf, dim=0.0):
        surf.fill((240, 222, 190))

    @staticmethod
    def scr(p, pt):
        """World point to screen pixels (1x)."""
        return ((p.ox + pt[0] * Z * p.k) / Z, (p.oy + pt[1] * Z * p.k) / Z)

    # ------------------------------------------------------------ the courtyard
    def yard(self, p, t):
        w = gust(t)
        p.fill([(-900, -1200), (1900, -1200), (1900, 770), (-900, 770)], (238, 216, 182), shade=False, ink=False, grad=True)
        for wx, wy, ww_, wh in ((40, 120, 230, 300), (730, 120, 230, 300), (160, -420, 220, 270), (620, -420, 220, 270)):
            p.fill([(wx + 18, wy + 18), (wx + ww_ + 26, wy + 18), (wx + ww_ + 26, wy + wh + 30), (wx + 18, wy + wh + 30)], (0, 0, 0),
                   shade=False, ink=False, grad=False, alpha=30)
            p.fill([(wx - 14, wy - 14), (wx + ww_ + 14, wy - 14), (wx + ww_ + 14, wy + wh + 14), (wx - 14, wy + wh + 14)], (252, 248, 240), shade=False)
            p.fill([(wx, wy), (wx + ww_, wy), (wx + ww_, wy + wh), (wx, wy + wh)], (110, 170, 220), shade=False)
            p.fill([(wx + 20, wy), (wx + 70, wy), (wx, wy + 90), (wx, wy + 40)], (170, 210, 240), shade=False, ink=False, grad=False)
            p.stroke([(wx + ww_ / 2, wy), (wx + ww_ / 2, wy + wh)], 6, (252, 248, 240), closed=False)
            p.stroke([(wx, wy + wh / 2), (wx + ww_, wy + wh / 2)], 6, (252, 248, 240), closed=False)
            p.fill([(wx - 26, wy + wh + 14), (wx + ww_ + 26, wy + wh + 14), (wx + ww_ + 26, wy + wh + 32), (wx - 26, wy + wh + 32)], (226, 220, 206), shade=False)
        p.fill([(380, 330), (620, 330), (620, 770), (380, 770)], (252, 248, 240), shade=False)          # the door
        p.fill([(398, 348), (602, 348), (602, 770), (398, 770)], (176, 120, 80))
        for k in range(1, 6):
            p.stroke([(404, 348 + k * 70), (596, 348 + k * 70)], 3, (150, 98, 62), closed=False)
        p.oval((570, 570), 11, 11, (236, 186, 60), shade=False)
        p.fill([(-900, 745), (1900, 745), (1900, 775), (-900, 775)], (214, 204, 190), shade=False)
        p.fill([(-900, 775), (1900, 775), (1900, 1400), (-900, 1400)], (226, 206, 168), shade=False, ink=False, grad=True)
        for k in range(8):                                                # paving lines
            yy = 800 + k * k * 9
            p.stroke([(-900, yy), (1900, yy)], 2, (206, 184, 146), closed=False)
        for px_ in (60, 940):                                             # potted plants, leaves in the breeze
            sway = w * 10 + math.sin(t * 2 + px_) * 3
            for dx, dy, r in ((-40, 590, 46), (30, 570, 50), (0, 520, 54), (-20, 640, 40), (40, 640, 40)):
                p.oval((px_ + dx + sway * (680 - dy) / 160, dy), r, r * 0.85, (80, 160, 90))
            p.fill([(px_ - 52, 670), (px_ + 52, 670), (px_ + 40, 780), (px_ - 40, 780)], (196, 104, 74))

    # ------------------------------------------------------------ flashback panels
    def ghost(self, big, pp, draw, alpha=200):
        """Draw a character see-through (a soul), then a halo over its head."""
        self.layer.fill((0, 0, 0, 0))
        gp = Painter(self.pg, self.layer, CHIBI, k=pp.k, ox=pp.ox, oy=pp.oy)
        info = draw(gp)
        self.layer.set_alpha(alpha)
        big.blit(self.layer, (0, 0))
        self.layer.set_alpha(255)
        hx, top = info["head"][0], info["top"]
        pp.stroke(ell(hx, top - 18, info["r"] * 0.62, info["r"] * 0.16, 36), 7, (255, 206, 60))
        return info

    def scaled(self, pp, s, anchor):
        """A painter s times smaller around a world point (for the little uncle beside the big car)."""
        k2 = pp.k * s
        sx, sy = pp.ox + anchor[0] * Z * pp.k, pp.oy + anchor[1] * Z * pp.k
        return Painter(self.pg, pp.surf, CHIBI, k=k2, ox=sx - anchor[0] * Z * k2, oy=sy - anchor[1] * Z * k2)

    def car(self, pp, x, t):
        y = FEET + 6
        bump = abs(math.sin(t * 18)) * 4
        pp.fill(ell(x, y + 6, 280, 22), (0, 0, 0), shade=False, ink=False, grad=False, alpha=45)
        body = spline([(x - 280, y - 70 - bump), (x - 270, y - 160 - bump), (x - 120, y - 190 - bump), (x - 60, y - 300 - bump),
                       (x + 130, y - 300 - bump), (x + 200, y - 190 - bump), (x + 285, y - 170 - bump), (x + 290, y - 70 - bump)], 8)
        pp.fill(body, (70, 130, 220))
        win = spline([(x - 40, y - 280 - bump), (x + 120, y - 280 - bump), (x + 175, y - 195 - bump), (x - 100, y - 195 - bump)], 6)
        pp.fill(win, (190, 226, 246), shade=False)
        pp.oval((x + 40, y - 230 - bump), 34, 36, (236, 190, 150))                    # the Dost at the wheel
        pp.fill(ell(x + 40, y - 232 - bump, 36, 40, 30, math.pi * 1.0, math.pi * 2.0), (60, 36, 26), shade=False)
        pp.oval((x - 270, y - 120 - bump), 18, 14, (255, 236, 150), shade=False)       # headlight (it faces left)
        for wx in (-170, 170):
            pp.oval((x + wx, y - 60), 62, 62, (44, 40, 48), shade=False)
            pp.oval((x + wx, y - 60), 26, 26, (200, 200, 210), shade=False)

    def panel(self, big, n, since, length, t, post):
        pg = self.pg
        s = n - 1
        L, T, w, h = PANEL
        rect = pg.Rect(L * Z, T * Z, w * Z, h * Z)
        sh_ = pg.Surface((w * Z, h * Z), pg.SRCALPHA)
        sh_.fill((0, 0, 0, 60))
        big.blit(sh_, rect.move(14 * Z, 16 * Z))
        big.set_clip(rect)
        for yy in range(rect.top, rect.bottom, 4):
            pg.draw.rect(big, mix((190, 226, 250), (255, 238, 210), (yy - rect.top) / rect.height), (rect.left, yy, rect.width, 4))
        pk = 0.5
        pp = Painter(pg, big, CHIBI, k=pk, ox=rect.centerx - 500 * Z * pk, oy=rect.bottom - 40 * Z - FEET * Z * pk)
        for hx_, hh in ((-260, 380), (60, 520), (900, 460), (1200, 560)):                 # houses far behind
            pp.fill([(hx_, FEET - hh), (hx_ + 240, FEET - hh), (hx_ + 240, FEET), (hx_, FEET)], (236, 214, 190), shade=False)
            for wy in range(FEET - hh + 50, FEET - 80, 110):
                for wx in (40, 140):
                    pp.fill([(hx_ + wx, wy), (hx_ + wx + 60, wy), (hx_ + wx + 60, wy + 55), (hx_ + wx, wy + 55)], (120, 170, 210), shade=False, ink=False)
        pp.fill([(-600, FEET), (1600, FEET), (1600, FEET + 300), (-600, FEET + 300)], (226, 206, 166), shade=False, ink=False)
        ax = 430
        act = lambda **k: Act(t=t, wind=gust(t), **k)
        if s == 1:
            if since < length * 0.5:                                      # sparks at her feet: she leaps
                jump = abs(math.sin(t * 9)) * 70
                jp = Painter(pg, big, CHIBI, k=pk, ox=pp.ox, oy=pp.oy - jump * Z * pk)
                info = lady(jp, CHIBI, ax, act(mood="shock", arm_r=("up", "up", 1), arm_l=("up", "up", 1)), **AUNTY)
                post.append(lambda srf: self.sparks(srf, self.scr(pp, (ax, FEET - 30)), t, 26, 110))
                post.append(lambda srf: self.pop_text(srf, self.f_big, "BHADAAM!", RED, (L + 620, T + 130), since / 0.25, -8))
                if "bhadaam" not in self.cache:
                    self.cache["bhadaam"] = 1
                    self.events.append((t, "crash"))
            else:                                                         # ...and a brand new saree
                lady(pp, CHIBI, ax, act(mood="laugh", arm_r=("present", "present", 1)), saree=(240, 140, 40), blouse=(30, 120, 96), grey=True)
        elif s == 2:
            lady(pp, CHIBI, ax, act(blink=(t % 3) < 0.15), **AUNTY)
            post.append(lambda srf: self.pop_text(srf, self.f_big, "70", ORANGE, (L + 620, T + 220), since / 0.3, -6))
        elif s == 3:                                                      # dancing in the sparks
            jp = Painter(pg, big, CHIBI, k=pk, ox=pp.ox, oy=pp.oy - abs(math.sin(t * 6)) * 40 * Z * pk)
            a = "up" if math.sin(t * 6) > 0 else "shrug"
            lady(jp, CHIBI, ax, act(mood="laugh", arm_r=(a, a, 1), arm_l=("up", "up", 1)), **AUNTY)
            post.append(lambda srf: self.sparks(srf, self.scr(pp, (ax - 300, FEET - 420)), t, 10, 70))
            post.append(lambda srf: self.sparks(srf, self.scr(pp, (ax + 320, FEET - 480)), t + 0.5, 10, 70))
        elif s in (4, 5):                                                 # her soul, waving bye
            rise = 60 * (since / length if s == 4 else 1.0)
            gp_ = Painter(pg, big, CHIBI, k=pk, ox=pp.ox, oy=pp.oy - rise * Z * pk)
            face = act(mood="dead") if s == 4 else act(mood="laugh", arm_r=("up", "up", 1))   # + + eyes as she goes
            self.ghost(big, gp_, lambda g: lady(g, CHIBI, ax + 40, face, **AUNTY))
            if s == 4 and "chime4" not in self.cache:
                self.cache["chime4"] = 1
                self.events.append((t, "chime"))
        elif s == 6:                                                      # the little uncle, the big car, BOOM
            k = since / length
            hit = 0.66
            cx = 1500 - 900 * ease(min(1.0, max(0.0, (k - 0.42) / (hit - 0.42))))
            if k < hit:
                ux = 150 + 300 * min(1.0, k / 0.5)
                up = self.scaled(pp, 0.42, (ux, FEET))
                info = man(up, CHIBI, ux, "uncle", act(mood="angry", walk=t * 9 if k < 0.5 else 0.0, arm_r=("up", "up", 1)))
                hx_, hy_ = info["hands"][1]
                up.limb([(hx_ - 10, hy_ + 30), (hx_ + 20, hy_ - 200)], 10, (150, 96, 50))                  # his stick
            elif k > 0.8:
                ug = self.scaled(pp, 0.42, (520, FEET))
                ug2 = Painter(pg, big, CHIBI, k=ug.k, ox=ug.ox, oy=ug.oy - (300 + (k - 0.8) * 600) * Z * ug.k)
                self.ghost(big, ug2, lambda g: man(g, CHIBI, 520, "uncle", act(mood="laugh", arm_r=("up", "up", 1))))
            self.car(pp, cx + (math.sin(t * 60) * 6 if hit <= k < hit + 0.08 else 0), t)
            if k >= hit:
                def burst(srf):
                    srf.set_clip(pg.Rect(L + 6, T + 6, w - 12, h - 12))
                    self.boom(srf, self.scr(pp, (520, FEET - 150)), (k - hit) * length)
                    srf.set_clip(None)
                post.append(burst)
                if "boom" not in self.cache:
                    self.cache["boom"] = 1
                    self.events.append((t, "crash"))
        elif s == 8:                                                      # the reunion, on a cloud
            for dx, dy, r in ((-260, 40, 120), (-120, -10, 150), (60, -30, 170), (230, 0, 140), (360, 40, 110)):
                pp.oval((500 + dx, FEET - 40 + dy), r, r * 0.8, (255, 255, 255), shade=False)
            self.ghost(big, pp, lambda g: lady(g, CHIBI, 360, act(mood="laugh", arm_r=("present", "present", 1)), **AUNTY))
            self.ghost(big, pp, lambda g: man(g, CHIBI, 640, "uncle", act(mood="laugh", arm_l=("present", "present", 1))))
            hy = FEET - 860 - 20 * math.sin(t * 4)
            for dx in (-34, 34):
                pp.oval((500 + dx, hy), 46, 46, (240, 80, 110), shade=False)
            pp.fill([(500 - 78, hy + 14), (500 + 78, hy + 14), (500, hy + 110)], (240, 80, 110), shade=False, ink=False)
            if "chime8" not in self.cache:
                self.cache["chime8"] = 1
                self.events.append((t, "chime"))
        elif s == 13:                                                     # dadaji alone; dadi's soul waves from a cloud
            pp.fill([(-40, FEET - 760), (560, FEET - 760), (560, FEET + 40), (-40, FEET + 40)], (236, 190, 70))
            pp.fill([(0, FEET - 720), (520, FEET - 720), (520, FEET), (0, FEET)], (250, 242, 226), shade=False)
            man(pp, CHIBI, 260, "dadaji", act(mood="sad", blink=(t % 3) < 0.15))
            for dx, dy, r in ((-150, 30, 90), (0, -10, 120), (150, 30, 90)):
                pp.oval((860 + dx, FEET - 60 + dy), r, r * 0.8, (255, 255, 255), shade=False)
            self.ghost(big, pp, lambda g: lady(g, CHIBI, 860, act(mood="laugh", arm_r=("up", "up", 1)), **DADI))
        big.set_clip(None)
        pg.draw.rect(big, (40, 30, 50), rect, 7 * Z, border_radius=26 * Z)
        if s in (2, 4, 6) or (s == 1 and since < length * 0.5):

            def label(srf):
                img = self.text(self.f_small, "FLASHBACK", (255, 255, 255), 0)
                r = img.get_rect(topleft=(L + 24, T + 18)).inflate(26, 10)
                pg.draw.rect(srf, (40, 30, 60), r, border_radius=14)
                srf.blit(img, img.get_rect(center=r.center))
            post.append(label)

    # ------------------------------------------------------------ overlays on the friends
    def tears(self, surf, p, info, t):
        pg = self.pg
        hx, hy, r = info["head"][0], info["head"][1], info["r"]
        for side in (-1, 1):
            ex, ey = self.scr(p, (hx + side * r * 0.38, hy + r * 0.32))
            rr = r * p.k
            pts_ = [(ex + side * (3 + 4 * math.sin(t * 9 + k)), ey + k * rr * 0.12) for k in range(7)]
            pg.draw.lines(surf, (110, 180, 255), False, pts_, max(4, int(rr * 0.07)))
            for j in range(2):
                d = (t * 2 + j * 0.5) % 1
                pg.draw.circle(surf, (110, 180, 255), (int(ex + side * rr * 0.25), int(ey + rr * 0.8 + d * rr)), max(4, int(rr * 0.06)))

    # ------------------------------------------------------------ a frame
    def frame(self, surf, n, since, length, t, cam):
        pg = self.pg
        s = n - 1
        k, fx, fy = cam
        big = self.big
        big.blit(self.sky, (0, 0))
        p = Painter(pg, big, CHIBI, seed=1, k=k, ox=W * Z / 2 - fx * Z * k, oy=0.42 * H * Z - fy * Z * k)
        self.yard(p, t)
        speaker = LINES[n][0]
        post = []
        info = {}
        for who, ph, per in (("p1", 0.0, 3.4), ("p2", 2.3, 3.7)):
            x = X[who]
            walk = 0.0
            if who == "p1" and s == 11 and since > length * 0.6:            # off he goes, for the crackers
                x -= 900 * ease((since - length * 0.6) / 0.7)
                walk = t * 11
                if "poof11" not in self.cache:
                    self.cache["poof11"] = 1
                    self.events.append((t, "poof"))
            if who == "p1" and s == 12:
                continue
            if who == "p1" and s == 13 and since < 0.7:
                x -= 700 * (1 - ease(since / 0.7))
                walk = t * 11
            talking = who == speaker
            env = self.env[n]
            f = int(max(0.0, since) * 30)
            talk = env[f] if talking and f < len(env) else 0.0
            if who == "p1":
                mood = mood1(s)
            else:
                mood = "shock" if s in (13, 14, 15) else "happy"            # alarmed at "dadaji"
            look = 0.0 if talking or speaker == "intro" else (0.6 if X[speaker] > X[who] else -0.6)
            arm_r, arm_l = self.arms(n, who, since)
            a = Act(t=t, talk=talk, blink=((t + ph) % per) < 0.13, look=look, wind=gust(t), mood=mood, arm_r=arm_r, arm_l=arm_l, walk=walk)
            info[who] = man(p, CHIBI, x, WHO[who], a)
        if panel_for(s) and cam == TWO:
            self.panel(big, n, since, length, t, post)
        surf.blit(pg.transform.smoothscale(big, (W, H)), (0, 0))
        self.frame_no += 1
        finish(pg, surf, self.grains[self.frame_no % 4], self.vignette)
        chibi_demo.Skit.overlay(self, surf, t)
        for draw in post:
            draw(surf)
        d1, d2 = info.get("p1"), info.get("p2")
        scr_info = lambda d: {"head": self.scr(p, d["head"]), "r": d["r"] * k}
        if d1 and s == 7:
            self.tears(surf, p, d1, t)
        if d1 and s >= 13:
            (lx, ly), (rx, ry) = d1["hands"]
            self.box(surf, self.scr(p, ((lx + rx) / 2, (ly + ry) / 2 + 20)))
        if d1 and s == 9:
            hx, top = self.scr(p, (d1["head"][0], d1["top"]))
            self.pop_text(surf, self.f_big, "!!", ORANGE, (hx + 130, top - 10), since / 0.3, 10)
        if d1 and s == 15:
            self.sweat(surf, scr_info(d1))
            hx, top = self.scr(p, (d1["head"][0], d1["top"]))
            self.pop_text(surf, self.f_big, "!!", RED, (hx + 120, top - 10), since / 0.3, 10)
        if d2 and s in (13, 14):
            self.sweat(surf, scr_info(d2))
        if d2 and s == 15:
            self.phone(surf, self.scr(p, d2["hands"][1]), angle=-15)
        self.draw_puffs(surf)

    def scene(self, surf, i, since, length, t):
        cur = shot(i)
        prev = shot(i - 1) if i else cur
        q = ease(since / 0.5)
        cam = cur if q >= 1 else tuple(prev[j] + (cur[j] - prev[j]) * q for j in range(3))
        self.frame(surf, i, since, length, t, cam)
        return (1.0, W / 2, H / 2)


def end_card(sk, frame, t, e):
    sk.frame(frame, len(LINES) - 1, 3.0, 3.0, t, TWO)


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
        sheru.base.Skit.__init__(sk, pg)
        sk.env = [[0.2, 0.5, 0.9, 0.4, 0.2] * 24 for _ in LINES]
        sk.setup(pg)
        (out / "stills").mkdir(parents=True, exist_ok=True)
        surf = pg.Surface((W, H))
        picks = [int(a) for a in sys.argv[sys.argv.index("--still") + 1:]] or range(len(LINES))
        for n in picks:
            sk.cache = {k: v for k, v in sk.cache.items() if not isinstance(v, int)}
            length = 4.0
            sk.scene(surf, n, float(os.environ.get("SINCE", 3.0 if n == 7 else 1.6)), length, 10.0 + n)
            pg.image.save(surf, str(out / "stills" / f"line_{n:02d}.png"))
        print(out / "stills")
    else:
        render(out)
