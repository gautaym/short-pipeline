"""Stick Katha, episode 3: "Bas Tera Pyaar". Run: python -m reel_engine.stick.bas_tera_pyaar

The girlfriend says she wants nothing expensive, only his love, in a filmy rhyming line of our own
(people do talk in song-hook style; the line is original, not a lyric). Then her "small" wishlist arrives,
the cart climbs to Rs 3,47,000 with "aur tum" at the bottom, he faints, Bhagwan Vishnu appears, Chitragupt Ji
(from episode 2) offers to open his khaata too, and Bhagwan Vishnu says the list will settle his account. No brands, no song lyrics or melodies.
"""
import math

from ..config import REPO_ROOT
from .durvasa import GROUND, H, INK, ORANGE, RED, W, ease
from .kit import Look, Pose, figure, hold, on_phone, shock, stand
from .pressure_cooker import Skit as Base, boy, gradient, render as run

EPISODE, NAME, MUSIC_SEED = 3, "stick_bas_tera_pyaar_hi", 91
VOICES = {
    "boy": "maya:hi:Shaunak@+0~1.1",
    "gf": "maya:hi:Ishwari@+0~1.08",
    "chitragupt": "maya:hi:Satvik@+1~1.05",
    "vishnu": "maya:hi:Abhay@-2~0.95",
}
WISHLIST = [   # (what he reads out, the entry, its price)
    ("Bag…", "BAG", 18000),
    ("heels…", "HEELS", 9500),
    ("नया phone…", "NAYA PHONE", 110000),
    ("Goa trip…", "GOA TRIP", 85000),
    ("matching hoodie…", "MATCHING HOODIE", 4500),
    ("और एक bag, अलग colour में?!", "EK AUR BAG (ALAG COLOUR)", 120000),
]
LINES = [   # (speaker, spoken line, caption on the punchlines only)
    ("gf", "ना मैनूं bag चाहिदा, ना heels, ना car… बस चाहिदा तेरा प्यार, मेरे यार!", "BAS CHAHIDA *TERA PYAAR*!"),
    ("boy", "सच में, baby? तुम कितनी simple हो!", "KITNI *SIMPLE* HO!"),
    ("gf", "हाँ जी! वैसे ना, एक छोटी सी list भेजी है। बस देख लेना, ज़्यादा कुछ नहीं।", ""),
    ("boy", " ".join(spoken for spoken, _, _ in WISHLIST), ""),
    ("gf", "[excited] और सबसे last में… तुम!", "AUR SABSE LAST MEIN... *TUM*!"),
    ("boy", "Total… तीन लाख सैंतालीस हज़ार?!", "TOTAL: *RS 3,47,000*?!"),
    ("vishnu", "हे पुत्र… प्रेम में भी, हिसाब देखकर चलना चाहिए।", ""),
    ("chitragupt", "प्रभु, इसका खाता भी खोल दूँ?", "ISKA *KHAATA* BHI KHOL DOON?"),
    ("vishnu", "रहने दो चित्रगुप्त। इसका हिसाब तो, ये list ही कर देगी।", "ISKA HISAAB TOH *YE LIST* HI KAR DEGI."),
]
HOOK = "JAB WOH BOLE: 'MUJHE KUCH NAHI CHAHIYE'..."
COMMENT = {3: "COMMENT: LIST MEIN AUR KYA HOGA?", 8: "TAG KARO JISKO 'BAS TERA PYAAR' CHAHIYE"}
CUTS = (2, 3, 5, 6, 7)
LABELS = {"boy": "LADKA", "gf": "GIRLFRIEND", "chitragupt": "CHITRAGUPT JI", "vishnu": "BHAGWAN VISHNU"}
SPEAKER_COLOUR = {"boy": (255, 255, 255), "gf": (255, 170, 210), "chitragupt": (255, 200, 120), "vishnu": (150, 200, 255)}
VOICE_FX = {"gf": "phone", "vishnu": "divine"}
GF = Look(head=(226, 170, 130), skin=(226, 170, 130), extras=("braid",), mood="happy", shirt=(236, 72, 150),
          pants=(250, 230, 120), hair=(36, 26, 26), shoes=(250, 250, 250), extra_colour={"braid": (255, 210, 60)})
