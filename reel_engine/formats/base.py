"""The Format base class: what every video format plug-in provides.

A format is constructed with a seed and the parsed CLI options, then the renderer calls
update() and draw() once per frame until finished() is true. The base class handles the
shared parts: seeded RNGs, the intro/outro timing, the hook title, the HUD row, effects,
the sound-event log and the end card. A format fills in the abstract methods below.
"""
import random
from abc import ABC, abstractmethod
from argparse import Namespace
from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

from ..core.audio import SoundBank
from ..core.canvas import ARENA_L, ARENA_R, ARENA_T, INTRO_S, OUTRO_S, H, W
from ..core.effects import Effects
from ..core.text import Fonts, fit_width, wrap


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


class Format(ABC):
    name: ClassVar[str]
    order: ClassVar[int] = 100                 # position in --mode random / --mix even rotation
    default_duration: ClassVar[float] = 40.0   # seconds of play before time-up (--max-play overrides)
    options: ClassVar[tuple[Option, ...]] = ()
    intro_s: ClassVar[float] = INTRO_S
    outro_s: ClassVar[float] = OUTRO_S
    wins: ClassVar[tuple[str, ...]] = ()       # end reasons that get the victory sound
    in_random_pool: ClassVar[bool] = True

    def __init__(self, pg, seed: int, opts: Namespace):
        self.pg, self.seed, self.opts = pg, seed, opts
        self.rng = random.Random(seed)
        self.nrng = np.random.default_rng(seed)
        self.max_play = getattr(opts, "max_play", None) or self.default_duration
        self.events: list[tuple[float, str, int]] = []
        self.frame_events = 0
        self.done: str | None = None
        self.end_t: float | None = None
        self.play_t = 0.0
        self.fonts = Fonts(pg)
        self.fx = Effects(pg, self.rng, self.fonts)
        self.init_state()
        self.setup()
        self.title = getattr(opts, "title", None) or self.rng.choice(self.title_hooks())
        self.build()
        self.title_surfs = [self.fonts.title.render(line, True, (255, 255, 255))
                            for line in wrap(self.fonts.title, self.title, W - 80)[:2]]

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
        """Advance the simulation by dt seconds of play."""

    @abstractmethod
    def check_end(self, t: float) -> str | None:
        """The end condition: return an outcome key such as 'win' or 'time', or None to keep going."""

    @abstractmethod
    def end_card(self) -> EndCard:
        """Headline and subline shown when the reel ends."""

    @abstractmethod
    def sounds(self) -> SoundBank:
        """The sounds this format's events refer to."""

    @abstractmethod
    def draw_world(self, screen, t: float) -> None:
        """Draw everything below the title and HUD: background, board, actors, particles."""

    def stats(self) -> list[str]:
        """Left, centre and right HUD labels."""
        return ["", "", ""]

    def progress(self) -> float:
        """Progress bar fill, 0..1."""
        return 0.0

    def hud_accent(self) -> tuple[int, int, int]:
        return (255, 255, 255)

    def outcome(self) -> dict[str, Any]:
        """Facts about how the reel ended, for titles and descriptions."""
        return {"result": self.done, "play_time": round(self.play_t, 1)}

    def end_sound(self, why: str) -> str:
        return "clear" if why in self.wins else "fail"

    # ---------------------------------------------------------- shared behaviour
    def sfx(self, t: float, kind: str, idx: int = 0, force: bool = False) -> None:
        """Log a sound event, capped at four per frame unless forced."""
        if force or self.frame_events < 4:
            self.events.append((t, kind, idx))
            self.frame_events += 1

    def update(self, dt: float, t: float) -> None:
        self.frame_events = 0
        if self.done is None and t >= self.intro_s:
            self.step(dt, t)
            self.play_t += dt
            why = self.check_end(t)
            if why:
                self.done, self.end_t = why, t
                self.sfx(t, self.end_sound(why), force=True)
        self.fx.update(dt)

    def finished(self, t: float) -> bool:
        return bool(self.done) and t >= self.end_t + self.outro_s

    def draw(self, screen, t: float) -> None:
        self.draw_world(screen, t)
        self.fx.draw_floaters(screen)
        self.draw_title(screen)
        self.draw_hud(screen)
        self.fx.draw_flash(screen)
        if self.done:
            self.draw_end_card(screen, t)

    def draw_title(self, screen) -> None:
        y = 60
        for s in self.title_surfs:
            screen.blit(s, s.get_rect(midtop=(W / 2, y)))
            y += s.get_height() + 4

    def draw_hud(self, screen) -> None:
        for i, txt in enumerate(self.stats()):
            s = self.fonts.stat.render(txt, True, (235, 235, 245))
            x = [ARENA_L + 10, W / 2, ARENA_R - 10][i]
            anchor = ["midleft", "center", "midright"][i]
            screen.blit(s, s.get_rect(**{anchor: (x, 252)}))
        frac = self.progress()
        self.pg.draw.rect(screen, (70, 70, 85), (ARENA_L, 290, ARENA_R - ARENA_L, 16), border_radius=8)
        if frac > 0:
            self.pg.draw.rect(screen, self.hud_accent(), (ARENA_L, 290, int((ARENA_R - ARENA_L) * frac), 16),
                              border_radius=8)

    def draw_end_card(self, screen, t: float) -> None:
        pg = self.pg
        k = min(1.0, (t - self.end_t) / 0.4)
        veil = pg.Surface((W, H - ARENA_T), pg.SRCALPHA)
        veil.fill((0, 0, 0, int(150 * k)))
        screen.blit(veil, (0, ARENA_T))
        card = self.end_card()
        hs = fit_width(pg, self.fonts.big.render(card.head, True, (255, 255, 255)), W - 60)
        ss = self.fonts.stat.render(card.sub, True, (230, 230, 240))
        hs.set_alpha(int(255 * k))
        ss.set_alpha(int(255 * k))
        screen.blit(hs, hs.get_rect(center=(W / 2, H * 0.5)))
        screen.blit(ss, ss.get_rect(center=(W / 2, H * 0.5 + 100)))
