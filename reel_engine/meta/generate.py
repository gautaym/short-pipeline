"""Generate a title, description and tags for a rendered reel from what actually happened in it.

Titles come from the format's titles(outcome) ideas, combined with its series name and number
("Broke out of the SPIRAL in 22.4s | Brick Escape #14"). An idea used by one of the format's
recent reels is skipped, and the ledger refuses exact repeats, so no two videos share a title.
"""
import json
import os
from dataclasses import dataclass
from typing import Any

from .. import formats
from .ledger import Entry, Ledger

TITLE_MAX = 100          # YouTube's limit
TWISTS = {"multiball": "a surprise multiball", "regrow": "bricks growing back", "earthquake": "cracking walls",
          "split": "the ball splitting in three", "rage": "boss rage mode", "storm": "a ball storm",
          "underdog": "an underdog boost", "turbo": "a turbo boost", "shatter": "a ring shattering",
          "reverse": "the rings reversing", "spark": "a second spark", "mega": "a mega bomb",
          "life": "an extra life"}


@dataclass
class Meta:
    title: str
    description: str
    tags: list[str]
    series_no: int


def pick_title(fmt, outcome: dict[str, Any], series_no: int, ledger: Ledger) -> str:
    suffix = f" | {fmt.series or fmt.name} #{series_no}"
    ideas = fmt.titles(outcome) or ["Watch till the end"]
    recent = set(ledger.recent_cores(fmt.name))
    start = series_no % len(ideas)                       # rotate, so consecutive reels differ
    ordered = ideas[start:] + ideas[:start]
    for core in sorted(ordered, key=lambda c: c in recent):
        title = (core[: TITLE_MAX - len(suffix)] + suffix).strip()
        if not ledger.title_used(title):
            return title
    raise ValueError(f"no unused title for {fmt.name} #{series_no}")


def build(summary: dict[str, Any], ledger: Ledger, channel_tags: list[str], channel_hashtags: list[str]) -> Meta:
    fmt = formats.get(summary["mode"])
    o = summary["outcome"]
    n = ledger.next_series_no(fmt.name)
    title = pick_title(fmt, o, n, ledger)
    lines = [summary["title"], ""]
    what = fmt.describe(o)
    if what:
        lines.append(what)
    if o.get("twist"):
        lines.append(f"Plot twist along the way: {TWISTS.get(o['twist'], o['twist'])}.")
    lines += [fmt.cta, "", f"{fmt.series or fmt.name} #{n}. Every video is simulated from a random seed "
                           f"(this one: {summary['seed']}), so no two are the same."]
    tags_line = " ".join("#" + h for h in ["shorts", *fmt.hashtags, *channel_hashtags])
    lines += ["", tags_line]
    tags = list(dict.fromkeys([*fmt.tags, *channel_tags]))
    return Meta(title, "\n".join(lines), tags, n)


def record(summary: dict[str, Any], ledger: Ledger, channel: dict[str, Any]) -> Meta:
    """Generate metadata for a rendered reel, add it to the ledger and write sidecar files.

    Next to reel_x.mp4 this writes reel_x.txt (ready to copy and paste) and reel_x.json.
    """
    meta = build(summary, ledger, channel.get("tags", []), channel.get("hashtags", []))
    ledger.add(Entry(summary["mode"], summary["seed"], meta.series_no, summary["out"], summary["duration"],
                     summary["title"], meta.title, meta.description, meta.tags, summary["outcome"],
                     summary.get("score", 0.0)))
    stem = os.path.splitext(summary["out"])[0]
    kids = channel.get("made_for_kids")
    with open(stem + ".txt", "w", encoding="utf-8") as f:
        f.write(f"TITLE\n{meta.title}\n\nDESCRIPTION\n{meta.description}\n\nTAGS\n{', '.join(meta.tags)}\n\n"
                f"MADE FOR KIDS\n{'not set in configs/default.yaml (channel.made_for_kids)' if kids is None else kids}\n")
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump({"title": meta.title, "description": meta.description, "tags": meta.tags,
                   "made_for_kids": kids, "format": summary["mode"], "seed": summary["seed"],
                   "series_no": meta.series_no, "outcome": summary["outcome"]}, f, indent=2)
    return meta
