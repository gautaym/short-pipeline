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
from ..story.theatre import ease
from . import EndCard, Format, Option, register

STORIES = REPO_ROOT / "stories"
GAP_S = 0.45                    # pause after each narrated line
LEAD_S = 1.0                    # a beat of silence on the opening frame before the question
FAST_LEAD_S = 0.1               # stories with `pace: fast` start talking at once
FAST_GAP_S = 0.2                # and leave only a breath between lines
FAST_PACE = 1.12                # the narrator speaks this much quicker (pitch kept)
REPLY_GAP_S = 0.3               # the narrator takes the question straight up, as in conversation
MOVE_S = 0.9                    # puppets glide to their new marks over this long
WORDS_PER_S = 2.4               # used to time lines when no voice model is installed
CAPTION_Y = 470
HIGHLIGHT = (120, 220, 230)
ART_HIGHLIGHT = (255, 196, 90)
ART_CAPTION_Y = 1330            # lower third, above what the Shorts buttons cover: faces stay clear
CARD_FILL = (26, 22, 56, 215)   # name and title cards: deep indigo with a gold edge
NAME_Y = 950                    # a beat's name card, lower left, above the caption band
NAME_IN_S = 0.5                 # it slides in this far into the beat
NAME_HOLD_S = 4.0               # and stays this long
TITLE_Y = 300                   # a beat's title card (an event or a place), top centre
TITLE_IN_S = 0.2
HOOK_BOTTOM = H - 330           # `hook_at: bottom_left|bottom_right`: the question sits just above the bottom
HOOK_MARGIN = 60                # this far from the side
HOOK_SIDE_W = 300               # and keeps clear of the Shorts buttons down the right edge
# Stories with `edit:` get a short-video edit layer: per-beat `cut: [...]` effects, a film grade, and
# word-by-word captions (`edit: {grade: film, captions: kinetic}`).
PUNCH_S = 0.35                  # cut punch: the frame kicks in and settles back
PUNCH_ZOOM = 0.14
GLITCH_S = 0.4                  # cut glitch: colour split and torn slices
FLASH_S = 0.3                   # cut flash: a white flash
CUT_SOUNDS = {"punch": "punch", "glitch": "glitch", "flash": "bell", "drop": "drop", "buzz": "buzz",
              "scratch": "scratch"}
