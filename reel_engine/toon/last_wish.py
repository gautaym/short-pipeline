"""The Last Wish (आख़िरी इच्छा): a jail skit for Bhess ki Eyes, drawn in Blender in the 2D chibi look.
Run: python -m reel_engine.toon.last_wish [--still FRAME ...] [--sound]

The jailer tells three prisoners they will hang and asks each for a last wish. Two ask to go home and are let
go; the third, clever one asks him to call the other two back... Pipeline as in positive_bhai_3d.py:
  1. every line is voiced (Maya TTS, local), with held beats for the run-outs, the drumroll and the scratch;
  2. Blender (blender/last_wish3d.py, cast in blender/chibi3d.py) renders the frames in front of painted
     backgrounds made locally with Z-Image (the gallows yard at dusk, the jail gate);
  3. pygame adds the hook, pop words, the comment pill and the end card; the mix adds the music (a suspense
     hook, bouncy release, drumroll, record scratch into silence, a chase), sound effects and laughter.
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
from .positive_bhai_3d import envelope, tok, crickets, slide_whistle, boing

NAME = "last_wish_hi"
FPS, W, H = 30, 1080, 1920
MUSIC_SEED = 41
VOICES = {   # v2 (2026-11-07): everyone goofy, pitched up and quick, like a tape on fast-forward
    "jailer": "maya:hi:Abhay@+2~1.5",
    "p1": "maya:hi:Ritvik@+5~1.45",          # innocent
    "p2": "maya:hi:Shaunak@+4~1.45",         # casually confident
    "p3": "maya:hi:Satvik@+4~1.45",          # clever, then terrified
}
VOICE_FX = {}
LINES = [   # (speaker, spoken line, caption)
    ("jailer", "तुम तीनों को फाँसी दी जाएगी!", ""),                          # 0
    ("jailer", "बताओ, तुम्हारी आख़िरी इच्छा क्या है?", ""),                   # 1
    ("p1", "सर... मुझे घर जाना है।", ""),                                      # 2
    ("jailer", "चलो ठीक है, तुम निकलो।", ""),                                 # 3
    ("p1", "[excited] सच में? धन्यवाद सर!", ""),                              # 4  (and he ambles off)
    ("jailer", "अब तू बता, तेरी आख़िरी इच्छा क्या है?", ""),                   # 5
    ("p2", "सर... मुझे भी घर जाना है।", ""),                                   # 6
    ("jailer", "चलो, तुम भी निकलो।", ""),                                     # 7
    ("p2", "[excited] वाह सर! आप तो बहुत अच्छे हो!", ""),                      # 8  (and he ambles off too)
    ("jailer", "तू बोल भाई, तेरी आख़िरी इच्छा क्या है?", ""),                  # 9  (a drumroll)
    ("p3", "सर... उन दोनों को वापस बुला लो!", ""),                            # 10 (they hear it)
    ("p2", "तेरी तो...!", ""),                                                 # 11 (and the two pounce)
    ("p3", "आआआ! सर! मेरी आख़िरी इच्छा cancel कर दो!", ""),                     # 12
    ("jailer", "No backsies! चलो, एक-एक करके लटको।", ""),                     # 13 (deadpan)
]
LINE_VOICE = {}
LINE_FX = {}
# held beats after a line: the stares (2, 6), turning to go (4, 8), the drumroll (9), the reaction to 420's wish
# (10, see BEAT), the pounce (11), the freeze (13)
PAUSE = {0: 1.25, 2: 0.4, 4: 0.45, 6: 0.4, 8: 0.45, 9: 0.75, 11: 0.5, 12: 0.2, 13: 0.4}
# the beat after "उन दोनों को वापस बुला लो!" (seconds after his voice ends, 2026-11-07 direction): a big thud; a
# pause; 102 can't believe it (a surprise sting) and a woman's laugh plays while the two look at each other; the
# laugh fades away; then, in half a second, both faces turn murderous, on a second thud
BEAT = dict(thud=0.0, surprise=0.75, laugh=0.75, laugh_full=3.0, laugh_fade=3.0, kill=7.0, end=7.35)
PAUSE[10] = BEAT["end"]
HOOK = "3 KAIDI. 1 AAKHRI ICHHA."
COMMENT = {8: "COMMENT: TUMHARI AAKHRI ICHHA KYA HOGI?"}
END_TOP, END_SUB = "SOCH SAMAJH KAR", "AAKHRI ICHHA MAANGO!"
END_TAG = "TAG KARO US DOST KO JO AISA KAREGA"
PLATES = {"yard": "out/2026-11-07/last_wish/bg/gallows_dusk_2.png", "gate": "out/2026-11-07/last_wish/bg/gate_2.png"}
LAST = len(LINES) - 1
OUTRO = 6.6                                      # the pull-out: the woman's laugh again (BEAT's 3 s + 3 s fade), then a beat
DASH = (0.0, 0.35)                               # the two storm back, from the start of line 11


EL_DIR = REPO_ROOT / "out" / "2026-11-07" / "last_wish" / "eleven"     # the ElevenLabs takes (eleven/lines.json)
# v3 (2026-11-07): ElevenLabs voices (eleven_v3), then nudged up and quicker like a tape on fast-forward;
# the jailer the least, so he stays kadak
# a tape on fast-forward: speed and pitch rise together (pace = 2 ** (semitones / 12)), the cartoon "chipmunk" voice
TAPE = {who: (st, 2 ** (st / 12)) for who, st in {"jailer": 3.0, "p1": 5.5, "p2": 4.5, "p3": 5.0}.items()}
GAP_S, LEAD_S, TAIL_S = 0.12, 0.1, 0.6


def el_clip(n, who):
    from ..core.voice import repitch, tighten
    if not (EL_DIR / f"{n:02d}_{who}.mp3").exists():          # not generated yet: a stand-in silence, for test stills
        print(f"warning: no ElevenLabs take for line {n:02d}; using silence")
        return np.zeros(int(SR * 0.9), np.float32) + 1e-4
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(EL_DIR / f"{n:02d}_{who}.mp3"), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = tighten(np.frombuffer(raw, np.float32).copy(), SR)
    semis, pace = TAPE[who]
    x = repitch(x, SR, semis, pace)
    return (x * (0.6 / (float(np.abs(x).max()) or 1.0))).astype(np.float32)


def timeline():
    clips = [el_clip(n, who) for n, (who, _, _) in enumerate(LINES)]
    starts, t = [], LEAD_S
    for n, c in enumerate(clips):
        starts.append(t)
        t += len(c) / SR + GAP_S + PAUSE.get(n, 0.0)
    story_end = t + TAIL_S
    lines = []
    for i, ((who, text, _), c) in enumerate(zip(LINES, clips)):
        nxt = starts[i + 1] if i + 1 < len(starts) else story_end
        lines.append(dict(start=starts[i], len=nxt - starts[i], who=who, env=envelope(c), voice=len(c) / SR))
    L = lines[LAST]
    freeze = L["start"] + L["voice"] + 0.35          # the camera starts pulling out here
    total = max(story_end + 2.2, freeze + OUTRO)     # the laugh again, full then fading, as the camera pulls out
    return clips, starts, story_end, total, lines, freeze


# ---------------------------------------------------------------- sound
def brass(f0, dur, level=0.6):
    """A low brass hit (the "dun dun DUNN")."""
    t = np.arange(int(SR * dur)) / SR
    ph = 2 * np.pi * f0 * t * (1 + 0.004 * np.sin(2 * np.pi * 5 * t) * (t > 0.25))
    w = sum(np.sin(k * ph) / k ** 0.9 for k in range(1, 9))
    w = np.tanh(1.6 * w) * np.minimum(1, t * 40) * np.exp(-t * (0.8 if dur > 0.8 else 2.2)) * np.minimum(1, (dur - t) * 10)
    sub = np.sin(2 * np.pi * f0 / 2 * t) * np.exp(-t * 2.0)
    w = w + 0.6 * sub
    return (w / np.abs(w).max() * level).astype(np.float32)


def orch_hit(root, dur, level=0.7, minor=True):
    """An orchestra hit: a brass chord (root, fifth, octave, third) with a noisy attack, in a register that
    phone speakers play."""
    t = np.arange(int(SR * dur)) / SR
    w = np.zeros(len(t))
    for ratio, amp in ((1.0, 1.0), (1.5, 0.7), (2.0, 0.6), (1.189 if minor else 1.26, 0.5), (0.5, 0.8)):
        ph = 2 * np.pi * root * ratio * t * (1 + 0.003 * np.sin(2 * np.pi * 5.5 * t) * (t > 0.2))
        w += amp * sum(np.sin(k * ph) / k for k in range(1, 7))
    w = np.tanh(1.4 * w / 3)
    w += 0.5 * np.random.default_rng(3).uniform(-1, 1, len(t)) * np.exp(-t * 30)
    env = np.minimum(1, t * 120) * np.exp(-t * (0.9 if dur > 0.8 else 3.5)) * np.minimum(1, (dur - t) * 8)
    w = w * env
    return (w / np.abs(w).max() * level).astype(np.float32)


def dun_dun_dunn():
    """"DUN DUN DUNNN": two short hits and a long one, a semitone down."""
    out = np.zeros(int(SR * 2.2), np.float32)
    for at, x in ((0.0, orch_hit(196.0, 0.3)), (0.3, orch_hit(196.0, 0.3)), (0.62, orch_hit(185.0, 1.5, 0.85))):
        s = int(at * SR)
        out[s:s + len(x)] += x
    return out / np.abs(out).max() * 0.9


def timpani(level=0.8):
    t = np.arange(int(SR * 0.9)) / SR
    w = np.sin(2 * np.pi * 70 * t * (1 - 0.15 * t)) * np.exp(-t * 5) + 0.3 * np.random.default_rng(1).uniform(-1, 1, len(t)) * np.exp(-t * 40)
    return (w / np.abs(w).max() * level).astype(np.float32)


def drumroll(dur, level=0.55):
    """A snare roll that swells, ending on a crash."""
    rng = np.random.default_rng(4)
    out = np.zeros(int(SR * (dur + 1.4)), np.float32)
    t = 0.0
    while t < dur:
        n = int(0.045 * SR)
        hit = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / (n / 5))
        a = int(t * SR)
        out[a:a + n] += (hit * (0.3 + 0.7 * (t / dur) ** 1.5)).astype(np.float32)
        t += 1 / 24
    n = int(1.4 * SR)
    crash = rng.uniform(-1, 1, n)
    crash = np.diff(crash, prepend=0) * np.exp(-np.arange(n) / (SR * 0.35))
    a = int(dur * SR)
    out[a:a + n] += (crash * 1.4).astype(np.float32)
    return out / np.abs(out).max() * level


def skid(level=0.4):
    t = np.arange(int(SR * 0.35)) / SR
    f = 1800 - 900 * t / 0.35
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.random.default_rng(2).uniform(0.6, 1.0, len(t))
    return (w * np.minimum(1, t * 50) * np.minimum(1, (0.35 - t) * 20) * level).astype(np.float32)


def laughter(level=0.6):
    """An audience laughing: five voices laughing (Maya, local), staggered and spread."""
    from ..core import voice as tts
    voices = ["maya:hi:Ritvik@+2~1.1", "maya:hi:Shaunak@+1~1.1", "maya:hi:Satvik@+1~1.1", "maya:hi:Abhay@-2~1.1",
              "maya:hi:Ishwari@+0~1.1", "maya:hi:Ritvik@-1~1.0"]
    line = "[laughs] हा हा हा हा हा!"
    clips = []
    for v in voices:
        tts.prepare([line], v.partition("@")[0])
    for v in voices:
        clips.append(tts.say(line, v))
    out = np.zeros(int(SR * 3.2), np.float32)
    for k, c in enumerate(clips):
        a = int((0.05 + 0.12 * k) * SR)
        c = c[:len(out) - a]
        out[a:a + len(c)] += c * (0.8 if k % 2 else 1.0)
    fade = np.linspace(1, 0, int(SR * 0.8), dtype=np.float32)
    out[-len(fade):] *= fade
    return out / (np.abs(out).max() or 1.0) * level


def slap(level=0.85, seed=0):
    """A sharp open-hand CHATAAK: a bright crack over a body hit."""
    rng = np.random.default_rng(seed)
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    crack = np.diff(rng.uniform(-1, 1, n + 1)) * np.exp(-t * 60)
    body = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 35)
    w = 1.3 * crack + 0.6 * body
    return (w / np.abs(w).max() * level).astype(np.float32)


SLAP_DT = 0.28


def slap_window(lines, freeze):
    """(first swing, last moment): the two slap 420 from just after they arrive until the outro laugh fades."""
    return lines[11]["start"] + DASH[1], freeze + BEAT["laugh_full"]


def slap_times(lines, freeze):
    """When each slap lands (the hand meets the face 0.35 of the way into each swing, as in the Blender scene)."""
    s0, s1 = slap_window(lines, freeze)
    out, k = [], 0
    while s0 + (k + 0.35) * SLAP_DT < s1:
        out.append(s0 + (k + 0.35) * SLAP_DT)
        k += 1
    return out


def laugh_fading(full, fade, level=0.7):
    """The woman's laugh (Pixabay): full for `full` seconds, then dying away over `fade` seconds."""
    x = sample("laugh_woman", level)[:int(SR * (full + fade))].copy()
    a = int(SR * full)
    n = len(x) - a
    x[a:] *= np.linspace(1, 0, n, dtype=np.float32) ** 1.6
    return x


