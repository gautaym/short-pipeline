"""Shortcuts for making a story episode: review the art, pick takes, render both languages with
previews, and start a new script.

    reel review <id>                 contact sheets of every take, and of the chosen cut-outs
    reel pick <id> shiva=3 vasuki=1  choose takes (copies the take over the main picture)
    reel make <id>                   render English and Hindi, each with a frame sheet and a phone preview
    reel new-story <id> --segment science
"""
import re
import subprocess
from pathlib import Path

from ..config import REPO_ROOT
from ..core.video import find_tool
from ..story import art

REVIEW = REPO_ROOT / "out" / "_review"
PREVIEW_MB = 28                     # phones (Remote Control) take files up to 30 MB


def _sheet(pg, items: list[tuple[str, object]], out: Path, cols: int = 8, cell=(230, 400), bg=(60, 60, 70)) -> Path:
    """Pictures in a labelled grid, each scaled to fit its cell."""
    font = pg.font.Font(None, 22)
    rows = max(1, (len(items) + cols - 1) // cols)
    sheet = pg.Surface((cols * cell[0] + 20, rows * cell[1] + 10))
    sheet.fill(bg)
    for i, (label, img) in enumerate(items):
        w, h = img.get_size()
        sc = min((cell[1] - 40) / h, (cell[0] - 10) / w)
        x, y = 10 + (i % cols) * cell[0], 10 + (i // cols) * cell[1]
        sheet.blit(pg.transform.smoothscale(img, (max(1, int(w * sc)), max(1, int(h * sc)))), (x, y))
        sheet.blit(font.render(label, True, (255, 255, 0)), (x, y + cell[1] - 30))
    out.parent.mkdir(parents=True, exist_ok=True)
    pg.image.save(sheet, str(out))
    return out


def review(story_id: str) -> list[Path]:
    """One sheet with every drawn take, one with the chosen puppets cut out over red."""
    from ..core.render import init_pygame
    pg = init_pygame()
    folder = art.folder(story_id)
    takes = sorted(p for p in folder.glob("*.png") if not p.stem.endswith("_cut"))
    sheets = [_sheet(pg, [(p.stem.replace("puppet_", ""), pg.image.load(str(p))) for p in takes],
                     REVIEW / f"{story_id}_takes.png")]
    chosen = sorted({p.stem.replace("puppet_", "") for p in takes if p.stem.startswith("puppet_")
                     and not p.stem.rsplit("_", 1)[-1].isdigit()})
    if chosen:
        sheets.append(_sheet(pg, [(n, art.cut(pg, story_id, n)) for n in chosen],
                             REVIEW / f"{story_id}_cuts.png", bg=(200, 60, 60)))
    return sheets


def pick(story_id: str, choices: list[str]) -> list[str]:
    """`name=take` for each puppet or backdrop: that take becomes the one the reel uses."""
    done = []
    for choice in choices:
        name, take = choice.split("=")
        kind = "backdrop" if (art.folder(story_id) / f"backdrop_{name}.png").exists() else "puppet"
        main = art.folder(story_id) / f"{kind}_{name}.png"
        src = main if take == "1" else main.with_name(f"{kind}_{name}_{take}.png")
        if not src.exists():
            raise SystemExit(f"no take {take} of {name} in {art.folder(story_id)}")
        if src != main:
            # keep the old first take as an extra take, so nothing is lost
            spare = main.with_name(f"{kind}_{name}_was1.png")
            if not spare.exists():
                main.replace(spare)
            main.write_bytes(src.read_bytes())
        main.with_name(f"{main.stem}_cut.png").unlink(missing_ok=True)
        done.append(f"{name}: take {take}")
    return done


def live(story_id: str) -> list[str]:
    """Make the story's missing living-face loops (LivePortrait, in lpenv)."""
    from ..formats.story import load_story
    from ..story.art import make_live
    return make_live(load_story(story_id))


def make(story_id: str, langs: tuple[str, ...] = ("en", "hi"), seed: int = 1) -> list[Path]:
    """Render the story in each language, then a frame sheet and a phone-size preview beside each reel.
    Living faces the story lists (art.live) are made first if missing."""
    import re
    import sys
    live(story_id)
    made = []
    for lang in langs:
        run = subprocess.run([sys.executable, "-m", "reel_engine", "render", "--mode", "story", "--story", story_id,
                              "--lang", lang, "--seed", str(seed), "--no-ledger"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO_ROOT)
        found = re.search(r"-> (.+\.mp4) \(([\d.]+)s\)", run.stdout)
        if run.returncode or not found:
            raise SystemExit(f"render failed for {story_id} ({lang}):\n{run.stdout[-1500:]}{run.stderr[-1500:]}")
        video, duration = Path(found.group(1)), float(found.group(2))
        ff = find_tool()
        subprocess.run([ff, "-v", "error", "-y", "-i", str(video), "-vf", "fps=1/4,scale=216:384,tile=12x3",
                        "-frames:v", "1", str(video.with_name(video.stem + "_frames.png"))], check=True)
        preview = video.with_name(video.stem + "_preview.mp4")
        kbps = int(PREVIEW_MB * 8000 / duration) - 128            # fits the size limit at any length
        subprocess.run([ff, "-v", "error", "-y", "-i", str(video), "-vf", "scale=720:1280", "-c:v", "libx264",
                        "-b:v", f"{max(400, kbps)}k", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k",
                        str(preview)], check=True)
        print(f"{lang}: {video} ({duration:.1f}s), preview {preview.stat().st_size / 1e6:.1f} MB", flush=True)
        made += [video, preview]
        text = upload_text(story_id, lang)
        if text:
            (video.parent / "upload.txt").write_text(text, encoding="utf-8")
    return made


TAGS_LIMIT = 500          # characters of tags, as YouTube's Tags box allows
HASHTAGS_MAX = 60         # YouTube ignores every hashtag in a description that has more than this


def as_hashtag(tag: str) -> str:
    """"diwali kyu manate hai" -> "#diwalikyumanatehai" (spaces and punctuation dropped, Hindi kept whole)."""
    return "#" + re.sub(r"[\s,.'’:;!?()\-#]", "", tag.lower())


def upload_text(story_id: str, lang: str) -> str | None:
    """The upload.txt beside a reel, as in reels-2: TITLE, DESCRIPTION, the hashtags, then more TAGS,
    every one written as a hashtag. From the story's `upload` block (None if it has none)."""
    from ..formats.story import load_story
    up = load_story(story_id).get("upload")
    if not up or lang not in up:
        return None
    hashtags = [as_hashtag(h) for h in up.get("hashtags", []) + up[lang].get("hashtags", [])]
    tags, used = [], 0
    for tag in up[lang].get("tags", []) + up.get("tags", []):     # the language's own searches first
        tag = as_hashtag(tag)
        if tag in tags or tag in hashtags or len(tag) < 3:
            continue
        if used + len(tag) + 1 > TAGS_LIMIT or len(hashtags) + len(tags) >= HASHTAGS_MAX:
            continue                                                  # a shorter tag may still fit
        used += len(tag) + 1
        tags.append(tag)
    description = " ".join(up[lang]["description"].split())
    return (f"TITLE\n{up[lang]['title']}\n\nDESCRIPTION\n{description}\n\n{' '.join(hashtags)}\n\n"
            f"TAGS\n{' '.join(tags)}\n")


def write_upload(story_id: str) -> list[Path]:
    """Write upload.txt beside the newest render of the story in each language."""
    from ..config import REPO_ROOT as root
    written = []
    for lang in ("en", "hi"):
        found = sorted((root / "out").glob(f"*/story_{story_id}_{lang}_1/story_{story_id}_{lang}_1.mp4"),
                       key=lambda q: q.stat().st_mtime)
        text = upload_text(story_id, lang)
        if found and text:
            path = found[-1].parent / "upload.txt"
            path.write_text(text, encoding="utf-8")
            written.append(path)
    return written


TEMPLATE = '''# {title}
# Review notes: sources and facts used, anything tellings disagree on, and what the script hedges.
id: {id}
topic: {topic}
segment: {segment}
# ask: false        # uncomment for a story that is not a question: the narrator opens with the title alone
title:
  en: "A question someone would ask?"
  hi: "..."
series:
  en: "{series}"
  hi: "..."
summary:
  en: "..."
  hi: "..."
music: chill
cast: {{}}
opening:
  beat: 1                      # the most striking beat, shown behind the question
# Arc: hook -> rising stakes -> climax -> turn (the science or the twist) -> payoff that answers
# the opening question. Concrete true details beat general statements.
art:
  puppet_style: >-
    {puppet_style}
  prop_style: >-
    {prop_style}
  backdrop_style: >-
    An empty landscape painted in flat folk art style, bright colours with dark outlines, seen full frame
    with no border or frame. Uninhabited scenery only: no people, no figures, no animals, no text.
    Vertical composition.
  cast: {{}}
  puppets: {{}}
  props: {{}}
  backdrops:
    scene: "..."
  anchors: {{}}
beats:
  - en: "..."
    hi: "..."
    caption: "SHORT LINE, *KEY* WORD."
    scene: cosmos
    stage:
      backdrop: scene
      actors: {{}}
end:
  head: "..."
  sub: "..."
'''

STYLES = {
    "leather": ("A single flat painted leather shadow puppet, traditional Andhra Tholu Bommalata style, mounted on a "
                "thin bamboo stick, bright flat colours with dark outlines, a pale cut edge and visible rivet joints, "
                "full body from head to feet, studio photo against a plain pure black backdrop, nothing else in the frame.",
                "A single flat painted cut-out object, not a person: no body, no arms, no legs, bright flat colours with "
                "dark outlines and a pale cut edge, studio photo against a plain pure black backdrop, nothing else in "
                "the frame, no text."),
    "paper": ("A single full-body character cut-out made of layered coloured paper, flat paper-craft illustration with "
              "clean cut edges and subtle paper texture, bright colours, full body from head to feet, studio photo "
              "against a plain pure black backdrop, nothing else in the frame, no text.",
              "A single cut-out made of layered coloured paper, flat paper-craft illustration with clean cut edges, "
              "subtle paper texture and soft layered depth, bright colours, studio photo against a plain pure black "
              "backdrop, nothing else in the frame, no text, no letters, no numbers."),
}


def new_story(story_id: str, segment: str) -> Path:
    path = REPO_ROOT / "stories" / f"{story_id}.yaml"
    if path.exists():
        raise SystemExit(f"{path} already exists")
    science = segment == "science"
    puppet_style, prop_style = STYLES["paper" if science else "leather"]
    path.write_text(TEMPLATE.format(id=story_id, title=story_id.replace("_", " ").title(),
                                    topic="science" if science else "mythology", segment=segment,
                                    series="Science Stories" if science else "Sky Stories",
                                    puppet_style=puppet_style, prop_style=prop_style), encoding="utf-8")
    return path
