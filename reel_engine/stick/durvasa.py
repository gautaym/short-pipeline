"""Stick Katha, episode 1: Durvasa Rishi vs one grain of rice. Run: python -m reel_engine.stick.durvasa

Review notes. Vana Parva (the Mahabharata, the Pandavas' exile in the forest): Duryodhana sends the
short-tempered sage Durvasa, with his many disciples (popularly ten thousand), to the Pandavas late in
the day, after Draupadi has eaten and the akshaya patra (the Sun's gift, full until she has eaten) can
give no more food. Durvasa goes to bathe in the river and asks for a meal on his return. Draupadi prays
to Shri Krishna, who comes, finds one grain of rice (in some tellings a bit of leaf) stuck to the pot and
eats it; at the river every sage suddenly feels full, and fearing the Pandavas' anger for refusing a meal,
they quietly leave. Sources: wikipedia.org (Durvasa; Akshaya Patra), Vana Parva summaries.
The jokes land on the situation and on the viewer, never on Shri Krishna.
"""
import math
import os
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..core import voice as tts
from ..core.audio import SR, mix, sample, tone, whoosh
from ..core.music import compose
from .kit import Look, Pose, figure, hold, point, shock, stand, walk

W, H, FPS = 1080, 1920, 30
VOICE = "maya:hi:Shaunak@+0~1.12"
PAPER = (248, 242, 228)
NIGHT = (24, 30, 56)
INK = (28, 22, 22)
CHALK = (240, 236, 226)
RED = (226, 54, 40)
ORANGE = (255, 150, 40)
GROUND = 1230                     # feet line; captions sit below it
CAP_Y = 1430
LEAD, GAP, TAIL, END_S = 0.1, 0.22, 0.6, 2.2

DURVASA = Look(head=(245, 225, 205), extras=("beard", "topknot", "tilak"), mood="angry", body=(230, 120, 40))
KRISHNA = Look(head=(80, 140, 230), extras=("feather",), mood="happy", body=(250, 200, 60))
DRAUPADI = Look(extras=("braid",), mood="worried", body=(220, 50, 70), extra_colour={"braid": (230, 60, 60)})
PANDAV = Look(mood="neutral", body=(240, 200, 120))
BHAI = Look(mood="happy", body=(250, 190, 40))

LINES = [
    ("Mythology का सबसे गुस्से वाला इंसान कौन? ये वाला।", "MYTHOLOGY'S *ANGRIEST* MAN?"),
    ("गुस्सा इतना, कि श्राप देना इनकी hobby थी।", "HOBBY: *CURSING PEOPLE*."),
    ("एक बार, Pandavas जंगल में exile काट रहे थे।", "PANDAVAS. *EXILE*. JUNGLE."),
    ("और एक शाम, पहुँच गए Durvasa Rishi। साथ में, दस हज़ार शिष्य।", "PLUS *10,000* DISCIPLES."),
    ("बोले, हम नहाकर आते हैं, खाना ready रखना।", "\"KHAANA *READY* RAKHNA.\""),
    ("Problem? घर में, एक दाना भी नहीं था।", "FOOD AT HOME: *ZERO*."),
    ("Draupadi ने Shri Krishna को याद किया। Krishna आए, बर्तन में बस एक चावल का दाना चिपका था। उन्होंने वही खा लिया।", "ONE GRAIN. *GULP*."),
    ("[excited] और नदी में, दस हज़ार शिष्यों का पेट भर गया!", "10,000 STOMACHS: *FULL*."),
    ("डकार मारी, और चुपचाप निकल लिए।", "*BURP*. AND... BYE."),
    ("और तुम, एक pizza slice के बाद भी पूछते हो, और कुछ है?", "AND YOU: \"*AUR KUCH HAI?*\""),
]
HOOK = "MYTHOLOGY KA SABSE GUSSE WALA INSAAN?"
COMMENT = {5: "GUESS KARO: AB KYA HUA?", 9: "COMMENT: TUMHARA PET KITNE MEIN BHARTA?"}


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


