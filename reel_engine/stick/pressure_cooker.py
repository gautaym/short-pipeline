"""Stick Katha, episode 2: "Sheru". Run: python -m reel_engine.stick.pressure_cooker

A comedy skit, our own take on a premise the user saw in another reel (2026-11-05): a boy yells at his
friend on the phone, Bhagwan Vishnu reminds him from the clouds that anger is no good, Chitragupt Ji reads
out his anger account, the boy apologises, and the friend's reply sets him off again. The dialogue, the
"khaata" gag fills the part the user did not remember. The jokes land on the boy; Bhagwan Vishnu and Chitragupt
Ji stay dignified (and dryly funny).
"""
import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..core import voice as tts
from ..core.audio import SR, mix, sample, tone, whoosh
from ..core.music import compose
from .durvasa import CHALK, Episode, FPS, GROUND, H, INK, ORANGE, PAPER, RED, W, ease
from .kit import Look, Pose, facepalm, figure, hold, namaste, on_phone, shock, stand, throw

LEAD, GAP, TAIL, END_S = 0.1, 0.25, 0.9, 2.2
VOICES = {
    "boy": "maya:hi:Shaunak@+0~1.1",
    "friend": "maya:hi:Ritvik@+0~1.1",
    "vishnu": "maya:hi:Abhay@-2~0.95",
    "chitragupt": "maya:hi:Satvik@+1~1.05",
}
KHAATA = [   # (what Chitragupt Ji says, the entry written in the khaata)
    ("इस साल।", ""),
    ("सत्ताईस बार गुस्सा।", "27x GUSSA"),
    ("तीन phone तोड़े।", "3 PHONE TODE"),
    ("Ludo हारकर, board खिड़की से फेंका।", "LUDO HAARA: BOARD KHIDKI SE"),
    ("Mummy को बोला पढ़ रहा हूँ, और चार घंटे reels देखीं।", "'PADH RAHA HOON' = 4 GHANTE REELS"),
    ("दोस्त का charger लिया, आज तक नहीं लौटाया।", "DOST KA CHARGER: AAJ TAK NAHI LAUTAYA"),
    ("Gym की fees भरी, गए सिर्फ़ दो दिन।", "GYM FEES BHARI, GAYE 2 DIN"),
    ("Group में on the way लिखा, जब नहाए भी नहीं थे।", "'ON THE WAY' (NAHAAYE BHI NAHI THE)"),
    ("और ग्यारह शादियों में, सिर्फ़ खाना खाने गए।", "11 SHAADIYAAN: SIRF KHAANE KE LIYE"),
]
LINES = [   # (speaker, spoken line, on-screen caption: only the punchlines get one)
    ("boy", "एक लड़की क्या मिल गई, अपने दोस्त को ही भूल गया!", ""),
    ("boy", "अब अगर मैंने तुझे phone किया ना, तो मेरे नाम का कुत्ता पाल लेना!", "*MERE NAAM KA KUTTA* PAAL LENA!"),
    ("vishnu", "हे पुत्र। किसी के लिए हिंसा की भावना रखना, बुरी बात है।", ""),
    ("boy", "ये तो मैंने कहीं नहीं पढ़ा, प्रभु।", ""),
    ("vishnu", "इसका मतलब, तुमने गीता भी नहीं पढ़ी। चित्रगुप्त!", "*CHITRAGUPT*!"),
    ("chitragupt", "प्रणाम प्रभु। इस बालक का खाता खोलता हूँ।", ""),
    ("boy", "अरे यार प्रभु, आप इन्हें ही क्यों भेज देते हो? ये बहुत detail में जाते हैं!", "YE BAHUT *DETAIL MEIN* JAATE HAIN!"),
    ("chitragupt", " ".join(spoken for spoken, _ in KHAATA), ""),
    ("boy", "बस बस! नहीं होऊँगा गुस्सा, और गीता भी पढ़ लूँगा।", ""),
    ("boy", "और आप सही कहते हो प्रभु। मुझे उससे माफ़ी माँगनी चाहिए।", ""),
    ("boy", "Sorry भाई, मैंने कुछ ज़्यादा ही बोल दिया।", ""),
    ("friend", "हाँ यार, कोई बात नहीं! तू शाम को घर आ जा, मैं तेरे लिए Sheru मँगवा के रखता हूँ।", ""),
    ("boy", "Sheru? ये क्या है bro?", "*SHERU*? YE KYA HAI BRO?"),
    ("friend", "[excited] अरे, नया dog food है! तू ही तो बोला था, कि तेरे नाम का कुत्ता पाल लूँ। तो तेरे लिए ही मँगवाया है!",
     "TERE LIYE HI *MANGWAYA* HAI!"),
    ("chitragupt", "Entry नंबर अट्ठाईस।", "ENTRY NO. *28*."),
]
HOOK = "JAB DOST KO GIRLFRIEND MIL JAAYE..."
COMMENT = {7: "COMMENT: TUMHARA GUSSA COUNT?", 14: "TAG KARO US DOST KO JO GIRLFRIEND KE BAAD GAYAB HAI"}
SPEAKER_COLOUR = {"boy": (255, 255, 255), "friend": (150, 230, 160), "vishnu": (150, 200, 255), "chitragupt": (255, 200, 120)}

