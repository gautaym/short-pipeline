"""Positive Bhai, part 1: "Talking to a Really POSITIVE Friend". Run: python -m reel_engine.toon.positive_bhai

A dark-comedy skit for a separate channel (not KathaVerse / Stick Katha): a goofy friend confesses one
disaster after another, and his relentlessly positive friend spins every one of them into a win, until the
goofy one offers to start with Positive Bhai's own grandparents. The script is the user's (2026-11-06),
with "sir" changed to "bhai yaar"; the Diwali, process-fast and vision-board lines and the grandparents twist
are added. Everything happens off stage in cartoon flashback panels: sparks, a car bump, two smiling ghosts.
Drawn in the toon look (toon/kit.py); voices, timing and the mix come from the shared skit renderer.
"""
import math
import random
from pathlib import Path

from ..config import REPO_ROOT
from . import sheru as sheru_toon
from ..stick.durvasa import ORANGE, RED, ease
from ..stick.pressure_cooker import render as run
from .kit import (FPS, H, INK, P, S, W, Bean, bean, build_set, chicken, finish, line, mix, poly, shaded_ellipse,
                   soft_shadow)

EPISODE, NAME, MUSIC_SEED = 1, "positive_bhai_hi", 21
SERIES, END_SUB, TAGLINE = "POSITIVE BHAI", "Follow for Part 2", ""
VOICES = {
    "p1": "maya:hi:Ritvik@+2~1.2",          # goofy
    "p2": "maya:hi:Shaunak@+1~1.18",        # warm, encouraging
}
SAD, SOB, PERKY = "maya:hi:Ritvik@+2~1.05", "maya:hi:Ritvik@+2~1.0", "maya:hi:Ritvik@+2~1.2"   # same pitch: one person
LINES = [   # (speaker, spoken line, on-screen caption: punchlines only)
    ("p1", "[sighs] भाई यार... वो कल मैंने पड़ोस वाली आंटी की साड़ी में पटाखे छोड़ दिए।", ""),
    ("p2", "अरे, कोई बात नहीं! तुमने अपनी गलती accept की, accountability ली। Positive होकर सोचो, आज तुम्हारे एक नेक काम की वजह से, आंटी को नई साड़ी मिली होगी!", ""),
    ("p1", "[sighs] अच्छा... वैसे वो सत्तर साल की आंटी थीं।", ""),
    ("p2", "और क्या! सत्तर की उम्र में ज़िंदगी slow और boring हो जाती है। तुम्हारी वजह से उनकी life में excitement और fun आया होगा। बिना Diwali के, Diwali हो गई!", ""),
    ("p1", "[sighs] वो heart attack से मर गई।", ""),
    ("p2", "इसमें तुम क्या कर सकते हो? जिसको जाना है, वो तो चला ही जाएगा। तुमने तो बस, process fast कर दिया।", ""),
    ("p1", "और फिर अंकल मुझे मारने आए, तो मैंने उन्हें गाड़ी से उड़ा दिया।", ""),
    ("p1", "भाई यार... मैं खराब हूँ क्या?", ""),
    ("p2", "बिल्कुल नहीं! Constructive सोचो। दोनों पचहत्तर-पचहत्तर साल के थे। तुमने तो उनका reunion करवा दिया! नहीं तो वो अंकल, पूरी ज़िंदगी अकेले रोते रहते।",
     "TUMNE UNKA *REUNION* KARWA DIYA!"),
    ("p1", "[excited] अच्छा! तो सोच रहा हूँ, माहौल देखकर, और अंकल-आंटियों को ठोक दूँ!", ""),
    ("p2", "[excited] Great idea! चलो, मैं तुम्हें step by step बताता हूँ। पहले, एक vision board बनाते हैं!", ""),
    ("p1", "[excited] Thank you भाई! मैं पटाखे लेकर आता हूँ!", ""),
    ("p2", "ठीक है भाई! All the best!", ""),
    ("p1", "[excited] अरे हाँ भाई, तुम्हारे दादाजी भी तो दादी के जाने के बाद अकेले हैं ना? Reunion वहीं से शुरू करता हूँ!", ""),
    ("p2", "...भाई, positivity की भी एक limit होती है!", "POSITIVITY KI BHI EK *LIMIT* HOTI HAI!"),
    ("p2", "[whispers] तू तो criminal है भाई... Hello, police?", "TU TOH *CRIMINAL* HAI BHAI... HELLO, *POLICE*?"),
]
LINE_VOICE = {0: SAD, 2: SAD, 4: SAD, 6: SAD, 7: SOB, 9: PERKY, 11: PERKY, 13: PERKY}
LINE_FX = {7: "sob"}
VOICE_FX = {}
HOOK = "TALKING TO A REALLY POSITIVE FRIEND"
COMMENT = {5: "COMMENT: TUMHARA DOST BHI AISA HAI?", 15: "TAG KARO APNE SABSE POSITIVE DOST KO"}
CUTS = (2, 4, 6, 8, 9, 13, 15)
LABELS = {"p1": "DOST", "p2": "POSITIVE BHAI"}
SPEAKER_COLOUR = {"p1": (255, 226, 120), "p2": (170, 220, 255)}