class Episode:
    def __init__(self, pg):
        self.pg = pg
        from ..core.text import font_file
        self.f_cap = pg.font.Font(font_file("Poppins-ExtraBold"), 80)
        self.f_big = pg.font.Font(font_file("Poppins-ExtraBold"), 120)
        self.f_mid = pg.font.Font(font_file("Poppins-ExtraBold"), 62)
        self.f_small = pg.font.Font(font_file("Poppins-SemiBold"), 40)
        self.f_hook = pg.font.Font(font_file("Poppins-ExtraBold"), 96)
        self.rng = random.Random(7)
        self.events = []          # (time, sound)
        self.puffs = []
        self.cache = {}

    # ------------------------------------------------------------ text helpers
    def text(self, font, s, colour, outline=8, edge=INK):
        key = (id(font), s, colour, outline, edge)
        if key not in self.cache:
            from ..core.text import outlined
            self.cache[key] = outlined(self.pg, font, s, colour, outline, edge)
        return self.cache[key]

    def pop_text(self, surf, font, s, colour, centre, k, angle=0.0, outline=8):
        """Text that pops in (overshoot) as k goes 0 -> 1."""
        if k <= 0:
            return
        img = self.text(font, s, colour, outline)
        sc = 1.0 + 0.5 * (1 - ease(k * 1.6)) if k < 0.6 else 1.0
        sc *= min(1.0, k * 4)
        if sc <= 0.02:
            return
        img = self.pg.transform.rotozoom(img, angle, sc)
        surf.blit(img, img.get_rect(center=centre))

    def pill(self, surf, s, y, k):
        if k <= 0:
            return
        from ..core.text import fit_width
        word = fit_width(self.pg, self.text(self.f_mid, s, (255, 220, 120), 6), W - 140)
        pill = self.pg.Surface((word.get_width() + 60, word.get_height() + 12), self.pg.SRCALPHA)
        self.pg.draw.rect(pill, (20, 8, 4, 220), pill.get_rect(), border_radius=pill.get_height() // 2)
        self.pg.draw.rect(pill, (255, 196, 90), pill.get_rect(), 5, border_radius=pill.get_height() // 2)
        pill.blit(word, word.get_rect(center=pill.get_rect().center))
        sc = 1 + 0.2 * (1 - ease(k * 3)) + 0.03 * math.sin(k * 30)
        pill = self.pg.transform.smoothscale(pill, (int(pill.get_width() * sc), int(pill.get_height() * sc)))
        surf.blit(pill, pill.get_rect(center=(W / 2, y)))

    def bubble(self, surf, s, at, tail, k):
        if k <= 0:
            return
        word = self.text(self.f_mid, s, INK, 0)
        r = word.get_rect(center=at).inflate(60, 40)
        sc = min(1.0, k * 5)
        if sc < 1:
            r = r.inflate(-r.width * (1 - sc), -r.height * (1 - sc))
        self.pg.draw.polygon(surf, (255, 255, 255), [(r.centerx - 30, r.bottom - 4), (r.centerx + 30, r.bottom - 4), tail])
        self.pg.draw.polygon(surf, INK, [(r.centerx - 30, r.bottom - 2), tail, (r.centerx + 30, r.bottom - 2)], 6)
        self.pg.draw.rect(surf, (255, 255, 255), r, border_radius=34)
        self.pg.draw.rect(surf, INK, r, 6, border_radius=34)
        if sc >= 1:
            surf.blit(word, word.get_rect(center=r.center))

    def tag(self, surf, head, sub, at, k):
        if k <= 0:
            return
        a = self.text(self.f_mid, head, (255, 255, 255), 0)
        b = self.text(self.f_small, sub, (255, 210, 120), 0)
        box = self.pg.Surface((max(a.get_width(), b.get_width()) + 50, a.get_height() + b.get_height() + 24), self.pg.SRCALPHA)
        box.fill((30, 24, 52, 230))
        self.pg.draw.rect(box, (255, 196, 90), (0, 0, 10, box.get_height()))
        box.blit(a, (28, 6))
        box.blit(b, (28, 6 + a.get_height()))
        x = at[0] - (1 - ease(k * 2.5)) * (box.get_width() + at[0] + 40)
        surf.blit(box, (x, at[1]))

    def caption(self, surf, s, since, length, light):
        """Word-by-word caption: each word pops in, *starred* words in orange."""
        words = s.split()
        n = len(words)
        spread = max(0.5, length * 0.55)
        imgs = []
        for i, wd in enumerate(words):
            hl = "*" in wd
            colour = ORANGE if hl else (255, 255, 255)
            imgs.append((self.text(self.f_cap, wd.replace("*", ""), colour, 8, INK), i * spread / n))
        rows, row, width = [], [], 0
        for img, at in imgs:
            if row and width + img.get_width() + 22 > W - 100:
                rows.append(row)
                row, width = [], 0
            row.append((img, at))
            width += img.get_width() + 22
        rows.append(row)
        y = CAP_Y - (len(rows) - 1) * 50
        for row in rows:
            total = sum(i.get_width() for i, _ in row) + 22 * (len(row) - 1)
            x = (W - total) / 2
            for img, at in row:
                k = (since - at) / 0.16
                if k > 0:
                    sc = 1.0 + 0.35 * (1 - ease(k)) if k < 1 else 1.0
                    im = img if sc == 1 else self.pg.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
                    surf.blit(im, im.get_rect(center=(x + img.get_width() / 2, y)))
                x += img.get_width() + 22
            y += 100

    # ------------------------------------------------------------ scenery
    def paper(self, surf, colour=PAPER, ground=True, ink=INK):
        surf.fill(colour)
        if ground:
            self.pg.draw.line(surf, ink, (0, GROUND + 4), (W, GROUND + 4), 6)

    def trees(self, surf, ink, t, xs=(90, 300, 820, 1000), y=GROUND):
        for i, x in enumerate(xs):
            sway = math.sin(t * 1.3 + i) * 6
            self.pg.draw.line(surf, ink, (x, y), (x + sway * 0.3, y - 260), 10)
            for j, (dx, dy, r) in enumerate(((0, -300, 90), (-60, -250, 70), (60, -250, 70))):
                c = (int(x + dx + sway), int(y + dy))
                self.pg.draw.circle(surf, (110, 170, 90) if ink == INK else (40, 70, 60), c, r)
                self.pg.draw.circle(surf, ink, c, r, 6)

    def hut(self, surf, x, ink):
        y = GROUND
        self.pg.draw.rect(surf, (210, 170, 110), (x - 120, y - 170, 240, 170))
        self.pg.draw.rect(surf, ink, (x - 120, y - 170, 240, 170), 6)
        self.pg.draw.polygon(surf, (190, 140, 70), [(x - 160, y - 165), (x, y - 300), (x + 160, y - 165)])
        self.pg.draw.polygon(surf, ink, [(x - 160, y - 165), (x, y - 300), (x + 160, y - 165)], 6)
        self.pg.draw.rect(surf, ink, (x - 35, y - 110, 70, 110))

    def moon(self, surf):
        self.pg.draw.circle(surf, (250, 240, 200), (860, 300), 70)
        self.pg.draw.circle(surf, NIGHT, (890, 280), 62)
        rng = random.Random(3)
        for _ in range(40):
            self.pg.draw.circle(surf, (230, 230, 255), (rng.randint(0, W), rng.randint(80, 900)), rng.choice((2, 3)))

    def river(self, surf, t, y0=GROUND - 40):
        self.pg.draw.rect(surf, (60, 110, 190), (0, y0, W, H - y0))
        for row in range(6):
            y = y0 + 30 + row * 45
            pts = [(x, y + 8 * math.sin(x / 60 + t * 3 + row)) for x in range(0, W + 20, 20)]
            self.pg.draw.lines(surf, (170, 210, 250), False, pts, 4)

    def pot(self, surf, at, tipped=0.0, ink=INK, glow=0.0):
        p = self.pg.Surface((180, 150), self.pg.SRCALPHA)
        self.pg.draw.ellipse(p, (170, 110, 60), (10, 30, 160, 115))
        self.pg.draw.ellipse(p, ink, (10, 30, 160, 115), 6)
        self.pg.draw.ellipse(p, (90, 55, 30), (40, 18, 100, 34))
        self.pg.draw.ellipse(p, ink, (40, 18, 100, 34), 6)
        p = self.pg.transform.rotate(p, -100 * tipped)
        surf.blit(p, p.get_rect(center=at))

    def steam(self, surf, at, t, rate=4, big=1.0, ink=INK):
        if int(t * FPS) % rate == 0:
            self.puffs.append([at[0] + self.rng.choice((-1, 1)) * 40 * big, at[1], self.rng.uniform(-1.5, 1.5), 0.0, big])

    def draw_puffs(self, surf):
        alive = []
        for q in self.puffs:
            q[0] += q[2]
            q[1] -= 5 * q[4]
            q[3] += 1 / FPS
            if q[3] < 0.9:
                alive.append(q)
                r = int((12 + 28 * q[3]) * q[4])
                s = self.pg.Surface((r * 2 + 4, r * 2 + 4), self.pg.SRCALPHA)
                a = int(230 * (1 - q[3] / 0.9))
                self.pg.draw.circle(s, (255, 255, 255, a), (r + 2, r + 2), r)
                self.pg.draw.circle(s, (110, 110, 110, a), (r + 2, r + 2), r, 4)
                surf.blit(s, (q[0] - r, q[1] - r))
        self.puffs = alive

    def zap(self, surf, a, b, t):
        rng = random.Random(int(t * 20))
        pts = [a]
        for k in range(1, 8):
            x = a[0] + (b[0] - a[0]) * k / 8 + rng.uniform(-30, 30)
            y = a[1] + (b[1] - a[1]) * k / 8 + rng.uniform(-30, 30)
            pts.append((x, y))
        pts.append(b)
        self.pg.draw.lines(surf, (255, 240, 80), False, pts, 16)
        self.pg.draw.lines(surf, (255, 255, 255), False, pts, 6)

    def army(self, surf, t, n_rows, x0, x1, ink, look=None, phase_speed=9.0, front=GROUND - 60, depth=260,
             appear=1.0, belly=0.0, mood="angry", tiptoe=False, burp=0.0):
        """Rows of tiny identical disciples: farther rows smaller and higher."""
        look = look or Look(mood=mood, extras=("topknot",), width=7, body=(230, 120, 40))
        look.mood = mood
        rng = random.Random(11)
        for row in range(n_rows):
            k = row / max(1, n_rows - 1)
            s = 0.55 - 0.3 * k
            y = front - depth * k
            gap = 70 * s / 0.4
            count = int((x1 - x0) / gap) + 1
            for i in range(count):
                if rng.random() > appear:
                    continue
                x = x0 + i * gap + (row % 2) * gap / 2
                ph = t * phase_speed + i * 0.7 + row
                if tiptoe:
                    pose = walk(ph * 0.5, tiptoe=True)
                elif phase_speed:
                    pose = walk(ph, 0.45, angry=mood == "angry")
                else:
                    pose = stand(t + i)
                pose.belly = belly
                face = -1 if phase_speed < 0 else 1
                figure(self.pg, surf, x, y, s, pose, look, ink, face=face, t=t)

    # ------------------------------------------------------------ scenes
    def scene(self, surf, i, since, length, t):
        pg = self.pg
        k = since / max(0.1, length)
        cam = (1.0, W / 2, H / 2)
        if i == 0:                                         # Durvasa stomps towards us, steam and STOMPs
            self.paper(surf)
            for j in range(12):                            # the ground dashes stream by: a treadmill walk
                x = (j * 120 - since * 260) % (W + 120) - 60
                pg.draw.line(surf, (180, 165, 150), (x, GROUND + 40), (x + 50, GROUND + 40), 6)
            ph = since * math.pi / 0.45
            pts = figure(pg, surf, 400, GROUND, 1.7, walk(ph, 0.55, angry=True), DURVASA, INK, 1, t)
            self.steam(surf, pts["head"], t, 3, 1.4)
            if int(since / 0.45) != int((since - 1 / FPS) / 0.45):
                self.events.append((t, "stomp"))
            if abs(math.cos(ph)) > 0.93 and since > 0.2:
                self.pop_text(surf, self.f_big, "STOMP!", RED, (800, 1020), 1.0, 8)
                cam = (1.03, 540, 900)
            self.tag(surf, "DURVASA RISHI", "Gussa level: 9000", (530, 720), (since - 0.5) / 0.6)
        elif i == 1:                                       # cursing as a hobby
            self.paper(surf)
            pts = figure(pg, surf, 360, GROUND, 1.8, point(t), DURVASA, INK, 1, t)
            self.steam(surf, pts["head"], t, 4, 1.2)
            hit = since > 0.5
            vic = Look(mood="shock" if hit else "happy", head=(90, 90, 90) if hit else (255, 255, 255))
            vp = figure(pg, surf, 900, GROUND, 1.0, shock(t) if hit else stand(t), vic, INK, -1, t)
            if 0.5 < since < 1.0:
                self.zap(surf, pts["hands"][0], vp["head"], t)
            if since > 0.5 and "zap1" not in self.cache:
                self.cache["zap1"] = 1
                self.events.append((t, "zap"))
            for j in range(3):                             # bystanders running for their lives
                x = 700 - (since * 500) - j * 90 if j % 2 else 650 + since * 450 + j * 60
                figure(pg, surf, x, GROUND, 0.7, walk(t * 14 + j, 0.6), Look(mood="shock"), INK, -1 if j % 2 else 1, t)
            n = int(min(1.0, k * 1.2) * 999)
            self.pop_text(surf, self.f_mid, f"CURSES THIS WEEK: {n}", RED, (W / 2, 330), 1.0)
            if hit:
                self.pop_text(surf, self.f_big, "CURSED!", RED, (760, 600), (since - 0.5) / 0.4, -6)
        elif i == 2:                                       # the Pandavas in the forest
            self.paper(surf, (238, 244, 222))
            self.trees(surf, INK, t)
            self.hut(surf, 900, INK)
            xs = (120, 250, 380, 520, 640)
            for j, x in enumerate(xs):
                pose = stand(t + j)
                if j == 1:
                    pose.belly = 0.6                       # Bhima
                figure(pg, surf, x, GROUND, 1.05 if j != 1 else 1.25, pose, PANDAV, INK, 1, t)
            figure(pg, surf, 780, GROUND, 1.0, hold(t), DRAUPADI, INK, -1, t)
            self.pot(surf, (700, GROUND - 205))
            self.tag(surf, "THE PANDAVAS", "Exile mode: ON", (40, 380), (since - 0.3) / 0.6)
        elif i == 3:                                       # night: Durvasa plus ten thousand
            self.paper(surf, NIGHT, ink=CHALK)
            self.moon(surf)
            z = 1.55 - 0.55 * ease(k * 1.6)
            self.army(surf, since, 5, -40, W + 40, CHALK, front=GROUND - 40, appear=min(1.0, 0.25 + k * 1.4))
            x = W - 260 * ease(since / 0.9) - 120
            pts = figure(pg, surf, x + 60, GROUND + 6, 1.45, walk(since * 7, 0.5, angry=True), DURVASA, CHALK, -1, t)
            self.steam(surf, pts["head"], t, 4, 1.1)
            cam = (z, pts["head"][0], 900)
            if since > length * 0.45:
                if "stamp" not in self.cache:
                    self.cache["stamp"] = 1
                    self.events.append((t, "drop"))
                self.pop_text(surf, self.f_big, "x 10,000", (255, 210, 80), (W / 2, 460), (since - length * 0.45) / 0.4, -5)
        elif i == 4:                                       # "khaana ready rakhna"
            self.paper(surf, NIGHT, ink=CHALK)
            self.moon(surf)
            self.river(surf, t, GROUND + 120)
            self.army(surf, since, 3, 80 - since * 220, 700 - since * 220, CHALK, front=GROUND - 30, depth=160,
                      phase_speed=-9)
            pts = figure(pg, surf, 720, GROUND + 6, 1.45, point(t), DURVASA, CHALK, -1, t)
            self.steam(surf, pts["head"], t, 5, 1.0)
            self.bubble(surf, "KHAANA READY!", (560, 620), (pts["head"][0] - 30, pts["head"][1] - 60), (since - 0.3) / 0.3)
        elif i == 5:                                       # the empty pot
            self.paper(surf, (40, 40, 66), ink=CHALK)
            for j, x in enumerate((110, 230, 350, 470, 590)):
                p = shock(t + j)
                if j == 1:
                    p.belly = 0.6
                pts = figure(pg, surf, x, GROUND, 0.95 if j != 1 else 1.15, p, Look(mood="shock", body=(240, 200, 120)), CHALK, 1, t)
                if (since * 3 + j) % 1.5 < 0.7:            # sweat drops
                    hx, hy = pts["head"]
                    pg.draw.circle(surf, (120, 190, 255), (int(hx + 45), int(hy - 10 + (since * 120) % 60)), 9)
            figure(pg, surf, 890, GROUND, 1.0, shock(t), Look(extras=("braid",), mood="shock", body=(220, 50, 70)), CHALK, -1, t)
            tip = ease(since / 0.4)
            self.pot(surf, (720, GROUND - 60), tip, CHALK)
            if since < 0.1 and "drop5" not in self.cache:
                self.cache["drop5"] = 1
                self.events.append((t, "scratch"))
            self.pop_text(surf, self.f_big, "0 GRAINS", RED, (W / 2, 640), (since - 0.4) / 0.4, 4)
            cam = (1.0 + 0.02 * math.sin(since * 50) * max(0, 1 - since), W / 2, H / 2)
        elif i == 6:                                       # Shri Krishna and one grain of rice
            self.paper(surf, (252, 236, 200))
            for r in range(5):                             # a soft golden glow behind him
                pg.draw.circle(surf, (255, 225 - r * 8, 150 - r * 10), (330, 860), 380 - r * 60)
            enter = ease(since / 0.8)
            kp = figure(pg, surf, -100 + 430 * enter, GROUND, 1.5, walk(since * 6, 0.4) if enter < 1 else stand(t),
                        KRISHNA, INK, 1, t)
            figure(pg, surf, 850, GROUND, 1.3, hold(t), DRAUPADI, INK, -1, t)
            potat = (700, GROUND - 270)
            self.pot(surf, potat)
            g0 = 0.3
            gk = (since / length - g0) / 0.45
            if gk < 0:
                gx, gy = potat[0] - 40, potat[1] - 60
            else:
                q = ease(gk)
                gx = potat[0] - 40 + (kp["mouth"][0] - potat[0] + 40) * q
                gy = potat[1] - 60 + (kp["mouth"][1] - potat[1] + 60) * q - math.sin(q * math.pi) * 220
            if gk < 1:
                for r, a in ((40, 50), (24, 110)):
                    glow = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
                    pg.draw.circle(glow, (255, 240, 150, a), (r, r), r)
                    surf.blit(glow, (gx - r, gy - r))
                pg.draw.ellipse(surf, (255, 255, 245), (gx - 9, gy - 5, 18, 10))
                pg.draw.ellipse(surf, INK, (gx - 9, gy - 5, 18, 10), 2)
                if gk < 0:
                    self.pop_text(surf, self.f_mid, "1 GRAIN", ORANGE, (potat[0], potat[1] - 170), (since - 0.6) / 0.3)
            else:
                self.pop_text(surf, self.f_big, "GULP!", RED, (420, 520), (gk - 1) * 3, -8)
                cam = (1.0 + 0.06 * max(0.0, 1 - (gk - 1) * 3), kp["head"][0], kp["head"][1])
                if "gulp" not in self.cache:
                    self.cache["gulp"] = 1
                    self.events.append((t, "gulp"))
            if gk < 0 and "grain" not in self.cache and since > 0.6:
                self.cache["grain"] = 1
                self.events.append((t, "pop"))
        elif i == 7:                                       # at the river: ten thousand full stomachs
            self.paper(surf, NIGHT, ink=CHALK)
            self.moon(surf)
            self.river(surf, t, GROUND + 80)
            b = ease(since / (length * 0.7))
            self.army(surf, since, 4, -20, W + 20, CHALK, front=GROUND + 10, depth=220, phase_speed=0, belly=b, mood="shock")
            d = figure(pg, surf, 540, GROUND + 70, 1.5, Pose(belly=b, arms=(0.6, 1.2, -0.6, -1.2)),
                       Look(head=DURVASA.head, extras=DURVASA.extras, mood="shock", body=DURVASA.body), CHALK, 1, t)
            if b > 0.3:
                self.pop_text(surf, self.f_big, "FULL?!", (255, 210, 80), (W / 2, 470), (b - 0.3) / 0.2, 5)
        elif i == 8:                                       # burp, and tiptoe away
            self.paper(surf, NIGHT, ink=CHALK)
            self.moon(surf)
            self.river(surf, t, GROUND + 80)
            if since < 0.6:
                self.pop_text(surf, self.f_big, "BURRRP!", (255, 210, 80), (W / 2, 520), since / 0.25, -6)
                cam = (1.0 + 0.03 * math.sin(since * 60), W / 2, H / 2)
                if "burp" not in self.cache:
                    self.cache["burp"] = 1
                    self.events.append((t, "burp"))
            off = max(0.0, since - 0.5) * 230
            self.army(surf, since, 3, -20 + off, W + 20 + off, CHALK, front=GROUND + 10, depth=160, phase_speed=4,
                      belly=0.8, mood="shy", tiptoe=True)
            shy = Look(head=DURVASA.head, extras=DURVASA.extras, mood="shy", blush=1.0, body=DURVASA.body)
            pts = figure(pg, surf, 540 + off * 0.9, GROUND + 70, 1.5, Pose(**{**walk(since * 5, tiptoe=True).__dict__, "belly": 0.8}),
                         shy, CHALK, 1, t)
            self.steam(surf, pts["head"], t, 10, 0.4)
        elif i == 9:                                       # you, after one slice of pizza
            self.paper(surf, (236, 232, 245))
            pg.draw.rect(surf, (120, 90, 170), (560, GROUND - 230, 470, 230), border_radius=30)   # a sofa
            pg.draw.rect(surf, INK, (560, GROUND - 230, 470, 230), 6, border_radius=30)
            pg.draw.rect(surf, (140, 110, 190), (540, GROUND - 330, 90, 330), border_radius=30)
            pg.draw.rect(surf, INK, (540, GROUND - 330, 90, 330), 6, border_radius=30)
            pts = figure(pg, surf, 330, GROUND, 1.7, hold(t), BHAI, INK, 1, t)
            hx, hy = pts["hands"][0]
            box = pg.Rect(0, 0, 220, 30)
            box.midleft = (hx - 40, hy)
            pg.draw.rect(surf, (230, 200, 150), box)       # an empty pizza box with crumbs
            pg.draw.rect(surf, INK, box, 5)
            for c in range(5):
                pg.draw.circle(surf, (200, 140, 60), (box.left + 30 + c * 38, box.top - 4), 5)
            self.bubble(surf, "AUR KUCH HAI?", (560, 560), (pts["head"][0] + 40, pts["head"][1] - 60), (since - 0.9) / 0.3)
        self.draw_puffs(surf)
        return cam


def render(out_dir: Path) -> Path:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    tts.prepare([l for l, _ in LINES], VOICE.partition("@")[0])
    clips = [tts.say(l, VOICE) for l, _ in LINES]
    starts, t = [], LEAD
    for c in clips:
        starts.append(t)
        t += len(c) / SR + GAP
    story_end = t + TAIL
    total = story_end + END_S
    ep = Episode(pg)
    out_dir.mkdir(parents=True, exist_ok=True)
    silent = out_dir / "_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
                           "-crf", "19", str(silent)], stdin=subprocess.PIPE)
    frame = pg.Surface((W, H))
    world = pg.Surface((W, H))
    last = -1
    for f in range(int(total * FPS)):
        t = f / FPS
        if t < story_end:
            i = max(0, max(j for j, s in enumerate(starts) if s <= t) if t >= starts[0] else 0)
            nxt = starts[i + 1] if i + 1 < len(starts) else story_end
            since, length = t - starts[i], nxt - starts[i]
            if i != last:
                last = i
                ep.puffs.clear()
                if i:
                    ep.events.append((t, "cut"))
            z, cx, cy = ep.scene(world, i, since, length, t)
            punch = 1.0 + 0.07 * max(0.0, 1 - since / 0.25) if i else 1.0      # each cut kicks in
            z *= punch
            if z > 1.001:
                cw, ch = W / z, H / z
                x0 = min(max(0, cx - cw / 2), W - cw)
                y0 = min(max(0, cy - ch / 2), H - ch)
                frame.blit(pg.transform.smoothscale(world.subsurface((x0, y0, cw, ch)), (W, H)), (0, 0))
            else:
                frame.blit(world, (0, 0))
            light = i in (0, 1, 2, 6, 9)
            ep.caption(frame, LINES[i][1], since, length, light)
            if i == 0:                                     # the hook, on the very first frame
                from ..core.text import fit_width, wrap
                y = 170
                for line in wrap(ep.f_hook, HOOK, W - 120)[:3]:
                    img = fit_width(pg, ep.text(ep.f_hook, line, (255, 220, 90), 9), W - 80)
                    frame.blit(img, img.get_rect(midtop=(W / 2, y)))
                    y += img.get_height() - 22
                tagl = ep.text(ep.f_small, "S T I C K   K A T H A   ·   E P   1", (226, 54, 40), 0)
                frame.blit(tagl, tagl.get_rect(midtop=(W / 2, 120)))
            if i in COMMENT:
                ep.pill(frame, COMMENT[i], 250 if i != 9 else 330, (since - 0.5) / 0.6)
        else:                                              # end card: the series, and Durvasa still stomping
            e = t - story_end
            ep.paper(frame)
            pts = figure(pg, frame, 300 + e * 240, GROUND, 1.2, walk(e * 7, 0.55, angry=True), DURVASA, INK, 1, t)
            ep.steam(frame, pts["head"], t, 3, 1.0)
            ep.draw_puffs(frame)
            ep.pop_text(frame, ep.f_big, "STICK KATHA", RED, (W / 2, 560), e / 0.4)
            ep.pop_text(frame, ep.f_mid, "Episode 1  ·  Follow for more", INK, (W / 2, 700), (e - 0.3) / 0.4, outline=0)
            if e < 0.3:
                veil = pg.Surface((W, H))
                veil.set_alpha(int(255 * (1 - e / 0.3)))
                frame.blit(veil, (0, 0))
        ff.stdin.write(pg.image.tobytes(frame, "RGB"))
    ff.stdin.close()
    ff.wait()

    rng = np.random.default_rng(5)
    bank = {
        "stomp": sample("punch", 0.55),
        "zap": sample("glitch", 0.6),
        "drop": sample("drop", 0.7),
        "scratch": sample("scratch", 0.6),
        "pop": sample("pop", 0.6),
        "cut": whoosh(0.35, 300, 2500, 0.35),
        "gulp": (tone(320, 0.35, 6, harm=0.6, chirp=-0.6) * 0.6),
        "burp": (np.concatenate([tone(85 + rng.uniform(-8, 8), 0.06, 1, harm=0.9, noise=0.4) for _ in range(14)]) * 0.7),
    }
    events = [(tt, name, 0) for tt, name in ep.events]
    bed = compose(total, 41, "chiptune")
    speech = list(zip(starts, clips))
    pcm = mix(events, bank, total, bed=bed, bed_level=0.7, speech=speech)
    wav = out_dir / "_audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    final = out_dir / "stick_durvasa_hi.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(final)], check=True)
    silent.unlink()
    wav.unlink()
    print(f"{final} ({total:.1f}s)")
    return final


if __name__ == "__main__":
    import datetime
    render(REPO_ROOT / "out" / datetime.date.today().isoformat() / "stick_durvasa_hi")