SKIN = (242, 192, 150)
BOY = dict(skin=SKIN, shirt=(236, 84, 64), pants=(52, 84, 178), hair=(42, 30, 30), shoes=(250, 250, 250))
FRIEND = Look(head=(204, 150, 110), skin=(204, 150, 110), mood="happy", shirt=(46, 184, 140), pants=(58, 58, 74),
              hair=(30, 24, 24), shoes=(240, 64, 70))
VISHNU = Look(head=(70, 130, 228), skin=(70, 130, 228), extras=("crown", "four_arms", "tilak"), mood="happy",
              shirt=(252, 200, 50), pants=(250, 170, 40))
CHITRAGUPT = Look(head=(236, 190, 150), skin=(236, 190, 150), extras=("crown", "mustache"), mood="neutral",
                  shirt=(168, 36, 64), pants=(244, 232, 206), shoes=(120, 70, 40))
WALL_TOP, WALL_BOTTOM = (64, 150, 168), (128, 200, 196)        # a teal bedroom wall
FLOOR = (196, 120, 70)


def boy(mood, blush=0.0, head=SKIN):
    return Look(head=head, mood=mood, blush=blush, **BOY)


def gradient(pg, size, top, bottom):
    w, h = size
    k = np.linspace(0, 1, h)[None, :, None]
    arr = np.array(top)[None, None, :] * (1 - k) + np.array(bottom)[None, None, :] * k
    surf = pg.Surface(size)
    pg.surfarray.blit_array(surf, np.broadcast_to(arr, (w, h, 3)).astype(np.uint8))
    return surf


