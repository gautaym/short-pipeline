"""Command line: `reel render ...` and `reel contact-sheet ...`.

Old-style calls without a subcommand (`reel --mode escape`, or `python brickreel.py --mode
escape`) are treated as `render`, so the original brickreel.py flags keep working.
"""
import argparse
import os
import sys

from . import formats
from .config import load_settings

COMMANDS = ("render", "contact-sheet", "ledger", "organise", "story-art", "review", "pick", "make", "new-story", "track", "live")


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
    r.add_argument("--no-voice", action="store_true", help="leave out the spoken hook and result")
    r.add_argument("--twist", default="auto",
                   help="mid-reel surprise: auto (seeded chance), none, or a twist name for the format")
    r.add_argument("--preview", action="store_true", help="show a live window instead of rendering")
    r.add_argument("--config", default=None, help="YAML settings file (default configs/default.yaml)")
    _add_format_options(r)

    r.add_argument("--no-ledger", action="store_true", help="skip titles/descriptions and the ledger")

    org = sub.add_parser("organise", help="move older flat out/reel_*.mp4 files into one folder per reel")
    org.add_argument("--config", default=None)

    lg = sub.add_parser("ledger", help="list recently rendered reels and their titles")
    lg.add_argument("-n", "--last", type=int, default=20)
    lg.add_argument("--config", default=None)

    a = sub.add_parser("story-art", help="draw the pictures for an illustrated story (local image model)")
    a.add_argument("story", help="story id from stories/")
    a.add_argument("--takes", type=int, default=2, help="versions of each puppet, to choose from")
    a.add_argument("--only", default=None, help="only these puppets or backdrops, e.g. shiva,ocean")
    a.add_argument("--redo", action="store_true", help="draw again even if a picture exists")

    rv = sub.add_parser("review", help="contact sheets of a story's drawn takes and chosen cut-outs")
    rv.add_argument("story")
    pk = sub.add_parser("pick", help="choose takes for a story, e.g. reel pick ra apep=1 khepri=3")
    pk.add_argument("story")
    pk.add_argument("choices", nargs="+", help="name=take")
    mk = sub.add_parser("make", help="render a story in English and Hindi, with frame sheets and phone previews")
    mk.add_argument("story")
    mk.add_argument("--langs", default="en,hi")
    lv = sub.add_parser("live", help="make the living-face loops (blinks, head movement) a story lists")
    lv.add_argument("story")
    tr = sub.add_parser("track", help="live table of a reel queue, per reel and task, at localhost:8765")
    tr.add_argument("stories", nargs="+", help="story ids in queue order")
    tr.add_argument("--since", default=None, help="count work done after this time today, e.g. 14:30")
    ns = sub.add_parser("new-story", help="start a story script from the template")
    ns.add_argument("story")
    ns.add_argument("--segment", required=True, choices=["indian_myth", "world_myth", "science"])

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
    results = run_jobs(jobs, settings, workers)
    if not opts.no_ledger:
        from .config import load_channel
        from .meta.generate import record
        from .meta.ledger import Ledger
        ledger = Ledger(settings.ledger_path())
        channel = load_channel(opts.config)
        try:
            for res in results:
                meta = record(res, ledger, channel)
                print(f"  title: {meta.title}")
        finally:
            ledger.close()
        if channel.get("made_for_kids") is None:
            print("note: channel.made_for_kids is not set in the config; it must be before any upload.")
    for res in results:
        write_preview(res["out"])
        print(f"  folder: {os.path.dirname(os.path.abspath(res['out']))}")
    return 0


def write_preview(video: str) -> None:
    """A 6-frame strip next to the video, to recognise the reel at a glance."""
    from .core.render import sidecars
    from .tools.contact_sheet import contact_sheet
    contact_sheet([video], sidecars(video)["preview"], n=6, cols=6, width=160)


def cmd_organise(opts: argparse.Namespace) -> int:
    """Move flat reel_<slug>_<seed>.mp4 files (and their .txt/.json) into per-reel folders."""
    import shutil
    from datetime import datetime
    from .core.render import reel_path, sidecars
    from .meta.ledger import Ledger
    settings = load_settings(opts.config)
    root = settings.output_dir
    ledger = Ledger(settings.ledger_path())
    moved = 0
    for name in sorted(os.listdir(root)):
        if not (name.startswith("reel_") and name.endswith(".mp4")):
            continue
        old = os.path.join(root, name)
        stem = name[len("reel_"):-len(".mp4")]
        slug, _, seed = stem.rpartition("_")
        day = datetime.fromtimestamp(os.path.getmtime(old)).date().isoformat()
        new = reel_path(root, slug, int(seed), day)
        os.makedirs(os.path.dirname(new), exist_ok=True)
        shutil.move(old, new)
        side = sidecars(new)
        for ext, key in ((".txt", "upload"), (".json", "meta")):
            if os.path.exists(old[:-4] + ext):
                shutil.move(old[:-4] + ext, side[key])
        ledger.move(old, new)
        write_preview(new)
        moved += 1
        print(f"{name} -> {os.path.dirname(new)}")
    ledger.close()
    print(f"moved {moved} reels")
    return 0


def cmd_ledger(opts: argparse.Namespace) -> int:
    from .meta.ledger import Ledger
    ledger = Ledger(load_settings(opts.config).ledger_path())
    for row in ledger.recent(opts.last):
        vid, created, fmt, n, title, path, uploaded = row
        print(f"{vid:>4}  {created[:16]}  {fmt:<12} #{n:<4} {'uploaded' if uploaded else '        '}  {title}")
    ledger.close()
    return 0


def cmd_story_art(opts: argparse.Namespace) -> int:
    from .formats.story import load_story
    from .story.art import generate
    only = opts.only.split(",") if opts.only else None
    for path in generate(load_story(opts.story), opts.takes, only, opts.redo):
        print(path)
    return 0


def cmd_contact_sheet(opts: argparse.Namespace) -> int:
    from .tools.contact_sheet import contact_sheet
    out = opts.out or os.path.splitext(opts.videos[0])[0] + "_sheet.png"
    print(contact_sheet(opts.videos, out, opts.frames, opts.cols, opts.width, opts.safe_zones))
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):                # Hindi titles on a Windows console
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0] not in COMMANDS and argv[0] not in ("-h", "--help")):
        argv = ["render"] + argv
    opts = build_parser().parse_args(argv)
    if opts.command == "contact-sheet":
        return cmd_contact_sheet(opts)
    if opts.command == "ledger":
        return cmd_ledger(opts)
    if opts.command == "story-art":
        return cmd_story_art(opts)
    if opts.command == "track":
        import datetime
        from .tools.tracker import track
        since = None
        if opts.since:
            h, m = map(int, opts.since.split(":"))
            since = datetime.datetime.now().replace(hour=h, minute=m, second=0).timestamp()
        track(opts.stories, since)
        return 0
    if opts.command == "live":
        from .tools.story_tools import live
        for line in live(opts.story) or ["nothing to make"]:
            print(line)
        return 0
    if opts.command in ("review", "pick", "make", "new-story"):
        from .tools import story_tools as st
        if opts.command == "review":
            out = st.review(opts.story)
        elif opts.command == "pick":
            out = st.pick(opts.story, opts.choices)
        elif opts.command == "make":
            out = st.make(opts.story, tuple(opts.langs.split(",")))
        else:
            out = [st.new_story(opts.story, opts.segment)]
        for line in out:
            print(line)
        return 0
    if opts.command == "organise":
        return cmd_organise(opts)
    return cmd_render(opts)
