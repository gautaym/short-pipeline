"""Blender scene: a campfire, then a storm. Will the fire survive the wind?

Runs inside Blender:

    blender --background --factory-startup --python blender/fire.py -- params.json

params: seed, out_dir, frames, fps, width, height, samples, resolution, spin_frame (when the
wind starts), wind (strength), render (false = bake and measure only), start/end (frames to render).
Writes out_dir/result.json: flame height (metres) every few frames, the calm and peak heights,
timings; and PNG frames to out_dir/frames/ when rendering.
"""
import colorsys
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
rng = random.Random(ARGS["seed"])
OUT = Path(ARGS["out_dir"])
FRAMES = ARGS.get("frames", 600)
SPIN = ARGS.get("spin_frame", 90)
DOMAIN = (3.6, 3.6, 9.0)
SAMPLE_EVERY = 5
FLAME_ON = 0.05


def clear() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def surface(name, colour, rough=0.6, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    if emission:
        b.inputs["Emission Color"].default_value = (*colour, 1)
        b.inputs["Emission Strength"].default_value = emission
    return m


def fire_material():
    """Smoke from the density grid, light from the flame grid through a fire colour ramp."""
    m = bpy.data.materials.new("Fire")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    info = nt.nodes.new("ShaderNodeAttribute")
    info.attribute_name = "density"
    flame = nt.nodes.new("ShaderNodeAttribute")
    flame.attribute_name = "flame"
    dens = nt.nodes.new("ShaderNodeMath")
    dens.operation = "MULTIPLY"
    dens.inputs[1].default_value = 12.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0, 0, 0, 1)
    els[1].position, els[1].color = 1.0, (1.0, 0.85, 0.45, 1)
    mid = els.new(0.2)
    mid.color = (0.6, 0.05, 0.0, 1)
    mid2 = els.new(0.55)
    mid2.color = (1.0, 0.3, 0.02, 1)
    strength = nt.nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    strength.inputs[1].default_value = 14.0
    nt.links.new(info.outputs["Fac"], dens.inputs[0])
    nt.links.new(dens.outputs[0], vol.inputs["Density"])
    nt.links.new(flame.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], vol.inputs["Emission Color"])
    nt.links.new(flame.outputs["Fac"], strength.inputs[0])
    nt.links.new(strength.outputs[0], vol.inputs["Emission Strength"])
    vol.inputs["Color"].default_value = (0.18, 0.17, 0.17, 1)
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    return m