FEET = 1300
X1, X2 = 260, 820
GOOFY = Bean(shirt=(250, 168, 40), hair=(84, 46, 30), skin=(240, 200, 160), size=0.9)
POSITIVE = Bean(shirt=(126, 84, 196), hair=(40, 30, 70), skin=(222, 176, 128), size=0.95)
AUNTY = Bean(shirt=(226, 70, 130), hair=(96, 90, 100), skin=(236, 196, 160), size=0.42, buttons=0)
UNCLE = Bean(shirt=(244, 240, 226), hair=(214, 214, 220), skin=(226, 186, 150), size=0.42, buttons=0)
PANEL = (110, 330, 860, 420)
LADY = ("veil", "long_saree", "saree", "side_plait", "bindi")
GENT = ("bald", "specs", "mustache", "grey", "kurta")


class Skit(sheru_toon.Skit):
    def __init__(self, pg):
        sheru_toon.base.Skit.__init__(self, pg)                            # fonts, text and effect helpers
        import numpy as np
        self.big_room = build_set(pg)
        xs, ys = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H), indexing="ij")
        self.vignette = (1 - 0.28 * np.clip((xs ** 2 * 0.8 + ys ** 2 * 0.6) - 0.25, 0, None)).astype(np.float32)
        rng = np.random.default_rng(3)
        self.grains = [rng.normal(0, 3.5, (W, H)).astype(np.float32) for _ in range(4)]
        self.small_room = pg.transform.smoothscale(self.big_room, (W, H))
        finish(pg, self.small_room, self.grains[0], self.vignette)
        self.big = pg.Surface((W * S, H * S))
        self.layer = pg.Surface((W * S, H * S), pg.SRCALPHA)
        self.frame_no = 0

    def talk(self, i, who, since, length, t):
        if LINES[i][0] != who or since > length - 0.3:
            return 0.0
        return abs(math.sin(t * 13)) * (0.65 + 0.35 * math.sin(t * 4.1))

    # ------------------------------------------------------------ pieces
    def hens(self, big, t):
        for hx, hy, ph, sc in ((690, 1600, 0.0, 0.7), (930, 1560, 1.7, 0.62), (620, 1730, 3.1, 0.8)):
            chicken(self.pg, big, hx + math.sin(t * 0.7 + ph) * 18, hy, t, ph, sc, -1 if ph < 3 else 1)

    def sparks(self, surf, at, t, n=18, spread=110):
        pg = self.pg
        rng = random.Random(int(t * FPS))
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(10, spread)
            x, y = at[0] + math.cos(a) * r, at[1] + math.sin(a) * r * 0.7
            c = rng.choice(((255, 230, 90), (255, 150, 40), (255, 90, 60), (255, 255, 220)))
            pg.draw.line(surf, c, (x, y), (x + math.cos(a) * 18, y + math.sin(a) * 18), 4)
        for _ in range(3):
            x, y = at[0] + rng.uniform(-spread, spread), at[1] + rng.uniform(-spread * 0.6, 0)
            pg.draw.circle(surf, (200, 200, 210), (int(x), int(y)), rng.randint(14, 26))

    def ghost(self, big, x, y, look, t, extras, mood="happy", reach=(None, None)):
        """A smiling, see-through soul with a halo, bobbing in the air."""
        pg = self.pg
        bob = math.sin(t * 2.5 + x) * 8
        lay = self.layer
        lay.fill((0, 0, 0, 0))
        pts = bean(pg, lay, x, y + bob, look, mood, 0.0, False, t=t, look=0.0, extras=extras, lift=18, reach=reach)
        lay.set_alpha(225)
        big.blit(lay, (0, 0))
        lay.set_alpha(255)
        hx, top = pts["head"][0], pts["top"]
        r = pg.Rect(0, 0, int(70 * look.size / 0.42 * S), int(18 * look.size / 0.42 * S))
        r.center = P(hx, top - 16)
        pg.draw.ellipse(big, (255, 210, 60), r, int(6 * S))
        return pts

    def car(self, big, x, y, colour, face, driver, t, s=1.0):
        pg = self.pg
        bump = abs(math.sin(t * 18)) * 3
        y = y - bump
        soft_shadow(pg, big, x, y + 4, 130 * s, 16 * s, 90)
        body = [(x - 120 * s, y - 20 * s), (x + 120 * s, y - 20 * s), (x + 124 * s, y - 70 * s), (x + face * 60 * s, y - 74 * s),
                (x + face * 30 * s, y - 120 * s), (x - face * 70 * s, y - 120 * s), (x - face * 100 * s, y - 74 * s), (x - 124 * s, y - 70 * s)]
        poly(pg, big, body, colour, edge=5)
        win = [(x + face * 22 * s, y - 112 * s), (x + face * 50 * s, y - 76 * s), (x - face * 88 * s, y - 76 * s), (x - face * 64 * s, y - 112 * s)]
        poly(pg, big, win, (180, 220, 245), edge=4)
        hx = x - face * 20 * s
        shaded_ellipse(pg, big, hx, y - 92 * s, 18 * s, 18 * s, driver.skin, edge=3)
        poly(pg, big, [(hx - 19 * s, y - 94 * s), (hx - 16 * s, y - 108 * s), (hx, y - 112 * s), (hx + 16 * s, y - 108 * s), (hx + 19 * s, y - 94 * s)],
             driver.hair, edge=3)
        for wx in (-70, 70):
            shaded_ellipse(pg, big, x + wx * s, y - 16 * s, 26 * s, 26 * s, (40, 36, 44), edge=4, gloss=False)
            shaded_ellipse(pg, big, x + wx * s, y - 16 * s, 10 * s, 10 * s, (200, 200, 210), edge=2, gloss=False)
        shaded_ellipse(pg, big, x + face * 118 * s, y - 50 * s, 8 * s, 8 * s, (255, 240, 150), edge=2, gloss=False)

    def panel(self, big, i, since, length, t, post):
        """The flashback: a framed cartoon above the two friends."""
        pg = self.pg
        L, T, w, h = PANEL
        G = T + h - 40
        rect = pg.Rect(*P(L, T), w * S, h * S)
        soft_shadow(pg, big, L + w / 2 + 20, T + h + 24, w / 2, 26, 70)
        big.set_clip(rect)
        sheru_toon.vgrad(pg, big, (rect.x, rect.y, rect.w, rect.h), (196, 226, 250), (255, 236, 206))
        for hx_, hh in ((L + 40, 150), (L + 210, 200), (L + 560, 170), (L + 720, 220)):   # houses far behind
            poly(pg, big, [(hx_, G - hh), (hx_ + 130, G - hh), (hx_ + 130, G), (hx_, G)], (236, 214, 190), edge=3)
            for wy in range(G - hh + 24, G - 30, 50):
                pg.draw.rect(big, (120, 170, 210), (*P(hx_ + 24, wy), 26 * S, 22 * S))
                pg.draw.rect(big, (120, 170, 210), (*P(hx_ + 80, wy), 26 * S, 22 * S))
        poly(pg, big, [(L, G), (L + w, G), (L + w, T + h), (L, T + h)], (226, 204, 160), edge=0)
        ax, aunty_x = L + w / 2, L + 330
        if i == 1:
            if since < length * 0.5:                                          # sparks at the hem, she leaps
                jump = abs(math.sin(t * 9)) * 50
                bean(pg, big, aunty_x, G, AUNTY, "shock", 0.0, False, t=t, extras=LADY, lift=jump,
                     arms=((2.6, 0.3), (2.6, 0.3)))
                post.append(lambda s: self.sparks(s, (aunty_x, G - 20), t, 26, 120))
                post.append(lambda s: self.pop_text(s, self.f_big, "BHADAAM!", RED, (L + 640, T + 120), since / 0.25, -8))
                if "bhadaam" not in self.cache:
                    self.cache["bhadaam"] = 1
                    self.events.append((t, "crash"))
            else:                                                             # ...and a brand new saree
                new = Bean(shirt=(60, 170, 150), hair=AUNTY.hair, skin=AUNTY.skin, size=AUNTY.size, buttons=0)
                bean(pg, big, aunty_x, G, new, "happy", 0.0, False, t=t, extras=LADY,
                     arms=((0.4, 0.3), (2.4, 0.4)))
                post.append(lambda s: self.pop_text(s, self.f_mid, "NAYI SAREE!", (40, 150, 120), (L + 640, T + 120),
                                                    (since - length * 0.5) / 0.3, 6, outline=6))
        elif i == 2:
            bean(pg, big, aunty_x, G, AUNTY, "neutral", 0.0, (t % 3) < 0.15, t=t, extras=LADY)
            post.append(lambda s: self.pop_text(s, self.f_big, "70", ORANGE, (L + 600, T + 170), since / 0.3, -6))
        elif i == 3:                                                          # dancing in the sparks
            bean(pg, big, aunty_x, G, AUNTY, "happy", 0.6, False, t=t, extras=LADY,
                 lift=abs(math.sin(t * 6)) * 30, arms=((2.5 + 0.3 * math.sin(t * 6), 0.4), (2.5 - 0.3 * math.sin(t * 6), 0.4)))
            post.append(lambda s: self.sparks(s, (aunty_x - 120, G - 160), t, 10, 70))
            post.append(lambda s: self.sparks(s, (aunty_x + 140, G - 200), t + 0.5, 10, 70))
            post.append(lambda s: self.pop_text(s, self.f_mid, "FUN!", (220, 60, 140), (L + 640, T + 110), since / 0.3, 8, outline=6))
            if since > length * 0.6:
                post.append(lambda s: self.pop_text(s, self.f_big, "DIWALI!", ORANGE, (L + 640, T + 220), (since - length * 0.6) / 0.3, -6))
        elif i in (4, 5):                                                     # a soul with a halo, waving bye
            rise = (since / length) * 30 if i == 4 else 30
            self.ghost(big, aunty_x + 60, G - rise, AUNTY, t, LADY,
                       reach=(None, (aunty_x + 140, G - rise - 220 + 20 * math.sin(t * 8))))
            if i == 4 and "chime4" not in self.cache:
                self.cache["chime4"] = 1
                self.events.append((t, "chime"))
            if i == 5 and since > length * 0.55:
                post.append(lambda s: self.pop_text(s, self.f_mid, "FAST-TRACK!", ORANGE, (L + 640, T + 110),
                                                    (since - length * 0.55) / 0.3, -6, outline=6))
        elif i == 6:                                                          # uncle storms over; BOOM
            k = since / length
            tiny = Bean(shirt=UNCLE.shirt, hair=UNCLE.hair, skin=UNCLE.skin, size=0.2, buttons=0)
            hit = 0.66
            car_x = L + w + 220 - (w - 230) * ease(min(1.0, max(0.0, (k - 0.42) / (hit - 0.42))))
            if k < hit:
                ux = L + 130 + 200 * min(1.0, k / 0.5)
                stick = (ux + 34, G - 100 + 14 * math.sin(t * 12))
                u = bean(pg, big, ux, G, tiny, "angry", 0.0, False, t=t, extras=GENT,
                         lift=abs(math.sin(t * 10)) * 6, reach=(None, stick))
                hx, hy = u["hands"][1]
                line(pg, big, (hx - 4, hy + 30), (hx + 7, hy - 34), (150, 96, 50), 5)
                post.append(lambda s: self.pop_text(s, self.f_mid, "RUK JA!", RED, (ux + 20, T + 130), 1.0, 0, outline=6))
            self.car(big, car_x + (math.sin(t * 60) * 4 if hit <= k < hit + 0.08 else 0), G, (60, 120, 220), -1, GOOFY, t, 1.4)
            if k > 0.8:                                                       # a small soul floats up, over the roof
                self.ghost(big, L + 300, G - 170 - (k - 0.8) * 100, tiny, t, GENT)
            if k >= hit:
                def burst(s):
                    s.set_clip(pg.Rect(L + 6, T + 6, w - 12, h - 12))           # the boom stays inside the panel
                    self.boom(s, (L + 330, G - 90), (k - hit) * length)
                    s.set_clip(None)
                post.append(burst)
                if "boom" not in self.cache:
                    self.cache["boom"] = 1
                    self.events.append((t, "crash"))
        elif i == 8:                                                          # the reunion, on a cloud
            sheru_toon.cloud(pg, big, ax, G + 10, 0.75)
            a = self.ghost(big, ax - 70, G - 4, AUNTY, t, LADY, reach=(None, (ax, G - 160)))
            self.ghost(big, ax + 70, G - 4, UNCLE, t + 1, GENT, reach=((ax, G - 160), None))
            if since > 0.6:
                hy = T + 70 - 10 * math.sin(t * 4)
                for dx in (-16, 16):
                    shaded_ellipse(pg, big, ax + dx, hy, 21, 21, (240, 80, 110), edge=0, gloss=False, dark=0.9)
                poly(pg, big, [(ax - 36, hy + 6), (ax + 36, hy + 6), (ax, hy + 52)], (240, 80, 110), edge=0)
            if "chime8" not in self.cache:
                self.cache["chime8"] = 1
                self.events.append((t, "chime"))
        elif i == 13:                                                         # Positive Bhai's grandparents
            fr = pg.Rect(*P(ax - 300, T + 30), 300 * S, 300 * S)
            pg.draw.rect(big, (236, 190, 70), fr.inflate(30 * S, 30 * S), border_radius=12 * S)
            pg.draw.rect(big, (250, 240, 220), fr)
            dadi = Bean(shirt=(200, 120, 60), hair=AUNTY.hair, skin=AUNTY.skin, size=0.42, buttons=0)
            dada = Bean(shirt=(240, 240, 230), hair=UNCLE.hair, skin=UNCLE.skin, size=0.5, buttons=0)
            bean(pg, big, ax - 150, T + 320, dada, "worried", 0.0, (t % 3) < 0.15, t=t + 1, extras=GENT)
            pg.draw.rect(big, INK, fr.inflate(30 * S, 30 * S), 5 * S, border_radius=12 * S)
            sheru_toon.cloud(pg, big, ax + 220, T + 300, 0.55)
            self.ghost(big, ax + 220, T + 296, dadi, t, LADY,
                       reach=(None, (ax + 300, T + 130 + 14 * math.sin(t * 8))))
            post.append(lambda s: self.pop_text(s, self.f_small, "DADAJI (AKELE)", INK, (ax - 150, T + h - 20), since / 0.3, 0, outline=0))
        big.set_clip(None)
        pg.draw.rect(big, INK, rect, 8 * S, border_radius=26 * S)

        if not (i in (2, 4, 6) or (i == 1 and since < length * 0.5)):
            return

        def label(s):
            img = self.text(self.f_small, "FLASHBACK", (255, 255, 255), 0)
            r = img.get_rect(topleft=(L + 24, T + 18)).inflate(26, 10)
            pg.draw.rect(s, (40, 30, 60), r, border_radius=14)
            s.blit(img, img.get_rect(center=r.center))
        post.append(label)

    def boom(self, surf, at, e):
        """A cartoon explosion: a spiky orange burst with a yellow heart, BOOM! across it, then smoke."""
        pg = self.pg
        k = ease(min(1.0, e / 0.25))
        fade = max(0.0, 1 - max(0.0, e - 0.9) / 0.5)
        if fade <= 0:
            return
        x, y = at
        lay = pg.Surface((W, H), pg.SRCALPHA)
        for j in range(6):                                                 # smoke rolling out
            a = j * math.pi / 3 + 0.3
            r = 60 + 120 * k + e * 40
            c = (int(x + math.cos(a) * r), int(y + math.sin(a) * r * 0.6))
            pg.draw.circle(lay, (90, 80, 90, 200), c, int(40 + 30 * k) + 4)
            pg.draw.circle(lay, (190, 186, 196, 220), c, int(40 + 30 * k))
        for rad, col in ((170, (240, 90, 40)), (110, (255, 200, 60))):
            pts = [(x + (rad if j % 2 == 0 else rad * 0.55) * k * math.cos(j * math.pi / 8 + 0.2),
                    y + (rad if j % 2 == 0 else rad * 0.55) * k * math.sin(j * math.pi / 8 + 0.2) * 0.8) for j in range(16)]
            pg.draw.polygon(lay, col + (255,), pts)
            pg.draw.polygon(lay, INK + (255,), pts, 6)
        lay.set_alpha(int(255 * fade))
        surf.blit(lay, (0, 0))
        if fade > 0.5:
            self.pop_text(surf, self.f_big, "BOOM!", RED, (x, y), e / 0.2, -8)

    def tears(self, surf, pts, t):
        pg = self.pg
        hx, hy, r = pts["head"][0] + 0.5 * 22 * 0.9, pts["head"][1], pts["r"]
        for side in (-1, 1):
            ex, ey = hx + side * r * 0.36, hy + r * 0.2
            pts_ = [(ex + side * (4 + 6 * math.sin(t * 9 + k)), ey + k * 18) for k in range(7)]
            pg.draw.lines(surf, (110, 180, 255), False, pts_, 9)
            for j in range(2):
                d = (t * 2 + j * 0.5) % 1
                pg.draw.circle(surf, (110, 180, 255), (int(ex + side * 30), int(ey + 120 + d * 160)), 7)

    def thumb(self, surf, at):
        pg = self.pg
        x, y = at
        pg.draw.circle(surf, INK, (int(x), int(y)), 17)
        pg.draw.circle(surf, POSITIVE.skin, (int(x), int(y)), 13)
        r = pg.Rect(0, 0, 16, 30)
        r.midbottom = (x, y - 6)
        pg.draw.rect(surf, POSITIVE.skin, r, border_radius=7)
        pg.draw.rect(surf, INK, r, 4, border_radius=7)

    def box(self, surf, at):
        pg = self.pg
        r = pg.Rect(0, 0, 170, 110)
        r.center = at
        for k in range(5):                                                   # rocket sticks poking out
            x = r.left + 25 + k * 30
            pg.draw.line(surf, INK, (x, r.top), (x + 4, r.top - 46), 5)
            pg.draw.polygon(surf, (240, 70, 70) if k % 2 else (255, 200, 60), [(x - 8, r.top - 40), (x + 14, r.top - 40), (x + 3, r.top - 66)])
        pg.draw.rect(surf, (220, 50, 50), r, border_radius=10)
        pg.draw.rect(surf, (255, 210, 70), (r.left, r.centery - 18, r.width, 36))
        pg.draw.rect(surf, INK, r, 5, border_radius=10)
        img = self.text(self.f_small, "PATAKHE", (200, 30, 30), 0)
        surf.blit(img, img.get_rect(center=r.center))

    def sweat(self, surf, pts):
        x, y = pts["head"][0] - pts["r"] * 0.85, pts["head"][1] - pts["r"] * 0.4
        self.pg.draw.polygon(surf, (120, 190, 255), [(x, y - 26), (x - 14, y + 4), (x + 14, y + 4)])
        self.pg.draw.circle(surf, (120, 190, 255), (int(x), int(y + 6)), 14)

    # ------------------------------------------------------------ the scenes
    def scene(self, surf, i, since, length, t):
        pg = self.pg
        self._t = t
        cam = (1.0, W / 2, H / 2)
        big = self.big
        big.blit(self.big_room, (0, 0))
        post = []
        self.hens(big, t)
        if i in (1, 2, 3, 4, 5, 6, 8, 13):
            self.panel(big, i, since, length, t, post)

        # the goofy friend
        x1, mood1, lift1, reach1, grip1 = X1, "happy", 0.0, (None, None), None
        if i in (0, 2, 4):
            mood1 = "worried"
        elif i in (6, 7):
            mood1 = "worried"
        elif i in (9, 11):
            lift1 = abs(math.sin(t * 7)) * 18
        elif i == 1 or i == 3 or i == 5 or i == 8 or i == 10:
            mood1 = "worried" if i < 8 else "happy"
        if i == 11 and since > length * 0.6:                                  # off he runs, for the crackers
            x1 = X1 - 700 * ease((since - length * 0.6) / 0.6)
            lift1 = abs(math.sin(t * 14)) * 24
            if "poof11" not in self.cache:
                self.cache["poof11"] = 1
                self.events.append((t, "poof"))
        if i == 12:
            x1 = -400
        if i == 15:                                                           # he's scared now
            mood1, lift1 = "shock", abs(math.sin(t * 40)) * 5
        if i >= 13:
            x1 = X1 - (400 * (1 - ease(since / 0.6)) if i == 13 else 0)
            grip1 = (x1, FEET - 250, 62)
        p1 = None
        if x1 > -300:
            p1 = bean(pg, big, x1, FEET, GOOFY, mood1, self.talk(i, "p1", since, length, t), (t % 3.3) < 0.12, t=t,
                      look=0.6, extras=() if mood1 in ("worried", "shock") else ("teeth",), lift=lift1, reach=reach1, grip=grip1)

        # Positive Bhai
        mood2, reach2, look2 = "happy", (None, None), -0.6
        hand_up = (X2 - 175, FEET - 560)
        if i in (1, 3, 5, 8, 10) and since > 0.5:
            reach2 = (hand_up, None)
        if i == 12:
            reach2 = ((X2 - 170 + 40 * math.sin(t * 9), FEET - 640), None)
        if i == 14:
            mood2 = "shock"
        if i == 15:
            mood2, look2 = "shock", 0.6
            reach2 = ((X2 - 110, FEET - 480), None)
        p2 = bean(pg, big, X2, FEET, POSITIVE, mood2, self.talk(i, "p2", since, length, t), (t % 3.7) < 0.12, t=t + 1,
                  look=look2, extras=("specs",), reach=reach2)

        if p1 and i == 7:
            post.append(lambda s: self.tears(s, p1, t))
        if i in (1, 3, 5, 8, 10) and since > 0.5:
            post.append(lambda s: self.thumb(s, p2["hands"][0]))
        if p1 and i >= 13:
            post.append(lambda s: self.box(s, (p1["hands"][0][0] + 62, p1["hands"][0][1] + 30)))
        if i == 14:
            post.append(lambda s: self.sweat(s, p2))
            cam = (1.0 + 0.06 * ease(since / 0.6), X2, FEET - 560)
        if i == 15:
            post.append(lambda s: self.phone(s, (p2["hands"][0][0] - 4, p2["hands"][0][1] + 4), angle=15))
            if p1:
                post.append(lambda s: self.sweat(s, p1))
                post.append(lambda s: self.pop_text(s, self.f_big, "!!", RED, (p1["head"][0] + 120, p1["top"] - 30), since / 0.3, 10))
        if i == 9 and p1:
            post.append(lambda s: self.pop_text(s, self.f_big, "!!", ORANGE, (p1["head"][0] + 120, p1["top"] - 20), since / 0.3, 10))

        surf.blit(pg.transform.smoothscale(big, (W, H)), (0, 0))
        self.frame_no += 1
        finish(pg, surf, self.grains[self.frame_no % 4], self.vignette)
        for draw in post:
            draw(surf)
        self.draw_puffs(surf)
        return cam