class Skit(Episode):
    def __init__(self, pg):
        super().__init__(pg)
        from ..core.text import font_file
        self.f_list = pg.font.Font(font_file("Poppins-ExtraBold"), 46)

    def room_base(self):
        """The bedroom, painted once: a teal wall with a diamond wallpaper, a sunset window with curtains,
        a poster, a plant, a striped rug and a red bed on a wooden floor."""
        if "room" in self.cache:
            return self.cache["room"]
        pg = self.pg
        surf = gradient(pg, (W, H), WALL_TOP, WALL_BOTTOM)
        for yy in range(60, GROUND, 120):                                    # wallpaper diamonds
            for xx in range((yy // 120 % 2) * 60, W, 120):
                pg.draw.polygon(surf, (90, 178, 186), [(xx, yy - 18), (xx + 14, yy), (xx, yy + 18), (xx - 14, yy)])
        pg.draw.rect(surf, (230, 210, 170), (0, GROUND - 60, W, 60))       # skirting board
        surf.blit(gradient(pg, (W, H - GROUND), FLOOR, (150, 84, 48)), (0, GROUND))
        for yy in range(GROUND + 40, H, 70):                                # floor planks
            pg.draw.line(surf, (140, 80, 44), (0, yy), (W, yy), 4)
            for xx in range((yy // 70 % 3) * 140, W, 420):
                pg.draw.line(surf, (140, 80, 44), (xx, yy - 70), (xx, yy), 4)
        pg.draw.line(surf, INK, (0, GROUND + 4), (W, GROUND + 4), 6)
        win = pg.Rect(640, 330, 300, 360)                                   # a sunset window
        surf.blit(gradient(pg, win.size, (255, 140, 90), (255, 214, 130)), win)
        pg.draw.circle(surf, (255, 240, 170), (840, 600), 60)
        for hx, hh in ((660, 80), (720, 120), (790, 70), (860, 140), (910, 90)):
            pg.draw.rect(surf, (120, 70, 110), (hx, win.bottom - hh, 50, hh))
        pg.draw.rect(surf, INK, win, 8)
        pg.draw.line(surf, INK, (790, 330), (790, 690), 6)
        for cx in (600, 980):                                               # mustard curtains
            pts = [(cx - 30, 300), (cx + 30, 300), (cx + 45, 720), (cx - 45, 720)]
            pg.draw.polygon(surf, (240, 180, 50), pts)
            pg.draw.polygon(surf, INK, pts, 5)
        pg.draw.line(surf, INK, (550, 300), (1030, 300), 10)
        poster = pg.Rect(110, 380, 220, 300)                                # a poster: an abstract planet
        pg.draw.rect(surf, (50, 40, 90), poster)
        pg.draw.circle(surf, (250, 120, 160), (220, 520), 70)
        pg.draw.ellipse(surf, (255, 220, 100), (130, 505, 180, 30), 6)
        for sx, sy in ((150, 420), (290, 440), (170, 640), (280, 620)):
            pg.draw.circle(surf, (255, 255, 255), (sx, sy), 5)
        pg.draw.rect(surf, INK, poster, 7)
        pg.draw.rect(surf, (90, 60, 40), (990, GROUND - 120, 60, 120))     # a plant in a pot
        for a in (-0.6, -0.2, 0.2, 0.6):
            tip = (1020 + 120 * math.sin(a), GROUND - 120 - 150 * math.cos(a))
            pg.draw.line(surf, (40, 150, 70), (1020, GROUND - 120), tip, 12)
            pg.draw.ellipse(surf, (60, 190, 90), (tip[0] - 30, tip[1] - 18, 60, 36))
        pg.draw.ellipse(surf, (200, 60, 90), (300, GROUND + 60, 520, 120))  # a striped rug
        for k_, c in ((0.75, (250, 200, 70)), (0.5, (60, 170, 160)), (0.25, (250, 250, 240))):
            r = pg.Rect(0, 0, int(520 * k_), int(120 * k_))
            r.center = (560, GROUND + 120)
            pg.draw.ellipse(surf, c, r)
        bed = pg.Rect(40, GROUND - 170, 390, 170)                           # a red bed with a striped blanket
        pg.draw.rect(surf, (200, 52, 60), bed, border_radius=22)
        for xx in range(bed.left + 20, bed.right - 30, 50):
            pg.draw.line(surf, (240, 120, 100), (xx, bed.top + 30), (xx + 20, bed.bottom - 12), 8)
        pg.draw.rect(surf, INK, bed, 7, border_radius=22)
        pg.draw.rect(surf, (255, 246, 220), (60, GROUND - 215, 130, 56), border_radius=20)
        pg.draw.rect(surf, INK, (60, GROUND - 215, 130, 56), 5, border_radius=20)
        self.cache["room"] = surf
        return surf

    def room(self, surf, dim=0.0):
        surf.blit(self.room_base(), (0, 0))
        if dim:
            veil = self.pg.Surface((W, H), self.pg.SRCALPHA)
            veil.fill((255, 214, 120, int(80 * dim)))
            surf.blit(veil, (0, 0))

    def divine_light(self, surf, k):
        """Slowly turning golden rays and twinkling sparkles from where Bhagwan Vishnu appears."""
        pg = self.pg
        t = getattr(self, "_t", 0.0)
        beam = pg.Surface((W, H), pg.SRCALPHA)
        cx, cy = W / 2 + 130, 380
        for j in range(12):
            a = t * 0.15 + j * math.pi / 6
            pts = [(cx, cy), (cx + 1600 * math.cos(a - 0.08), cy + 1600 * math.sin(a - 0.08)),
                   (cx + 1600 * math.cos(a + 0.08), cy + 1600 * math.sin(a + 0.08))]
            pg.draw.polygon(beam, (255, 226, 120, int(60 * k)), pts)
        pg.draw.polygon(beam, (255, 236, 160, int(90 * k)),
                        [(cx - 160, 0), (cx + 160, 0), (cx + 360, GROUND), (cx - 360, GROUND)])
        surf.blit(beam, (0, 0))
        rng = random.Random(int(t * 6))
        for _ in range(int(14 * k)):
            x, y = rng.uniform(150, W - 100), rng.uniform(150, GROUND - 100)
            pg.draw.line(surf, (255, 250, 200), (x - 10, y), (x + 10, y), 3)
            pg.draw.line(surf, (255, 250, 200), (x, y - 10), (x, y + 10), 3)

    def cloud(self, surf, cx, cy, s=1.0):
        pg = self.pg
        puffs = ((-150, 10, 70), (-70, -30, 90), (30, -40, 100), (130, -5, 80), (200, 20, 60), (-200, 25, 55))
        for dx, dy, r in puffs:
            pg.draw.circle(surf, INK, (int(cx + dx * s), int(cy + dy * s)), int((r + 6) * s))
        for dx, dy, r in puffs:
            pg.draw.circle(surf, (250, 200, 220), (int(cx + dx * s), int(cy + dy * s)), int(r * s))
        for dx, dy, r in puffs:
            pg.draw.circle(surf, (255, 255, 255), (int(cx + dx * s - 6 * s), int(cy + dy * s - 8 * s)), int(r * s * 0.85))
        pg.draw.rect(surf, (250, 200, 220), (cx - 220 * s, cy + 10 * s, 440 * s, 60 * s))

    def vishnu(self, surf, t, k_in, pose=None, mood="happy"):
        """Bhagwan Vishnu on his cloud, coming down into the top of the frame as k_in goes 0 -> 1."""
        pg = self.pg
        y = -300 + 990 * ease(k_in)
        for r, a in ((260, 40), (190, 60), (130, 90)):                    # the halo
            g = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
            pg.draw.circle(g, (255, 220, 120, a), (r, r), r)
            surf.blit(g, (W / 2 + 130 - r, y - 330 - r))
        import copy
        look = copy.copy(VISHNU)
        look.mood = mood
        pts = figure(pg, surf, W / 2 + 130, y, 1.05, pose or stand(t), look, INK, -1, t)
        self.cloud(surf, W / 2 + 130, y + 30, 0.9)
        if len(pts["hands"]) >= 4:
            cx, cy = pts["hands"][2]                                       # the chakra, spinning
            pg.draw.circle(surf, (255, 200, 60), (int(cx), int(cy - 22)), 22)
            pg.draw.circle(surf, INK, (int(cx), int(cy - 22)), 22, 4)
            for j in range(6):
                a = t * 8 + j * math.pi / 3
                pg.draw.line(surf, INK, (cx, cy - 22), (cx + 20 * math.cos(a), cy - 22 + 20 * math.sin(a)), 3)
            sx, sy = pts["hands"][3]                                       # the conch
            pg.draw.ellipse(surf, (255, 250, 240), (sx - 16, sy - 40, 32, 44))
            pg.draw.ellipse(surf, INK, (sx - 16, sy - 40, 32, 44), 4)
            pg.draw.arc(surf, INK, (sx - 9, sy - 30, 18, 20), 0, 4.5, 3)
        return pts

    def khaata(self, surf, since, length, t):
        """Chitragupt Ji's ledger, close up: a parchment page where each entry is stamped in as he reads it."""
        pg = self.pg
        k = ease(since / 0.4)
        if k <= 0:
            return
        page = pg.Rect(0, 0, 940, 760)
        page.center = (W / 2, 745 + (1 - k) * 1100)
        shade = pg.Surface((W, H), pg.SRCALPHA)
        shade.fill((20, 10, 30, int(110 * k)))
        surf.blit(shade, (0, 0))
        pg.draw.rect(surf, (250, 236, 200), page, border_radius=18)
        for yy in range(page.top + 150, page.bottom - 20, 70):
            pg.draw.line(surf, (220, 196, 150), (page.left + 30, yy + 34), (page.right - 30, yy + 34), 3)
        pg.draw.rect(surf, INK, page, 7, border_radius=18)
        for y in (page.top - 14, page.bottom - 10):
            pg.draw.rect(surf, (170, 110, 60), (page.left - 20, y, page.width + 40, 26), border_radius=12)
            pg.draw.rect(surf, INK, (page.left - 20, y, page.width + 40, 26), 4, border_radius=12)
        head = self.text(self.f_mid, "KHAATA: LADKA (2026)", (150, 40, 50), 0)
        surf.blit(head, head.get_rect(midtop=(W / 2, page.top + 30)))
        total = sum(len(sp) + 1 for sp, _ in KHAATA)
        done = 0
        from ..core.text import fit_width
        for j, (spoken, entry) in enumerate(KHAATA):
            at = 0.15 + (length - 0.4) * done / total
            done += len(spoken) + 1
            if j == 0 or since < at:                                       # "is saal" is the heading, not an entry
                continue
            img = fit_width(pg, self.text(self.f_list, entry, (60, 40, 40) if j < 4 else (190, 40, 50), 0), page.width - 140)
            q = ease((since - at) / 0.18)
            y = page.top + 150 + (j - 1) * 70
            sc = 1 + 0.4 * (1 - q)
            im = pg.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
            im.set_alpha(int(255 * q))
            surf.blit(im, im.get_rect(midleft=(page.left + 90, y + 4)))
            pg.draw.circle(surf, (190, 40, 50), (page.left + 52, int(y + 4)), 14)
            key = f"item{j}"
            if key not in self.cache:
                self.cache[key] = 1
                self.events.append((t, "ding"))
        late = since > length * 0.45                                       # the boy, in front, wilting
        pose = facepalm(t) if since > length * 0.7 else shock(t) if since < length * 0.2 else stand(t)
        figure(pg, surf, 200, 1700, 1.5, pose, boy("shy" if late else "shock", blush=1.0 if late else 0.0), INK, 1, t)

    def doggee(self, surf, k, t):
        """A bright dog-food packet, "SHERU", bouncing in with a NEW! burst and a paw print."""
        if k <= 0:
            return
        pg = self.pg
        bag = pg.Surface((340, 420), pg.SRCALPHA)
        pg.draw.polygon(bag, (250, 140, 40), [(20, 40), (320, 40), (300, 410), (40, 410)])
        pg.draw.polygon(bag, (250, 200, 60), [(20, 40), (320, 40), (318, 90), (22, 90)])
        for x in range(30, 320, 24):
            pg.draw.line(bag, INK, (x, 30), (x + 12, 44), 4)
        pg.draw.polygon(bag, INK, [(20, 40), (320, 40), (300, 410), (40, 410)], 7)
        label = self.text(self.f_mid, "SHERU", (255, 255, 255), 6)
        bag.blit(label, label.get_rect(center=(170, 150)))
        sub = self.text(self.f_small, "dog food", INK, 0)
        bag.blit(sub, sub.get_rect(center=(170, 205)))
        cx, cy = 170, 300
        pg.draw.circle(bag, (120, 70, 40), (cx, cy + 20), 42)
        for dx, dy in ((-46, -30), (-16, -58), (18, -58), (48, -30)):
            pg.draw.circle(bag, (120, 70, 40), (cx + dx, cy + dy), 18)
        sc = (0.2 + 0.6 * k) * (1 + 0.04 * math.sin(t * 8))
        bag = pg.transform.rotozoom(bag, -8 + 4 * math.sin(t * 3), sc)
        surf.blit(bag, bag.get_rect(center=(760, 1010)))
        if k >= 1:
            star = [(900 + (70 if j % 2 == 0 else 38) * math.cos(j * math.pi / 8 + t),
                     860 + (70 if j % 2 == 0 else 38) * math.sin(j * math.pi / 8 + t)) for j in range(16)]
            pg.draw.polygon(surf, (240, 50, 60), star)
            new = self.text(self.f_small, "NEW!", (255, 255, 255), 0)
            surf.blit(new, new.get_rect(center=(900, 860)))

    def phone(self, surf, at, cracked=False, angle=0.0):
        pg = self.pg
        ph = pg.Surface((60, 100), pg.SRCALPHA)
        pg.draw.rect(ph, (30, 30, 40), (0, 0, 60, 100), border_radius=10)
        pg.draw.rect(ph, (120, 200, 250), (6, 8, 48, 80), border_radius=4)
        if cracked:
            for a, b in (((30, 40), (8, 20)), ((30, 40), (50, 75)), ((30, 40), (12, 70)), ((30, 40), (52, 15))):
                pg.draw.line(ph, (255, 255, 255), a, b, 3)
        ph = pg.transform.rotate(ph, angle)
        surf.blit(ph, ph.get_rect(center=at))

    def chitragupt(self, surf, t, since_in, x=830, writing=False, scroll=0.0):
        pg = self.pg
        if since_in < 0:
            return None
        if since_in < 0.5:                                                # arrives in a puff of smoke
            for j in range(9):
                a = j * 2 * math.pi / 9
                r = 60 + since_in * 400
                c = (int(x + math.cos(a) * r * 0.6), int(GROUND - 180 + math.sin(a) * r * 0.4))
                pg.draw.circle(surf, (200, 200, 210), c, int(70 * (1 - since_in / 0.5)) + 10)
        if since_in < 0.15:
            return None
        pts = figure(pg, surf, x, GROUND, 1.35, hold(t), CHITRAGUPT, INK, -1, t)
        (hx, hy), _ = pts["hands"]
        top = hy - 30
        length = 60 + 290 * ease(scroll)                                   # the scroll, unrolling to the floor
        pg.draw.rect(surf, (250, 236, 200), (hx - 110, top, 120, length))
        pg.draw.rect(surf, INK, (hx - 110, top, 120, length), 4)
        rng = random.Random(4)
        for row in range(int(length / 26) - 1):
            w = rng.randint(50, 100)
            pg.draw.line(surf, (150, 120, 90), (hx - 100, top + 20 + row * 26), (hx - 100 + w, top + 20 + row * 26), 4)
        pg.draw.rect(surf, (170, 110, 60), (hx - 125, top - 14, 150, 24), border_radius=10)
        pg.draw.rect(surf, (170, 110, 60), (hx - 125, top + length - 10, 150, 24), border_radius=10)
        if writing:
            qx, qy = hx - 40 + 20 * math.sin(t * 14), top + length * 0.6
            pg.draw.line(surf, INK, (qx, qy), (qx + 40, qy - 70), 5)
            pg.draw.polygon(surf, (240, 240, 240), [(qx + 40, qy - 70), (qx + 70, qy - 120), (qx + 30, qy - 60)])
        return pts

    def scene(self, surf, i, since, length, t):
        pg = self.pg
        self._t = t
        k = since / max(0.1, length)
        cam = (1.0, W / 2, H / 2)
        bx = 300
        vishnu_on = 2 <= i <= 8 or i == 12
        if i <= 1:                                                        # the angry call, then the throw
            self.room(surf)
            if i == 0:
                pts = figure(pg, surf, bx, GROUND, 1.7, on_phone(t), boy("angry", head=(255, 235, 225)), INK, 1, t)
                self.phone(surf, (pts["hands"][0][0] + 8, pts["hands"][0][1] + 8), angle=-15)
                self.steam(surf, pts["head"], t, 6, 0.9)
                if (since * 2) % 1 < 0.5:
                    self.pop_text(surf, self.f_mid, "!!", RED, (pts["head"][0] + 120, pts["head"][1] - 80), 1.0, 10)
            else:
                tk = max(0.0, (since - (length - 1.1)) / 0.7)              # the throw comes at the end of his line
                pose = on_phone(t) if tk <= 0 else throw(min(1.0, tk))
                pts = figure(pg, surf, bx, GROUND, 1.7, pose, boy("angry", head=(255, 210, 200)), INK, 1, t)
                self.steam(surf, pts["head"], t, 3, 1.3)
                if tk <= 0.75:
                    self.phone(surf, (pts["hands"][0][0] + 8, pts["hands"][0][1] + 8), angle=-15 - tk * 300)
                else:
                    q = min(1.0, (tk - 0.75) / 0.25)
                    sx, sy = pts["hands"][0]
                    self.phone(surf, (sx + (620 - sx) * q, sy + (GROUND - 40 - sy) * q), cracked=q >= 1, angle=q * 400)
                    if q >= 1:
                        self.pop_text(surf, self.f_big, "CRASH!", RED, (640, GROUND - 260), (tk - 1.0) * 4 + 0.3, -8)
                        cam = (1.04, 600, GROUND - 200)
                        if "crash" not in self.cache:
                            self.cache["crash"] = 1
                            self.events.append((t, "crash"))
        elif i in (2, 3, 4):                                              # a voice from the clouds
            self.room(surf, min(1.0, since * 2) if i == 2 else 1.0)
            self.divine_light(surf, min(1.0, since * 2) if i == 2 else 1.0)
            self.phone(surf, (620, GROUND - 40), cracked=True, angle=40)
            k_in = since / 0.9 if i == 2 else 1.0
            mood = "shock" if i == 2 else "worried"
            look = boy(mood)
            pts = figure(pg, surf, bx, GROUND, 1.7, shock(t) if i == 2 and since < 1.0 else stand(t), look, INK, 1, t)
            self.vishnu(surf, t, k_in, pose=Pose(arms=(1.2, 0.4, -0.3, -0.2)) if i == 4 and since > length * 0.5 else None)
            if i == 2 and since < 0.15 and "chime" not in self.cache:
                self.cache["chime"] = 1
                self.events.append((t, "chime"))
            if i == 2:
                self.tag(surf, "BHAGWAN VISHNU", "Customer support, live", (40, 760), (since - 0.6) / 0.6)
            if i == 4 and since > length * 0.6:
                self.pop_text(surf, self.f_big, "?!", RED, (pts["head"][0] + 100, pts["head"][1] - 90), (since - length * 0.6) / 0.3)
        elif i in (5, 6, 7):                                              # Chitragupt Ji and the khaata
            self.room(surf, 1.0)
            self.divine_light(surf, 1.0)
            self.phone(surf, (620, GROUND - 40), cracked=True, angle=40)
            self.vishnu(surf, t, 1.0)
            arrive = since if i == 5 else 9.0
            if i == 5 and since < 0.1 and "poof" not in self.cache:
                self.cache["poof"] = 1
                self.events.append((t, "poof"))
            scroll = 0.0 if i == 5 and since < 0.9 else (min(1.0, (since - 0.9) / 0.8) if i == 5 else 1.0)
            if i == 5 and scroll > 0 and "unroll" not in self.cache:
                self.cache["unroll"] = 1
                self.events.append((t, "unroll"))
            self.chitragupt(surf, t, arrive, scroll=scroll)
            mood = "worried" if i != 6 else "shock"
            if i == 7:
                mood = "shy" if since > length * 0.45 else "worried"
            figure(pg, surf, bx, GROUND, 1.7, shock(t) if i == 6 else facepalm(t) if i == 7 and since > length * 0.7 else stand(t),
                   boy(mood, blush=1.0 if i == 7 and since > length * 0.45 else 0.0), INK, 1, t)
            if i == 5:
                self.tag(surf, "CHITRAGUPT JI", "Head of Accounts, Yamlok", (40, 760), (since - 0.5) / 0.6)
            if i == 7:                                                    # the khaata, entry by entry
                self.khaata(surf, since, length, t)
        elif i in (8, 9):                                                 # the promise, then the apology
            self.room(surf, 1.0 if i == 8 else 0.4)
            if i == 8:
                self.divine_light(surf, 1.0)
                self.vishnu(surf, t, 1.0)
                self.chitragupt(surf, t, 9.0, scroll=1.0)
                figure(pg, surf, bx, GROUND, 1.7, namaste(t), boy("worried"), INK, 1, t)
                self.phone(surf, (620, GROUND - 40), cracked=True, angle=40)
            else:
                pick = ease(since / 0.8)
                pts = figure(pg, surf, bx + 120 * pick, GROUND, 1.7, hold(t) if pick < 1 else on_phone(t), boy("neutral"), INK, 1, t)
                hx, hy = pts["hands"][0]
                at = (620 + (hx - 620) * pick, GROUND - 40 + (hy - GROUND + 40) * pick)
                self.phone(surf, at, cracked=True, angle=40 * (1 - pick) - 15 * pick)
                if pick >= 1:
                    self.pop_text(surf, self.f_mid, "CALLING...", INK, (W / 2 + 140, 520), (since - 0.8) / 0.3, 0, outline=0)
        elif i in (10, 11, 12, 13):                                               # the call, split screen
            self.room(surf, 0.3)
            pts = figure(pg, surf, bx + 120, GROUND, 1.7, on_phone(t), boy("worried" if i == 10 else "shock" if i == 12 else "neutral" if i == 11 else "angry"), INK, 1, t)
            self.phone(surf, (pts["hands"][0][0] + 8, pts["hands"][0][1] + 8), cracked=True, angle=-15)
            win = pg.Rect(560, 230, 470, 560)                               # the friend, in a call window
            surf.blit(gradient(pg, win.size, (120, 90, 200), (240, 130, 170)), win)
            pg.draw.circle(surf, (255, 220, 120), (win.left + 380, win.top + 140), 46)
            fx = win.centerx - 30
            fp = figure(pg, surf, fx, win.bottom - 30, 1.0, on_phone(t), FRIEND, INK, -1, t)
            heart = (fx + 90, win.top + 90 + 8 * math.sin(t * 4))         # his girlfriend's heart sticker
            pg.draw.circle(surf, (240, 80, 110), (int(heart[0] - 14), int(heart[1])), 18)
            pg.draw.circle(surf, (240, 80, 110), (int(heart[0] + 14), int(heart[1])), 18)
            pg.draw.polygon(surf, (240, 80, 110), [(heart[0] - 31, heart[1] + 6), (heart[0] + 31, heart[1] + 6), (heart[0], heart[1] + 44)])
            pg.draw.rect(surf, INK, win, 8, border_radius=30)
            name = self.text(self.f_small, "BHAI (ON CALL)", (255, 255, 255), 0)
            bar = pg.Rect(win.left, win.bottom - 4, win.width, 56)
            pg.draw.rect(surf, (40, 40, 60), bar, border_radius=16)
            surf.blit(name, name.get_rect(center=bar.center))
            if i == 12:
                self.pop_text(surf, self.f_big, "?", RED, (pts["head"][0] + 110, pts["head"][1] - 90), since / 0.3, 10)
            if i == 13 and since > 0.4:                                   # the dog-food packet
                self.doggee(surf, ease((since - 0.4) / 0.3), t)
            if False:
                card = pg.Rect(0, 0, 640, 150)
                card.center = (W / 2, 960)
                kk = ease((since - length * 0.62) / 0.3)
                card.inflate_ip(-640 * (1 - kk), -150 * (1 - kk))
                pg.draw.rect(surf, (255, 255, 255), card, border_radius=24)
                pg.draw.rect(surf, INK, card, 6, border_radius=24)
                if kk > 0.95:
                    a = self.text(self.f_small, "CONTACT SAVED AS", (120, 120, 120), 0)
                    b = self.text(self.f_mid, "PRESSURE COOKER", RED, 0)
                    surf.blit(a, a.get_rect(center=(W / 2, card.top + 40)))
                    surf.blit(b, b.get_rect(center=(W / 2, card.top + 100)))
        elif i == 14:                                                     # whistle!
            self.room(surf, 1.0)
            self.divine_light(surf, 1.0)
            self.vishnu(surf, t, 1.0, pose=facepalm(t), mood="closed")
            self.chitragupt(surf, t, 9.0, writing=True, scroll=1.0)
            heat = min(1.0, since / 0.5)
            head = (255, int(235 - 150 * heat), int(225 - 170 * heat))
            pts = figure(pg, surf, bx, GROUND, 1.7, Pose(arms=(0.5, 1.2, -0.5, -1.2), lift=6 * math.sin(t * 40) * heat),
                         boy("angry", head=head), INK, 1, t)
            hx, hy = pts["head"]
            for j in range(4):                                            # a pressure-cooker jet from his head
                y = hy - 60 - j * 70 - (since * 400) % 70
                r = 22 + j * 12
                pg.draw.circle(surf, (255, 255, 255), (int(hx + math.sin(t * 20 + j) * 10), int(y)), r)
                pg.draw.circle(surf, (150, 150, 150), (int(hx + math.sin(t * 20 + j) * 10), int(y)), r, 4)
            if "whistle" not in self.cache:
                self.cache["whistle"] = 1
                self.events.append((t, "whistle"))
            self.pop_text(surf, self.f_big, "SEETI!", RED, (300, 470), since / 0.3, 8)
            cam = (1.0 + 0.02 * math.sin(since * 50), W / 2, H / 2)
        self.draw_puffs(surf)
        return cam


def phone_line(clip):
    """Narrow the friend's voice to a phone line (300 Hz to 3.4 kHz)."""
    spec = np.fft.rfft(clip)
    f = np.fft.rfftfreq(len(clip), 1 / SR)
    spec[(f < 300) | (f > 3400)] = 0
    out = np.fft.irfft(spec, len(clip)).astype(np.float32)
    return out * (0.6 / (np.abs(out).max() or 1))


def sob(clip):
    """A crying wobble: the voice trembles in loudness about six times a second."""
    tt = np.arange(len(clip)) / SR
    wobble = 1 - 0.38 * (0.5 + 0.5 * np.sin(2 * np.pi * 6.2 * tt + np.sin(2 * np.pi * 0.7 * tt)))
    out = (clip * wobble).astype(np.float32)
    return out * (0.6 / (np.abs(out).max() or 1))


def divine(clip):
    """A soft echo for the voice from the clouds."""
    out = np.zeros(len(clip) + int(SR * 0.7), dtype=np.float32)
    for delay, level in ((0.0, 1.0), (0.17, 0.35), (0.34, 0.16), (0.51, 0.07)):
        a = int(SR * delay)
        out[a:a + len(clip)] += clip * level
    return out * (0.6 / (np.abs(out).max() or 1))


EPISODE, NAME, MUSIC_SEED = 2, "stick_sheru_hi", 77
CUTS = (2, 5, 9, 10, 13, 14)
LABELS = {"boy": "LADKA", "friend": "DOST", "vishnu": "BHAGWAN VISHNU", "chitragupt": "CHITRAGUPT JI"}
VOICE_FX = {"friend": "phone", "vishnu": "divine"}


def end_card(sk, frame, t, e):
    pts = figure(sk.pg, frame, 300, GROUND, 1.2, stand(t), boy("angry", head=(255, 140, 120)), INK, 1, t)
    sk.steam(frame, pts["head"], t, 3, 1.0)


def render(out_dir: Path, ep=None) -> Path:
    """Voice, draw and mix a skit. `ep` is the episode's module (this one by default): its LINES, VOICES,
    Skit, HOOK, COMMENT, EPISODE, NAME, CUTS, LABELS, SPEAKER_COLOUR, VOICE_FX, MUSIC_SEED and end_card."""
    import os
    import sys
    ep = ep or sys.modules[__name__]
    LINES, VOICES, HOOK, COMMENT = ep.LINES, ep.VOICES, ep.HOOK, ep.COMMENT
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    line_voice, line_fx = getattr(ep, "LINE_VOICE", {}), getattr(ep, "LINE_FX", {})
    voice_of = [line_voice.get(n, VOICES[who]) for n, (who, _, _) in enumerate(LINES)]
    for v in dict.fromkeys(x.partition("@")[0] for x in voice_of):
        tts.prepare([l for (_, l, _), x in zip(LINES, voice_of) if x.partition("@")[0] == v], v)
    clips = []
    for n, (who, line, _) in enumerate(LINES):
        c = tts.say(line, voice_of[n])
        fx = line_fx.get(n, ep.VOICE_FX.get(who))
        clips.append(phone_line(c) if fx == "phone" else divine(c) if fx == "divine" else sob(c) if fx == "sob" else c)
    starts, t = [], LEAD
    for (who, _, _), c in zip(LINES, clips):
        starts.append(t)
        t += (len(c) - (int(SR * 0.5) if ep.VOICE_FX.get(who) == "divine" else 0)) / SR + GAP
    story_end = t + TAIL
    total = story_end + END_S
    sk = ep.Skit(pg)
    out_dir.mkdir(parents=True, exist_ok=True)
    silent = out_dir / "_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
                           "-crf", "19", str(silent)], stdin=subprocess.PIPE)
    frame, world = pg.Surface((W, H)), pg.Surface((W, H))
    last = -1
    from ..core.text import fit_width, wrap
    for f in range(int(total * FPS)):
        t = f / FPS
        if t < story_end:
            i = max(j for j, s in enumerate(starts) if s <= t) if t >= starts[0] else 0
            nxt = starts[i + 1] if i + 1 < len(starts) else story_end
            since, length = t - starts[i], nxt - starts[i]
            if i != last:
                last = i
                if i in ep.CUTS:
                    sk.events.append((t, "cut"))
            z, cx, cy = sk.scene(world, i, since, length, t)
            if z > 1.001:
                cw, ch = W / z, H / z
                x0 = min(max(0, cx - cw / 2), W - cw)
                y0 = min(max(0, cy - ch / 2), H - ch)
                frame.blit(pg.transform.smoothscale(world.subsurface((x0, y0, cw, ch)), (W, H)), (0, 0))
            else:
                frame.blit(world, (0, 0))
            who = LINES[i][0]
            if LINES[i][2]:                                                # captions on the punchlines only
                label = sk.text(sk.f_small, ep.LABELS[who], ep.SPEAKER_COLOUR[who], 5)
                frame.blit(label, label.get_rect(center=(W / 2, 1262)))
                sk.caption(frame, LINES[i][2], since, length, True)
            if i == 0:                                                     # the hook, on the first frame
                y = 150
                for line in wrap(sk.f_hook, HOOK, W - 120)[:3]:
                    img = fit_width(pg, sk.text(sk.f_hook, line, (255, 220, 90), 9), W - 80)
                    frame.blit(img, img.get_rect(midtop=(W / 2, y)))
                    y += img.get_height() - 22
                tagline = getattr(ep, "TAGLINE", "S T I C K   K A T H A   ·   E P   " + str(ep.EPISODE))
                if tagline:
                    tagl = sk.text(sk.f_small, tagline, RED, 0)
                    frame.blit(tagl, tagl.get_rect(midtop=(W / 2, 100)))
            if i in COMMENT:
                sk.pill(frame, COMMENT[i], 250, (since - 0.4) / 0.6)
        else:                                                              # end card
            e = t - story_end
            sk.room(frame, 0.5)
            ep.end_card(sk, frame, t, e)
            sk.draw_puffs(frame)
            sk.pop_text(frame, sk.f_big, getattr(ep, "SERIES", "STICK KATHA"), RED, (W / 2, 560), e / 0.4)
            sk.pop_text(frame, sk.f_mid, getattr(ep, "END_SUB", f"Episode {ep.EPISODE}  ·  Follow for more"), INK,
                        (W / 2, 700), (e - 0.3) / 0.4, outline=0)
            if e < 0.3:
                veil = pg.Surface((W, H))
                veil.set_alpha(int(255 * (1 - e / 0.3)))
                frame.blit(veil, (0, 0))
        ff.stdin.write(pg.image.tobytes(frame, "RGB"))
    ff.stdin.close()
    ff.wait()

    n = int(SR * 1.4)
    tt = np.arange(n) / SR
    whistle = (np.sin(2 * np.pi * (1650 + 40 * np.sin(2 * np.pi * 7 * tt)) * tt) * 0.5
               + np.random.default_rng(2).uniform(-1, 1, n) * 0.25) * np.minimum(1, tt * 8) * np.minimum(1, (1.4 - tt) * 4)
    bank = {
        "crash": sample("glitch", 0.7) + np.pad(sample("drop", 0.5), (0, max(0, len(sample("glitch")) - len(sample("drop")))))[:len(sample("glitch"))],
        "chime": sample("bell", 0.6),
        "poof": whoosh(0.5, 200, 3000, 0.5),
        "unroll": whoosh(0.8, 150, 1200, 0.35, seed=3),
        "ding": sample("pop", 0.6),
        "cut": whoosh(0.3, 300, 2500, 0.3),
        "whistle": whistle.astype(np.float32) * 0.7,
    }
    events = [(tt_, name, 0) for tt_, name in sk.events]
    bed = compose(total, ep.MUSIC_SEED, "chiptune")
    pcm = mix(events, bank, total, bed=bed, bed_level=0.6, speech=list(zip(starts, clips)))
    wav = out_dir / "_audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    final = out_dir / f"{ep.NAME}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(final)], check=True)
    silent.unlink()
    wav.unlink()
    print(f"{final} ({total:.1f}s)")
    return final


if __name__ == "__main__":
    import datetime
    render(REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME)