def build() -> dict:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = ARGS.get("width", 1080), ARGS.get("height", 1920)
    scene.render.fps = ARGS.get("fps", 30)
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / "frames" / "f_")
    ee = scene.eevee
    ee.taa_render_samples = ARGS.get("samples", 24)
    for attr, val in (("volumetric_tile_size", "4"), ("volumetric_samples", 64), ("volumetric_end", 40.0)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    scene.view_settings.view_transform = "AgX"
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.012, 1)

    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    bpy.context.object.data.materials.append(surface("Ground", (0.03, 0.028, 0.03), rough=0.45))

    # logs and stones around the fire
    logm = surface("Log", (0.12, 0.06, 0.03), rough=0.8)
    for k in range(rng.randint(5, 7)):
        a = 2 * math.pi * k / 6 + rng.uniform(-0.3, 0.3)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=1.1, location=(0.25 * math.cos(a), 0.25 * math.sin(a), 0.22),
                                            rotation=(math.radians(65), 0, a + math.pi / 2))
        bpy.context.object.data.materials.append(logm)
    stone = surface("Stone", (0.25, 0.24, 0.23), rough=0.7)
    for k in range(14):
        a = 2 * math.pi * k / 14
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.12, 0.18), location=(0.85 * math.cos(a), 0.85 * math.sin(a), 0.08))
        bpy.context.object.data.materials.append(stone)

    # smoke + fire domain
    W, D, Hd = DOMAIN
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, Hd / 2))
    dom = bpy.context.object
    dom.scale = (W, D, Hd)
    bpy.ops.object.transform_apply(scale=True)
    mod = dom.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "GAS"
    ds.resolution_max = ARGS.get("resolution", 96)
    ds.cache_type = "ALL"
    ds.cache_directory = str(OUT / "cache")
    ds.cache_frame_start, ds.cache_frame_end = 1, FRAMES
    if hasattr(ds, "use_dissolve_smoke"):
        ds.use_dissolve_smoke = True
        ds.dissolve_speed = 40
    if hasattr(ds, "flame_vorticity"):
        ds.flame_vorticity = 0.6
    if hasattr(ds, "vorticity"):
        ds.vorticity = 0.3
    ds.beta = 2.5                                        # hot gas rises harder
    if hasattr(ds, "burning_rate"):
        ds.burning_rate = 0.22                           # flames last longer, so they climb higher
    if hasattr(ds, "flame_smoke"):
        ds.flame_smoke = 0.6

    # the fuel: a disc inside the logs
    bpy.ops.mesh.primitive_cylinder_add(radius=0.55, depth=0.3, location=(0, 0, 0.3))
    src = bpy.context.object
    src.hide_render = True
    fm = src.modifiers.new("Fluid", "FLUID")
    fm.fluid_type = "FLOW"
    fs = fm.flow_settings
    fs.flow_type = "BOTH"
    fs.flow_behavior = "INFLOW"
    fs.fuel_amount = ARGS.get("fuel", 3.0)
    fs.temperature = 4.0
    fs.surface_distance = 0.2
    fs.use_initial_velocity = True
    fs.velocity_coord = (0, 0, 3.0)                      # the fire breathes upwards

    # the storm: a gusting wind from the left that rises after SPIN and dies down near the end
    bpy.ops.object.effector_add(type="WIND", location=(-DOMAIN[0] / 2 - 0.2, 0, 2.0), rotation=(0, math.radians(90), 0))
    wind = bpy.context.object
    strength = ARGS.get("wind", rng.uniform(1.5, 4.5))
    for f in range(1, FRAMES + 1, 5):
        wind.field.strength = strength * wind_level(f)
        wind.field.keyframe_insert("strength", frame=f)
    bpy.ops.object.effector_add(type="TURBULENCE", location=(0, 0, 3))
    turb = bpy.context.object
    turb.field.strength = ARGS.get("turbulence", rng.uniform(0.3, 0.8))
    turb.field.size = 1.0

    # firelight: an orange point light that flickers
    bpy.ops.object.light_add(type="POINT", location=(0, 0, 0.9))
    lamp = bpy.context.object
    lamp.data.color = (1.0, 0.45, 0.12)
    lamp.data.shadow_soft_size = 0.4
    for f in range(1, FRAMES + 1, 3):
        lamp.data.energy = 900 * (1 + 0.35 * math.sin(f * 0.9) * math.sin(f * 0.37)) * (1 + 0.8 * min(1, max(0, (f - SPIN) / 120)))
        lamp.data.keyframe_insert("energy", frame=f)
    bpy.ops.object.light_add(type="AREA", location=(0, 6, 5))
    rim = bpy.context.object
    rim.data.energy, rim.data.size, rim.data.color = 300, 6, (0.4, 0.5, 1.0)
    rim.rotation_euler = (math.radians(-60), 0, 0)

    bpy.ops.object.camera_add(location=(0, -6.2, 1.7), rotation=(math.radians(84), 0, 0))
    cam = bpy.context.object
    cam.data.lens = 28                                   # close and low: the fire fills the frame
    scene.camera = cam
    return {"domain": dom, "strength": strength}


