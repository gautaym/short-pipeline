"""Blender scene: a wrecking ball swings into a tower of glowing blocks (rigid-body physics, Eevee).

Runs inside Blender, not in the reel_engine venv:

    blender --background --factory-startup --python blender/tower.py -- params.json

params.json: {"seed": 1, "out_dir": "...", "frames": 600, "fps": 30, "width": 1080, "height": 1920,
              "samples": 32, "start": 1, "end": 600}
Writes PNG frames to out_dir/frames/ and out_dir/result.json (how many blocks fell, hit frames).
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
rng = random.Random(ARGS["seed"])
OUT = Path(ARGS["out_dir"])
FRAMES = ARGS.get("frames", 600)


def clear() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            block.remove(item)


def material(name, colour, emission=0.0, rough=0.35, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*colour, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return m


def hsv(h, s, v):
    import colorsys
    return colorsys.hsv_to_rgb(h % 1, s, v)


def build() -> dict:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = ARGS.get("width", 1080), ARGS.get("height", 1920)
    scene.render.fps = ARGS.get("fps", 30)
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / "frames" / "f_")
    eevee = scene.eevee
    eevee.taa_render_samples = ARGS.get("samples", 32)
    if hasattr(eevee, "use_raytracing"):
        eevee.use_raytracing = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy" if "AgX - Punchy" in [i.identifier for i in
                                                                    scene.view_settings.bl_rna.properties["look"].enum_items] else "None"

    world = bpy.data.worlds.new("World") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.014, 0.03, 1)
    bg.inputs["Strength"].default_value = 1.0

    bpy.ops.rigidbody.world_add()
    rbw = scene.rigidbody_world
    rbw.substeps_per_frame = 10
    rbw.solver_iterations = 20
    rbw.point_cache.frame_start, rbw.point_cache.frame_end = 1, FRAMES

    # ground
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    ground = bpy.context.object
    ground.data.materials.append(material("Ground", (0.02, 0.022, 0.035), rough=0.32, metal=0.0))
    bpy.ops.rigidbody.object_add(type="PASSIVE")
    ground.rigid_body.friction = 0.8

    # tower of blocks
    size = 0.5
    base, levels = rng.choice([4, 5]), rng.randint(12, 16)
    hue0 = rng.random()
    mats = [material(f"B{k}", hsv(hue0 + 0.07 * k, 0.9, 0.85), emission=0.25, rough=0.28) for k in range(8)]
    blocks = []
    bpy.ops.mesh.primitive_cube_add(size=size * 0.96)
    proto = bpy.context.object
    proto_mesh = proto.data
    bpy.data.objects.remove(proto)
    for z in range(levels):
        for i in range(base):
            for j in range(base):
                if 0 < i < base - 1 and 0 < j < base - 1:
                    continue                                     # hollow inside: fewer bodies, same look
                ob = bpy.data.objects.new(f"blk_{z}_{i}_{j}", proto_mesh.copy())
                scene.collection.objects.link(ob)
                ob.location = ((i - (base - 1) / 2) * size, (j - (base - 1) / 2) * size, size / 2 + z * size * 0.985)
                ob.data.materials.append(mats[(z * 8 // levels) % 8])
                bpy.context.view_layer.objects.active = ob
                ob.select_set(True)
                bpy.ops.rigidbody.object_add(type="ACTIVE")
                ob.rigid_body.mass = 0.6
                ob.rigid_body.friction = 0.7
                ob.rigid_body.use_deactivation = True
                ob.rigid_body.use_start_deactivated = True
                ob.select_set(False)
                blocks.append(ob)

    # wrecking ball: kinematic, swinging on a pendulum through the tower
    top = levels * size
    pivot = Vector((0, 0, top + rng.uniform(3.0, 4.5)))
    length = pivot.z - top * rng.uniform(0.45, 0.7)
    side = rng.choice([-1, 1])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.9, 1.2), segments=48, ring_count=24)
    ball = bpy.context.object
    bpy.ops.object.shade_smooth()
    ball.data.materials.append(material("Steel", (0.95, 0.55, 0.25), emission=0.15, rough=0.22, metal=1.0))
    bpy.ops.rigidbody.object_add(type="ACTIVE")
    ball.rigid_body.kinematic = True
    ball.rigid_body.mass = 50
    swing_start = ARGS.get("swing_start", 75)
    half = rng.uniform(55, 70)                                        # frames per half swing
    amp = math.radians(rng.uniform(60, 75))
    hits = []
    prev = None
    for f in range(1, FRAMES + 1):
        k = max(0.0, (f - swing_start) / half)
        a = side * amp * math.cos(math.pi * k) * (0.82 ** k)          # a damped pendulum
        x = math.sin(a)
        if prev is not None and f > swing_start and (prev > 0) != (x > 0):
            hits.append(f)                                            # passing through the tower
        prev = x
        if f % 2 == 1 or f == FRAMES:
            ball.location = pivot + Vector((x * length, 0, -math.cos(a) * length))
            ball.keyframe_insert("location", frame=f)
    # chain: a thin rod from the pivot to the ball, keyed alongside the ball
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=1, vertices=16)
    chain = bpy.context.object
    chain.data.materials.append(material("Chain", (0.5, 0.5, 0.55), rough=0.35, metal=1.0))
    for f in range(1, FRAMES + 1, 2):
        scene.frame_set(f)
        bpos = ball.location.copy()
        d = bpos - pivot
        chain.location = pivot + d / 2
        chain.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        chain.scale = (1, 1, d.length)
        chain.keyframe_insert("location", frame=f)
        chain.keyframe_insert("rotation_euler", frame=f)
        chain.keyframe_insert("scale", frame=f)

    # lights
    bpy.ops.object.light_add(type="AREA", location=(6, -6, top + 4))
    key = bpy.context.object
    key.data.energy, key.data.size = 3000, 6
    key.rotation_euler = (math.radians(50), 0, math.radians(45))
    key.visible_glossy = False                                       # no light-panel reflection on the floor
    bpy.ops.object.light_add(type="AREA", location=(-6, 4, 3))
    fill = bpy.context.object
    fill.data.energy, fill.data.size, fill.data.color = 900, 8, (0.5, 0.6, 1.0)
    fill.rotation_euler = (math.radians(70), 0, math.radians(-120))
    fill.visible_glossy = False
    bpy.ops.object.light_add(type="POINT", location=(0, 0, 0.6))
    under = bpy.context.object                                       # coloured bounce light from the floor
    under.data.energy, under.data.color, under.data.shadow_soft_size = 400, hsv(hue0 + 0.5, 0.6, 1.0), 2

    # camera: slow orbit, framed tall
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.lens = 32
    scene.camera = cam
    target = bpy.data.objects.new("CamTarget", None)
    scene.collection.objects.link(target)
    target.location = (0, 0, top * 0.45)
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    radius, h = top * 1.0 + 5, top * 0.5 + 1.2
    a0 = math.radians(rng.uniform(-40, -10)) + (0 if side < 0 else math.pi)
    for f in range(1, FRAMES + 1, 10):
        a = a0 + math.radians(35) * f / FRAMES
        cam.location = (math.cos(a) * radius, math.sin(a) * radius, h)
        cam.keyframe_insert("location", frame=f)
    return {"blocks": blocks, "ball": ball, "hits": hits, "levels": levels, "base": base}


def bake_and_measure(info: dict) -> dict:
    scene = bpy.context.scene
    start = {b.name: b.matrix_world.translation.copy() for b in info["blocks"]}
    with bpy.context.temp_override(scene=scene, point_cache=scene.rigidbody_world.point_cache):
        bpy.ops.ptcache.bake(bake=True)
    scene.frame_set(FRAMES)
    fell = sum(1 for b in info["blocks"] if (b.matrix_world.translation - start[b.name]).length > 0.4)
    return {"blocks": len(info["blocks"]), "fell": fell, "levels": info["levels"], "hits": info["hits"],
            "frames": FRAMES, "fps": scene.render.fps}


import time

t0 = time.time()
clear()
info = build()
t1 = time.time()
result = bake_and_measure(info)
t2 = time.time()
(OUT / "frames").mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = ARGS.get("start", 1), ARGS.get("end", FRAMES)
if ARGS.get("render", True):
    bpy.ops.render.render(animation=True)
t3 = time.time()
n = scene.frame_end - scene.frame_start + 1
result.update(build_s=round(t1 - t0, 1), bake_s=round(t2 - t1, 1), render_s=round(t3 - t2, 1),
              per_frame_s=round((t3 - t2) / n, 2))
(OUT / "result.json").write_text(json.dumps(result))
