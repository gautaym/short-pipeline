"""Maths Test: a silent classroom skit (no dialogue: laughs, pauses, camera moves, a ticking score).

Bunty is stuck on Q3 and goes "psst" to Golu, showing his paper with a finger on Q3. Golu shows his own paper and
taps it: it is completely blank. They look at each other and break into a weird, wheezing laugh together, and
Madam turns and sees them.

Run: python -m reel_engine.toon.maths_test [--render | --still T ... | --insert | --looks]
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame as pg

from ..core import blender
from ..core.text import font_file, font_path

OUT = Path("out/2026-11-08/maths_test")
PAPER = (900, 1240)
INK, BLUE, RED = (30, 30, 36), (30, 60, 170), (210, 30, 40)
LINE = (170, 196, 226)

QUESTIONS = ["Q1.  7 + 5 = ?", "Q2.  15 - 9 = ?", "Q3.  If 2x + 4 = 10,", "       find x.", "Q4.  12 x 3 = ?",
             "Q5.  Half of 50 = ?"]
ANSWERS = {"bunty": {0: "12", 1: "6", 4: "36", 5: "25"}, "golu": {}}      # line index -> his handwritten answer


def paper(who: str) -> pg.Surface:
    """An exam sheet, large and plain enough to read in a phone close-up."""
    W, H = PAPER
    s = pg.Surface(PAPER)
    s.fill((252, 250, 242))
    for y in range(330, H - 40, 76):
        pg.draw.line(s, LINE, (40, y), (W - 40, y), 2)
    pg.draw.line(s, (236, 150, 150), (110, 0), (110, H), 3)                  # the margin
    head = pg.font.Font(font_file("Poppins-ExtraBold"), 62)
    small = pg.font.Font(font_file("Poppins-SemiBold"), 34)
    q = pg.font.Font(font_path(), 50)
    hand = pg.font.Font(font_file("Poppins-SemiBold"), 54)
    t = head.render("MATHS TEST", True, INK)
    s.blit(t, ((W - t.get_width()) // 2, 36))
    t = small.render("Time: 1 Hour        Marks: 20", True, INK)
    s.blit(t, ((W - t.get_width()) // 2, 118))
    s.blit(small.render("Name:", True, INK), (130, 200))
    name = pg.transform.rotate(hand.render(who.upper(), True, BLUE), 4)
    s.blit(name, (250, 182))
    pg.draw.line(s, INK, (240, 252), (620, 252), 2)
    for i, line in enumerate(QUESTIONS):
        y = 346 + i * 120
        s.blit(q.render(line, True, INK), (130, y))
        if i == 3:
            continue
        ay = y + 58 if i != 2 else y + 178
        pg.draw.line(s, (120, 120, 130), (560, ay + 6), (W - 70, ay + 6), 2)
        a = ANSWERS[who].get(i)
        if a:
            s.blit(pg.transform.rotate(hand.render(a, True, BLUE), 5), (600, ay - 62))
    if who == "bunty":                                                       # Q3 circled and a big "?"
        pg.draw.ellipse(s, RED, (110, 570, 620, 210), 5)
        qm = pg.font.Font(font_file("Poppins-ExtraBold"), 150).render("?", True, RED)
        s.blit(pg.transform.rotate(qm, -10), (740, 560))
    else:                                                                    # Golu: not one answer, just a smiley
        pg.draw.circle(s, BLUE, (760, 1150), 46, 4)
        for dx in (-16, 16):
            pg.draw.circle(s, BLUE, (760 + dx, 1138), 6)
        pg.draw.arc(s, BLUE, (734, 1126, 52, 40), 3.5, 5.9, 4)
    pg.draw.rect(s, (190, 186, 170), (0, 0, W, H), 3)
    return s


FPS, W, H = 30, 1080, 1920
# the beats (seconds), 2026-11-08: the board and Madam; the class writing (the caption at 4-6 s); Bunty stares at his
# paper for 2 s, then "psst"; Golu turns; Bunty shows Q3; Golu grins and shows his blank sheet; the stare; the look;
# the weird laugh; Madam looks up and the clock stops; the freeze; the end card
BEATS = dict(open=0.0, cls=2.4, bunty=4.4, psst=6.4, golu=7.4, show_b=8.2, ins_b=9.0, golu2=11.5, show_g=12.4,
             ins_g=13.1, stare=15.3, look=16.2, laugh=17.0, madam=20.6, freeze=22.2, end=23.2)
TOTAL = 23.2                       # v6 (2026-11-08): quicker; ends on the freeze
ANNOUNCE = ("announce_mathstest", 0.15, 1.5)          # booming, goofy "Maaaths... TEST!": take, start (s), pitch up
PLATES = {"front": OUT / "bg" / "board_text.png", "back": OUT / "bg" / "back_1.png"}
CAPTION = (4.0, 6.0, "WO DOST JO TUMSE BHI FISSADI HAI!")
# the two whispered lines (ElevenLabs, goofy: nudged up like a fast tape), over the paper close-ups
WHISPER = [("bunty_yewala", "ins_b", 0.55, 3.0, "YEH WAALA?"),
           ("golu_dekhle", "ins_g", 0.35, 2.5, "HAAN... DEKH LE, SAARE!")]


def params(out, stills=None):
    pdir = OUT / "papers"
    pdir.mkdir(parents=True, exist_ok=True)
    pg.init()
    for who in ("bunty", "golu"):
        pg.image.save(paper(who), str(pdir / f"{who}.png"))
    papers = {"bunty": pdir / "bunty.png", "golu": pdir / "golu.png", "blank": pdir / "golu.png"}
    p = dict(out_dir=str(out), mode="scene", width=W, height=H, fps=FPS, samples=16, frames=int(TOTAL * FPS),
             beats=BEATS, plates={k: str(v.resolve()) for k, v in PLATES.items()},
             papers={k: str(v.resolve()) for k, v in papers.items()})
    if stills:
        p["stills"] = stills
    return p


def stills(times):
    out = OUT / "test"
    blender.run("exam3d", params(out, [int(t * FPS) + 1 for t in times]), timeout=1800)
    print((out / "stills").resolve())


# ---------------------------------------------------------------- the paper close-ups (drawn here, crisp)
INSERT_SCALE = 1.12
PAPER_AT = (36, 250)                       # the sheet's top-left on screen in the close-up
TAPS = {   # where the finger lands on each sheet (paper pixels), in order
    "bunty": [(640, 690), (640, 690), (640, 690)],                              # Q3, three taps
    "golu": [(720, 410), (720, 530), (720, 770), (720, 890), (720, 1010)],      # every blank answer line
}
TAP_DT = {"bunty": 0.42, "golu": 0.32}
SKIN = {"bunty": (222, 172, 122), "golu": (240, 198, 156)}
OUTLINE = (34, 22, 26)


def hand(surf, tip, skin):
    """A chibi hand pointing, coming in from the bottom right: a white sleeve, a round fist, one finger."""
    tx, ty = tip
    ang = math.radians(28)
    dx, dy = math.sin(ang), math.cos(ang)               # from the fingertip back along the arm
    fist = (tx + dx * 230, ty + dy * 230)
    arm_end = (tx + dx * 900, ty + dy * 900)
    for w, col in ((150, OUTLINE), (132, (246, 246, 240))):
        pg.draw.line(surf, col, (fist[0] + dx * 60, fist[1] + dy * 60), arm_end, w)
    pg.draw.line(surf, OUTLINE, (tx, ty), fist, 58)
    pg.draw.line(surf, skin, (tx, ty), fist, 42)
    pg.draw.circle(surf, OUTLINE, (int(tx), int(ty)), 29)
    pg.draw.circle(surf, skin, (int(tx), int(ty)), 21)
    pg.draw.circle(surf, OUTLINE, (int(fist[0]), int(fist[1])), 88)
    pg.draw.circle(surf, skin, (int(fist[0]), int(fist[1])), 78)
    pg.draw.circle(surf, (250, 170, 170), (int(fist[0] - 30), int(fist[1] - 20)), 14)


def insert(frame, who, u, sheet, t):
    """The close-up of a sheet, u seconds into the shot: the hand slides in, then taps each spot in TAPS."""
    frame.fill((168, 116, 70))
    for k in range(0, H, 90):                                   # the desk's wood grain
        pg.draw.line(frame, (150, 100, 58), (0, k + 30 * math.sin(k * 0.01)), (W, k + 20), 3)
    z = INSERT_SCALE * (1.0 + 0.04 * min(1.0, u / 2.5))           # a slow push in
    big = pg.transform.smoothscale(sheet, (int(sheet.get_width() * z), int(sheet.get_height() * z)))
    wob = (6 * math.sin(t * 1.3), 5 * math.sin(t * 1.7))
    ox = (W - big.get_width()) / 2 + wob[0]
    oy = PAPER_AT[1] - (z - INSERT_SCALE) * 400 + wob[1]
    shadow = pg.Surface(big.get_size(), pg.SRCALPHA)
    shadow.fill((0, 0, 0, 70))
    frame.blit(shadow, (ox + 14, oy + 16))
    frame.blit(big, (ox, oy))
    taps, per, t0 = TAPS[who], TAP_DT[who], 0.45
    if u < t0:
        k = 1 - (1 - u / t0) ** 3
        px, py = taps[0]
        tip = (ox + px * z + (1 - k) * 700, oy + py * z + (1 - k) * 900)
    else:
        v = (u - t0) / per
        n = min(len(taps) - 1, int(v))
        q = v % 1.0 if v < len(taps) else 1.0
        px, py = taps[n]
        lift = 0.0 if q > 0.5 else 26 * (1 - q / 0.5) if n == int(v) and v >= 1 else 26 * max(0.0, 1 - q / 0.5)
        tip = (ox + px * z, oy + py * z - lift)
    hand(frame, tip, SKIN[who])


def tap_times():
    """When the finger lands on the sheet (seconds), for the knock sounds."""
    out = []
    for who, key in (("bunty", "ins_b"), ("golu", "ins_g")):
        out += [BEATS[key] + 0.45 + k * TAP_DT[who] + 0.25 for k in range(len(TAPS[who]))]
    return out


# ---------------------------------------------------------------- sound
EL = OUT / "eleven"
SR = 44100


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def countdown(dur, rate0=4.0, rate1=5.5, level=0.5):
    """A modern countdown (2026-11-08 direction), made here: fast, soft, deep, rounded ticks, each a short warm
    "tok" (a falling low sine with a muffled click), alternating tick/tok, quickening slightly as it goes."""
    out = np.zeros(int(dur * SR) + SR, np.float32)
    rng = np.random.default_rng(5)
    t, k = 0.0, 0
    while t < dur:
        n = int(0.075 * SR)
        x = np.arange(n) / SR
        f0 = 235.0 if k % 2 == 0 else 190.0
        body = np.sin(2 * np.pi * np.cumsum(f0 * (1 - 0.25 * x / 0.075)) / SR) * np.exp(-x * 45)
        body += 0.3 * np.sin(2 * np.pi * f0 * 2.01 * x) * np.exp(-x * 80)
        click = rng.uniform(-1, 1, n) * np.exp(-x * 900)
        click = np.convolve(click, np.ones(12) / 12, "same")          # muffled, not sharp
        tick = (body + 0.5 * click) * np.minimum(1, x * 2000)
        a = int(t * SR)
        out[a:a + n] += (tick / np.abs(tick).max()).astype(np.float32)
        t += 1.0 / (rate0 + (rate1 - rate0) * t / dur)
        k += 1
    return out[:int(dur * SR)] * level


def chime(level=0.55):
    """A smooth modern notification: two soft bell notes, a fifth apart."""
    out = np.zeros(int(1.8 * SR), np.float32)
    for at, f in ((0.0, 880.0), (0.14, 1318.5)):
        x = np.arange(int(1.6 * SR)) / SR
        w = (np.sin(2 * np.pi * f * x) + 0.25 * np.sin(2 * np.pi * f * 2.0 * x) * np.exp(-x * 6)
             + 0.1 * np.sin(2 * np.pi * f * 3.0 * x) * np.exp(-x * 9)) * np.exp(-x * 3.2) * np.minimum(1, x * 300)
        a = int(at * SR)
        out[a:a + len(w)] += w[:len(out) - a].astype(np.float32)
    return out / np.abs(out).max() * level


def snicker():
    """The two laughing like cartoon pests (2026-11-08 direction): an original, wordless, high-pitched snigger,
    made from the ElevenLabs laughs pushed up into a squeaky register, sped up, chopped into rapid "heh-heh-heh"
    bursts and doubled a little higher for a ganging-up, wheezy cackle. Returns [(clip, start, level)]."""
    from ..core.voice import repitch
    span = BEATS["madam"] - BEATS["laugh"]

    def squeak(x, semis, rate_hz, seed):
        y = repitch(x, SR, semis, 2 ** (semis / 12) * 1.15)            # chipmunk: high and quick
        y = np.resize(y, int(span * SR)).astype(np.float32)             # keep going until Madam looks up
        t = np.arange(len(y)) / SR
        jitter = np.random.default_rng(seed).uniform(-0.6, 0.6)
        chop = 0.25 + 0.75 * (0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * t + jitter)) ** 2   # heh-heh-heh
        y = y * chop
        return y / (float(np.abs(y).max()) or 1.0)

    t0 = BEATS["laugh"]
    if (EL / "sfx_snicker1.mp3").exists() and (EL / "sfx_snicker2.mp3").exists():   # the bug-gang snigger (SFX)
        out = []
        for name, at, lv in (("sfx_snicker1", 0.0, 0.9), ("sfx_snicker2", 0.35, 0.8)):
            x = load(EL / f"{name}.mp3")
            x = np.resize(x / (float(np.abs(x).max()) or 1.0), int(span * SR)).astype(np.float32)
            out.append((x, t0 + at, lv))
        if (EL / "bunty_giggle.mp3").exists():                                  # their own giggles, underneath
            out.append((squeak(load(EL / "bunty_giggle.mp3"), 5.0, 7.5, 1), t0 + 0.1, 0.3))
            out.append((squeak(load(EL / "golu_giggle.mp3"), 4.0, 6.5, 2), t0 + 0.5, 0.28))
        return out
    if (EL / "bunty_giggle.mp3").exists() and (EL / "golu_giggle.mp3").exists():   # the mischievous, evil giggles
        bl, gl = load(EL / "bunty_giggle.mp3"), load(EL / "golu_giggle.mp3")
        return [(squeak(bl, 5.0, 7.5, 1), t0, 0.85),
                (squeak(gl, 4.0, 6.5, 2), t0 + 0.45, 0.8),
                (squeak(bl[int(0.6 * SR):], 9.0, 9.0, 3), t0 + 1.1, 0.3),
                (squeak(gl[int(0.6 * SR):], 8.0, 8.0, 4), t0 + 1.6, 0.28)]
    bl = load(EL / "bunty_laugh.mp3")
    gl = load(EL / "golu_laugh.mp3")[int(3.4 * SR):int(7.9 * SR)]
    return [(squeak(bl, 8.0, 7.5, 1), t0, 0.8),                        # Bunty starts: a squeaky snigger
            (squeak(gl, 6.0, 6.5, 2), t0 + 0.45, 0.75),                # Golu joins, a bit lower
            (squeak(bl[int(1.0 * SR):], 11.0, 9.0, 3), t0 + 1.1, 0.35),   # a higher wheeze on top
            (squeak(gl[int(0.8 * SR):], 9.5, 8.0, 4), t0 + 1.6, 0.3)]


def soundtrack():
    """The grandfather clock sets the scene, then a soft, fast countdown ticks under everything until Madam looks
    up, when it stops dead; then the psst, knocks on the paper, stings, the giggles (cut dead), the scratch and the
    thud, the old clock creeping back, and a "time's up" chime with a laugh on the end card."""
    from ..core.audio import sample
    from .positive_bhai_3d import slide_whistle
    B = BEATS
    n = int(TOTAL * SR)
    out = np.zeros(n + SR * 2, np.float32)

    def put(t, x, level=1.0):
        a = int(t * SR)
        x = x[:len(out) - a]
        out[a:a + len(x)] += x * level

    def faded(x, fin=0.0, fout=0.0):
        x = x.copy()
        if fin:
            k = int(fin * SR)
            x[:k] *= np.linspace(0, 1, k)
        if fout:
            k = int(fout * SR)
            x[-k:] *= np.linspace(1, 0, k)
        return x

    tick = sample("clock_tick", 0.5)[int(0.6 * SR):int(10.2 * SR)]          # the grandfather clock
    put(0.0, faded(np.resize(tick, int((B["bunty"] + 0.4) * SR)), 0, 0.5))
    span = B["madam"] - B["bunty"] + 0.2                                    # the countdown, from Bunty's panic:
    if (EL / "sfx_countdown.mp3").exists():                                 # ElevenLabs (2026-11-08), else made here
        cd = load(EL / "sfx_countdown.mp3")
        cd = np.resize(cd / (float(np.abs(cd).max()) or 1.0), int(span * SR)).astype(np.float32) * 0.6
    else:
        cd = countdown(span, 4.0, 5.5, 0.55)
    cd = faded(cd, 0.4, 0)[:int((B["madam"] - B["bunty"]) * SR)]
    cd[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))             # stops dead when Madam looks up
    put(B["bunty"], cd)
    put(B["freeze"] + 0.45, faded(np.resize(tick, int((TOTAL - B["freeze"] - 0.45) * SR)), 0.1, 0.2), 0.8)
    put(B["bunty"] + 0.1, sample("surprise_phoenix", 0.35))                  # he reads Q3...
    put(B["psst"] + 0.45, sample("psst", 0.95))
    if (EL / f"{ANNOUNCE[0]}.mp3").exists():                                 # "Maaaths... TEST!"
        from ..core.voice import repitch as _rp
        x = _rp(load(EL / f"{ANNOUNCE[0]}.mp3"), SR, ANNOUNCE[2], 2 ** (ANNOUNCE[2] / 12))
        put(ANNOUNCE[1], x / (float(np.abs(x).max()) or 1.0), 0.95)
    from ..core.voice import repitch
    for name, key, at, semis, _ in WHISPER:
        if (EL / f"{name}.mp3").exists():
            x = repitch(load(EL / f"{name}.mp3"), SR, semis, 2 ** (semis / 12))
            put(B[key] + at, x / (float(np.abs(x).max()) or 1.0), 0.8)
    put(B["golu"], sample("question", 0.4))                                # Golu: "?"
    for ts in tap_times():
        put(ts, sample("wood_pop", 0.5))                                   # knocks on the paper
    put(B["golu2"] + 0.6, sample("sparkle", 0.4))                          # Golu's sly grin
    put(B["stare"], sample("thud", 0.6))                                   # the blank sheet sinks in
    put(B["look"] + 0.7, sample("pluck", 0.4))                             # ...the grins
    for x, t0, lv in snicker():
        x = x[:int((B["madam"] - t0) * SR)].copy()
        x[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))         # cut dead
        put(t0, x, lv)
    put(B["madam"], sample("scratch", 0.7))
    put(B["madam"] + 0.32, sample("thud_dragon", 0.95))
    put(B["end"], sample("confirm", 0.5))                                  # time's up
    put(B["end"] + 0.5, slide_whistle(0.6, 0.3))
    lw = sample("laugh_woman", 0.55)[:int(2.4 * SR)]
    put(B["end"] + 0.6, faded(lw, 0, 1.6))
    out = np.tanh(out[:n] * 1.1)
    return (out * 32767 * 0.95).astype(np.int16)


# ---------------------------------------------------------------- overlays and the mux
def overlay_and_mux(out: Path):
    from ..stick.durvasa import ORANGE, RED, Episode
    pg.init()
    sk = Episode(pg)
    sheets = {who: pg.image.load(str(OUT / "papers" / f"{who}.png")) for who in ("bunty", "golu")}
    silent = out / "_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
                           str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-crf",
                           "19", str(silent)], stdin=subprocess.PIPE)
    B = BEATS
    for f in range(int(TOTAL * FPS)):
        t = f / FPS
        frame = pg.image.load(str(out / "frames" / f"f_{f + 1:04d}.png"))
        if B["ins_b"] <= t < B["golu2"]:
            insert(frame, "bunty", t - B["ins_b"], sheets["bunty"], t)
        if B["ins_g"] <= t < B["stare"]:
            insert(frame, "golu", t - B["ins_g"], sheets["golu"], t)
        for _, key, at, _, cap in WHISPER:                      # the whispered line, as a caption
            if B[key] + at <= t < B[key] + at + 1.8:
                sk.pill(frame, cap, 1640, (t - B[key] - at) / 0.25)
        c0, c1, _ = CAPTION
        if c0 <= t < c1:                                       # the hook caption
            k = (t - c0) / 0.25
            sk.pop_text(frame, sk.f_mid, "WO DOST JO", (255, 255, 255), (W / 2, 330), k, -3, outline=7)
            sk.pop_text(frame, sk.f_mid, "TUMSE BHI", (255, 255, 255), (W / 2, 420), k - 0.3, 2, outline=7)
            sk.pop_text(frame, sk.f_big, "FISSADI HAI!", ORANGE, (W / 2, 540), k - 0.6, -4)
        ps = B["psst"] + 0.45
        if ps <= t < ps + 0.9:
            sk.pop_text(frame, sk.f_big, "PSST!", (120, 220, 255), (300, 520), (t - ps) / 0.15, -8)
        if B["golu"] <= t < B["golu"] + 0.6:
            sk.pop_text(frame, sk.f_big, "?", (255, 255, 255), (W / 2 + 280, 470), (t - B["golu"]) / 0.15, 10)
        if B["laugh"] <= t < B["madam"]:
            q = t - B["laugh"]
            for k, (word, pos, ang) in enumerate((("HEHEHE", (270, 420), -10), ("HOHOHO", (800, 470), 9),
                                                  ("HIHIHI", (300, 1500), 6), ("HUHUHU", (790, 1440), -7))):
                if q > 0.3 + k * 0.7:
                    wob = 8 * math.sin(t * 20 + k)
                    sk.pop_text(frame, sk.f_mid, word, (255, 230, 90), (pos[0] + wob, pos[1]),
                                (q - 0.3 - k * 0.7) / 0.2, ang + wob / 4, outline=7)
        m = t - B["madam"]
        if 0 <= m < 1.2:                                       # the glare: a red flash
            red = pg.Surface((W, H), pg.SRCALPHA)
            red.fill((200, 20, 30, int(90 * max(0.0, 1 - m / 0.7))))
            frame.blit(red, (0, 0))
            if m > 0.3:
                sk.pop_text(frame, sk.f_big, "!!", RED, (W / 2 + 300, 520), (m - 0.3) / 0.15, 8)
        e = t - B["end"]
        if e > 0:                                               # the end card
            veil = pg.Surface((W, H))
            veil.set_alpha(int(min(1.0, e / 0.5) * 130))
            frame.blit(veil, (0, 0))
            sk.pop_text(frame, sk.f_mid, "TAG KARO", (255, 255, 255), (W / 2, 640), e / 0.3, -3, outline=7)
            sk.pop_text(frame, sk.f_mid, "APNE", (255, 255, 255), (W / 2, 730), (e - 0.15) / 0.3, 2, outline=7)
            sk.pop_text(frame, sk.f_big, "FISSADI DOST", ORANGE, (W / 2, 860), (e - 0.3) / 0.3, -3)
            sk.pop_text(frame, sk.f_mid, "KO!", (255, 255, 255), (W / 2, 990), (e - 0.45) / 0.3, 3, outline=7)
        ff.stdin.write(pg.image.tobytes(frame, "RGB"))
    ff.stdin.close()
    ff.wait()
    wav = out / "_audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(soundtrack().tobytes())
    final = out / "maths_test_hi.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a",
                    "192k", "-shortest", str(final)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "24",
                    "-c:a", "aac", "-b:a", "128k", str(out / "preview_phone.mp4")], check=True)
    silent.unlink()
    wav.unlink()
    print(f"{final} ({TOTAL:.1f}s)")
    return final


def render():
    out = OUT / "maths_test_hi"
    p = params(out)
    root = Path(__file__).resolve().parents[2]
    stamp = hashlib.sha1((json.dumps(p, sort_keys=True) + (root / "blender" / "exam3d.py").read_text(encoding="utf-8")
                          + (root / "blender" / "chibi3d.py").read_text(encoding="utf-8")).encode()).hexdigest()
    sfile = out / "frames.stamp"
    if not (sfile.exists() and sfile.read_text() == stamp):
        blender.run("exam3d", p, timeout=6 * 3600)
        sfile.write_text(stamp)
    return overlay_and_mux(out)


def looks():
    pg.init()
    (OUT / "looks").mkdir(parents=True, exist_ok=True)
    for who in ("bunty", "golu"):
        pg.image.save(paper(who), str(OUT / "looks" / f"paper_{who}.png"))
    try:
        blender.run("exam3d", dict(out_dir=str(OUT / "looks"), mode="lineup", samples=32), timeout=900)
    except RuntimeError:
        pass                                                                  # lineup writes no result.json
    print((OUT / "looks").resolve())


if __name__ == "__main__":
    if "--render" in sys.argv:
        render()
    elif "--insert" in sys.argv:                               # test frames of the paper close-ups only
        pg.init()
        (OUT / "test").mkdir(parents=True, exist_ok=True)
        for who in ("bunty", "golu"):
            fr = pg.Surface((W, H))
            insert(fr, who, 1.6, pg.image.load(str(OUT / "papers" / f"{who}.png")), 1.0)
            pg.image.save(fr, str(OUT / "test" / f"insert_{who}.png"))
    elif "--looks" in sys.argv:
        looks()
    elif "--still" in sys.argv:
        stills([float(a) for a in sys.argv[sys.argv.index("--still") + 1:]])