WORD_POP_S = 0.16               # kinetic captions: each word pops in over this long
COMMENT_Y = 250                 # a beat's `comment: "..."` prompt: a pill near the top, clear of the faces
COMMENT_IN_S = 0.6              # it pops in this far into the beat and stays to the beat's end


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
               Option("--lang", "story: narration language, en or hi", {"choices": ["en", "hi"], "default": "en"}),
               Option("--captions", "story: all, or few (only beats marked `key: true`)",
                      {"choices": ["all", "few"], "default": "all"}))
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
        if self.asks():
            opening = [("[excited] " + self.title_text, self.asker(self.settings))]   # the hook, asked eagerly
            if self.reply():                                                # and the narrator taking it up
                opening.append((self.reply(), self.narrator(self.settings)))
        else:                                                               # a story told straight: the
            opening = [(self.title_text, self.narrator(self.settings))]     # narrator says the hook
        self.lines = [t for t, _ in opening] + [b[self.lang] for b in self.beats]
        self.voices = [v for _, v in opening] + [self.narrator(self.settings)] * len(self.beats)
        if self.settings.voice:
            for v in dict.fromkeys(self.voices):
                if tts.available(v):
                    tts.prepare([t for t, w in zip(self.lines, self.voices) if w == v], v)
        lengths = [self.spoken_length(text, v) for text, v in zip(self.lines, self.voices)]
        fast = self.fast()
        lead, gap = (FAST_LEAD_S, FAST_GAP_S) if fast else (LEAD_S, GAP_S)
        self.open_times, t = [], lead
        for n in lengths[:len(opening)]:
            self.open_times.append(t)
            t += n + REPLY_GAP_S
        self.starts, t = [], t - REPLY_GAP_S + gap
        for n in lengths[len(opening):]:
            self.starts.append(t)
            t += n + gap
        self.title_len = lengths[0]
        self.max_play = t + 0.4
        self.beat_i = 0
        self.prev_state: dict = {}
        self.state: dict = {}

    def narrator(self, settings) -> str:
        """The segment narrator's own voice (the same person in both languages), else the default."""
        v = self.character_voice("narrator") or (settings.voice_name_hi if self.lang == "hi" else settings.voice_name)
        return v + f"@+0~{FAST_PACE}" if self.fast() and "@" not in v else v

    def character_voice(self, role: str) -> str | None:
        own = self.sc.get("voice", {}).get(self.lang) if role == "narrator" else None
        if own:                                             # a story's own narrator, e.g. a young voice for POV
            return own
        from ..story.art import segment
        pair = segment(self.sc)
        if not pair:
            return None
        return load_story("_library").get("voices", {}).get(pair[role], {}).get(self.lang)

    def asks(self) -> bool:
        """Whether the reel opens on the asker's question: most do, but a story that is not a
        question-and-answer sets `ask: false` and the narrator opens alone."""
        return bool(self.sc.get("segment")) and self.sc.get("ask", True) is not False

    def reply(self) -> str | None:
        """What the narrator says to the question before the story starts ("Let me tell you."), from
        the story's `reply:` or the narrator's in the library; in Hindi it carries the narrator's
        gender (बताता हूँ / बताती हूँ)."""
        own = self.sc.get("reply")
        if own:
            return own[self.lang]
        from ..story.art import segment
        pair = segment(self.sc)
        if not pair:
            return None
        return load_story("_library").get("replies", {}).get(pair["narrator"], {}).get(self.lang)

    def asker(self, settings) -> str:
        """The question is asked by the segment's asker (a young adult), else the narrator."""
        if not self.sc.get("segment"):
            return self.narrator(settings)
        return self.character_voice("asker") or (settings.voice_name_asker_hi if self.lang == "hi"
                                                 else settings.voice_name_asker)

    def spoken_length(self, text: str, voice: str | None = None) -> float:
        voice = voice or self.narrator(self.settings)
        if self.settings.voice and tts.available(voice):
            return len(tts.say(text, voice, self.settings.voice_speed)) / SR
        return max(1.2, len(text.split()) / WORDS_PER_S)

    def narration(self) -> list[tuple]:
        """(start, text, voice) for every spoken line: the question, then each beat."""
        times = self.open_times + [t + 0.1 for t in self.starts]
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
        few = "_few" if getattr(self.opts, "captions", "all") == "few" else ""
        return f"story_{self.sc['id']}_{self.lang}{few}"

    def sounds(self) -> SoundBank:
        from ..core.audio import overlay, sample, whoosh
        recorded = {"punch": sample("punch", 0.6), "glitch": sample("glitch", 0.4), "drop": sample("drop", 0.7),
                    "bell": sample("bell", 0.35), "buzz": sample("buzz", 0.3), "pop": sample("pop", 0.22),
                    "scratch": sample("scratch", 0.45)} if self.sc.get("edit") else {}
        return {**recorded,"clear": tone(392, 1.6, 2.5, harm=0.3) * 0.25, "fail": tone(392, 1.6, 2.5, harm=0.3) * 0.25,
                "whoosh": whoosh(0.7, 250, 2600, 0.5),                     # a change of scene
                "swish": whoosh(0.4, 600, 5000, 0.32, seed=3),            # a title card
                "chime": overlay((0, tone(1568, 0.9, 5, harm=0.15) * 0.16),   # a name card
                                 (0.07, tone(2349, 0.8, 6, harm=0.1) * 0.12))}

    def cue_sounds(self, i: int, since: float, t: float) -> None:
        """Transition sounds the first time a beat is drawn: a whoosh when the scene changes, a swish under a
        title card, a chime as a name card slides in."""
        if i in self.cued:
            return
        self.cued.add(i)
        stage = self.beats[i].get("stage", {})
        before = self.beats[i - 1].get("stage", {}) if i > 0 else {}
        if i == 0 or stage.get("backdrop") != before.get("backdrop"):
            self.sfx(t - since, "whoosh", force=True)
        if self.beats[i].get("title_card"):
            self.sfx(t - since + TITLE_IN_S, "swish", force=True)
        if self.beats[i].get("name"):
            self.sfx(t - since + NAME_IN_S, "chime", force=True)
        for cut in self.beats[i].get("cut", []):                     # edit effects carry their own sounds
            if cut in CUT_SOUNDS:
                self.sfx(t - since, CUT_SOUNDS[cut], force=True)
        for item in stage.get("fx", []):                             # a thrown discus: a swish out, a boom as it lands
            if isinstance(item, dict) and "strike" in item:
                from ..story.theatre import STRIKE_AT, STRIKE_S
                go = t - since + self.beat_len(i) * STRIKE_AT
                self.sfx(go, "swish", force=True)
                self.sfx(go + STRIKE_S, "twist", force=True)

    def card(self, i: int, kind: str):
        """The beat's name card (`name: {head, sub}`) or event title (`title_card: "..."`), drawn once."""
        key = (i, kind)
        if key not in self.cards:
            from ..core.text import font_file
            pg = self.pg
            spec = self.beats[i].get("name" if kind == "name" else "title_card")
            surf = None
            if kind == "name" and spec:
                head = pg.font.Font(font_file("Poppins-ExtraBold"), 62).render(spec["head"], True, (255, 252, 244))
                sub = pg.font.Font(font_file("Poppins-SemiBold"), 38).render(spec.get("sub", ""), True, ART_HIGHLIGHT)
                w, h = max(head.get_width(), sub.get_width()) + 84, head.get_height() + sub.get_height() + 30
                surf = pg.Surface((w, h), pg.SRCALPHA)
                pg.draw.rect(surf, CARD_FILL, (0, 0, w, h), border_radius=18)
                pg.draw.rect(surf, ART_HIGHLIGHT, (0, 0, 14, h), border_top_left_radius=18, border_bottom_left_radius=18)
                surf.blit(head, (44, 10))
                surf.blit(sub, (46, 10 + head.get_height() + 4))
            elif kind == "title" and spec:
                text = pg.font.Font(font_file("Poppins-ExtraBold"), 70).render(spec, True, (255, 252, 244))
                w, h = text.get_width() + 90, text.get_height() + 36
                surf = pg.Surface((w, h), pg.SRCALPHA)
                pg.draw.rect(surf, CARD_FILL, (0, 0, w, h), border_radius=22)
                pg.draw.rect(surf, ART_HIGHLIGHT, (0, 0, w, h), 6, border_radius=22)
                surf.blit(text, text.get_rect(center=(w / 2, h / 2 + 3)))
            self.cards[key] = surf
        return self.cards[key]

    def draw_cards(self, screen, i: int, since: float) -> None:
        """The title card pops in at the top for the whole beat; the name card slides in from the left and
        out again after a few seconds."""
        length = self.beat_len(i)
        title = self.card(i, "title")
        if title is not None:
            k = max(0.0, min(1.0, (since - TITLE_IN_S) / 0.35, (length - since) / 0.3))
            if k > 0:
                e = k * k * (3 - 2 * k)
                s = title if e > 0.99 else self.pg.transform.smoothscale(
                    title, (int(title.get_width() * (0.85 + 0.15 * e)), int(title.get_height() * (0.85 + 0.15 * e))))
                s.set_alpha(int(255 * e))
                screen.blit(s, s.get_rect(center=(W / 2, TITLE_Y)))
        name = self.card(i, "name")
        if name is not None:
            out = min(length - 0.3, NAME_IN_S + NAME_HOLD_S)
            k = max(0.0, min(1.0, (since - NAME_IN_S) / 0.45, (out - since) / 0.35))
            if k > 0:
                e = k * k * (3 - 2 * k)
                name.set_alpha(int(255 * e))
                y = self.beats[i]["name"].get("y", NAME_Y)                 # a beat may raise it off a face
                screen.blit(name, (50 - (1 - e) * (name.get_width() + 60), y))

    def draw_comment(self, screen, i: int, since: float) -> None:
        """A beat's `comment:` prompt (a question for the comments) in a dark pill at the top, popping in
        and pulsing gently, so viewers have a reason to open the comments while still watching."""
        text = self.beats[i].get("comment")
        if not text:
            return
        key = ("comment", i)
        if key not in self.cards:
            from ..core.text import fit_width, font_file, gold_text
            word = gold_text(self.pg, self.pg.font.Font(font_file("Poppins-ExtraBold"), 64), text.upper())
            word = fit_width(self.pg, word, W - 140)
            pill = self.pg.Surface((word.get_width() + 60, word.get_height() + 10), self.pg.SRCALPHA)
            self.pg.draw.rect(pill, (20, 8, 4, 210), pill.get_rect(), border_radius=pill.get_height() // 2)
            self.pg.draw.rect(pill, (255, 196, 90, 255), pill.get_rect(), 4, border_radius=pill.get_height() // 2)
            pill.blit(word, word.get_rect(center=pill.get_rect().center))
            self.cards[key] = pill
        pill = self.cards[key]
        k = max(0.0, min(1.0, (since - COMMENT_IN_S) / 0.25, (self.beat_len(i) - since) / 0.25))
        if k <= 0:
            return
        pop = 1 + 0.25 * (1 - k) + 0.03 * math.sin(since * 6)
        s = self.pg.transform.smoothscale(pill, (int(pill.get_width() * pop), int(pill.get_height() * pop)))
        s.set_alpha(int(255 * k))
        screen.blit(s, s.get_rect(center=(W / 2, COMMENT_Y)))

    def end_sound(self, why: str) -> str:
        return "clear"

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        self.stage = Stage(self.pg, self.seed)
        self.canvas = self.pg.Surface((W, H))
        self.layer = self.pg.Surface((W * 2, H * 2), self.pg.SRCALPHA)
        self.caption_cache: dict[int, object] = {}
        self.cards: dict[tuple, object] = {}
        self.cued: set[int] = set()
        from ..core.text import font_path
        self.caption_font = self.pg.font.Font(font_path(), 68)
        self.actors: dict[str, Actor] = {}
        self.marks: dict[str, tuple[dict, dict]] = {}                 # name -> (from, to)
        self.mark_beat = -1
        from ..story.theatre import Theatre
        self.theatre = Theatre.load(self.pg, self.sc, self.seed)
        if self.theatre:
            from ..core.text import font_file
            self.caption_font = self.pg.font.Font(font_file("Poppins-ExtraBold"), 74)
            self.kinetic_font = self.pg.font.Font(font_file("Poppins-ExtraBold"), 84)
            self.kinetic_cache: dict[int, tuple] = {}
            # the end card in the same type: the title in the display face, the rest in Poppins
            self.fonts.big = self.pg.font.Font(self.display_font(), 100)
            self.fonts.stat = self.pg.font.Font(font_file("Poppins-SemiBold"), 40)
            self.fonts.cta = self.pg.font.Font(font_file("Poppins-SemiBold"), 42)
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
        self.cue_sounds(i, since, t)
        if self.sc.get("edit"):
            self.draw_cuts(screen, i, since, t)
        self.draw_cards(screen, i, since)
        self.draw_comment(screen, i, since)
        if self.kinetic():
            self.draw_kinetic(screen, i, since)
            return
        cap = self.caption(i)
        if cap is not None:
            end = self.starts[i] + self.beat_len(i)
            a = max(0.0, min(1.0, since / 0.35, (end - self.play_t) / 0.35))
            self.shade.set_alpha(int(255 * a))
            screen.blit(self.shade, (0, ART_CAPTION_Y - 260))
            cap.set_alpha(int(255 * a))
            screen.blit(cap, cap.get_rect(center=(W / 2, ART_CAPTION_Y)))

    def display_font(self) -> str:
        """Cinzel Decorative for myths and legends, Poppins for science, maths and facts."""
        from ..core.text import font_file
        return font_file("Poppins-ExtraBold" if self.sc.get("topic") == "science" else "CinzelDecorative-Bold")

    def gold(self) -> bool:
        """Stories with `lettering: gold` (the cartoon ones) set the question and captions in bordered gold."""
        return self.sc.get("lettering") == "gold"

    def fast(self) -> bool:
        """Stories with `pace: fast`: the hook is on the very first frame and the lines come close together."""
        return self.sc.get("pace") == "fast"

    def dip(self, screen, k: float) -> None:
        """Black over the frame, fully at k = 0 and gone by k = 1: a quick dip between cold open and story."""
        if k < 1:
            veil = self.pg.Surface((W, H))
            veil.set_alpha(int(255 * (1 - max(0.0, k))))
            screen.blit(veil, (0, 0))

    def draw_hook(self, screen) -> None:
        """The question in big type at the top, with the series and part above it."""
        side = {"bottom_left": "left", "bottom_right": "right"}.get(self.sc.get("hook_at"))   # or top centre
        if not hasattr(self, "hook_card"):
            from ..core.text import font_file, soft_text, wrap
            if self.gold():
                from ..core.text import gold_text
                big = self.pg.font.Font(font_file("Poppins-ExtraBold"), 96)
                rows = [gold_text(self.pg, big, line)
                        for line in wrap(big, self.sc["title"]["en"].upper(), W - (HOOK_SIDE_W if side else 120))[:4]]
            else:
                big = self.pg.font.Font(self.display_font(), 92 if self.sc.get("topic") != "science" else 96)
                rows = [soft_text(self.pg, big, line, (255, 248, 232), 210)
                        for line in wrap(big, self.sc["title"]["en"].upper(), W - 120)[:4]]
            self.hook_card = self.pg.Surface((W, sum(r.get_height() - 18 for r in rows) + 18), self.pg.SRCALPHA)
            y = 0
            for r in rows:
                if side == "left":
                    self.hook_card.blit(r, r.get_rect(topleft=(HOOK_MARGIN, y)))
                elif side == "right":
                    self.hook_card.blit(r, r.get_rect(topright=(W - HOOK_MARGIN, y)))
                else:
                    self.hook_card.blit(r, r.get_rect(midtop=(W / 2, y)))
                y += r.get_height() - 18
            part = self.sc.get("series_part")
            words = ("", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN")
            part = words[part] if isinstance(part, int) and part < len(words) else part   # the serif's digits are small
            label = self.sc.get("series", {}).get("en", "") + (f"  ·  PART {part}" if part else "")
            small = self.pg.font.Font(font_file("Poppins-SemiBold"), 40)
            spaced = "  ".join(label.upper().split()) if label else ""             # a little letter spacing
            from ..core.text import fit_width
            self.series_tag = fit_width(self.pg, soft_text(self.pg, small, " ".join(spaced), ART_HIGHLIGHT, 190),
                                        W - 60) if label else None
        k = 1.0 if self.fast() else min(1.0, self.play_t / 0.35)
        self.hook_card.set_alpha(int(255 * k))
        if side:                                                 # low in a corner, clear of the face
            top = HOOK_BOTTOM - self.hook_card.get_height() - 50
            if self.theatre:
                self.shade.set_alpha(int(255 * k))
                screen.blit(self.shade, (0, HOOK_BOTTOM - 380))
            if self.series_tag is not None:
                self.series_tag.set_alpha(int(255 * k))
                at = {"left": {"midleft": (HOOK_MARGIN - 6, top)}, "right": {"midright": (W - HOOK_MARGIN + 6, top)}}[side]
                screen.blit(self.series_tag, self.series_tag.get_rect(**at))
            screen.blit(self.hook_card, (0, top + 50))
            return
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
            if getattr(self.opts, "captions", "all") == "few" and not self.beats[i].get("key"):
                text = ""                                            # the picture and the cards carry this beat
            words = []
            for w in text.split():
                hot = w.startswith("*") or w.rstrip(".,!?").endswith("*")
                words.append((w.replace("*", ""), hot))
            hi = ART_HIGHLIGHT if self.theatre else HIGHLIGHT
            if self.gold():                                          # cream words, gold key words, maroon border
                from ..core.text import gold_text
                pieces = [gold_text(self.pg, self.caption_font, w, outline=6, shadow=6) if hot
                          else gold_text(self.pg, self.caption_font, w, (255, 250, 236), (255, 236, 200), 6, shadow=6)
                          for w, hot in words]
            elif self.theatre:
                from ..core.text import soft_text
                pieces = [soft_text(self.pg, self.caption_font, w, hi if hot else (255, 252, 244), 200)
                          for w, hot in words]
            else:
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

    # ---------------------------------------------------------- edit layer
    def kinetic(self) -> bool:
        edit = self.sc.get("edit")
        return isinstance(edit, dict) and edit.get("captions") == "kinetic"

    def draw_cuts(self, screen, i: int, since: float, t: float) -> None:
        """The beat's `cut` effects over the picture, then the story's grade."""
        import numpy as np
        pg, cuts = self.pg, self.beats[i].get("cut", [])
        if "speedlines" in cuts:
            self.draw_speedlines(screen, t)
        if "punch" in cuts and since < PUNCH_S:
            k = PUNCH_ZOOM * (1 - ease(since / PUNCH_S))
            big = pg.transform.smoothscale(screen, (int(W * (1 + k)), int(H * (1 + k))))
            screen.blit(big, big.get_rect(center=(W / 2, H / 2)))
        if "glitch" in cuts and since < GLITCH_S:
            k = 1 - since / GLITCH_S
            px = pg.surfarray.pixels3d(screen)                       # (W, H, 3)
            dx = int(26 * k)
            px[:, :, 0] = np.roll(px[:, :, 0], dx, axis=0)          # red one way, blue the other
            px[:, :, 2] = np.roll(px[:, :, 2], -dx, axis=0)
            rng = np.random.default_rng(int(since * 60) + i)
            for _ in range(int(7 * k) + 1):                          # torn horizontal slices
                y0 = int(rng.integers(0, H - 80))
                h = int(rng.integers(12, 80))
                px[:, y0:y0 + h] = np.roll(px[:, y0:y0 + h], int(rng.integers(-90, 90) * k), axis=0)
            del px
        if "flash" in cuts and since < FLASH_S:
            veil = pg.Surface((W, H))
            veil.fill((255, 250, 235))
            veil.set_alpha(int(230 * (1 - since / FLASH_S)))
            screen.blit(veil, (0, 0))
        if self.sc["edit"].get("grade") == "film" if isinstance(self.sc["edit"], dict) else False:
            self.draw_grade(screen, t)

    def draw_speedlines(self, screen, t: float) -> None:
        """Anime speed lines rushing in from the edges, redrawn a few times a second."""
        import math
        import numpy as np
        pg = self.pg
        if not hasattr(self, "speed_frames"):
            self.speed_frames = []
            cx, cy = W / 2, H * 0.52
            for seed in range(4):
                rng = np.random.default_rng(seed)
                layer = pg.Surface((W, H), pg.SRCALPHA)
                for _ in range(90):
                    a = rng.uniform(0, 2 * math.pi)
                    r0 = rng.uniform(0.62, 0.85) * 1100
                    wide = rng.uniform(0.004, 0.012)
                    pts = [(cx + 1500 * math.cos(a - wide), cy + 1500 * math.sin(a - wide)),
                           (cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                           (cx + 1500 * math.cos(a + wide), cy + 1500 * math.sin(a + wide))]
                    pg.draw.polygon(layer, (255, 255, 255, int(rng.uniform(60, 150))), pts)
                self.speed_frames.append(layer)
        screen.blit(self.speed_frames[int(t * 12) % len(self.speed_frames)], (0, 0))

    def draw_grade(self, screen, t: float) -> None:
        """A film look: darkened corners and a fine moving grain."""
        import numpy as np
        pg = self.pg
        if not hasattr(self, "vignette"):
            x = (np.arange(W)[:, None] - W / 2) / (W / 2)
            y = (np.arange(H)[None, :] - H / 2) / (H / 2)
            r = np.sqrt(x * x * 0.9 + y * y * 0.55)
            self.vignette = pg.Surface((W, H), pg.SRCALPHA)
            pg.surfarray.pixels_alpha(self.vignette)[:] = (np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * 170).astype(np.uint8)
            self.grain = []
            for seed in range(4):
                g = pg.Surface((W // 2, H // 2), pg.SRCALPHA)
                n = np.random.default_rng(seed).integers(0, 255, (W // 2, H // 2), dtype=np.uint8)
                pg.surfarray.pixels3d(g)[:] = n[:, :, None]
                pg.surfarray.pixels_alpha(g)[:] = 14
                self.grain.append(pg.transform.scale(g, (W, H)))
        screen.blit(self.vignette, (0, 0))
        screen.blit(self.grain[int(t * 24) % len(self.grain)], (0, 0))

    def draw_kinetic(self, screen, i: int, since: float) -> None:
        """The caption one word at a time, each popping in as it would be said; key words in gold."""
        y0 = self.beats[i].get("caption_y", ART_CAPTION_Y)              # a close-up lifts its words off the face
        if i not in self.kinetic_cache:
            from ..core.text import gold_text
            text = self.beats[i].get("caption", "")
            words, hot = [], False
            for w in text.split():                                   # *...* may span several words
                start = w.startswith("*") or w.startswith("\"*")
                hot = hot or start
                words.append((w.replace("*", ""), hot))
                if w.rstrip(".,!?\"").endswith("*"):
                    hot = False
            font = self.kinetic_font
            pieces = [gold_text(self.pg, font, w, outline=7, shadow=7) if h
                      else gold_text(self.pg, font, w, (255, 255, 255), (232, 232, 240), 7, (10, 10, 14), 7)
                      for w, h in words]
            spots, rows, row, width = [], [], [], 0
            for n, p in enumerate(pieces):
                if row and width + p.get_width() > W - 120:
                    rows.append(row)
                    row, width = [], 0
                row.append(n)
                width += p.get_width() + 16
            rows.append(row)
            h = max((p.get_height() for p in pieces), default=0)
            top = -(h * len(rows) + 6 * (len(rows) - 1)) / 2
            for r, row in enumerate(rows):
                total = sum(pieces[n].get_width() for n in row) + 16 * (len(row) - 1)
                x = (W - total) / 2
                for n in row:
                    spots.append((x + pieces[n].get_width() / 2, y0 + top + r * (h + 6) + h / 2))
                    x += pieces[n].get_width() + 16
            self.kinetic_cache[i] = (pieces, spots)
        pieces, spots = self.kinetic_cache[i]
        if not pieces:
            return
        length = self.beat_len(i)
        end = self.starts[i] + length
        fade = max(0.0, min(1.0, (end - self.play_t) / 0.2))
        self.shade.set_alpha(int(255 * min(1.0, since / 0.2) * fade))
        screen.blit(self.shade, (0, y0 - 260))
        span = max(0.5, length * 0.7)                                # words land across most of the line
        for n, (p, (x, y)) in enumerate(zip(pieces, spots)):
            age = since - n * span / len(pieces)
            if age < 0:
                break
            s = 1.0 + 0.4 * (1 - ease(min(1.0, age / WORD_POP_S)))
            q = p if s == 1.0 else self.pg.transform.smoothscale(p, (int(p.get_width() * s), int(p.get_height() * s)))
            q.set_alpha(int(255 * fade))
            screen.blit(q, q.get_rect(center=(x, y)))

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
