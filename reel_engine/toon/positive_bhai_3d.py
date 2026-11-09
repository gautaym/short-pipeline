"""Positive Bhai (the 48 s recut) drawn in Blender, in two looks for comparison with the pygame chibi cut.
Run: python -m reel_engine.toon.positive_bhai_3d [--style toon|flat|both] [--still FRAME ...]
(--sound writes only the soundtrack, as an mp3, to try the sound effects.)

Same script, voices and order as positive_bhai_recut.py (cold open on the car, then the chat). Here:
  1. every line is voiced (shared skit timing, plus a held beat after the cold open for the uncle's flight);
  2. Blender (blender/positive_bhai3d.py, cast and sets in blender/chibi3d.py) renders the frames, posing
     each one from the line being spoken: lip-sync from the voice's loudness, gestures on its beats;
  3. the frames get the overlays (FLASHBACK tag, BHADAAM!, 70, comment pills, the final caption, the end
     card) and the mix (voices, cuts, BOOM, music) and become positive_bhai_3d_<style>_hi.mp4.
style "toon": cel-shaded 3D with perspective; style "flat": flat colours, thick ink, no perspective (2D).
"""
import datetime
import math
import os
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..core import blender
from ..core.audio import SR, mix, sample, whoosh
from ..core.music import compose
from ..stick.durvasa import ORANGE, RED
from ..stick.pressure_cooker import say_part, voice_track
from . import positive_bhai_recut as rc

# the episode, for voice_track: the recut's lines, with a beat held after the cold open
# v4 (2026-11-06): the uncle scene comes back in its place in the story, after "process fast" (the cold open
# stays), and the reel ends on "Reunion वहीं से शुरू करता हूँ!" with Bhai keeling over
ORDER = [7, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14]
UNCLE_AGAIN = 7                                  # where the uncle scene plays the second time
VOICES, VOICE_FX = rc.VOICES, rc.VOICE_FX
LINE_VOICE = {j: rc.pb.LINE_VOICE[o] for j, o in enumerate(ORDER) if o in rc.pb.LINE_VOICE}
LINE_FX = {j: rc.pb.LINE_FX[o] for j, o in enumerate(ORDER) if o in rc.pb.LINE_FX}
COMMENT = {ORDER.index(6): "COMMENT: TUMHARA DOST BHI AISA HAI?", len(ORDER) - 1: "TAG KARO APNE SABSE POSITIVE DOST KO"}
CUTS = tuple(sorted({1, UNCLE_AGAIN} | {j for j, o in enumerate(ORDER) if o in rc.pb.CUTS}))
LABELS, SPEAKER_COLOUR = rc.LABELS, rc.SPEAKER_COLOUR
SERIES, END_SUB, MUSIC_SEED = rc.SERIES, rc.END_SUB, rc.MUSIC_SEED
# the director's cut (2026-11-06): the heart attack told slowly, in pieces ("|" is a spoken pause), then a
# beat of dead silence, and Positive Bhai's breezy "ओह... ok. कोई नहीं!"; the reunion line in the user's words
DIRECTED = {
    # v5: Bhai carries on through the age and the fun (the Dost only says the heart attack), a bit faster
    2: ("p2", "अरे, कोई बात नहीं! उन्हें नई साड़ी मिल गई होगी!", ""),
    3: ("p2", "वैसे भी, वो सत्तर साल की थीं।", ""),
    4: ("p2", "उनकी भी life में थोड़ा fun और excitement आया होगा।", ""),
    5: ("p1", "[sighs] भाई...|वो heart attack से मर गई।", ""),   # in one breath (v4)
    6: ("p2", "ओह... ok. कोई नहीं, सब मोह माया है भाई।", ""),
    8: ("p1", "भाई... मैं खराब बंदा हूँ क्या?", ""),
    9: ("p2", "तूने तो यार दोनों का मिलन करा दिया!", ""),
    11: ("p2", "म्म्म...|हम्म।", ""),                            # reluctant "mm... hmm" (v5)
}
LINES = [DIRECTED.get(o, rc.ALL[o]) for o in ORDER]
FAST_P2 = "maya:hi:Shaunak@+1~1.3"              # Bhai a little quicker up to "मोह माया"
for j, o in enumerate(ORDER):
    if o in (2, 3, 4, 6):
        LINE_VOICE[j] = FAST_P2