def soundtrack(clips, starts, story_end, total, lines, freeze):
    def at(i, frac=0.0):
        return lines[i]["start"] + frac * lines[i]["voice"]

    def after(i, dt=0.0):
        return lines[i]["start"] + lines[i]["voice"] + dt

    bank = {
        "dun": dun_dun_dunn(),
        "boom": sample("explosion_low", 0.8),
        "timp": timpani(),
        "tok": tok(),
        "zip": whoosh(0.2, 600, 5000, 0.45),
        "whoosh": whoosh(0.35, 300, 3200, 0.4),
        "step": [sample("step1", 0.22), sample("step2", 0.22), sample("step3", 0.22)],
        "roll": drumroll(lines[9]["len"] - lines[9]["voice"] * 0.4 + lines[10]["voice"] * 0.2),
        "thud_big": sample("thud_dragon", 0.95),
        "surprise": sample("surprise_phoenix", 0.6),
        "laugh_w": laugh_fading(BEAT["laugh_full"], BEAT["laugh_fade"]),
        "slap": [slap(0.85, k) for k in range(4)],
        "punch": sample("punch_heavy", 0.5),
        "sparkle": sample("sparkle", 0.4),
    }
    ev = []
    hit0 = after(0, 0.02)                               # the hook: timpani at frame 0, then "DUN DUN DUNNN" in the
    ev += [(0.0, "timp", 0), (hit0 - 0.05, "zip", 0), (hit0, "dun", 0), (hit0 + 0.62, "boom", 0)]   # clear
    ev += [(after(2, 0.08), "tok", 0), (after(2, 0.26), "tok", 0), (at(3), "sparkle", 0)]
    ev += [(at(5), "timp", 0), (after(6, 0.08), "tok", 0), (after(6, 0.26), "tok", 0), (at(7), "sparkle", 0)]
    # the two ambling off: slow footsteps until the scratch
    t, k = after(4, 0.3), 0
    while t < after(10):
        ev.append((t, "step", k % 3))
        t += 0.42
        k += 1
    ev += [(at(9, 0.4), "roll", 0)]
    B = after(10)                                       # the reaction beat (see BEAT)
    ev += [(B + BEAT["thud"], "thud_big", 0), (B + BEAT["surprise"], "surprise", 0), (B + BEAT["laugh"], "laugh_w", 0),
           (B + BEAT["kill"], "thud_big", 0)]
    # the two storm back and the slapping starts, right through to the freeze
    ev += [(at(11, DASH[0]), "whoosh", 0)]
    s0 = at(11, 0) + DASH[1]
    for k, t in enumerate(slap_times(lines, freeze)):  # through the pull-out, until the laugh fades
        ev.append((t, "slap", k % 4))
        if k % 3 == 2:
            ev.append((t, "punch", 0))
    ev += [(freeze, "laugh_w", 0)]                     # the camera pulls out: the same laugh, the same fade

    bed = np.zeros(int(total * SR) + SR, np.float32)

    tracks = {}

    def el_music(name):
        """An ElevenLabs music track (eleven/music_<name>.mp3), or None if it isn't there."""
        if name not in tracks:
            f = EL_DIR / f"music_{name}.mp3"
            tracks[name] = None
            if f.exists():
                raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout
                tracks[name] = np.frombuffer(raw, np.float32).copy()
        return tracks[name]

    def section(t0, t1, style, seed, level=1.0, track=None, offset=0.0):
        """Music from t0 to t1: an ElevenLabs track (looped from `offset` s if short), else music composed here."""
        if t1 <= t0:
            return
        n = int((t1 - t0) * SR)
        src = el_music(track) if track else None
        if src is not None and len(src) > SR:
            a0 = int(offset * SR) % len(src)
            x = np.resize(np.roll(src, -a0), n).astype(np.float32)
        else:
            x = compose(t1 - t0 + 2.0, seed, style)[:n]
        x = x / (np.sqrt(np.mean(x ** 2)) or 1.0) * level
        k = min(len(x) // 3, int(0.08 * SR))
        x[:k] *= np.linspace(0, 1, k)
        x[-k:] *= np.linspace(1, 0, k)
        a = int(t0 * SR)
        bed[a:a + len(x)] += x[:len(bed) - a]

    section(0.0, hit0 - 0.05, "tense", MUSIC_SEED, 0.9, "suspense")                # the announcement, then the hit alone
    section(at(1), at(3), "tense", MUSIC_SEED + 7, 0.9, "suspense", 3.0)
    section(at(3), at(5), "chiptune", MUSIC_SEED + 1, 1.0, "goofy")                 # "चलो ठीक है": bouncy
    section(at(5), at(7), "tense", MUSIC_SEED + 2, 0.8, "suspense", 6.0)
    section(at(7), at(9), "chiptune", MUSIC_SEED + 1, 1.0, "goofy", 4.0)
    section(at(9), after(10, 0.02), "tense", MUSIC_SEED + 3, 0.9, "suspense", 8.0)   # the big question
    # (silence for the thud, the disbelief and the laugh)
    section(s0, freeze + BEAT["laugh_full"], "chiptune", MUSIC_SEED + 5, 1.1, "chaos")   # the slapping
    section(freeze + BEAT["laugh_full"] + 1.0, total, "festive", MUSIC_SEED + 6, 0.5, "goofy", 7.0)   # the end card
    return mix(ev, bank, total, bed=bed[:int(total * SR)], bed_level=0.5, speech=list(zip(starts, clips)))


# ---------------------------------------------------------------- overlays and the mux
def overlay_and_mux(out: Path, clips, starts, story_end, total, lines, freeze):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame as pg
    pg.init()
    from ..stick.durvasa import Episode
    sk = Episode(pg)
    silent = out / "_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", "-crf", "19", str(silent)],
                          stdin=subprocess.PIPE)
    n_frames = int(total * FPS)
    hit0 = lines[0]["start"] + lines[0]["voice"] + 0.02
    beat0 = lines[10]["start"] + lines[10]["voice"]
    slaps = slap_times(lines, freeze)
    words = [("CHATAAK!", RED, (300, 620), -10), ("THAPPAD!", ORANGE, (790, 560), 8), ("CHATAAK!", (255, 255, 255), (760, 760), 6),
             ("DHISHUM!", RED, (300, 820), -6)]
    for f in range(n_frames):
        t = f / FPS
        frame = pg.image.load(str(out / "frames" / f"f_{f + 1:04d}.png"))
        i = max([j for j, s in enumerate(starts) if s <= t] or [0])
        since = t - lines[i]["start"]
        b = t - beat0
        if t < 2.0:                                             # the hook
            sk.pill(frame, HOOK, 230, t / 0.3)
        if hit0 <= t < hit0 + 1.2:                              # "DUN DUN DUNNN": a red flash and FAANSI!
            red = pg.Surface((W, H), pg.SRCALPHA)
            red.fill((200, 20, 30, int(110 * max(0.0, 1 - (t - hit0) / 0.6))))
            frame.blit(red, (0, 0))
            sk.pop_text(frame, sk.f_big, "FAANSI!", RED, (W / 2, 1450), (t - hit0) / 0.2, -6)
        if i in COMMENT and since > 0.3:
            sk.pill(frame, COMMENT[i], 250, (since - 0.3) / 0.5)
        if 0 <= b < BEAT["surprise"]:                           # the thud
            sk.pop_text(frame, sk.f_big, "!!", RED, (W / 2, 520), b / 0.15, 6)
        if BEAT["surprise"] <= b < BEAT["kill"]:                # can't believe it
            sk.pop_text(frame, sk.f_big, "?!", (255, 255, 255), (W / 2 + 260, 520), (b - BEAT["surprise"]) / 0.2, 10)
        if BEAT["kill"] <= b < BEAT["end"] + 0.6:               # murderous: a red pulse
            red = pg.Surface((W, H), pg.SRCALPHA)
            red.fill((220, 0, 20, int(38 + 22 * math.sin(t * 25))))
            frame.blit(red, (0, 0))
        for k, ts in enumerate(slaps):                          # a pop word on every other slap
            if k % 2 == 0 and ts <= t < ts + 0.4 and t < freeze + 1.0:
                word, col, pos, ang = words[(k // 2) % len(words)]
                sk.pop_text(frame, sk.f_big, word, col, pos, (t - ts) / 0.1, ang)
        e = t - (freeze + BEAT["laugh_full"] - 0.5)             # the end card, as the laugh fades
        if e > 0:
            veil = pg.Surface((W, H))
            veil.set_alpha(int(min(1.0, e / 0.6) * 120))
            frame.blit(veil, (0, 0))
            sk.pop_text(frame, sk.f_mid, END_TOP, (255, 255, 255), (W / 2, 560), e / 0.35, -3, outline=6)
            sk.pop_text(frame, sk.f_big, "AAKHRI ICHHA", ORANGE, (W / 2, 700), (e - 0.15) / 0.35, -3)
            sk.pop_text(frame, sk.f_mid, "MAANGO!", (255, 255, 255), (W / 2, 840), (e - 0.3) / 0.35, 3, outline=6)
            if e > 0.9:
                sk.pill(frame, END_TAG, 1700, (e - 0.9) / 0.4)
        ff.stdin.write(pg.image.tobytes(frame, "RGB"))
    ff.stdin.close()
    ff.wait()

    pcm = soundtrack(clips, starts, story_end, total, lines, freeze)
    wav = out / "_audio.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    final = out / f"{NAME}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(final)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(final), "-vf", "scale=720:1280", "-c:v", "libx264", "-crf", "24", "-c:a",
                    "aac", "-b:a", "128k", str(out / "preview_phone.mp4")], check=True)
    silent.unlink()
    wav.unlink()
    print(f"{final} ({total:.1f}s)")
    return final