def end_card(sk, frame, t, e):
    def draw(lay):
        a = bean(sk.pg, lay, X1, FEET, GOOFY, "happy", 0.0, False, t=t, look=0.6, extras=("teeth",), grip=(X1, FEET - 250, 62))
        bean(sk.pg, lay, X2, FEET, POSITIVE, "worried", 0.0, False, t=t + 1, look=0.6, extras=("specs",),
             reach=((X2 - 110, FEET - 480), None))
        return a
    a = sk.front(draw)
    frame.blit(sk._front, (0, 0))
    sk.box(frame, (a["hands"][0][0] + 62, a["hands"][0][1] + 30))


def render(out_dir: Path) -> Path:
    import sys
    return run(out_dir, sys.modules[__name__])


if __name__ == "__main__":
    import datetime
    import sys
    if "--still" in sys.argv:
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame as pg
        pg.init()
        sk = Skit(pg)
        out = REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME / "stills"
        out.mkdir(parents=True, exist_ok=True)
        surf = pg.Surface((W, H))
        for i in [int(a) for a in sys.argv[sys.argv.index("--still") + 1:]] or range(len(LINES)):
            sk.cache = {k: v for k, v in sk.cache.items() if not isinstance(v, int)}
            length = 4.0
            sk.scene(surf, i, 2.6 if i in (1, 6) else 1.6, length, 10.0 + i)
            pg.image.save(surf, str(out / f"scene_{i:02d}.png"))
        print(out)
    else:
        render(REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME)
