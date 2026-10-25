"""The render loop: frames into ffmpeg, sound events into a WAV, then both muxed into one MP4.

Each reel starts with a fast pre-pass (see drama.py). With scouting it tries several seeds and
keeps the most dramatic; either way the pre-pass tells the render where the decisive moment
is, for slow motion. A batch is planned up front as a list of jobs, so it renders the same
reels whether it runs sequentially or across worker processes.
"""
import os
import random
from datetime import date
from argparse import Namespace
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, Iterator

from ..config import RenderSettings
from .audio import mix, write_wav
from .canvas import FPS, H, W
from .drama import scout
from .music import compose
from .video import FrameWriter, mux


@dataclass
class Job:
    mode: str
    seed: int
    out: str | None      # None: name it after the seed that scouting picks
    opts: Namespace
    scout: int = 1


def reel_path(output_dir: str, slug: str, seed: int, day: str | None = None) -> str:
    """Each reel gets its own folder, grouped by day: out/2026-10-25/food_wars_700004/food_wars_700004.mp4"""
    name = f"{slug}_{seed}"
    return os.path.join(output_dir, day or date.today().isoformat(), name, f"{name}.mp4")


def sidecars(video: str) -> dict[str, str]:
    """Where a reel's companion files go: plain names inside its own folder, else next to the video."""
    folder, base = os.path.split(video)
    stem = os.path.splitext(base)[0]
    if os.path.basename(folder) == stem:
        return {k: os.path.join(folder, v) for k, v in
                (("upload", "upload.txt"), ("meta", "meta.json"), ("preview", "preview.png"))}
    root = os.path.join(folder, stem)
    return {"upload": root + ".txt", "meta": root + ".json", "preview": root + ".preview.png"}


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
    count = opts.scout if getattr(opts, "scout", None) is not None else settings.scout
    if getattr(opts, "min_length", None) is None:
        opts.min_length = settings.min_length
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
        out = opts.out if (opts.out and opts.batch == 1) else None
        jobs.append(Job(mode, s, out, opts, count))
    return jobs


def prepare(pg, job: Job):
    """Run the pre-pass (scouting if asked) and return a game ready to render, plus its trace."""
    from .. import formats
    best, traces = scout(pg, job.mode, job.seed, min(job.scout, formats.get(job.mode).max_scout), job.opts)
    if len(traces) > 1:
        print(f"[{job.mode} {job.seed}] scouted {len(traces)} seeds, picked {best.seed} "
              f"(score {best.score:.1f}, {best.done} at {best.play_t:.1f}s)", flush=True)
    game = create(pg, job.mode, best.seed, job.opts)
    game.plan = best.plan()
    return game, best


def render(job: Job, settings: RenderSettings) -> dict[str, Any]:
    """Render one reel and return a summary of it."""
    pg = init_pygame()
    game, trace = prepare(pg, job)
    out = job.out or reel_path(settings.output_dir, game.slug(), game.seed)
    screen = pg.Surface((W, H))
    print(f"[{job.mode} {game.seed}] title='{game.title}'", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp_video, wav = out + ".video.mp4", out + ".wav"
    writer = FrameWriter(tmp_video, (W, H), FPS, settings.crf, settings.preset)
    n = 0
    try:
        for n, _ in enumerate(frames(game, screen), 1):
            writer.write(pg.image.tobytes(screen, "RGB"))
    finally:
        writer.close()
    if (game.done, game.play_t) != (trace.done, trace.play_t):
        print(f"[{job.mode} {game.seed}] WARNING: render diverged from the pre-pass "
              f"({game.done} vs {trace.done}); the format's gameplay depends on drawing", flush=True)
    duration = n / FPS
    bed = None
    if settings.music and not getattr(job.opts, "no_music", False):
        bed = compose(duration, game.seed, game.music, game.music_key)
    write_wav(mix(game.events, game.sound_bank(), duration, bed, settings.music_level,
                  spoken_lines(game, settings, job.opts), settings.voice_level), wav)
    mux(tmp_video, wav, out, settings.audio_bitrate)
    os.remove(tmp_video)
    os.remove(wav)
    card = game.end_card()
    print(f"[{job.mode} {game.seed}] {card.head} {card.sub} -> {out} ({duration:.1f}s)", flush=True)
    return {"mode": job.mode, "seed": game.seed, "out": out, "title": game.title,
            "duration": duration, "score": round(trace.score, 2), "outcome": game.outcome()}


def spoken_lines(game, settings: RenderSettings, opts: Namespace) -> list:
    """The hook at the start and the result after the game ends, if a voice is available."""
    if not settings.voice or getattr(opts, "no_voice", False):
        return []
    from . import voice
    if not voice.available():
        print("note: voice files not found in models/; rendering without a voice", flush=True)
        return []
    lines = [(0.15, game.title)]
    if game.end_t is not None:
        lines.append((game.end_t + 0.35, game.end_card().head))
    return [(t, voice.say(text, settings.voice_name, settings.voice_speed)) for t, text in lines]


def _render_star(args: tuple[Job, RenderSettings]) -> dict[str, Any]:
    return render(*args)


def run_jobs(jobs: list[Job], settings: RenderSettings, workers: int = 1) -> list[dict[str, Any]]:
    """Render every job, in parallel processes when workers > 1. Results keep the job order."""
    if workers <= 1 or len(jobs) <= 1:
        return [render(j, settings) for j in jobs]
    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
        return list(ex.map(_render_star, [(j, settings) for j in jobs]))


def preview(job: Job) -> None:
    """Play a reel live in a window at 45% size, without writing a file."""
    pg = init_pygame(preview=True)
    game, _ = prepare(pg, job)
    screen = pg.Surface((W, H))
    print(f"[{job.mode} {game.seed}] title='{game.title}'")
    window = pg.display.set_mode((int(W * 0.45), int(H * 0.45)))
    pg.display.set_caption(f"reel preview: {job.mode}")
    clock = pg.time.Clock()
    for _ in frames(game, screen):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
        window.blit(pg.transform.smoothscale(screen, window.get_size()), (0, 0))
        pg.display.flip()
        clock.tick(FPS)