BX = 300


def rupees(n: int) -> str:
    """Indian grouping: 347000 -> 3,47,000."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + parts) + "," + tail


def end_card(sk, frame, t, e):
    sk.fallen(frame, BX, 1.0, boy("closed"), t)


class Skit(Base):
    def call(self, surf, t, mood="happy", ding=False):
        """The girlfriend in a pink video-call window, top right."""
        pg = self.pg
        win = pg.Rect(560, 440, 470, 540)
        surf.blit(gradient(pg, win.size, (255, 150, 200), (255, 214, 150)), win)
        for j in range(5):                                                # floating hearts behind her
            hx = win.left + 60 + j * 90
            hy = win.top + 120 + 30 * math.sin(t * 2 + j)
            self.heart(surf, (hx, hy), 14, (255, 255, 255))
        look = Look(**{**GF.__dict__, "mood": mood})
        figure(pg, surf, win.centerx + 20, win.bottom - 30, 1.0, on_phone(t), look, INK, -1, t)
        pg.draw.rect(surf, INK, win, 8, border_radius=30)
        name = self.text(self.f_small, "BABY (ON CALL)", (255, 255, 255), 0)
        bar = pg.Rect(win.left, win.bottom - 4, win.width, 56)
        pg.draw.rect(surf, (120, 40, 90), bar, border_radius=16)
        surf.blit(name, name.get_rect(center=bar.center))
        if ding:
            note = pg.Rect(0, 0, 420, 90)
            note.midtop = (win.centerx, win.bottom + 70)
            pg.draw.rect(surf, (255, 255, 255), note, border_radius=22)
            pg.draw.rect(surf, INK, note, 5, border_radius=22)
            msg = self.text(self.f_small, "1 NEW MESSAGE: 'list'", INK, 0)
            surf.blit(msg, msg.get_rect(center=note.center))

    def heart(self, surf, at, r, colour):
        pg = self.pg
        x, y = at
        pg.draw.circle(surf, colour, (int(x - r * 0.55), int(y)), int(r * 0.62))
        pg.draw.circle(surf, colour, (int(x + r * 0.55), int(y)), int(r * 0.62))
        pg.draw.polygon(surf, colour, [(x - r * 1.15, y + r * 0.2), (x + r * 1.15, y + r * 0.2), (x, y + r * 1.4)])

    def fallen(self, surf, x, k, look, t):
        """The boy keeling over backwards onto the floor as k goes 0 -> 1."""
        pg = self.pg
        S = 1400
        tmp = pg.Surface((S, S), pg.SRCALPHA)
        figure(pg, tmp, S / 2, S / 2, 1.7, Pose(arms=(1.2, 0.3, -1.2, -0.3)), look, INK, 1, t)
        rot = pg.transform.rotate(tmp, 90 * ease(k))                      # head goes to the left, feet stay put
        surf.blit(rot, rot.get_rect(center=(x + 200, GROUND - 10)))
        if k >= 1:
            for j in range(3):                                            # dizzy stars
                a = t * 4 + j * 2.1
                cx, cy = x - 280 + 50 * math.cos(a), GROUND - 90 + 20 * math.sin(a)
                pg.draw.polygon(surf, (255, 220, 60), [(cx + 16 * math.cos(b * math.pi / 5) * (1 if b % 2 == 0 else 0.45),
                                                        cy + 16 * math.sin(b * math.pi / 5) * (1 if b % 2 == 0 else 0.45))
                                                       for b in range(10)])

    def wishlist(self, surf, since, length, t, last=0.0):
        """Her list as a phone screen: entries arrive as he reads them, the cart total climbing below."""
        pg = self.pg
        k = ease(since / 0.4) if last == 0 else 1.0
        page = pg.Rect(0, 0, 820, 900)
        page.center = (W / 2, 780 + (1 - k) * 1100)
        shade = pg.Surface((W, H), pg.SRCALPHA)
        shade.fill((40, 10, 40, int(110 * k)))
        surf.blit(shade, (0, 0))
        pg.draw.rect(surf, (30, 30, 40), page.inflate(40, 40), border_radius=60)
        pg.draw.rect(surf, (255, 248, 252), page, border_radius=36)
        top = pg.Rect(page.left, page.top, page.width, 110)
        pg.draw.rect(surf, (236, 72, 150), top, border_top_left_radius=36, border_top_right_radius=36)
        head = self.text(self.f_mid, "WISHLIST", (255, 255, 255), 0)
        surf.blit(head, head.get_rect(midleft=(page.left + 40, top.centery)))
        self.heart(surf, (page.right - 70, top.centery - 6), 22, (255, 255, 255))
        total_chars = sum(len(sp) + 1 for sp, _, _ in WISHLIST)
        done, total = 0, 0
        for j, (spoken, entry, price) in enumerate(WISHLIST):
            at = 0.2 + (length - 0.5) * done / total_chars if last == 0 else -1
            done += len(spoken) + 1
            if since < at:
                continue
            total += price
            q = ease((since - at) / 0.2) if last == 0 else 1.0
            y = page.top + 160 + j * 92
            from ..core.text import fit_width
            cost = self.text(self.f_list, "Rs " + rupees(price), (150, 40, 90), 0)
            name = fit_width(pg, self.text(self.f_list, entry, INK if j < 5 else RED, 0), page.width - cost.get_width() - 110)
            for img, rect in ((name, name.get_rect(midleft=(page.left + 40, y))),
                              (cost, cost.get_rect(midright=(page.right - 40, y)))):
                img.set_alpha(int(255 * q))
                surf.blit(img, rect)
            pg.draw.line(surf, (240, 210, 225), (page.left + 30, y + 40), (page.right - 30, y + 40), 3)
            if f"w{j}" not in self.cache:
                self.cache[f"w{j}"] = 1
                self.events.append((t, "ding"))
        if last > 0:                                                      # "... aur tum"
            y = page.top + 160 + len(WISHLIST) * 92
            q = ease(last / 0.3)
            img = self.text(self.f_mid, "+ TUM", (236, 72, 150), 0)
            img = pg.transform.rotozoom(img, 0, 0.6 + 0.4 * q)
            surf.blit(img, img.get_rect(midleft=(page.left + 40, y)))
            self.heart(surf, (page.left + 280, y), 22, (236, 72, 150))
            free = self.text(self.f_list, "FREE", (40, 160, 90), 0)
            surf.blit(free, free.get_rect(midright=(page.right - 40, y)))
        bar = pg.Rect(page.left, page.bottom - 120, page.width, 120)
        pg.draw.rect(surf, (40, 30, 50), bar, border_bottom_left_radius=36, border_bottom_right_radius=36)
        tot = self.text(self.f_mid, "TOTAL: Rs " + rupees(total), (255, 220, 90), 0)
        surf.blit(tot, tot.get_rect(center=bar.center))

    def scene(self, surf, i, since, length, t):
        pg = self.pg
        self._t = t
        cam = (1.0, W / 2, H / 2)
        self.room(surf, 0.0)
        if i == 0:                                                         # her filmy line
            pts = figure(pg, surf, BX, GROUND, 1.7, on_phone(t), boy("neutral"), INK, 1, t)
            self.phone(surf, (pts["hands"][0][0] + 8, pts["hands"][0][1] + 8), angle=-15)
            self.call(surf, t)
        elif i == 1:                                                       # he melts
            tint = pg.Surface((W, H), pg.SRCALPHA)
            tint.fill((255, 120, 180, 60))
            surf.blit(tint, (0, 0))
            sway = math.sin(t * 3) * 0.08
            pts = figure(pg, surf, BX, GROUND, 1.7, Pose(arms=(1.4, 1.9, -0.6, -1.9), lean=sway), boy("happy", blush=1.0), INK, 1, t)
            self.phone(surf, (pts["hands"][0][0] + 8, pts["hands"][0][1] + 8), angle=-15)
            for j in range(7):                                             # hearts rising off him
                y = pts["head"][1] - ((since * 160 + j * 90) % 520)
                x = pts["head"][0] - 120 + j * 40 + 20 * math.sin(t * 3 + j)
                self.heart(surf, (x, y), 18 + (j % 3) * 6, (240, 60, 110))
            self.call(surf, t)
        elif i == 2:                                                       # "ek chhoti si list"
            pts = figure(pg, surf, BX, GROUND, 1.7, on_phone(t), boy("happy"), INK, 1, t)
            self.phone(surf, (pts["hands"][0][0] + 8, pts["hands"][0][1] + 8), angle=-15)
            self.call(surf, t, ding=since > length * 0.55)
            if since > length * 0.55 and "msg" not in self.cache:
                self.cache["msg"] = 1
                self.events.append((t, "chime"))
        elif i in (3, 4):                                                  # the wishlist
            self.wishlist(surf, since, length, t, last=since if i == 4 else 0.0)
            late = i == 4 or since > length * 0.5
            figure(pg, surf, 200, 1720, 1.5, shock(t) if late else hold(t), boy("shock" if late else "worried"), INK, 1, t)
        elif i == 5:                                                       # the total, then down he goes
            fall = max(0.0, (since - (length - 0.9)) / 0.5)
            if fall <= 0:
                n = int(347000 * min(1.0, since / (length * 0.6)))
                shake = 6 * math.sin(t * 50)
                self.pop_text(surf, self.f_big, "Rs " + rupees(n), RED, (W / 2 + shake, 520), 1.0, -4)
                figure(pg, surf, BX, GROUND, 1.7, shock(t), boy("shock", head=(250, 250, 250)), INK, 1, t)
            else:
                self.fallen(surf, BX, min(1.0, fall), boy("closed"), t)
                if fall >= 1 and "thud" not in self.cache:
                    self.cache["thud"] = 1
                    self.events.append((t, "crash"))
                    cam = (1.04, BX, GROUND)
        elif i >= 6:                                                       # Bhagwan Vishnu, then Chitragupt Ji
            self.divine_light(surf, min(1.0, since * 2) if i == 6 else 1.0)
            self.fallen(surf, BX, 1.0, boy("closed"), t)
            if i == 6 and since < 0.1 and "chime" not in self.cache:
                self.cache["chime"] = 1
                self.events.append((t, "chime"))
            self.vishnu(surf, t, since / 0.9 if i == 6 else 1.0,
                        pose=Pose(arms=(1.2, 0.4, -0.3, -0.2)) if i == 8 else None, mood="closed" if i == 8 else "happy")
            if i >= 7:
                arrive = since if i == 7 else 9.0
                if i == 7 and since < 0.1 and "poof" not in self.cache:
                    self.cache["poof"] = 1
                    self.events.append((t, "poof"))
                scroll = min(1.0, max(0.0, (since - 0.6) / 0.6)) if i == 7 else max(0.0, 1 - since / 0.6)
                if i == 7 and since > 0.6 and "unroll" not in self.cache:
                    self.cache["unroll"] = 1
                    self.events.append((t, "unroll"))
                self.chitragupt(surf, t, arrive, x=840, scroll=scroll)
        self.draw_puffs(surf)
        return cam


if __name__ == "__main__":
    import datetime
    import sys
    run(REPO_ROOT / "out" / datetime.date.today().isoformat() / NAME, sys.modules[__name__])
