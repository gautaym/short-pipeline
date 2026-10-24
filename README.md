# reel_engine

Seeded, auto-playing videos for YouTube Shorts and Instagram Reels, rendered as vertical
9:16 MP4s (1080×1920, 30 fps) with generated sound. The same seed and options always produce
the same video.

Each video format is a plug-in. The engine currently ships the brick-breaker family:

| Format    | What happens | Hook |
|-----------|--------------|------|
| `classic` | 1 ball vs a brick shape (heart, star, a word…); power-up bricks spawn more balls | "Can 1 ball clear the HEART?" |
| `escape`  | the ball starts trapped in a maze of unbreakable grey bricks | "Where will it break out?" |
| `boss`    | a giant block with a big HP counter, ringed by power-up bricks | "1 ball vs a 999 HP block" |
| `wars`    | colour territories; each team's ball converts the others' bricks | "Which colour wins?" |

## Setup

You need Python 3.10 or newer and ffmpeg on your PATH.

**Windows**

```powershell
winget install Gyan.FFmpeg
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

**macOS**

```bash
brew install ffmpeg python
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

**Linux (Debian/Ubuntu)**

```bash
sudo apt install ffmpeg python3-venv
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

The project uses `pygame-ce`, a drop-in fork of pygame that publishes wheels for current Python
versions. Do not install `pygame` alongside it.

## Rendering

```bash
reel render --mode escape --seed 42             # one reel -> out/reel_escape_42.mp4
reel render --mode classic --shape text --text 2026
reel render --mode wars --teams 4 --max-play 20
reel render --mode boss --boss-hp 999 --title "Can it break 999?"
reel render --batch 8 --mix even --workers 4    # 8 reels, formats in rotation, 4 at a time
reel render --mode escape --preview             # watch it live in a window, no file
```

`reel` is the same as `python -m reel_engine`. The original commands still work:
`python brickreel.py --mode escape --seed 42`.

| Flag | Meaning |
|------|---------|
| `--mode` | a format name, or `random` (default) |
| `--seed` | seed for layout, palette and outcome (random if omitted) |
| `--batch N` | render N reels with consecutive seeds |
| `--mix even` | with `--mode random`, rotate through every format in a seeded order |
| `--workers N` | render N reels in parallel (same output as sequential) |
| `--scout N` | simulate N candidate seeds per reel and render the most dramatic (default from config: 8; `1` = use the seed exactly) |
| `--min-length S` | shortest reel in seconds (default from config: 20). Scouting avoids runs that end sooner; if one still does, its end card is held until S |
| `--twist` | `auto` (seeded chance of a mid-reel surprise), `none`, or a twist name such as `multiball` |
| `--max-play S` | seconds of play before time-up |
| `--title` | override the hook line |
| `--out` | output file (single reel only) |
| `--config` | YAML settings file (default `configs/default.yaml`) |

Format options (`--shape`, `--text`, `--teams`, `--boss-hp`) are listed by `reel render --help`.

Settings such as the output folder, x264 quality and default worker count live in
[configs/default.yaml](configs/default.yaml).

## What every reel gets

- **Hook card**: the first 1.5 s show the hook line big and centred, zooming in gently, then it
  settles into the title.
- **Drama engine**: before rendering, the engine simulates candidate seeds (fast, nothing is
  drawn), scores each run with the format's `drama_score()` (late decisive moments, near misses,
  comebacks, twists; long dull stretches lose points) and renders the best. The file is named
  after the chosen seed, and `--seed <that seed> --scout 1` reproduces it exactly.
- **Slow motion** around the decisive moment (last brick, escape, boss kill, last ball lost).
  The pre-pass knows when it happens, so slow motion starts just before it.
- **Twists**: a seeded chance of a mid-reel surprise with a "WAIT..." banner, e.g. multiball,
  bricks regrowing, walls cracking, boss rage mode, an underdog boost.
- **Polish**: ball trails, screen shake, a pop-in end card with a call to action, and a
  crossfade back into the first frame so the reel loops.

Twists by format: classic `multiball`, `regrow`; escape `earthquake`, `split`; boss `rage`,
`storm`; wars `underdog`.

## Reviewing output

```bash
reel contact-sheet out/reel_escape_42.mp4                 # 10 frames in a 5-column grid
reel contact-sheet out/*.mp4 -n 6 -o review.png           # one labelled row per video
```

## Project layout

```
reel_engine/
  cli.py              reel render / reel contact-sheet
  config.py           settings from configs/*.yaml
  core/               shared by every format
    canvas.py         canvas size, frame rate, simulation ticks, standard 9:16 layout
    render.py         frame loop, batch planning, parallel workers, live preview
    drama.py          simulate without drawing, score, pick the best seed, plan slow motion
    video.py          ffmpeg writer, audio mux, probing
    audio.py          tone synthesis and event mixer
    physics.py        balls and rectangle bounces
    text.py           fonts, wrapping, fit-to-width
    effects.py        particles, floating text, flash, screen shake, slow-motion vignette
    palette.py        colour helpers
  formats/
    __init__.py       plug-in registry (auto-discovers every module in this package)
    base.py           Format base class, Option, EndCard, Twist; hook card, end card, loop
    bricks/           the brick-breaker family (shared grid/paddle engine + 4 formats)
  tools/              contact sheets
configs/default.yaml
tests/
```

## Adding a format

Create a module anywhere under `reel_engine/formats/`. It is discovered automatically.

```python
from reel_engine.formats import EndCard, Format, Option, register

@register
class MyFormat(Format):
    name = "my_format"
    order = 50                       # place in the --mix even rotation
    default_duration = 30.0          # seconds of play before time-up
    options = (Option("--balls", "how many balls", {"type": int, "default": None}),)

    def setup(self): ...             # seeded layout; use self.rng / self.nrng only
    def title_hooks(self): return ["Hook line one", "Hook line two"]
    def step(self, dt, t): ...       # advance one 1/120 s tick; call self.mark("decisive") at the big moment
    def check_end(self, t): return "time" if self.play_t >= self.max_play else None
    def end_card(self): return EndCard("DONE!", "subline")
    def sounds(self): return {...}   # name -> numpy array (see core/audio.py)
    def draw_world(self, screen, t): ...
```

The base class handles the hook card, the title, the HUD row (`stats()` and `progress()`),
effects (`self.fx`), sound events (`self.sfx(t, name, index)`), slow motion, twists, the end card
and the loop. Optional overrides: `twists()`, `drama_score(trace)`, `sample()`, `outcome()`.

Determinism rules:

- Draw gameplay randomness only from `self.rng` or `self.nrng`, and visual-only randomness
  from `self.fx.rng`. Never use the global `random` module, time, or anything machine-specific.
- Gameplay must never depend on `draw_world()`: seed scouting simulates without drawing and
  must reach the same ending (a test checks this for every format).

## Tests

```bash
pytest      # determinism, simulate-vs-render match, scouting, twists, 3-second render of every format
```

## Notes

- Text uses FreeSans Bold, which ships inside pygame-ce (GNU FreeFont, GPL with the font
  exception), so the same seed renders identically on every OS.
- `--mode random` picks from the registered formats, so adding formats changes which format a
  given seed picks.
- Milestone 1 reproduced the original `brickreel.py` byte for byte; that script and its parity
  check live in git history (commit 15cf46f). Milestone 2 changed the look and the gameplay
  tuning on purpose.
