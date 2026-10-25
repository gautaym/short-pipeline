"""The physics engine and scene files."""
import random

import pytest

from reel_engine.physics.scene import load, resolve, scene_names
from reel_engine.physics.world import Body, World, WorldSettings


def test_seeded_ranges_and_choices():
    rng = random.Random(1)
    v = resolve({"a": "1.5..2.5", "b": {"choice": [3, 4]}, "c": ["-8..8", "text"]}, rng)
    assert 1.5 <= v["a"] <= 2.5 and v["b"] in (3, 4) and -8 <= v["c"][0] <= 8 and v["c"][1] == "text"


@pytest.mark.parametrize("name", scene_names())
def test_every_scene_loads_and_runs(name):
    sc = load(name, random.Random(3))
    w = World(sc.bodies, sc.world)
    for _ in range(120):
        w.step(1 / 120)
    assert w.t > 0 and len(sc.hooks) >= 1 and sc.outcomes


def test_orbit_conserves_energy():
    """Leapfrog keeps a two-body orbit's energy steady over several orbits."""
    bodies = [Body("Sun", 1.0, 20, (0, 0), fixed=True), Body("P", 1e-6, 5, (300, 0), (0, 80))]
    w = World(bodies, WorldSettings(G=3_000_000, softening=0.5, substeps=8))
    e0 = w.energy()
    for _ in range(120 * 60):
        w.step(1 / 120)
    assert abs(w.energy() - e0) / abs(e0) < 0.01


def test_black_hole_swallows_and_conserves_momentum():
    bodies = [Body("Hole", 10.0, 10, (0, 0), kind="black_hole", horizon=10),
              Body("Rock", 1.0, 2, (30, 0), (-200, 0))]
    w = World(bodies, WorldSettings(G=0, substeps=4))
    for _ in range(60):
        w.step(1 / 120)
    assert not w.alive[1] and w.events[0].kind == "swallowed"
    assert w.mass[0] == pytest.approx(11.0) and w.vel[0, 0] == pytest.approx(-200 / 11)