# held beats after a line (by its number in the full script): the uncle's flight; the Dost's deadpan stare after
# each of Bhai's spins (new saree, fun, process fast); the silence after "मर गई"; the Dost lighting up at "मिलन";
# Bhai frozen, then keeling over, at "dadaji"; a gulp
BEATS = {7: 1.3, 2: 0.75, 4: 0.75, 5: 1.0, 6: 0.7, 9: 0.6, 11: 1.0, 14: 1.5}
PAUSE = {j: BEATS[o] for j, o in enumerate(ORDER) if o in BEATS}
REACT = {2, 4, 6, 9, 14}                         # lines whose held beat cuts to a reaction in the courtyard
FPS, W, H = 30, 1080, 1920
HIT_T, FREEZE_T, FLIGHT_T = 2.3, 0.13, 1.35          # as in blender/positive_bhai3d.py


def envelope(c):
    hop = SR // FPS
    frames = len(c) // hop + 1
    rms = np.array([math.sqrt(float(np.mean(c[k * hop:(k + 1) * hop] ** 2))) if len(c[k * hop:(k + 1) * hop]) else 0.0
                    for k in range(frames)])
    top = float(np.percentile(rms, 95)) or 1.0
    e, out = 0.0, []
    for v in np.clip(rms / top, 0, 1):
        e = v if v > e else e * 0.6 + v * 0.4
        out.append(round(float(e), 3))
    return out


def timeline():
    clips, starts, story_end, total = voice_track(sys.modules[__name__])
    lines = []
    for i, (o, (who, _, _), c) in enumerate(zip(ORDER, LINES, clips)):
        nxt = starts[i + 1] if i + 1 < len(starts) else story_end
        L = dict(start=starts[i], len=nxt - starts[i], who=who, orig=o, env=envelope(c), voice=len(c) / SR)
        if o == 6:
            L["beat"] = onset_after_pause(L["env"]) / FPS              # "कोई नहीं!" after "ओह... ok."
        text = LINES[i][1]
        if "|" in text:                                # where the last spoken piece starts (the cut on "मर गई")
            from ..core import voice as tts
            voice = LINE_VOICE.get(i, VOICES[who])
            at = 0.0
            for k, part in enumerate(text.split("|")):
                at += 0.45 if k else 0.0
                L["mark"] = at
                d = len(say_part(part, voice)[0]) / SR
                at += d
            if o == 5:                                 # the cut lands on "मर गई", near the end of the breath
                L["mark"] += 0.6 * d
        lines.append(L)
    return clips, starts, story_end, total, lines


def reacting(L, since):
    return L["orig"] in REACT and since >= L["voice"]


def flashback(L, since):
    n, u = L["orig"], since / L["len"]
    if reacting(L, since):
        return False
    if n == 5:
        return since >= L.get("mark", L["len"] * 0.6)
    if n == 6:
        return since >= L.get("beat", 1.0) + 1.0
    if n == 1:
        return u >= 0.25
    if n == 2:
        return since / L["voice"] >= 0.45
    if n == 4:
        return since / L["voice"] >= 0.35
    if n == 14:
        return 0.15 < since / L["voice"] < 0.6
    return n in (7, 1, 2, 3, 4, 9)


