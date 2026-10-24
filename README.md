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
| `--max-play S` | seconds of play before time-up |
| `--title` | override the hook line |
| `--out` | output file (single reel only) |
| `--config` | YAML settings file (default `configs/default.yaml`) |

Format options (`--shape`, `--text`, `--teams`, `--boss-hp`) are listed by `reel render --help`.

Settings such as the output folder, x264 quality and default worker count live in
[configs/default.yaml](configs/default.yaml).

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
    canvas.py         canvas size, frame rate, standard 9:16 layout
    render.py         frame loop, batch planning, parallel workers, live preview
    video.py          ffmpeg writer, audio mux, probing
    audio.py          tone synthesis and event mixer
    physics.py        balls and rectangle bounces
    text.py           fonts, wrapping, fit-to-width
    effects.py        particles, floating text, flash
    palette.py        colour helpers
  formats/
    __init__.py       plug-in registry (auto-discovers every module in this package)
    base.py           Format base class, Option, EndCard
    bricks/           the brick-breaker family (shared grid/paddle engine + 4 formats)
  tools/              contact sheets, parity check against the original script
configs/default.yaml
legacy/brickreel_v0.py  the original single-file script, kept for the parity check
scripts/parity_check.py
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
    def step(self, dt, t): ...       # advance the simulation
    def check_end(self, t): return "time" if self.play_t >= self.max_play else None
    def end_card(self): return EndCard("DONE!", "subline")
    def sounds(self): return {...}   # name -> numpy array (see core/audio.py)
    def draw_world(self, screen, t): ...
```

The base class handles the intro and outro, the hook title, the HUD row (`stats()` and
`progress()`), effects (`self.fx`), sound events (`self.sfx(t, name, index)`) and the end card.

Determinism rule: draw all randomness from `self.rng` or `self.nrng` (seeded per reel). Never
use the global `random` module, time, or anything machine-specific.

## Tests

```bash
pytest                                  # determinism, parity, 3-second smoke render of every format
python scripts/parity_check.py          # ~110 cases, frame by frame, against legacy/brickreel_v0.py
```

## Known quirks (kept for parity, to fix in Milestone 2)

- `boss` screen shake draws from the gameplay RNG inside `draw()`, so drawing affects the outcome.
- Fonts come from the system (Arial on Windows, DejaVu on Linux), so the same seed can look
  different on another OS. A bundled open-licence font will replace this.
- `--mode random` picks from the registered formats, so adding formats changes which format a
  given seed picks.
