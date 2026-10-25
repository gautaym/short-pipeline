"""Scene files: a physics setup described in YAML, turned into a World with seeded values.

A scene names its bodies, the forces in play, what to show on screen and how it can end. Any
number may be a seeded range, written "1.6..2.2", or a pick, written {choice: [a, b, c]}, so
every seed is a different run. See scenes/*.yaml for examples.
"""
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..config import REPO_ROOT
from .world import Body, WorldSettings

SCENE_DIR = REPO_ROOT / "scenes"
RANGE = re.compile(r"^\s*(-?[\d.]+(?:e-?\d+)?)\s*\.\.\s*(-?[\d.]+(?:e-?\d+)?)\s*$")
NAMED_COLOURS = {
    "white": (255, 255, 255), "yellow": (255, 214, 64), "orange": (255, 150, 40), "red": (240, 70, 70),
    "pink": (255, 90, 170), "purple": (170, 110, 255), "blue": (70, 160, 255), "cyan": (60, 220, 255),
    "green": (110, 220, 90), "lime": (190, 240, 80), "grey": (160, 160, 175), "brown": (170, 110, 70),
    "black": (0, 0, 0),
}
PALETTE = ["red", "orange", "yellow", "lime", "cyan", "blue", "purple", "pink"]


@dataclass
class Scene:
    name: str
    hooks: list[str]
    duration: float
    world: WorldSettings
    bodies: list[Body]
    view: dict[str, Any]
    background: str
    equation: str
    readouts: list[dict[str, Any]]
    sweep: dict[str, Any] | None
    outcomes: list[dict[str, Any]]
    drama: dict[str, Any]
    music: str
    params: dict[str, Any] = field(default_factory=dict)     # resolved numbers, for text templates


def scene_names() -> list[str]:
    return sorted(p.stem for p in SCENE_DIR.glob("*.yaml")) if SCENE_DIR.is_dir() else []


def scene_path(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.suffix in (".yaml", ".yml") and p.exists():
        return p
    p = SCENE_DIR / f"{name_or_path}.yaml"
    if not p.exists():
        raise SystemExit(f"unknown scene {name_or_path!r}; available: {', '.join(scene_names())}")
    return p


def resolve(value: Any, rng) -> Any:
    """Replace seeded ranges and picks with concrete values, recursively."""
    if isinstance(value, str):
        m = RANGE.match(value)
        return rng.uniform(float(m.group(1)), float(m.group(2))) if m else value
    if isinstance(value, dict):
        if set(value) == {"choice"}:
            return resolve(rng.choice(value["choice"]), rng)
        return {k: resolve(v, rng) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, rng) for v in value]
    return value


def colour(value: Any, i: int = 0) -> tuple[int, int, int]:
    if value is None:
        value = PALETTE[i % len(PALETTE)]
    if isinstance(value, str):
        if value.startswith("#") and len(value) == 7:
            return tuple(int(value[k:k + 2], 16) for k in (1, 3, 5))
        if value in NAMED_COLOURS:
            return NAMED_COLOURS[value]
        raise SystemExit(f"unknown colour {value!r}")
    return tuple(int(v) for v in value)


def make_body(d: dict[str, Any], i: int) -> Body:
    try:
        return Body(name=str(d["name"]), mass=float(d.get("mass", 1.0)), radius=float(d.get("radius", 6)),
                    pos=tuple(float(v) for v in d["pos"]), vel=tuple(float(v) for v in d.get("vel", (0, 0))),
                    colour=colour(d.get("colour"), i), fixed=bool(d.get("fixed", False)),
                    kind=str(d.get("kind", "body")), glow=float(d.get("glow", 0)), trail=int(d.get("trail", 0)),
                    label=bool(d.get("label", False)), horizon=float(d.get("horizon", 0)))
    except KeyError as e:
        raise SystemExit(f"body {d.get('name', i)!r} is missing {e}") from None


def orbit_speed(G: float, mass: float, r: float) -> float:
    return math.sqrt(G * mass / r)


def expand_volley(v: dict[str, Any], rng) -> list[dict[str, Any]]:
    """One launcher, several bodies fired at different angles (degrees above horizontal)."""
    angles = v["angles"]
    if isinstance(angles, dict):                          # {pick: 5, from: [...], include: [45]}
        pool = [a for a in angles["from"] if a not in angles.get("include", [])]
        angles = sorted(angles.get("include", []) + rng.sample(pool, angles["pick"] - len(angles.get("include", []))))
    out = []
    for i, a in enumerate(angles):
        rad = math.radians(a)
        out.append({"name": f"{a:g}°", "mass": v.get("mass", 1), "radius": v.get("radius", 1),
                    "pos": v["from"], "vel": [v["speed"] * math.cos(rad), v["speed"] * math.sin(rad)],
                    "colour": PALETTE[i % len(PALETTE)], "trail": v.get("trail", 600), "label": True})
    return out


def circular_orbits(o: dict[str, Any], G: float) -> list[dict[str, Any]]:
    """Planets on circular orbits around a central body: {around: Sun, mass_centre, planets: [...]}."""
    out = []
    for p in o["planets"]:
        r, phase = float(p["r"]), math.radians(float(p.get("phase", 0)))
        v = orbit_speed(G, float(o["central_mass"]), r)
        out.append({**p, "pos": [r * math.cos(phase), r * math.sin(phase)],
                    "vel": [-v * math.sin(phase), v * math.cos(phase)], "trail": p.get("trail", 120)})
    return out


def load(name_or_path: str, rng) -> Scene:
    raw = yaml.safe_load(scene_path(name_or_path).read_text(encoding="utf-8"))
    data = resolve(raw, rng)
    w = data.get("world", {}) or {}
    ws = WorldSettings(G=float(w.get("G", 0)), softening=float(w.get("softening", 2)),
                       uniform=tuple(w.get("uniform", (0, 0))), drag=float(w.get("drag", 0)),
                       ground=w.get("ground"), merge=bool(w.get("merge", False)),
                       substeps=int(w.get("substeps", 4)), time_scale=float(w.get("time_scale", 1)))
    specs = list(data.get("bodies", []))
    if "orbits" in data:
        specs += circular_orbits(data["orbits"], ws.G)
    if "volley" in data:
        specs += expand_volley(data["volley"], rng)
    bodies = [make_body(d, i) for i, d in enumerate(specs)]
    show = data.get("show", {}) or {}
    params = {"drag": ws.drag, "G": ws.G, **(data.get("params", {}) or {})}
    return Scene(name=str(data.get("name", Path(name_or_path).stem)), hooks=list(data.get("hooks", ["Watch this"])),
                 duration=float(data.get("duration", 30)), world=ws, bodies=bodies,
                 view=data.get("view", {"centre": [0, 0], "width": 1000}),
                 background=str(data.get("background", "stars")), equation=str(show.get("equation", "")),
                 readouts=list(show.get("readouts", [])), sweep=show.get("sweep"),
                 outcomes=list(data.get("outcomes", [])), drama=data.get("drama", {}) or {},
                 music=str(data.get("music", "chill")), params=params)
