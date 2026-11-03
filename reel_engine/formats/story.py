"""story: a narrated tale told with paper-cut puppets. One script, Hindi or English narration.

Scripts live in stories/<id>.yaml:

    id: neelkanth
    title: {en: "Why is Shiva's throat blue?", hi: "..."}
    summary: {en: "...", hi: "..."}
    music: tense
    cast:
      shiva: {preset: shiva}
    beats:
      - en: "Narration in English."
        hi: "Narration in Hindi."
        caption: "SHORT ON-SCREEN LINE, *highlighted* WORD"
        scene: cosmos
        actors:
          shiva: {x: 560, pose: raise, face: 1, scale: 1.1, flags: [blue_throat], prop: bowl, glow: true}
        camera: {zoom: 1.15, focus: [540, 1000]}
    end: {head: "NEELKANTH", sub: "the blue-throated one"}

Each beat lasts as long as its narration (in the chosen language) plus a short pause; puppets
glide between their positions and poses from one beat to the next. Captions are English.

Puppet-theatre stories add an `art` block and a `stage` per beat (see reel_engine/story/art.py
and theatre.py); `reel story-art <id>` draws their puppets and backdrops. Once all are drawn, the
reel moves cut-out puppets on painted backdrops instead of the code-drawn puppets, with serif
captions in the lower third.
"""
import math
import random
from pathlib import Path

import yaml

from ..config import REPO_ROOT, load_settings
from ..core import voice as tts
from ..core.audio import SR, SoundBank, tone
from ..core.canvas import H, W
from ..core.text import outlined
from ..story.puppet import POSES, PRESETS, Actor, blend, draw, strings
from ..story.scenes import Stage, glow
from . import EndCard, Format, Option, register

STORIES = REPO_ROOT / "stories"
GAP_S = 0.45                    # pause after each narrated line
MOVE_S = 0.9                    # puppets glide to their new marks over this long
WORDS_PER_S = 2.4               # used to time lines when no voice model is installed
CAPTION_Y = 470
HIGHLIGHT = (120, 220, 230)
ART_HIGHLIGHT = (255, 196, 90)
ART_CAPTION_Y = 1330            # lower third, above what the Shorts buttons cover: faces stay clear


def story_ids() -> list[str]:
    return sorted(p.stem for p in STORIES.glob("*.yaml") if not p.stem.startswith("_")) if STORIES.is_dir() else []


