"""Blender scene: water pours over planks and pegs into three glasses. Which glass fills first?

Runs inside Blender:

    blender --background --factory-startup --python blender/water.py -- params.json

params: seed, out_dir, frames, fps, width, height, samples, resolution (fluid cells along the
longest side), inflow_frames, render (false = bake and measure only).
Writes out_dir/result.json: per-glass fill timeline, the winner, glass label positions on screen
(0..1), timings; and PNG frames to out_dir/frames/ when rendering.
"""
import colorsys
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
rng = random.Random(ARGS["seed"])
OUT = Path(ARGS["out_dir"])
FRAMES = ARGS.get("frames", 540)
DOMAIN = (4.4, 0.6, 7.8)              # width, depth, height (metres); thin, because we look from the front
GLASS_X = [-1.4, 0.0, 1.4]
GLASS_W, GLASS_H, WALL = 1.05, 2.1, 0.12
SAMPLE_EVERY = 5                      # frames between fill measurements


def clear() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def material(name, colour, emission=0.0, rough=0.4, metal=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Alpha"].default_value = alpha
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = 1.33
    if emission:
        b.inputs["Emission Color"].default_value = (*colour, 1)
        b.inputs["Emission Strength"].default_value = emission
    if alpha < 1 or transmission:
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED" if alpha < 1 else "DITHERED"
    return m


def box(name, centre, size, rot_y=0.0, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    ob.rotation_euler = (0, rot_y, 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        ob.data.materials.append(mat)
    return ob


def collider(ob, thickness=0.0):
    mod = ob.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "EFFECTOR"
    mod.effector_settings.effector_type = "COLLISION"
    if thickness:
        mod.effector_settings.surface_distance = thickness
    return ob


def build() -> dict:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = ARGS.get("width", 1080), ARGS.get("height", 1920)
    scene.render.fps = ARGS.get("fps", 30)
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / "frames" / "f_")
    scene.eevee.taa_render_samples = ARGS.get("samples", 24)
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = "AgX"
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.012, 0.025, 1)

    hue = rng.random()
    wood = material("Plank", colorsys.hsv_to_rgb(hue, 0.85, 0.7), emission=0.3, rough=0.5)
    glass_mat = material("Glass", (0.85, 0.9, 1.0), emission=0.35, rough=0.1, alpha=0.35)
    rim = material("Rim", (0.9, 0.95, 1.0), emission=2.0)
    water = material("Water", (0.01, 0.2, 0.95), emission=0.25, rough=0.04, transmission=0.35)

    W, D, Hd = DOMAIN
    dom = box("Domain", (0, 0, Hd / 2), (W, D, Hd))
    mod = dom.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "LIQUID"
    ds.resolution_max = ARGS.get("resolution", 128)
    ds.use_mesh = True
    ds.cache_type = "ALL"
    ds.cache_directory = str(OUT / "cache")
    ds.cache_frame_start, ds.cache_frame_end = 1, FRAMES
    if hasattr(ds, "use_collision_border_bottom"):
        for side in ("front", "back", "right", "left", "top", "bottom"):
            setattr(ds, f"use_collision_border_{side}", True)
    dom.data.materials.append(water)

    # the three glasses: open-topped U shapes, each a collider
    glasses = []
    for i, gx in enumerate(GLASS_X):
        parts = [box(f"G{i}_floor", (gx, 0, 0.08 + WALL / 2), (GLASS_W, D, WALL), mat=glass_mat),
                 box(f"G{i}_left", (gx - GLASS_W / 2, 0, 0.08 + GLASS_H / 2), (WALL, D, GLASS_H), mat=glass_mat),
                 box(f"G{i}_right", (gx + GLASS_W / 2, 0, 0.08 + GLASS_H / 2), (WALL, D, GLASS_H), mat=glass_mat)]
        for p in parts:
            collider(p)
        box(f"G{i}_rim", (gx, D / 2 + 0.02, 0.08 + GLASS_H), (GLASS_W + WALL, 0.02, 0.04), mat=rim)
        glasses.append({"x0": gx - GLASS_W / 2 + WALL / 2, "x1": gx + GLASS_W / 2 - WALL / 2,
                        "z0": 0.08 + WALL, "z1": 0.08 + GLASS_H})

    # obstacles: angled planks and round pegs, seeded
    for k in range(rng.randint(3, 4)):
        z = 2.6 + k * 1.15 + rng.uniform(-0.2, 0.2)
        x = rng.uniform(-1.3, 1.3)
        ang = math.radians(rng.choice([-1, 1]) * rng.uniform(14, 30))
        collider(box(f"Plank{k}", (x, 0, z), (rng.uniform(1.0, 1.6), D, 0.14), rot_y=ang, mat=wood))
    for k in range(rng.randint(4, 7)):
        bpy.ops.mesh.primitive_cylinder_add(radius=rng.uniform(0.1, 0.16), depth=D,
                                            location=(rng.uniform(-1.8, 1.8), 0, rng.uniform(2.0, 6.0)),
                                            rotation=(math.radians(90), 0, 0))
        peg = bpy.context.object
        peg.data.materials.append(wood)
        collider(peg)

    # the tap
    bpy.ops.mesh.primitive_cylinder_add(radius=ARGS.get("tap_radius", 0.05), depth=0.3,
                                        location=(rng.uniform(-1.1, 1.1), 0, Hd - 0.5))
    inflow = bpy.context.object
    inflow.hide_render = True
    fm = inflow.modifiers.new("Fluid", "FLUID")
    fm.fluid_type = "FLOW"
    fs = fm.flow_settings
    fs.flow_type = "LIQUID"
    fs.flow_behavior = "INFLOW"
    fs.use_initial_velocity = True
    fs.velocity_coord = (0, 0, -1.0)
    stop = ARGS.get("inflow_frames", 240)
    inflow.scale = (1, 1, 1)
    inflow.keyframe_insert("scale", frame=stop)
    inflow.scale = (0.001, 0.001, 0.001)                             # shrinking the tap turns it off
    inflow.keyframe_insert("scale", frame=stop + 1)

    # lights and camera, looking straight at the front
    bpy.ops.object.light_add(type="AREA", location=(0, -6, 6))
    key = bpy.context.object
    key.data.energy, key.data.size = 2500, 8
    key.rotation_euler = (math.radians(60), 0, 0)
    key.visible_glossy = False
    bpy.ops.object.light_add(type="AREA", location=(0, 3, 4))
    back = bpy.context.object
    back.data.energy, back.data.size, back.data.color = 1500, 6, colorsys.hsv_to_rgb(hue + 0.5, 0.5, 1)
    back.rotation_euler = (math.radians(-90), 0, 0)
    bpy.ops.object.camera_add(location=(0, -11.5, Hd / 2 - 0.9), rotation=(math.radians(90), 0, 0))
    cam = bpy.context.object
    cam.data.lens = 36                                               # lower and wider: glasses clear of captions
    scene.camera = cam
    labels = []
    for g in glasses:
        p = world_to_camera_view(scene, cam, Vector(((g["x0"] + g["x1"]) / 2, 0, g["z1"] + 0.35)))
        labels.append([round(p.x, 4), round(1 - p.y, 4)])
    return {"domain": dom, "glasses": glasses, "labels": labels, "tap_x": inflow.location.x}


def bake(dom) -> None:
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        bpy.ops.fluid.bake_all()


def measure(info: dict) -> list[list[float]]:
    """How full each glass is (0..1), every SAMPLE_EVERY frames.

    A grid of probe points fills each glass; the fill is the share of probes inside the liquid
    volume (a ray cast upwards that first hits an upward-facing surface starts inside). A thin
    falling stream covers few probes, so it never reads as a full glass.
    """
    from mathutils.bvhtree import BVHTree
    scene = bpy.context.scene
    dom = info["domain"]
    probes = []
    for g in info["glasses"]:
        pts = [Vector((g["x0"] + (g["x1"] - g["x0"]) * (i + 0.5) / 8, 0.0, g["z0"] + (g["z1"] - g["z0"]) * (j + 0.5) / 14))
               for i in range(8) for j in range(14)]
        probes.append(pts)
    up = Vector((0, 0, 1))
    timeline = []
    for f in range(1, FRAMES + 1, SAMPLE_EVERY):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = dom.evaluated_get(dg)
        if len(ev.data.vertices) < 300:                 # no real liquid yet (or none at all)
            timeline.append([0.0, 0.0, 0.0])
            continue
        tree = BVHTree.FromObject(ev, dg)
        inv = ev.matrix_world.inverted()
        rot = inv.to_3x3()
        row = []
        for pts in probes:
            inside = 0
            for p in pts:
                hit, normal, _, _ = tree.ray_cast(inv @ p, rot @ up)
                if hit is not None and normal.dot(rot @ up) > 0:
                    inside += 1
            row.append(round(inside / len(pts), 3))
        timeline.append(row)
    return timeline


t0 = time.time()
clear()
info = build()
t1 = time.time()
bake(info["domain"])
t2 = time.time()
timeline = measure(info)
t3 = time.time()
FULL = 0.85
full_at = [next((k * SAMPLE_EVERY + 1 for k, row in enumerate(timeline) if row[i] >= FULL), None) for i in range(3)]
done = [f for f in full_at if f is not None]
winner = full_at.index(min(done)) if done else max(range(3), key=lambda i: timeline[-1][i])
result = {"labels": info["labels"], "timeline": timeline, "every": SAMPLE_EVERY, "final": timeline[-1],
          "full_at": full_at, "winner": winner, "frames": FRAMES, "fps": bpy.context.scene.render.fps,
          "build_s": round(t1 - t0, 1), "bake_s": round(t2 - t1, 1), "measure_s": round(t3 - t2, 1)}
(OUT / "frames").mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = ARGS.get("start", 1), ARGS.get("end", FRAMES)
if ARGS.get("render", True):
    bpy.ops.render.render(animation=True)
t4 = time.time()
n = scene.frame_end - scene.frame_start + 1
result.update(render_s=round(t4 - t3, 1), per_frame_s=round((t4 - t3) / n, 2) if ARGS.get("render", True) else 0)
(OUT / "result.json").write_text(json.dumps(result))