def backdrops(out: Path) -> dict:
    """The gag-anime mood backgrounds, drawn here as images: sparkles, gloom, speed lines, shock."""
    import random
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    d = out / "backdrops"
    d.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(4)
    paths = {}

    def grad(top, bottom):
        s_ = pg.Surface((W, H))
        for y in range(H):
            k = y / H
            s_.fill(tuple(int(top[c] + (bottom[c] - top[c]) * k) for c in range(3)), (0, y, W, 1))
        return s_

    # sparkles: Positive Bhai's glow
    s_ = grad((255, 206, 224), (255, 238, 204))
    lay = pg.Surface((W, H), pg.SRCALPHA)
    for _ in range(70):
        r = rnd.randint(14, 70)
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        pg.draw.circle(lay, (255, 255, 255, 110), (x, y), r)
        pg.draw.circle(lay, (255, 255, 255, 200), (x, y), r, 4)
    for _ in range(30):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(20, 46)
        pts = [(x + math.cos(a * math.pi / 4) * (r if a % 2 == 0 else r * 0.22), y + math.sin(a * math.pi / 4) * (r if a % 2 == 0 else r * 0.22))
               for a in range(8)]
        pg.draw.polygon(lay, (255, 250, 210, 235), pts)
    s_.blit(lay, (0, 0))
    paths["sparkle"] = s_
    # gloom: the Dost's despair
    s_ = grad((60, 50, 104), (24, 20, 46))
    for _ in range(90):
        x = rnd.randint(0, W)
        y0 = rnd.randint(-200, H)
        ln = rnd.randint(200, 700)
        c = rnd.choice(((86, 74, 140), (40, 34, 72), (100, 90, 160)))
        pts = [(x + 10 * math.sin(k * 0.6), y0 + k * 20) for k in range(ln // 20)]
        pg.draw.lines(s_, c, False, pts, rnd.choice((3, 4, 6)))
    paths["gloom"] = s_
    # speed lines: a burst at the Dost
    s_ = pg.Surface((W, H))
    s_.fill((255, 200, 70))
    cx, cy = W / 2, H * 0.42
    for k in range(64):
        a0 = k / 64 * 2 * math.pi
        a1 = a0 + rnd.uniform(0.02, 0.06)
        far = 2400
        pg.draw.polygon(s_, (255, 240, 170) if k % 2 else (255, 150, 40),
                        [(cx + math.cos(a0) * 160, cy + math.sin(a0) * 160), (cx + math.cos(a0) * far, cy + math.sin(a0) * far),
                         (cx + math.cos(a1) * far, cy + math.sin(a1) * far)])
    pg.draw.circle(s_, (255, 252, 230), (int(cx), int(cy)), 220)
    paths["speed"] = s_
    # shock: cold blue with jagged cracks
    s_ = grad((170, 214, 255), (50, 96, 210))
    for k in range(34):
        a = k / 34 * 2 * math.pi
        r, pts = 180, []
        while r < 2200:
            pts.append((cx + math.cos(a) * r + rnd.uniform(-30, 30), cy + math.sin(a) * r + rnd.uniform(-30, 30)))
            r += rnd.uniform(90, 200)
        pg.draw.lines(s_, (240, 248, 255), False, pts, rnd.choice((4, 6, 9)))
    paths["shock"] = s_
    out_paths = {}
    for k, img in paths.items():
        p = d / f"{k}.png"
        pg.image.save(img, str(p))
        out_paths[k] = str(p.resolve())
    return out_paths


def onset_after_pause(env, start_f=6, within=75):
    """The frame where speech resumes after the longest pause in the first seconds of a line
    (e.g. "कोई नहीं" after "ओह... ok.")."""
    best, best_len, run = start_f, 0, 0
    for f in range(start_f, min(len(env), within)):
        if env[f] < 0.12:
            run += 1
        else:
            if run > best_len:
                best, best_len = f, run
            run = 0
    return best


def overlay_and_mux(out: Path, name: str, clips, starts, story_end, total, lines):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    from . import positive_bhai_chibi as pc, sheru
    sk = pc.Skit.__new__(pc.Skit)
    sheru.base.Skit.__init__(sk, pg)
    silent = out / "_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-crf", "19", str(silent)],
                          stdin=subprocess.PIPE)
    n_frames = int(total * FPS)
    for f in range(n_frames):
        t = f / FPS
        frame = pg.image.load(str(out / "frames" / f"f_{f + 1:04d}.png"))
        if t < story_end:
            i = max(j for j, s in enumerate(starts) if s <= t) if t >= starts[0] else 0
            L = lines[i]
            since, length = t - L["start"], L["len"]
            n, u = L["orig"], since / L["len"]
            if flashback(L, since):
                img = sk.text(sk.f_small, "FLASHBACK", (255, 255, 255), 0)
                r = img.get_rect(topleft=(56, 130)).inflate(26, 10)
                pg.draw.rect(frame, (40, 30, 60), r, border_radius=14)
                frame.blit(img, img.get_rect(center=r.center))
            if n == 1 and u > 0.45:
                sk.pop_text(frame, sk.f_big, "BHADAAM!", RED, (W / 2, 470), (u - 0.45) * length / 0.25, -8)
            if n == 3:
                sk.pop_text(frame, sk.f_big, "70", ORANGE, (W / 2 + 250, 560), since / 0.3, -6)
            if i == 1 and since < 1.6:
                sk.pop_text(frame, sk.f_mid, "THODI DER PEHLE...", ORANGE, (W / 2, 330), since / 0.3, -3)
            who = LINES[i][0]
            if LINES[i][2]:
                label = sk.text(sk.f_small, LABELS[who], SPEAKER_COLOUR[who], 5)
                frame.blit(label, label.get_rect(center=(W / 2, 1262)))
                sk.caption(frame, LINES[i][2], since, length, True)
            if n == 16 and since > 0.5:                       # police lights sweeping in from the edges
                red = int(since / 0.22) % 2 == 0
                glow = pg.Surface((W // 2, H), pg.SRCALPHA)
                for x in range(0, W // 2, 6):
                    a = int(120 * (1 - x / (W / 2)) ** 2)
                    pg.draw.rect(glow, (255, 30, 40, a) if red else (40, 90, 255, a), (x, 0, 6, H))
                if red:
                    frame.blit(glow, (0, 0))
                else:
                    frame.blit(pg.transform.flip(glow, True, False), (W // 2, 0))
            if i in COMMENT:
                sk.pill(frame, COMMENT[i], 250, (since - 0.4) / 0.6)
        else:
            e = t - story_end
            veil = pg.Surface((W, H))
            veil.set_alpha(110)
            frame.blit(veil, (0, 0))
            sk.pop_text(frame, sk.f_big, SERIES, RED, (W / 2, 560), e / 0.4)
            sk.pop_text(frame, sk.f_mid, END_SUB, (255, 255, 255), (W / 2, 700), (e - 0.3) / 0.4, outline=6)
            if e < 0.3:
                v2 = pg.Surface((W, H))
                v2.set_alpha(int(255 * (1 - e / 0.3)))
                frame.blit(v2, (0, 0))
        ff.stdin.write(pg.image.tobytes(frame, "RGB"))
    ff.stdin.close()
    ff.wait()

    pcm = soundtrack(clips, starts, story_end, total, lines)
    wav = out / "_audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    final = out / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(final)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "24", "-c:a",
                    "aac", "-b:a", "128k", str(out / "preview_phone.mp4")], check=True)
    silent.unlink()
    wav.unlink()
    print(f"{final} ({total:.1f}s)")
    return final


# ---------------------------------------------------------------- sound
def horn(dur=0.26, level=0.45):
    t = np.arange(int(SR * dur)) / SR
    w = np.tanh(3 * (np.sin(2 * np.pi * 415 * t) + np.sin(2 * np.pi * 523 * t)))
    return (w * np.minimum(1, t * 60) * np.minimum(1, (dur - t) * 40) * level).astype(np.float32)


def crackle(dur, level=0.5, rate=28, seed=5):
    """Crackers going off: a scatter of short, sharp noise bursts."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * dur), np.float32)
    for _ in range(int(dur * rate)):
        at = rng.integers(0, max(1, len(out) - 900))
        n = rng.integers(120, 700)
        burst = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (n / 4)) * rng.uniform(0.3, 1.0)
        out[at:at + n] += burst.astype(np.float32)
    return out * (level / (float(np.abs(out).max()) or 1.0))


def siren(dur=2.6, level=0.3):
    """A police siren wailing up and down (made here, not sampled)."""
    t = np.arange(int(SR * dur)) / SR
    f = 950 + 380 * np.sin(2 * np.pi * 0.85 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    return (w / 1.5 * np.minimum(1, t * 3) * np.minimum(1, (dur - t) * 2) * level).astype(np.float32)


def faded(x, dur, fade=0.25):
    x = x[:int(SR * dur)].copy()
    n, k = len(x), int(SR * fade)
    ramp = np.linspace(0, 1, k, dtype=np.float32)
    x[:k] *= ramp
    x[-k:] *= ramp[::-1]
    return x


def heartbeat(level=0.8):
    """Lub-dub: two low thumps."""
    out = []
    for f0, dur in ((62, 0.16), (52, 0.2)):
        t = np.arange(int(SR * dur)) / SR
        out.append(np.sin(2 * np.pi * f0 * t * (1 - 0.3 * t / dur)) * np.exp(-t / (dur / 4)))
        out.append(np.zeros(int(SR * 0.09)))
    w = np.concatenate(out)
    return (w / np.abs(w).max() * level).astype(np.float32)


def boing(dur=0.55, level=0.45):
    t = np.arange(int(SR * dur)) / SR
    f = 180 + 260 * np.exp(-t * 6) + 40 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 4)
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4)
    return (w * level).astype(np.float32)


def tok(level=0.6):
    """A woodblock knock: the deadpan beat."""
    t = np.arange(int(SR * 0.09)) / SR
    w = (np.sin(2 * np.pi * 820 * t) + 0.5 * np.sin(2 * np.pi * 1640 * t)) * np.exp(-t * 70)
    return (w / np.abs(w).max() * level).astype(np.float32)


def chan(level=0.5):
    """A bright stab for snap zooms."""
    t = np.arange(int(SR * 0.45)) / SR
    w = sum(np.sin(2 * np.pi * f * t) for f in (1046.5, 1318.5, 1568.0, 2093.0)) * np.exp(-t * 9)
    return (w / np.abs(w).max() * level).astype(np.float32)


def slide_whistle(dur=0.5, level=0.4, up=False):
    t = np.arange(int(SR * dur)) / SR
    f = (500 + 1100 * t / dur) if up else (1600 - 1100 * t / dur)
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t * 30) * np.minimum(1, (dur - t) * 20)
    return (w * level).astype(np.float32)


def wah(level=0.35):
    """A sad descending trombone-ish "wah wah wah waaah"."""
    out = []
    for f0, d in ((311, 0.28), (294, 0.28), (277, 0.28), (262, 0.8)):
        t = np.arange(int(SR * d)) / SR
        vib = 1 + 0.012 * np.sin(2 * np.pi * 6 * t) * (t > 0.3)
        ph = 2 * np.pi * np.cumsum(f0 * vib) / SR
        w = np.tanh(2.5 * (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph))) * np.minimum(1, t * 25) * np.minimum(1, (d - t) * 12)
        out.append(w)
    w = np.concatenate(out)
    return (w / np.abs(w).max() * level).astype(np.float32)


def crickets(dur, level=0.18, seed=3):
    """An awkward silence: crickets chirping."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * dur), np.float32)
    t = 0.1
    while t < dur - 0.2:
        for k in range(3):
            a = int((t + k * 0.045) * SR)
            n = int(0.022 * SR)
            tt = np.arange(n) / SR
            out[a:a + n] += (np.sin(2 * np.pi * 4700 * tt) * np.sin(np.pi * tt / 0.022)).astype(np.float32)[:len(out) - a]
        t += rng.uniform(0.45, 0.7)
    return out * level


def soundtrack(clips, starts, story_end, total, lines):
    """Voices over a score in sections, with Kenney CC0 effects (assets/sfx) and comedy stings made here:
    music that cuts dead for the heart attack and snaps back on "कोई नहीं", woodblock knocks on the deadpan stares,
    stabs on snap zooms, a record scratch, a slide whistle and a thud for Bhai keeling over, a siren to end."""
    def L(orig):
        return lines[ORDER.index(orig, 1)]           # the story's lines (the uncle's second time for 7)

    def at(orig, frac=0.0):
        return L(orig)["start"] + frac * L(orig)["len"]

    def after(orig, dt=0.0):                       # a moment after that line's voice ends (its held beat)
        return L(orig)["start"] + L(orig)["voice"] + dt

    bank = {
        "cut": whoosh(0.3, 300, 2500, 0.3),
        "step": [sample("step1", 0.35), sample("step2", 0.35), sample("step3", 0.35)],
        "engine": faded(sample("engine", 0.45), 1.25, 0.3),
        "horn": np.concatenate([horn(), np.zeros(int(SR * 0.08), np.float32), horn(0.34)]),
        "punch": sample("punch_heavy", 0.9),
        "explosion": sample("explosion", 0.8),
        "rumble": sample("explosion_low", 0.75),
        "fly": whoosh(1.2, 300, 4000, 0.45),
        "twinkle": sample("sparkle", 0.55),
        "fuse": crackle(1.0, 0.35, rate=45),
        "thud": sample("thud", 0.85),
        "sparkle": sample("sparkle", 0.45),
        "pop": sample("select", 0.6),
        "crackers": crackle(L(4)["voice"] * 0.65 + 0.7, 0.32, rate=22, seed=9),
        "crickets": crickets(L(11)["len"]),
        "ghost": sample("ghost", 0.5),
        "bell": sample("bell_heavy", 0.4),
        "board": sample("wood_pop", 0.7),
        "siren": siren(3.2),
        "sting": sample("confirm", 0.5),
        "heart": heartbeat(),
        "boing": boing(),
        "scratch": sample("scratch", 0.8),
        "gulp": sample("drop", 0.45),
        "tok": tok(),
        "chan": chan(),
        "zip": whoosh(0.18, 600, 5000, 0.4),
        "slide": slide_whistle(),
        "wah": wah(),
    }
    c0, c7 = starts[0], at(7)
    ev = [(starts[i], "cut", 0) for i in CUTS]
    # the uncle and the car: the cold open, and again in its place in the story
    for c in (c0, c7):
        ev += [(c + 0.05 + k * 0.24, "step", k % 3) for k in range(int((HIT_T - 0.25) / 0.24))]
        ev += [(c + HIT_T - 1.15, "engine", 0), (c + HIT_T - 0.62, "horn", 0), (c + HIT_T, "punch", 0),
               (c + HIT_T, "explosion", 0), (c + HIT_T + 0.02, "rumble", 0), (c + HIT_T + FREEZE_T, "fly", 0),
               (c + HIT_T + FREEZE_T + FLIGHT_T - 0.05, "twinkle", 0)]
    # BHADAAM, the soot reveal, the deadpan stares (one knock, two, three)
    def cut_at(orig, v):                           # a cut inside a line, at this fraction of its voice
        return at(orig) + v * L(orig)["voice"]

    ev += [(at(1, 0.25), "zip", 0), (at(1, 0.25), "fuse", 0), (at(1, 0.45), "explosion", 0), (at(1, 0.45), "rumble", 0),
           (at(1, 0.75), "thud", 0), (cut_at(2, 0.45) - 0.03, "zip", 0), (cut_at(2, 0.45), "boing", 0), (after(2, 0.12), "tok", 0),
           (at(3), "pop", 0), (cut_at(4, 0.35) - 0.03, "zip", 0), (cut_at(4, 0.35), "crackers", 0),
           (after(4, 0.1), "tok", 0), (after(4, 0.32), "tok", 0)]
    # the heart attack: dead silence, two heartbeats, the cut on "मर गई", her fall, her soul
    L5 = L(5)
    cut5 = at(5) + L5.get("mark", L5["len"] * 0.6)
    fall = cut5 + 0.15 * (L5["len"] - L5.get("mark", 0)) + 0.25
    ev += [(at(5, 0.08), "heart", 0), (cut5 - 0.75, "heart", 0), (fall, "thud", 0), (fall + 0.35, "ghost", 0)]
    # "ओह... ok." then "कोई नहीं!" with a snap zoom and sparkles; the ghost waves; the third stare
    back = at(6) + L(6).get("beat", 1.0)
    ev += [(back - 0.05, "chan", 0), (back, "sparkle", 0), (at(6) + L(6).get("beat", 1.0) + 1.0, "ghost", 0),
           (after(6, 0.1), "tok", 0), (after(6, 0.3), "tok", 0), (after(6, 0.5), "tok", 0)]
    # "मैं खराब हूँ क्या?": the sad trombone; the reunion; the Dost lights up; "ठोक दूँ?" speed lines
    ev += [(at(8) + L(8)["voice"] * 0.55, "wah", 0), (at(9), "bell", 0), (at(9, 0.1), "ghost", 0),
           (after(9, 0.05), "twinkle", 0), (at(10) - 0.02, "zip", 0), (at(10), "chan", 0)]
    # "आ... आ... ओह... हाँ, ठीक ही है।": awkward; the music drops out and the crickets come in
    ev += [(at(11) + 0.05, "crickets", 0)]
    # "dadaji": the record scratch, Bhai frozen, then keeling over like a plank
    ev += [(at(14) + L(14)["voice"] * 0.15, "cut", 0), (at(14) + L(14)["voice"] * 0.6, "cut", 0),
           (after(14), "scratch", 0), (after(14, 0.62), "slide", 0), (after(14, 0.9), "thud", 0),
           (story_end, "sting", 0)]

    # the score, in sections (each its own style), with silences where the comedy needs them
    bed = np.zeros(int(total * SR) + SR, np.float32)

    def section(t0, t1, style, seed, level=1.0):
        if t1 <= t0:
            return
        x = compose(t1 - t0 + 2.0, seed, style)[:int((t1 - t0) * SR)]
        x = x / (np.sqrt(np.mean(x ** 2)) or 1.0) * level
        k = min(len(x) // 3, int(0.12 * SR))
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
        a = int(t0 * SR)
        bed[a:a + len(x)] += x[:len(bed) - a]

    section(0.0, c0 + HIT_T, "tense", MUSIC_SEED, 0.8)                     # the uncle stomps, the car comes
    section(c0 + HIT_T + 0.4, at(5) - 0.05, "festive", MUSIC_SEED + 1)      # the story, bouncy
    section(back, c7, "chiptune", MUSIC_SEED + 2)                           # "कोई नहीं!" snaps it back
    section(c7, c7 + HIT_T, "tense", MUSIC_SEED, 0.8)                       # the uncle again
    section(c7 + HIT_T + 0.4, at(11), "chiptune", MUSIC_SEED + 2)
    section(at(14), after(14), "chiptune", MUSIC_SEED + 5)                  # after the awkward crickets
    section(story_end, total, "festive", MUSIC_SEED + 4)                    # the end card
    return mix(ev, bank, total, bed=bed[:int(total * SR)], bed_level=0.5, speech=list(zip(starts, clips)))


def sound_test() -> Path:
    """Only the soundtrack (voices, music, effects) as an mp3, to judge the sounds before a render."""
    clips, starts, story_end, total, lines = timeline()
    out = REPO_ROOT / "out" / datetime.date.today().isoformat() / "positive_bhai_sound_test"
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "sound_test.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(soundtrack(clips, starts, story_end, total, lines).tobytes())
    mp3 = out / "positive_bhai_sound_test.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)
    wav.unlink()
    print(mp3)
    return mp3


def render(style: str, stills=None) -> Path:
    name = f"positive_bhai_3d_{style}_hi"
    out = REPO_ROOT / "out" / datetime.date.today().isoformat() / name
    clips, starts, story_end, total, lines = timeline()
    params = dict(out_dir=str(out), style=style, width=W, height=H, fps=FPS, samples=24, frames=int(total * FPS),
                  story_end=story_end, lines=lines, backdrops=backdrops(out))
    if stills:
        params["stills"] = stills
        blender.run("positive_bhai3d", params, timeout=3600)
        print(out / "stills")
        return out
    import hashlib
    import json
    stamp = hashlib.sha1((json.dumps(params, sort_keys=True) + (REPO_ROOT / "blender" / "positive_bhai3d.py").read_text(encoding="utf-8")
                          + (REPO_ROOT / "blender" / "chibi3d.py").read_text(encoding="utf-8")).encode()).hexdigest()
    sfile = out / "frames.stamp"
    if not (sfile.exists() and sfile.read_text() == stamp):           # reuse frames only from the same scene and params
        blender.run("positive_bhai3d", params, timeout=6 * 3600)
        sfile.write_text(stamp)
    return overlay_and_mux(out, name, clips, starts, story_end, total, lines)


if __name__ == "__main__" and "--sound" in sys.argv:
    sound_test()
elif __name__ == "__main__":
    style = sys.argv[sys.argv.index("--style") + 1] if "--style" in sys.argv else "both"
    stills = None
    if "--still" in sys.argv:
        stills = [int(a) for a in sys.argv[sys.argv.index("--still") + 1:] if a.isdigit()]
    for s in (("toon", "flat") if style == "both" else (style,)):
        render(s, stills)
