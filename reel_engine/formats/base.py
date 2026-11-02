"""The Format base class: what every video format plug-in provides.

A format is constructed with a seed and the parsed CLI options, then the renderer calls
update() and draw() once per video frame until finished() is true. The base class handles
the shared layer:

- seeded RNG streams: `rng`/`nrng` for gameplay, `fx.rng` for visuals, a separate one for twists
- fixed-tick simulation, with slow motion around the decisive moment (planned by a pre-pass)
- the opening hook card, title, HUD row, effects, twist banner, end card and loop crossfade
- the sound-event log and a default drama score used by seed scouting

A format fills in the abstract methods. Rule: gameplay must never depend on draw() or on
`fx.rng`, so a reel simulated without drawing ends exactly as the rendered one does.
"""
import math
import random
from abc import ABC, abstractmethod
from argparse import Namespace
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar

import numpy as np

from ..core.audio import SoundBank, common_sounds
from ..core.canvas import (ARENA_L, ARENA_R, ARENA_T, FPS, HUD_BAR_Y, HUD_Y, INTRO_S, LOOP_S, MIN_VIDEO_S,
                           OUTRO_S, TICK, TICK_HZ, TICKS_PER_FRAME, TITLE_Y, H, W)
from ..core.drama import Plan, Trace
from ..core.effects import Effects
from ..core.text import Fonts, fit_width, outlined, text_block, wrap

TWIST_CHANCE = 0.6          # with --twist auto, the share of reels that get a twist
TWIST_WINDOW = (0.45, 0.7)  # when it fires, as a fraction of max play time
TWIST_BANNER_S = 1.8
END_POP_S = 0.45


@dataclass
class Option:
    """A CLI flag owned by a format. Formats may share a flag if the argparse settings match."""
    flag: str
    help: str
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass
class EndCard:
    head: str
    sub: str = ""


@dataclass
class Twist:
    """A mid-reel surprise. apply(t) changes the game and may return a subline for the banner."""
    name: str
    sub: str
    apply: Callable[[float], str | None]
    ready: Callable[[], bool] = lambda: True
    banner: str = "WAIT..."


def ease_out_back(k: float) -> float:
    c = 1.70158
    return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2


