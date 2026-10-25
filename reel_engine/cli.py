"""Command line: `reel render ...` and `reel contact-sheet ...`.

Old-style calls without a subcommand (`reel --mode escape`, or `python brickreel.py --mode
escape`) are treated as `render`, so the original brickreel.py flags keep working.
"""
import argparse
import os
import sys

from . import formats
from .config import load_settings

COMMANDS = ("render", "contact-sheet")


def _add_format_options(parser: argparse.ArgumentParser) -> None:
    """Add every registered format's flags. A flag shared by several formats is added once."""
    group = parser.add_argument_group("format options")
    seen: dict[str, formats.Option] = {}
    for fmt in formats.all_formats():
        for opt in fmt.options:
            prev = seen.get(opt.flag)
            if prev is None:
                seen[opt.flag] = opt
            elif prev.kwargs != opt.kwargs:
                raise SystemExit(f"format option {opt.flag} is declared differently by two formats")
    for opt in seen.values():
        group.add_argument(opt.flag, help=opt.help, **opt.kwargs)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="reel", description="Render auto-playing reels as 9:16 MP4s.")
    sub = ap.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="render reels (the default command)")
    r.add_argument("--mode", choices=["random"] + formats.names(), default="random")
    r.add_argument("--seed", type=int, default=None)
    r.add_argument("--title", default=None, help="override the hook line at the top")
    r.add_argument("--max-play", type=float, default=None, help="seconds of gameplay before time up")
    r.add_argument("--out", default=None, help="output file (single reel only)")
    r.add_argument("--batch", type=int, default=1, help="render this many reels with consecutive seeds")
    r.add_argument("--mix", choices=["random", "even"], default="random",
                   help="with --mode random: 'even' rotates through every format in turn")
    r.add_argument("--workers", type=int, default=None, help="reels to render in parallel")
    r.add_argument("--scout", type=int, default=None,
                   help="simulate this many seeds per reel and render the most dramatic (1 = exact seed)")
    r.add_argument("--min-length", type=float, default=None,
                   help="shortest reel in seconds (default from config: 20); 0 = no minimum")
    r.add_argument("--no-music", action="store_true", help="leave out the background music")
    r.add_argument("--twist", default="auto",
                   help="mid-reel surprise: auto (seeded chance), none, or a twist name for the format")
    r.add_argument("--preview", action="store_true", help="show a live window instead of rendering")
    r.add_argument("--config", default=None, help="YAML settings file (default configs/default.yaml)")
    _add_format_options(r)

    c = sub.add_parser("contact-sheet", help="grab frames from videos into one image")
    c.add_argument("videos", nargs="+")
    c.add_argument("-n", "--frames", type=int, default=10, help="frames per video")
    c.add_argument("--cols", type=int, default=5, help="columns (single video only)")
    c.add_argument("--width", type=int, default=216, help="width of each frame in pixels")
    c.add_argument("-o", "--out", default=None, help="output PNG (default: <first video>_sheet.png)")
    c.add_argument("--safe-zones", action="store_true",
                   help="tint the areas Shorts/Reels cover with their own buttons and captions")
    return ap


def cmd_render(opts: argparse.Namespace) -> int:
    from .core.render import plan_jobs, preview, run_jobs
    settings = load_settings(opts.config)
    workers = opts.workers if opts.workers is not None else settings.workers
    jobs = plan_jobs(opts, settings)
    if opts.preview:
        for j in jobs:
            preview(j)
        return 0
    run_jobs(jobs, settings, workers)
    return 0


def cmd_contact_sheet(opts: argparse.Namespace) -> int:
    from .tools.contact_sheet import contact_sheet
    out = opts.out or os.path.splitext(opts.videos[0])[0] + "_sheet.png"
    print(contact_sheet(opts.videos, out, opts.frames, opts.cols, opts.width, opts.safe_zones))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help")):
        argv = ["render"] + argv
    opts = build_parser().parse_args(argv)
    if opts.command == "contact-sheet":
        return cmd_contact_sheet(opts)
    return cmd_render(opts)
