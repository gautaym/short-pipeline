"""Positive Bhai, part 1, chibi, recut for Shorts retention. Run: python -m reel_engine.toon.positive_bhai_recut
(--still [line numbers] renders single frames with no voices).

The full chibi reel (positive_bhai_chibi.py) runs 67 s and opens on a spoken title, so viewers swiped away
in the first seconds. This cut:
  - opens cold on the most shocking line, "uncle ko gaadi se uda diya", with the car and the BOOM on frame 0;
  - then whooshes back to the start of the chat ("THODI DER PEHLE...") and plays the story without that line;
  - drops the spoken title, "All the best" and "Thank you bhai" (the Dost simply comes back with the box);
  - trims the three long Positive Bhai lines and two Dost lines, for about 48 s in all.
The drawing, moods, panels and voices are the chibi reel's; lines are mapped back to their original numbers.
"""
import math
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from ..stick.durvasa import ORANGE
from ..stick.pressure_cooker import render as run
from . import positive_bhai as pb, positive_bhai_chibi as pc, sheru
from .chibi import ease

TRIM = {   # original line number -> shorter line (same speaker and voice)
    2: ("p2", "अरे, कोई बात नहीं! Positive सोचो, आज तुम्हारी वजह से, आंटी को नई साड़ी मिली होगी!", ""),
    6: ("p2", "इसमें तुम्हारी क्या गलती? तुमने तो बस, process fast कर दिया।", ""),
    9: ("p2", "बिल्कुल नहीं! दोनों पचहत्तर साल के थे। तुमने तो उनका reunion करवा दिया!", ""),
    10: ("p1", "[excited] अच्छा! तो और अंकल-आंटियों को भी ठोक दूँ?", ""),
    14: ("p1", "[excited] अरे हाँ भाई, तुम्हारे दादाजी भी तो अकेले हैं ना? Reunion वहीं से शुरू करता हूँ!", ""),
}
ALL = [TRIM.get(n, line) for n, line in enumerate(pb.LINES)]      # every original line, trimmed where needed
ORDER = [7, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 14, 15, 16]          # the cold open, then the story without it
NEW = {o: j for j, o in enumerate(ORDER)}

LINES = [ALL[o] for o in ORDER]
VOICES, VOICE_FX = pb.VOICES, pb.VOICE_FX
LINE_VOICE = {j: pb.LINE_VOICE[o] for j, o in enumerate(ORDER) if o in pb.LINE_VOICE}
LINE_FX = {j: pb.LINE_FX[o] for j, o in enumerate(ORDER) if o in pb.LINE_FX}
HOOK = ""                                                         # the BOOM panel is the hook; a title would cover it
COMMENT = {NEW[6]: "COMMENT: TUMHARA DOST BHI AISA HAI?", len(ORDER) - 1: "TAG KARO APNE SABSE POSITIVE DOST KO"}
CUTS = tuple(sorted({1} | {NEW[o] for o in pb.CUTS if o in NEW}))
LABELS, SPEAKER_COLOUR = pb.LABELS, pb.SPEAKER_COLOUR
SERIES, END_SUB, TAGLINE, EPISODE, MUSIC_SEED = pb.SERIES, pb.END_SUB, pb.TAGLINE, pb.EPISODE, pb.MUSIC_SEED
NAME = "positive_bhai_recut_hi"
W, H = pc.W, pc.H


class Skit(pc.Skit):
    def __init__(self, pg):
        sheru.base.Skit.__init__(self, pg)
        from ..core import voice as tts
        from ..core.audio import SR
        hop = SR // 30
        self.env = []
        for n, (who, line, _) in enumerate(ALL):                       # indexed by the original line numbers
            c = tts.say(line, pb.LINE_VOICE.get(n, VOICES[who]))
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

    def scene(self, surf, i, since, length, t):
        o = ORDER[i]
        cur = pc.shot(o)
        prev = pc.shot(ORDER[i - 1]) if i else cur
        q = ease(since / 0.5)
        cam = cur if q >= 1 else tuple(prev[j] + (cur[j] - prev[j]) * q for j in range(3))
        self.frame(surf, o, since, length, t, cam)
        if i == 1 and since < 1.6:                                     # back to the start of the chat
            self.pop_text(surf, self.f_mid, "THODI DER PEHLE...", ORANGE, (W / 2, 330), since / 0.3, -3)
        return (1.0, W / 2, H / 2)


def end_card(sk, frame, t, e):
    sk.frame(frame, len(pb.LINES) - 1, 3.0, 3.0, t, pc.TWO)


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
        sk = Skit.__new__(Skit)
        sheru.base.Skit.__init__(sk, pg)
        sk.env = [[0.2, 0.5, 0.9, 0.4, 0.2] * 24 for _ in ALL]
        sk.setup(pg)
        (out / "stills").mkdir(parents=True, exist_ok=True)
        surf = pg.Surface((W, H))
        picks = [int(a) for a in sys.argv[sys.argv.index("--still") + 1:]] or range(len(LINES))
        for n in picks:
            sk.cache = {k: v for k, v in sk.cache.items() if not isinstance(v, int)}
            sk.scene(surf, n, float(os.environ.get("SINCE", 1.0)), 4.0, 10.0 + n)
            pg.image.save(surf, str(out / "stills" / f"line_{n:02d}.png"))
        print(out / "stills")
    else:
        render(out)