class Format(ABC):
    name: ClassVar[str]
    order: ClassVar[int] = 100                 # position in --mode random / --mix even rotation
    default_duration: ClassVar[float] = 40.0   # seconds of play before time-up (--max-play overrides)
    options: ClassVar[tuple[Option, ...]] = ()
    intro_s: ClassVar[float] = INTRO_S
    outro_s: ClassVar[float] = OUTRO_S
    wins: ClassVar[tuple[str, ...]] = ()       # end reasons that count as success
    in_random_pool: ClassVar[bool] = True
    heavy: ClassVar[bool] = False              # takes minutes per reel (e.g. Blender); skipped by quick tests
    max_scout: ClassVar[int] = 100             # cap on seeds scouting may try (pre-passes can be costly)
    seed_note: ClassVar[bool] = True           # say in the description that the reel was simulated from a seed
    loop_ending: ClassVar[bool] = True         # crossfade the last frames into the first
    cta: ClassVar[str] = "Follow for more"
    music: ClassVar[str] = "upbeat"            # background music style (see core/music.py)
    series: ClassVar[str] = ""                 # series name for titles, e.g. "Brick Escape"
    tags: ClassVar[tuple[str, ...]] = ()       # search tags for this format
    hashtags: ClassVar[tuple[str, ...]] = ()   # hashtags for the description (without #shorts)
    music_key: ClassVar[int] = 60              # MIDI root; C keeps it in tune with pentatonic effects
    end_veil: ClassVar[bool] = True            # darken the arena behind the end card...
    card_y: ClassVar[float] = H * 0.5          # ...or (False) put the card on a band at card_y

    def __init__(self, pg, seed: int, opts: Namespace):
        self.pg, self.seed, self.opts = pg, seed, opts
        self.rng = random.Random(seed)
        self.nrng = np.random.default_rng(seed)
        self.twist_rng = random.Random(f"twist:{seed}")
        self.max_play = getattr(opts, "max_play", None) or self.default_duration
        min_length = getattr(opts, "min_length", None)
        self.min_length = MIN_VIDEO_S if min_length is None else min_length
        self.events: list[tuple[float, str, int]] = []
        self.frame_events = 0
        self.frame_no = 0
        self.tick = 0
        self.done: str | None = None
        self.end_t: float | None = None
        self.play_t = 0.0
        self.time_scale = 1.0
        self.plan = Plan()
        self.moments: list[tuple[int, float, str]] = []   # (tick, play time, kind)
        self.samples: list[Any] = []                      # sample() once per second of play
        self.fonts = Fonts(pg)
        self.fx = Effects(pg, random.Random(f"fx:{seed}"), self.fonts)
        self.first_frame = None
        self.twist: Twist | None = None
        self.twist_at: float | None = None
        self.twist_fired: str | None = None
        self.twist_t: float | None = None
        self.twist_surf = None
        self._in_slowmo = False
        self.init_state()
        self.setup()
        self.title = getattr(opts, "title", None) or self.rng.choice(self._fitting_hooks())
        self.build()
        self._plan_twist()
        self.title_surfs = [self.fonts.title.render(line, True, (255, 255, 255))
                            for line in wrap(self.fonts.title, self.title, W - 80)[:2]]
        self.hook_surf = text_block(pg, self.fonts.hook, self.title, (255, 255, 255), W - 120, outline=6)
        self.veil = pg.Surface((W, H), pg.SRCALPHA)
        self.veil.fill((0, 0, 0, 255))
        self._end_cache: tuple[EndCard, Any, Any, Any] | None = None

    # ---------------------------------------------------------- for formats to implement
    def init_state(self) -> None:
        """Set up state needed before setup(); runs first, so RNG draws here come first."""

    @abstractmethod
    def setup(self) -> None:
        """Build the seeded layout: board, actors, palette."""

    @abstractmethod
    def title_hooks(self) -> list[str]:
        """Candidate hook lines; one is picked with the seeded RNG unless --title is given."""

    def build(self) -> None:
        """Prepare graphics once the layout and title are known."""

    @abstractmethod
    def step(self, dt: float, t: float) -> None:
        """Advance the simulation by one tick of dt seconds. t is the video time, for sounds."""

    @abstractmethod
    def check_end(self, t: float) -> str | None:
        """The end condition, checked every tick: an outcome key such as 'win', or None."""

    @abstractmethod
    def end_card(self) -> EndCard:
        """Headline and subline shown when the reel ends."""

    @abstractmethod
    def sounds(self) -> SoundBank:
        """The sounds this format's events refer to."""

    @abstractmethod
    def draw_world(self, screen, t: float) -> None:
        """Draw everything below the title and HUD: background, board, actors, particles."""

    def twists(self) -> list[Twist]:
        """Surprises this format can throw in mid-reel."""
        return []

    def stats(self) -> list[str]:
        """Left, centre and right HUD labels."""
        return ["", "", ""]

    def progress(self) -> float:
        """Progress bar fill, 0..1."""
        return 0.0

    def sample(self) -> Any:
        """A snapshot of the state, recorded once per second of play for drama scoring."""
        return self.progress()

    def hud_accent(self) -> tuple[int, int, int]:
        return (255, 255, 255)

    def outcome(self) -> dict[str, Any]:
        """Facts about how the reel ended, for titles and descriptions."""
        return {"result": self.done, "play_time": round(self.play_t, 1), "twist": self.twist_fired}

    @classmethod
    def titles(cls, o: dict[str, Any]) -> list[str]:
        """Title ideas from a finished reel's outcome(); the metadata picks one that is unused."""
        return ["How did this end?", "Watch till the end"]

    @classmethod
    def describe(cls, o: dict[str, Any]) -> str:
        """One sentence saying what happened, for the description."""
        return ""

    def slug(self) -> str:
        """File-name tag for this reel (formats with sub-variants, like physics scenes, extend it)."""
        return self.name

    def end_sound(self, why: str) -> str:
        return "clear" if why in self.wins else "fail"

    def drama_score(self, trace: Trace) -> float:
        """How watchable this run is; seed scouting renders the highest-scoring seed.

        Rewards a decisive moment late in the reel, wins, near misses and twists, and
        penalises long stretches where nothing changes.
        """
        s = 0.0
        if trace.decisive_t is not None:
            f = trace.decisive_t / self.max_play
            s += 3 - 4 * abs(f - 0.75)
        won = trace.done in self.wins
        s += 1.5 if won else 0.0
        prog = [p for p in trace.samples if isinstance(p, (int, float))]
        if not won and prog and prog[-1] >= 0.9:
            s += 2.0                                  # so close
        s -= 0.15 * max(0, longest_flat(prog) - 4)
        if trace.twist:
            s += 0.5
        if trace.play_t < 12:
            s -= 1.0
        return s

    # ---------------------------------------------------------- shared behaviour
    def _fitting_hooks(self) -> list[str]:
        """Hook lines that fit the two-line title area (all of them if none do)."""
        hooks = self.title_hooks()
        fit = [h for h in hooks if len(wrap(self.fonts.title, h, W - 80)) <= 2]
        return fit or hooks

    def sound_bank(self) -> SoundBank:
        return {**common_sounds(), **self.sounds()}

    def sfx(self, t: float, kind: str, idx: int = 0, force: bool = False) -> None:
        """Log a sound event, capped at four per frame unless forced."""
        if force or self.frame_events < 4:
            self.events.append((t, kind, idx))
            self.frame_events += 1

    def mark(self, kind: str) -> None:
        """Record a moment (e.g. 'decisive') at the current tick, for slow motion and scoring."""
        if kind == "decisive" and any(k == "decisive" for _, _, k in self.moments):
            return
        self.moments.append((self.tick, self.play_t, kind))

    def _plan_twist(self) -> None:
        mode = getattr(self.opts, "twist", None) or "auto"
        options = self.twists()
        if mode == "none" or not options:
            return
        if mode == "auto":
            if self.twist_rng.random() >= TWIST_CHANCE:
                return
            self.twist = self.twist_rng.choice(options)
        else:
            self.twist = next((tw for tw in options if tw.name == mode), None)
            if self.twist is None:
                return
        self.twist_at = self.twist_rng.uniform(*TWIST_WINDOW) * self.max_play

    def _maybe_twist(self, t: float) -> None:
        if self.twist is None or self.twist_fired or self.play_t < self.twist_at:
            return
        if self.play_t > 0.9 * self.max_play:
            self.twist = None
            return
        if not self.twist.ready():
            return
        sub = self.twist.apply(t) or self.twist.sub
        self.twist_fired, self.twist_t = self.twist.name, t
        self.mark("twist")
        self.sfx(t, "twist", force=True)
        self.fx.shake(14, 0.5)
        self.fx.flash = max(self.fx.flash, 0.5)
        if self.fx.enabled:
            self.twist_surf = self._banner(self.twist.banner, sub)

    def _banner(self, head: str, sub: str):
        pg = self.pg
        band = pg.Surface((W, 300), pg.SRCALPHA)
        band.fill((0, 0, 0, 185))
        hs = outlined(pg, self.fonts.banner, head, (255, 214, 64), 7)
        ss = text_block(pg, self.fonts.cta, sub, (255, 255, 255), W - 80, max_lines=2, outline=4)
        band.blit(hs, hs.get_rect(center=(W / 2, 112)))
        band.blit(ss, ss.get_rect(center=(W / 2, 228)))
        return band

    def _ticks_this_frame(self) -> int:
        if self.plan.slowmo:
            a, b = self.plan.slowmo
            if a <= self.tick < b:
                return 1
        return TICKS_PER_FRAME

    def update(self, dt: float, t: float) -> None:
        self.frame_events = 0
        if self.frame_no == 0:
            self.sfx(t, "hook", force=True)
        self.frame_no += 1
        self.time_scale = 1.0
        if self.done is None and t >= self.intro_s:
            n = self._ticks_this_frame()
            self.time_scale = n / TICKS_PER_FRAME
            if n < TICKS_PER_FRAME and not self._in_slowmo:
                self.sfx(t, "slowmo", force=True)
            self._in_slowmo = n < TICKS_PER_FRAME
            for _ in range(n):
                self.step(TICK, t)
                self.tick += 1
                self.play_t = self.tick / TICK_HZ
                if self.tick % TICK_HZ == 0:
                    self.samples.append(self.sample())
                self._maybe_twist(t)
                why = self.check_end(t)
                if why:
                    self.done, self.end_t = why, t
                    self.sfx(t, self.end_sound(why), force=True)
                    if why in self.wins:
                        self.fx.shake(10, 0.4)
                    break
        self.fx.update(dt * self.time_scale)

    def end_time(self) -> float:
        """Video time of the last frame: after the outro, and never before min_length."""
        return max(self.end_t + self.outro_s, self.min_length - 1 / FPS)

    def finished(self, t: float) -> bool:
        return bool(self.done) and t >= self.end_time()

    # ---------------------------------------------------------- drawing
    def draw(self, screen, t: float) -> None:
        self.draw_world(screen, t)
        dx, dy = self.fx.shake_offset()
        if dx or dy:
            screen.scroll(dx, dy)
        self.fx.draw_floaters(screen)
        if self.time_scale < 1:
            self.fx.draw_vignette(screen, 1 - self.time_scale)
        self.draw_hud(screen)
        self.draw_title(screen, t)
        if t < self.intro_s:
            self.draw_intro(screen, t)
        self.fx.draw_flash(screen)
        self.draw_twist(screen, t)
        if self.done:
            self.draw_end_card(screen, t)
        self.draw_loop(screen, t)
        if self.first_frame is None:
            self.first_frame = screen.copy()

    def draw_intro(self, screen, t: float) -> None:
        """Big hook line over a dimmed board, zooming in gently, then fading into the title."""
        fade = min(1.0, (self.intro_s - t) / 0.3)
        self.veil.set_alpha(int(150 * fade))
        screen.blit(self.veil, (0, 0))
        k = min(1.0, t / (self.intro_s * 0.8))
        scale = 0.86 + 0.14 * (1 - (1 - k) ** 3)
        w, h = self.hook_surf.get_size()
        hook = self.pg.transform.smoothscale(self.hook_surf, (int(w * scale), int(h * scale)))
        hook.set_alpha(int(255 * fade))
        screen.blit(hook, hook.get_rect(center=(W / 2, H * 0.44)))

    def draw_title(self, screen, t: float) -> None:
        k = max(0.0, min(1.0, (t - (self.intro_s - 0.3)) / 0.3))
        if k <= 0:
            return
        y = TITLE_Y
        for s in self.title_surfs:
            s.set_alpha(int(255 * k))
            screen.blit(s, s.get_rect(midtop=(W / 2, y)))
            y += s.get_height() + 4

    def draw_hud(self, screen) -> None:
        for i, txt in enumerate(self.stats()):
            s = fit_width(self.pg, self.fonts.stat.render(txt, True, (235, 235, 245)), (ARENA_R - ARENA_L) // 3 - 12)
            x = [ARENA_L + 10, W / 2, ARENA_R - 10][i]
            anchor = ["midleft", "center", "midright"][i]
            screen.blit(s, s.get_rect(**{anchor: (x, HUD_Y)}))
        frac = self.progress()
        self.pg.draw.rect(screen, (70, 70, 85), (ARENA_L, HUD_BAR_Y, ARENA_R - ARENA_L, 16), border_radius=8)
        if frac > 0:
            self.pg.draw.rect(screen, self.hud_accent(), (ARENA_L, HUD_BAR_Y, int((ARENA_R - ARENA_L) * frac), 16),
                              border_radius=8)

    def draw_twist(self, screen, t: float) -> None:
        if self.twist_surf is None or self.twist_t is None:
            return
        u = t - self.twist_t
        if u < 0 or u >= TWIST_BANNER_S:
            return
        k = min(1.0, u / 0.2)
        x = int(W * (1 - (1 - (1 - k) ** 3)))                    # slide in from the right
        self.twist_surf.set_alpha(int(255 * min(1.0, (TWIST_BANNER_S - u) / 0.3)))
        screen.blit(self.twist_surf, (x, int(H * 0.40)))

    def draw_end_card(self, screen, t: float) -> None:
        pg = self.pg
        u = t - self.end_t
        k = min(1.0, u / 0.4)
        cy = self.card_y
        if self.end_veil:
            self.veil.set_alpha(int(150 * k))
            screen.blit(self.veil, (0, ARENA_T), (0, 0, W, H - ARENA_T))
        else:
            self.veil.set_alpha(int(190 * k))
            screen.blit(self.veil, (0, cy - 120), (0, 0, W, 360))
        card = self.end_card()
        if self._end_cache is None or self._end_cache[0] != card:
            head = outlined(pg, self.fonts.big, card.head, (255, 255, 255), 6)
            if head.get_width() > W - 60:
                head = pg.transform.smoothscale(head, (W - 60, int(head.get_height() * (W - 60) / head.get_width())))
            sub = outlined(pg, self.fonts.stat, card.sub, (235, 235, 245), 3)
            cta = outlined(pg, self.fonts.cta, self.cta, (255, 214, 64), 4)
            self._end_cache = (card, head, sub, cta)
        _, head, sub, cta = self._end_cache
        pop = ease_out_back(min(1.0, u / END_POP_S))
        if pop > 0.01:
            w, h = head.get_size()
            hs = pg.transform.smoothscale(head, (max(1, int(w * pop)), max(1, int(h * pop))))
            screen.blit(hs, hs.get_rect(center=(W / 2, cy)))
        sub.set_alpha(int(255 * k))
        screen.blit(sub, sub.get_rect(center=(W / 2, cy + 100)))
        kc = max(0.0, min(1.0, (u - 0.6) / 0.3))
        if kc > 0:
            cta.set_alpha(int(255 * kc))
            screen.blit(cta, cta.get_rect(center=(W / 2, cy + 190)))

    def draw_loop(self, screen, t: float) -> None:
        """Crossfade into the first frame so the reel loops seamlessly."""
        if not (self.loop_ending and self.done and self.first_frame is not None):
            return
        start = self.end_time() - LOOP_S
        if t <= start:
            return
        k = (t - start) / (LOOP_S + 1 / FPS)
        self.first_frame.set_alpha(int(255 * min(1.0, k)))
        screen.blit(self.first_frame, (0, 0))
        self.first_frame.set_alpha(None)


def longest_flat(prog: list[float], eps: float = 0.01) -> int:
    """Longest run of consecutive seconds in which progress rose by less than eps."""
    best = run = 0
    for a, b in zip(prog, prog[1:]):
        run = run + 1 if b - a < eps else 0
        best = max(best, run)
    return best
