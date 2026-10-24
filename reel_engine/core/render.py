"""The render loop: frames into ffmpeg, sound events into a WAV, then both muxed into one MP4.

A batch is planned up front as a list of jobs (format + seed + output path), so it renders
the same reels whether it runs sequentially or across worker processes.
"""
import os
import random
from argparse import Namespace
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, Iterator

from ..config import RenderSettings
from .audio import mix, write_wav
from .canvas import FPS, H, W
from .video import FrameWriter, mux


@dataclass
class Job:
    mode: str
    seed: int
    out: str
    opts: Namespace


def init_pygame(preview: bool = False):
    """Import and initialise pygame, headless unless previewing."""
    if not preview:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame as pg
    pg.init()
    return pg


def create(pg, mode: str, seed: int, opts: Namespace):
    from .. import formats
    return formats.get(mode)(pg, seed, opts)


def frames(game, screen) -> Iterator[tuple[int, float]]:
    """Update and draw the game into `screen` once per frame until it has finished."""
    frame = 0
    while True:
        t = frame / FPS
        game.update(1 / FPS, t)
        game.draw(screen, t)
        yield frame, t
        frame += 1
        if game.finished(t):
            break


def plan_jobs(opts: Namespace, settings: RenderSettings) -> list[Job]:
    """Seeds and formats for a batch. --mix even rotates through the formats in a seeded order."""
    from .. import formats
    pool = formats.random_pool()
    seed = opts.seed if opts.seed is not None else random.randrange(1_000_000)
    order = list(pool)
    random.Random(seed).shuffle(order)      # rotation starts with a different format each batch
    jobs = []
    for i in range(opts.batch):
        s = seed + i
        if opts.mode != "random":
            mode = opts.mode
        elif opts.mix == "even":
            mode = order[i % len(order)]
        else:
            mode = random.Random(s * 7919).choice(pool)
        if opts.out and opts.batch == 1:
            out = opts.out
        else:
            out = os.path.join(settings.output_dir, f"reel_{mode}_{s}.mp4")
        jobs.append(Job(mode, s, out, opts))
    return jobs


def render(job: Job, settings: RenderSettings) -> dict[str, Any]:
    """Render one reel to job.out and return a summary of it."""
    pg = init_pygame()
    game = create(pg, job.mode, job.seed, job.opts)
    screen = pg.Surface((W, H))
    print(f"[{job.mode} {job.seed}] title='{game.title}'", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(job.out)), exist_ok=True)
    tmp_video, wav = job.out + ".video.mp4", job.out + ".wav"
    writer = FrameWriter(tmp_video, (W, H), FPS, settings.crf, settings.preset)
    n = 0
    try:
        for n, _ in enumerate(frames(game, screen), 1):
            writer.write(pg.image.tobytes(screen, "RGB"))
    finally:
        writer.close()
    duration = n / FPS
    write_wav(mix(game.events, game.sounds(), duration), wav)
    mux(tmp_video, wav, job.out, settings.audio_bitrate)
    os.remove(tmp_video)
    os.remove(wav)
    card = game.end_card()
    print(f"[{job.mode} {job.seed}] {card.head} {card.sub} -> {job.out} ({duration:.1f}s)", flush=True)
    return {"mode": job.mode, "seed": job.seed, "out": job.out, "title": game.title,
            "duration": duration, "outcome": game.outcome()}


def _render_star(args: tuple[Job, RenderSettings]) -> dict[str, Any]:
    return render(*args)


def run_jobs(jobs: list[Job], settings: RenderSettings, workers: int = 1) -> list[dict[str, Any]]:
    """Render every job, in parallel processes when workers > 1. Results keep the job order."""
    if workers <= 1 or len(jobs) <= 1:
        return [render(j, settings) for j in jobs]
    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
        return list(ex.map(_render_star, [(j, settings) for j in jobs]))


def preview(mode: str, seed: int, opts: Namespace) -> None:
    """Play a reel live in a window at 45% size, without writing a file."""
    pg = init_pygame(preview=True)
    game = create(pg, mode, seed, opts)
    screen = pg.Surface((W, H))
    print(f"[{mode} {seed}] title='{game.title}'")
    window = pg.display.set_mode((int(W * 0.45), int(H * 0.45)))
    pg.display.set_caption(f"reel preview: {mode}")
    clock = pg.time.Clock()
    for _ in frames(game, screen):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
        window.blit(pg.transform.smoothscale(screen, window.get_size()), (0, 0))
        pg.display.flip()
        clock.tick(FPS)