def params(out, lines, story_end, total, freeze):
    s0, s1 = slap_window(lines, freeze)
    return dict(out_dir=str(out), style="flat", mode="scene", width=W, height=H, fps=FPS, samples=16,
                frames=int(total * FPS), story_end=story_end, pull=freeze, lines=lines,
                beat0=lines[10]["start"] + lines[10]["voice"], beat=BEAT, slap0=s0, slap_dt=SLAP_DT, slap_end=s1,
                plates={k: str((REPO_ROOT / v).resolve()) for k, v in PLATES.items()})


def sound_test() -> Path:
    clips, starts, story_end, total, lines, freeze = timeline()
    out = REPO_ROOT / "out" / datetime.date.today().isoformat() / "last_wish" / "sound_test"
    out.mkdir(parents=True, exist_ok=True)
    wav = out / "sound_test.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(soundtrack(clips, starts, story_end, total, lines, freeze).tobytes())
    mp3 = out / "last_wish_sound_test.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)
    wav.unlink()
    print(mp3, f"{total:.1f}s")
    for k, (L, (who, text, _)) in enumerate(zip(lines, LINES)):
        print(f"{k:2d} {L['start']:6.2f} +{L['voice']:.2f} {who:6s} {text}")
    return mp3


def render(stills=None) -> Path:
    out = REPO_ROOT / "out" / "2026-11-07" / "last_wish" / NAME
    clips, starts, story_end, total, lines, freeze = timeline()
    p = params(out, lines, story_end, total, freeze)
    if stills:
        p["stills"] = stills
        blender.run("last_wish3d", p, timeout=3600)
        print(out / "stills")
        return out
    import hashlib
    import json
    stamp = hashlib.sha1((json.dumps(p, sort_keys=True) + (REPO_ROOT / "blender" / "last_wish3d.py").read_text(encoding="utf-8")
                          + (REPO_ROOT / "blender" / "chibi3d.py").read_text(encoding="utf-8")).encode()).hexdigest()
    sfile = out / "frames.stamp"
    if not (sfile.exists() and sfile.read_text() == stamp):
        blender.run("last_wish3d", p, timeout=6 * 3600)
        sfile.write_text(stamp)
    return overlay_and_mux(out, clips, starts, story_end, total, lines, freeze)


if __name__ == "__main__" and "--sound" in sys.argv:
    sound_test()
elif __name__ == "__main__":
    st = None
    if "--still" in sys.argv:
        st = [int(a) for a in sys.argv[sys.argv.index("--still") + 1:] if a.isdigit()]
    render(st)