def wind_level(f: int) -> float:
    """0..about 1.35: calm until SPIN, rising for 2 s, gusting, then dying down near the end."""
    calm_end = FRAMES - 120
    if f < SPIN:
        k = 0.0
    elif f < SPIN + 60:
        k = (f - SPIN) / 60
    elif f < calm_end:
        k = 1.0
    else:
        k = max(0.0, 1 - (f - calm_end) / 60)
    return k * (1 + 0.35 * math.sin(f * 0.21) * math.sin(f * 0.077))


def bake(dom) -> None:
    with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
        bpy.ops.fluid.bake_all()


def attach_volume(dom) -> None:
    """Load the baked OpenVDB sequence as a Volume object for rendering.

    Rendering the fluid domain directly shows nothing in this Blender version, while a Volume
    object made from the same cache renders reliably in Eevee. The VDB grid starts at the domain's
    corner, so the volume is moved onto it.
    """
    data = OUT / "cache" / "data"
    files = sorted(p.name for p in data.glob("*.vdb"))
    bpy.ops.object.volume_import(filepath=str(data / files[0]), directory=str(data),
                                 files=[{"name": n} for n in files], relative_path=False)
    vol = bpy.context.object
    vol.data.frame_start = 1
    lo = dom.matrix_world @ Vector(dom.bound_box[0])
    vox = DOMAIN[2] / dom.modifiers["Fluid"].domain_settings.resolution_max
    vol.location = (lo.x + vox / 2, lo.y + vox / 2, lo.z + vox / 2)
    vol.data.materials.append(fire_material())
    dom.hide_render = True


def measure(dom) -> list[float]:
    """Flame height in metres every SAMPLE_EVERY frames: the highest layer with real flame in it."""
    import numpy as np
    scene = bpy.context.scene
    heights = []
    for f in range(1, FRAMES + 1, SAMPLE_EVERY):
        scene.frame_set(f)
        ev = dom.evaluated_get(bpy.context.evaluated_depsgraph_get())   # grids live on the evaluated copy
        ds = ev.modifiers["Fluid"].domain_settings
        grid = np.array(ds.flame_grid)
        res = tuple(ds.domain_resolution)
        if grid.size != res[0] * res[1] * res[2] or grid.size == 0:
            heights.append(0.0)
            continue
        flame = grid.reshape(res[2], res[1], res[0])              # z, y, x
        layers = np.flatnonzero(flame.max(axis=(1, 2)) > FLAME_ON)
        heights.append(round(float((layers[-1] + 1) / res[2] * DOMAIN[2]), 2) if len(layers) else 0.0)
    return heights


t0 = time.time()
clear()
info = build()
t1 = time.time()
bake(info["domain"])
attach_volume(info["domain"])
t2 = time.time()
heights = measure(info["domain"])
t3 = time.time()
calm = max(heights[: max(1, SPIN // SAMPLE_EVERY)] or [0.0])
storm = heights[(SPIN + 60) // SAMPLE_EVERY: (FRAMES - 120) // SAMPLE_EVERY] or [0.0]
result = {"heights": heights, "every": SAMPLE_EVERY, "calm": calm, "peak": max(heights or [0.0]),
          "storm_min": min(storm), "storm_mean": round(sum(storm) / len(storm), 2),
          "wind": [round(wind_level(f), 3) for f in range(1, FRAMES + 1, SAMPLE_EVERY)],
          "spin_frame": SPIN, "strength": round(info["strength"], 2), "frames": FRAMES,
          "fps": bpy.context.scene.render.fps, "build_s": round(t1 - t0, 1), "bake_s": round(t2 - t1, 1),
          "measure_s": round(t3 - t2, 1)}
(OUT / "frames").mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = ARGS.get("start", 1), ARGS.get("end", FRAMES)
if ARGS.get("render", True):
    bpy.ops.render.render(animation=True)
t4 = time.time()
n = scene.frame_end - scene.frame_start + 1
result.update(render_s=round(t4 - t3, 1), per_frame_s=round((t4 - t3) / n, 2) if ARGS.get("render", True) else 0)
(OUT / "result.json").write_text(json.dumps(result))