def load_story(name: str) -> dict:
    p = Path(name)
    if not (p.suffix in (".yaml", ".yml") and p.exists()):
        p = STORIES / f"{name}.yaml"
    if not p.exists():
        raise SystemExit(f"unknown story {name!r}; available: {', '.join(story_ids())}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@register
class Story(Format):
    name = "story"
    order = 200
    default_duration = 60.0
    in_random_pool = False
    max_scout = 1
    heavy = True                 # a full narrated story per render: kept out of the quick per-format tests
    seed_note = False
    intro_s = 0.0
    options = (Option("--story", "story: script id from stories/ or a .yaml path", {"default": None}),
               Option("--lang", "story: narration language, en or hi", {"choices": ["en", "hi"], "default": "en"}))
    cta = "Follow for more stories"
    series = "Story"
    tags = ("story", "indian mythology", "animation", "shorts", "kahani")
    hashtags = ("story", "mythology", "animation")
    end_veil = True

    @classmethod
    def titles(cls, o):
        return [o["title"], f"{o['title']} #story", f"{o['title']} | {o['series_title']}"]

    @classmethod
    def describe(cls, o):
        return o.get("summary", "")

    # ---------------------------------------------------------- setup
    def setup(self) -> None:
        sid = getattr(self.opts, "story", None) or self.rng.choice(story_ids())
        self.sc = load_story(sid)
        from ..story.art import cast_segment
        cast_segment(self.sc)
        self.lang = getattr(self.opts, "lang", None) or "en"
        self.music = self.sc.get("music", "chill")
        self.settings = load_settings(getattr(self.opts, "config", None))
        self.cast = {k: PRESETS[v["preset"]] for k, v in self.sc["cast"].items()}
        self.beats = self.sc["beats"]
        self.title_text = self.sc["title"][self.lang]
        self.lines = [self.sc["title"][self.lang]] + [b[self.lang] for b in self.beats]
        self.voices = [self.asker(self.settings)] + [self.narrator(self.settings)] * len(self.beats)
        if self.settings.voice:
            for v in dict.fromkeys(self.voices):
                if tts.available(v):
                    tts.prepare([t for t, w in zip(self.lines, self.voices) if w == v], v)
        lengths = [self.spoken_length(text, v) for text, v in zip(self.lines, self.voices)]
        self.starts, t = [], lengths[0] + GAP_S + 0.2
        for n in lengths[1:]:
            self.starts.append(t)
            t += n + GAP_S
        self.title_len = lengths[0]
        self.max_play = t + 0.4
        self.beat_i = 0
        self.prev_state: dict = {}
        self.state: dict = {}

    def narrator(self, settings) -> str:
        return settings.voice_name_hi if self.lang == "hi" else settings.voice_name

    def asker(self, settings) -> str:
        """The question is asked by the segment's asker (a young girl's voice), else the narrator."""
        if not self.sc.get("segment"):
            return self.narrator(settings)
        return settings.voice_name_asker_hi if self.lang == "hi" else settings.voice_name_asker

    def spoken_length(self, text: str, voice: str | None = None) -> float:
        voice = voice or self.narrator(self.settings)
        if self.settings.voice and tts.available(voice):
            return len(tts.say(text, voice, self.settings.voice_speed)) / SR
        return max(1.2, len(text.split()) / WORDS_PER_S)

    def narration(self) -> list[tuple]:
        """(start, text, voice) for every spoken line: the question, then each beat."""
        times = [0.15] + [t + 0.1 for t in self.starts]
        return [(t, text, v) for t, text, v in zip(times, self.lines, self.voices)]

    def title_hooks(self) -> list[str]:
        return [self.sc["title"]["en"]]

    # ---------------------------------------------------------- timeline
    def current_beat(self) -> int:
        i = 0
        for k, s in enumerate(self.starts):
            if self.play_t >= s:
                i = k
        return i

    def step(self, dt: float, t: float) -> None:
        pass

    def check_end(self, t: float):
        return "told" if self.play_t >= self.max_play else None

    def end_card(self) -> EndCard:
        e = self.sc.get("end", {})
        return EndCard(e.get("head", "THE END"), e.get("sub", ""))

    def outcome(self):
        return {**super().outcome(), "story": self.sc["id"], "lang": self.lang, "title": self.title_text,
                "series_title": self.sc.get("series", {}).get(self.lang, "Stories"),
                "summary": self.sc.get("summary", {}).get(self.lang, "")}

    def slug(self) -> str:
        return f"story_{self.sc['id']}_{self.lang}"

    def sounds(self) -> SoundBank:
        return {"clear": tone(392, 1.6, 2.5, harm=0.3) * 0.25, "fail": tone(392, 1.6, 2.5, harm=0.3) * 0.25}

    def end_sound(self, why: str) -> str:
        return "clear"

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        self.stage = Stage(self.pg, self.seed)
        self.canvas = self.pg.Surface((W, H))
        self.layer = self.pg.Surface((W * 2, H * 2), self.pg.SRCALPHA)
        self.caption_cache: dict[int, object] = {}
        from ..core.text import font_path
        self.caption_font = self.pg.font.Font(font_path(), 68)
        self.actors: dict[str, Actor] = {}
        self.marks: dict[str, tuple[dict, dict]] = {}                 # name -> (from, to)
        self.mark_beat = -1
        from ..story.theatre import Theatre
        self.theatre = Theatre.load(self.pg, self.sc, self.seed)
        if self.theatre:
            from ..core.text import serif_path
            self.caption_font = self.pg.font.Font(serif_path("Bold"), 84)
            self.shade = self.caption_shade()

    def caption_shade(self):
        """A soft dark band behind the captions so they read over any picture."""
        import numpy as np
        band = self.pg.Surface((W, 520), self.pg.SRCALPHA)
        band.fill((8, 4, 2, 255))
        y = np.arange(520) / 519
        alpha = (np.minimum(1.0, np.minimum(y, 1 - y) * 3.2) * 150).astype(np.uint8)
        self.pg.surfarray.pixels_alpha(band)[:] = np.broadcast_to(alpha, (W, 520))
        return band

    def draw_staged(self, screen, t: float) -> None:
        opening = self.play_t < self.starts[0]
        cold = self.sc.get("opening")
        if opening and cold:                                     # cold open: the best frame, the question, the host
            b = int(cold.get("beat", 1)) - 1
            self.theatre.draw(screen, b, 4.0, self.beat_len(b), t, extras=cold.get("actors", {}),
                              extras_since=self.play_t)
            self.draw_hook(screen)
            self.dip(screen, (self.starts[0] - self.play_t) / 0.3)
            return
        i = 0 if opening else self.current_beat()
        since = 0.0 if opening else self.play_t - self.starts[i]
        self.theatre.draw(screen, i, since, self.beat_len(i), t, opening)
        if opening:
            self.draw_opening(screen, t)
            return
        if cold and i == 0:
            self.dip(screen, since / 0.3)
        cap = self.caption(i)
        if cap is not None:
            end = self.starts[i] + self.beat_len(i)
            a = max(0.0, min(1.0, since / 0.35, (end - self.play_t) / 0.35))
            self.shade.set_alpha(int(255 * a))
            screen.blit(self.shade, (0, ART_CAPTION_Y - 260))
            cap.set_alpha(int(255 * a))
            screen.blit(cap, cap.get_rect(center=(W / 2, ART_CAPTION_Y)))

    def dip(self, screen, k: float) -> None:
        """Black over the frame, fully at k = 0 and gone by k = 1: a quick dip between cold open and story."""
        if k < 1:
            veil = self.pg.Surface((W, H))
            veil.set_alpha(int(255 * (1 - max(0.0, k))))
            screen.blit(veil, (0, 0))

    def draw_hook(self, screen) -> None:
        """The question in big type at the top, with the series and part above it."""
        if not hasattr(self, "hook_card"):
            from ..core.text import outlined, serif_path, text_block
            big = self.pg.font.Font(serif_path("Bold"), 104)
            self.hook_card = text_block(self.pg, big, self.sc["title"]["en"].upper(), (250, 244, 228), W - 120, outline=7)
            part = self.sc.get("series_part")
            words = ("", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN")
            part = words[part] if isinstance(part, int) and part < len(words) else part   # the serif's digits are small
            label = self.sc.get("series", {}).get("en", "") + (f"  ·  PART {part}" if part else "")
            small = self.pg.font.Font(serif_path("Bold"), 58)
            self.series_tag = outlined(self.pg, small, label.upper(), ART_HIGHLIGHT, 4) if label else None
        k = min(1.0, self.play_t / 0.35)
        self.hook_card.set_alpha(int(255 * k))
        top = 250
        if self.series_tag is not None:
            self.series_tag.set_alpha(int(255 * k))
            screen.blit(self.series_tag, self.series_tag.get_rect(center=(W / 2, top)))
        screen.blit(self.hook_card, self.hook_card.get_rect(midtop=(W / 2, top + 50)))

    def target(self, name: str, spec: dict) -> dict:
        pose = dict(POSES[spec.get("pose", "stand")])
        return {"x": float(spec.get("x", W / 2)), "y": float(spec.get("y", H * 0.8)), "scale": float(spec.get("scale", 1.0)),
                "face": int(spec.get("face", 1)), "pose": pose, "alpha": 1.0, "flags": set(spec.get("flags", [])),
                "prop": spec.get("prop", "keep"), "glow": bool(spec.get("glow", False))}

    def advance_marks(self, i: int) -> None:
        """At a new beat, every actor glides from where it is now to its mark in the beat."""
        beat = self.beats[i]
        wanted = beat.get("actors", {}) or {}
        new = {}
        for name in set(self.marks) | set(wanted):
            now = self.marks[name][1] if name in self.marks else None
            if name in wanted:
                to = self.target(name, wanted[name])
                frm = now or {**to, "alpha": 0.0}
            else:
                frm = now
                to = {**now, "alpha": 0.0}
            new[name] = (frm, to)
        self.marks = new
        self.mark_beat = i

    def actor_now(self, name: str, k: float) -> Actor:
        frm, to = self.marks[name]
        e = k * k * (3 - 2 * k)
        look = self.cast[name]
        prop = to["prop"] if to["prop"] != "keep" else look.prop
        if prop != look.prop:
            from dataclasses import replace
            look = replace(look, prop=prop)
        a = Actor(look, frm["x"] + (to["x"] - frm["x"]) * e, frm["y"] + (to["y"] - frm["y"]) * e,
                  frm["scale"] + (to["scale"] - frm["scale"]) * e, to["face"] if k > 0.5 else frm["face"],
                  blend(frm["pose"], to["pose"], k), frm["alpha"] + (to["alpha"] - frm["alpha"]) * e,
                  phase=sum(map(ord, name)) % 7, flags=to["flags"] if k > 0.5 else frm["flags"])
        return a

    def camera(self, i: int, k: float) -> tuple[float, float, float]:
        def cam(b):
            c = (b or {}).get("camera", {}) or {}
            fx, fy = c.get("focus", (W / 2, H / 2))
            return float(c.get("zoom", 1.0)), float(fx), float(fy)
        z1, x1, y1 = cam(self.beats[i - 1]) if i > 0 else cam(None)
        z2, x2, y2 = cam(self.beats[i])
        e = k * k * (3 - 2 * k)
        return z1 + (z2 - z1) * e, x1 + (x2 - x1) * e, y1 + (y2 - y1) * e

    def caption(self, i: int):
        if i not in self.caption_cache:
            text = self.beats[i].get("caption", "")
            words = []
            for w in text.split():
                hot = w.startswith("*") or w.rstrip(".,!?").endswith("*")
                words.append((w.replace("*", ""), hot))
            hi = ART_HIGHLIGHT if self.theatre else HIGHLIGHT
            pieces = [outlined(self.pg, self.caption_font, w, hi if hot else (250, 244, 228), 5)
                      for w, hot in words]
            if not pieces:
                self.caption_cache[i] = None
            else:
                rows, row, width = [], [], 0                         # wrap to the screen width
                for p in pieces:
                    if row and width + p.get_width() > W - 120:
                        rows.append(row)
                        row, width = [], 0
                    row.append(p)
                    width += p.get_width() + 18
                rows.append(row)
                h = max(p.get_height() for p in pieces)
                surf = self.pg.Surface((W - 60, h * len(rows) + 10 * (len(rows) - 1)), self.pg.SRCALPHA)
                for r, row in enumerate(rows):
                    total = sum(p.get_width() for p in row) + 18 * (len(row) - 1)
                    x = (surf.get_width() - total) / 2
                    for p in row:
                        surf.blit(p, (x, r * (h + 10)))
                        x += p.get_width() + 18
                self.caption_cache[i] = surf
        return self.caption_cache[i]

    def draw_title(self, screen, t: float) -> None:
        pass

    def draw_hud(self, screen) -> None:
        pass

    def draw_world(self, screen, t: float) -> None:
        if self.theatre:
            return self.draw_staged(screen, t)
        pg = self.pg
        i = self.current_beat()
        if i != self.mark_beat:
            self.advance_marks(i)
        start = self.starts[i]
        k = max(0.0, min(1.0, (self.play_t - start) / MOVE_S)) if self.play_t >= self.starts[0] else 1.0
        scene = self.beats[i].get("scene", "cosmos")
        prev_scene = self.beats[i - 1].get("scene", "cosmos") if i > 0 else scene
        self.stage.draw(self.canvas, scene, t)
        if prev_scene != scene and k < 1:                           # cross-fade between scenes
            old = pg.Surface((W, H))
            self.stage.draw(old, prev_scene, t)
            old.set_alpha(int(255 * (1 - k)))
            self.canvas.blit(old, (0, 0))
        self.layer.fill((0, 0, 0, 0))
        for name in sorted(self.marks, key=lambda n: self.marks[n][1]["y"]):
            a = self.actor_now(name, k)
            if a.alpha <= 0.01:
                continue
            if self.marks[name][1]["glow"]:
                glow(pg, self.canvas, (a.x, a.y - 330 * a.scale), int(420 * a.scale), (120, 100, 60), 0.9 * a.alpha)
            big = Actor(a.look, a.x * 2, a.y * 2, a.scale * 2, a.face, a.pose, a.alpha, a.phase, a.flags)
            if a.alpha < 0.99:
                tmp = pg.Surface((W * 2, H * 2), pg.SRCALPHA)
                pts = draw(pg, tmp, big, t)
                tmp.set_alpha(int(255 * a.alpha))
                self.layer.blit(tmp, (0, 0))
            else:
                pts = draw(pg, self.layer, big, t)
            strings(pg, self.layer, pts)
            if "blue_throat" in a.flags:
                tx, ty = pts["throat"]
                glow(pg, self.canvas, (tx / 2, ty / 2), int(70 * a.scale), (40, 90, 200), 1.0)
        self.canvas.blit(pg.transform.smoothscale(self.layer, (W, H)), (0, 0))
        z, fx, fy = self.camera(i, max(0.0, min(1.0, (self.play_t - start) / max(0.1, self.beat_len(i)))))
        if z > 1.001:
            cw, ch = W / z, H / z
            x0 = min(max(0, fx - cw / 2), W - cw)
            y0 = min(max(0, fy - ch / 2), H - ch)
            view = self.canvas.subsurface((x0, y0, cw, ch))
            screen.blit(pg.transform.smoothscale(view, (W, H)), (0, 0))
        else:
            screen.blit(self.canvas, (0, 0))
        cap = self.caption(i) if self.play_t >= self.starts[0] else None
        if cap is not None:
            end = self.starts[i] + self.beat_len(i)
            a = min(1.0, (self.play_t - start) / 0.3, max(0.0, (end - self.play_t) / 0.3))
            cap.set_alpha(int(255 * max(0.0, a)))
            screen.blit(cap, cap.get_rect(center=(W / 2, CAPTION_Y)))
        if self.play_t < self.starts[0]:                             # opening title card
            self.draw_opening(screen, t)

    def draw_opening(self, screen, t: float) -> None:
        from ..core.text import text_block
        if not hasattr(self, "opening"):
            self.opening = text_block(self.pg, self.fonts.hook, self.sc["title"]["en"], (250, 244, 228), W - 140, outline=6)
        k = min(1.0, self.play_t / 0.6) * min(1.0, max(0.0, (self.starts[0] - self.play_t) / 0.4))
        self.opening.set_alpha(int(255 * k))
        screen.blit(self.opening, self.opening.get_rect(center=(W / 2, H * 0.42)))

    def beat_len(self, i: int) -> float:
        nxt = self.starts[i + 1] if i + 1 < len(self.starts) else self.max_play
        return nxt - self.starts[i]
