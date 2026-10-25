# reel_engine

Seeded, auto-playing videos for YouTube Shorts and Instagram Reels, rendered as vertical
9:16 MP4s (1080×1920, 30 fps) with generated sound. The same seed and options always produce
the same video.

Each video format is a plug-in:

| Format | What happens | Hook |
|--------|--------------|------|
| `classic` | 1 ball vs a brick shape (heart, star, a word…); power-up bricks spawn more balls | "Can 1 ball clear the HEART?" |
| `escape` | the ball starts trapped in a maze of unbreakable grey bricks | "Where will it break out?" |
| `boss` | a big block with an HP counter, ringed by power-up bricks | "Can it break the 200 HP boss?" |
| `wars` | colour territories; each team's ball converts the others' squares | "Which colour wins?" |
| `mystery` | a picture hidden under the bricks, revealed as they break, with a hint | "Guess the picture before it's revealed" |
| `ring_escape` | balls bounce inside spinning rings; every escape spawns 2 more | "Every escape = 2 more balls" |
| `food_wars` | colour wars with Indian foods as teams (mains, street food, sweets, drinks) | "BIRYANI vs DOSA vs PAV BHAJI" |
| `algo_race` | BFS, DFS, A* or greedy search race through the same maze | "Same maze. 3 brains. Which escapes first?" |
| `diwali` | one spark, a field of crackers, a chain reaction | "1 spark. 206 crackers." |
| `platformer` | a retro pixel-art runner on a freshly generated level | "Level 17. 3 lives. Go." |
| `physics` | any physics scene file: orbits, three suns, black holes, projectiles… | "Will Earth survive?" |

Format-specific options (see `reel render --help`): `--shape`, `--text` (classic/escape),
`--boss-hp`, `--teams`, `--picture`/`--answer` (mystery), `--rings`/`--goal` (ring_escape),
`--category` (food_wars), `--algos` (algo_race), `--duds` (diwali), `--lives` (platformer),
`--scene` (physics).

Mystery pictures: eight original pictures are built in (drawn in code). To add your own, put
images in `assets/pictures/`; the file name becomes the answer (`taj_mahal.jpg` → "TAJ MAHAL").
Only use images you own or that are in the public domain.

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
- **Music**: a copyright-free backing track generated from the seed in a style that suits the
  format (upbeat, chill, tense, festive, chiptune), mixed under the effects. Every reel is
  normalised to -14 LUFS. `--no-music` leaves it out.
- **Voice**: the hook is spoken at the start and the result at the end, by Kokoro (an open
  text-to-speech model, Apache 2.0) running offline. Put `kokoro-v1.0.onnx` and `voices-v1.0.bin`
  from the kokoro-onnx releases in `models/` (git-ignored); without them reels simply have no
  voice. Pick the voice with `voice_name` in the config; `--no-voice` leaves it out.
- **Phone safe zones**: titles, scores and the main action stay clear of the areas Shorts and
  Reels cover with their own buttons and captions.

Twists by format: classic `multiball`, `regrow`; escape `earthquake`, `split`; boss `rage`,
`storm`; wars `underdog`.

## Physics lab

`reel render --mode physics --scene black_hole` plays a physics scene described in a YAML file
in `scenes/` (or any path). Starter scenes: `kepler` (equal areas in equal times), `three_body`,
`black_hole` (a black hole passing through a solar system, with light bending) and `projectiles`
(which launch angle goes furthest with air drag).

A scene lists bodies (mass, radius, position, velocity, colour, glow, trail, `kind: black_hole`),
the world (gravity constant `G`, uniform gravity, air drag, ground, merging, time scale), the
camera (`view`: fixed, or `follow: true`), on-screen readouts and an equation line, and outcome
rules checked in order, e.g.

```yaml
outcomes:
  - {when: "swallowed(Earth)", result: swallowed, head: "EARTH WAS SWALLOWED!", sub: "after {t:.1f} seconds"}
  - {when: "time", result: survived, head: "EARTH SURVIVED!"}
```

Any number can be a seeded range (`"1.6..2.2"`) or a pick (`{choice: [a, b]}`), so every seed is
a new run and scouting keeps the most dramatic. Conditions: `time`, `swallowed(X|any)`,
`merged(X|any)`, `landed(X|all)`, `ejected(X|any, R)`, `escaped(X, R, FROM|origin)`. Gravity is
real Newtonian gravity (Kepler's laws emerge on their own); black-hole visuals are artistic.

## Titles, descriptions and the ledger

After rendering, every reel gets a title, description and tags built from what actually happened
in it ("Broke out of the SPIRAL in 22.4s | Brick Escape #14"), written next to the video:

- `reel_<format>_<seed>.txt`: title, description and tags, ready to copy and paste
- `reel_<format>_<seed>.json`: the same, plus the outcome, for tools

Each reel is also recorded in a ledger (`out/ledger.sqlite`), which numbers each series and
guarantees no title is ever reused. `reel ledger` lists the latest entries; `--no-ledger` skips
all of this.

`channel.made_for_kids` in the config deliberately has no default: it is a legal declaration
only you can make, and it must be set before anything is uploaded.

## Reviewing output

```bash
reel contact-sheet out/reel_escape_42.mp4                 # 10 frames in a 5-column grid
reel contact-sheet out/*.mp4 -n 6 -o review.png           # one labelled row per video
reel contact-sheet out/*.mp4 -n 5 --safe-zones           # tint the areas phone UI covers
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
