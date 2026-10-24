"""The drama engine: simulate reels without drawing, score them, and pick the best seed.

Rendering a reel is the slow part, simulating one is fast. So before rendering, the engine
can try several candidate seeds, score each run with the format's drama_score(), and render
only the winner. The same pre-pass also finds the decisive moment, which lets the render
start slow motion just before it happens.
"""
from argparse import Namespace
from dataclasses import dataclass, field
from typing import Any

from .canvas import FPS, TICK_HZ, TICKS_PER_FRAME

SLOWMO_BEFORE = 0.45   # seconds of play shown in slow motion before the decisive moment...
SLOWMO_AFTER = 0.15    # ...and after it
SHORT_PENALTY = 5.0    # score lost by a run that would end before the minimum length


@dataclass
class Plan:
    """Render-time knowledge from the pre-pass. slowmo is a tick range played at 1/4 speed."""
    slowmo: tuple[int, int] | None = None


@dataclass
class Trace:
    mode: str
    seed: int
    done: str | None
    play_t: float
    max_play: float
    decisive_tick: int | None = None
    decisive_t: float | None = None
    twist: str | None = None
    samples: list[Any] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    natural_s: float = 0.0     # video length before any padding up to the minimum

    def plan(self) -> Plan:
        if self.decisive_tick is None:
            return Plan()
        return Plan(slowmo=(max(0, self.decisive_tick - int(SLOWMO_BEFORE * TICK_HZ)),
                            self.decisive_tick + int(SLOWMO_AFTER * TICK_HZ)))


def simulate(pg, mode: str, seed: int, opts: Namespace) -> Trace:
    """Play a reel to its end without drawing, and summarise it."""
    from .render import create
    game = create(pg, mode, seed, opts)
    game.fx.enabled = False
    frame = 0
    while game.done is None:
        game.update(1 / FPS, frame / FPS)
        frame += 1
    dec = next(((tk, pt) for tk, pt, k in game.moments if k == "decisive"), (None, None))
    trace = Trace(mode, seed, game.done, game.play_t, game.max_play, dec[0], dec[1], game.twist_fired,
                  game.samples, game.outcome())
    trace.natural_s = natural_length(game, trace)
    trace.score = game.drama_score(trace)
    if trace.natural_s < game.min_length:
        trace.score -= SHORT_PENALTY
    return trace


def natural_length(game, trace: Trace) -> float:
    """Video length this run will have, counting the frames slow motion adds."""
    extra = 0.0
    window = trace.plan().slowmo
    if window:
        end_tick = round(trace.play_t * TICK_HZ)
        slow_ticks = max(0, min(window[1], end_tick) - window[0])
        extra = slow_ticks * (1 - 1 / TICKS_PER_FRAME) / FPS
    return game.end_t + game.outro_s + extra


def candidate_seeds(seed: int, count: int) -> list[int]:
    """Seeds tried for one reel. With count 1 that is just the seed itself."""
    return [seed] if count <= 1 else [seed * 1000 + k for k in range(count)]


def scout(pg, mode: str, seed: int, count: int, opts: Namespace) -> tuple[Trace, list[Trace]]:
    """Simulate every candidate seed and return the best trace (ties go to the lower seed)."""
    traces = [simulate(pg, mode, s, opts) for s in candidate_seeds(seed, count)]
    best = max(traces, key=lambda tr: (tr.score, -tr.seed))
    return best, traces
