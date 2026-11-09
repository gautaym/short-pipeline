"""Blender test shot: the Positive Bhai cold open in 3D chibi with toon shading.

The small, angry uncle stomps down the street waving his stick, the Dost's convertible comes in fast,
BOOM, and the uncle tumbles off into the sky with a twinkle; the camera whips back to the Dost's face.
Toon look: cel-shaded materials (two-tone ramps), inverted-hull outlines, a gradient sky, motion blur.
params style "flat" gives the 2D version: flat colours with no shading, thicker ink lines and an
orthographic (no perspective) camera, like cut-out 2D animation.

    blender --background --factory-startup --python blender/chibi_boom.py -- params.json

params: out_dir, width, height, fps, samples, start/end (frames). Writes out_dir/frames/f_####.png and
out_dir/result.json (frame count, the hit frame).
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
OUT = Path(ARGS["out_dir"])
FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Poppins-ExtraBold.ttf"
FRAMES = 180
FLAT = ARGS.get("style") == "flat"
HIT = 84            # the car meets the uncle
FREEZE = 4          # hit-stop frames
rng = random.Random(7)


def lin(c):
    return tuple((v / 255) ** 2.2 for v in c) + (1.0,)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


# ---------------------------------------------------------------- materials
_mats = {}


def toon(rgb, shadow=0.62, tint=(0.86, 0.84, 1.0)):
    """Cel shading: diffuse light -> two flat tones (lit colour, cool shadow colour)."""
    key = ("toon", rgb, shadow)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"toon_{len(_mats)}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    em = nt.nodes.new("ShaderNodeEmission")
    lit = lin(rgb)
    if FLAT:
        shadow, tint = 1.0, (1.0, 1.0, 1.0)
    dark = tuple(lit[i] * shadow * tint[i] for i in range(3)) + (1.0,)
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    cr.elements[0].position, cr.elements[0].color = 0.0, dark
    cr.elements[1].position, cr.elements[1].color = 0.32, lit
    nt.links.new(dif.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs["Color"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _mats[key] = m
    return m


def flat(rgb, strength=1.0):
    key = ("flat", rgb, strength)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"flat_{len(_mats)}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(rgb)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _mats[key] = m
    return m


INK = None


def outline_mat():
    global INK
    if INK is None:
        INK = bpy.data.materials.new("ink")
        INK.use_nodes = True
        nt = INK.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = lin((34, 22, 30))
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        INK.use_backface_culling = True
    return INK


def finish_obj(o, mat, ink=0.018, smooth=True):
    o.data.materials.append(mat)
    if smooth and o.type == "MESH":
        for p in o.data.polygons:
            p.use_smooth = True
    if ink and o.type == "MESH":
        o.data.materials.append(outline_mat())
        sol = o.modifiers.new("ink", "SOLIDIFY")
        sol.thickness = ink * (1.9 if FLAT else 1.0)
        sol.offset = 1.0
        sol.use_flip_normals = True
        sol.material_offset = 1
        sol.use_rim = False
    return o


# ---------------------------------------------------------------- shapes
def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def _place(o, loc, scale, rot, parent):
    o.parent = parent
    o.location = loc
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # outlines in true metres
    return o


def sph(loc, r, mat, parent=None, rot=(0, 0, 0), ink=0.018):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1)
    o = bpy.context.object
    r = r if isinstance(r, tuple) else (r, r, r)
    _place(o, loc, r, rot, parent)
    return finish_obj(o, mat, ink)


def cyl(loc, r, depth, mat, parent=None, rot=(0, 0, 0), r2=None, ink=0.018):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=depth)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r, radius2=r2, depth=depth)
    o = bpy.context.object
    _place(o, loc, (1, 1, 1), rot, parent)
    return finish_obj(o, mat, ink, smooth=True)


def box(loc, size, mat, parent=None, rot=(0, 0, 0), bevel=0.0, ink=0.018):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    _place(o, loc, size, rot, parent)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, 5
    return finish_obj(o, mat, ink if not bevel else ink, smooth=bool(bevel))


def torus(loc, R, r, mat, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=10)
    o = bpy.context.object
    _place(o, loc, (1, 1, 1), rot, parent)
    return finish_obj(o, mat, 0)


def star(name, pts, r_out, r_in, mat, parent=None, loc=(0, 0, 0), y=0.0):
    """A flat star in the x-z plane (facing the camera)."""
    me = bpy.data.meshes.new(name)
    verts = [(0, y, 0)]
    for k in range(pts * 2):
        a = math.pi * k / pts + math.pi / 2
        rr = (r_out if k % 2 == 0 else r_in) * (0.85 + 0.3 * rng.random())
        verts.append((math.cos(a) * rr, y, math.sin(a) * rr))
    n = len(verts) - 1
    faces = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    o.data.materials.append(mat)
    return o


def text(body, size, mat, parent, loc, back=None):
    font = bpy.data.fonts.load(str(FONT)) if FONT.exists() else None
    objs = []
    for k, (m, off, extra) in enumerate(((mat, 0.0, 0.0), (back, 0.04, 0.035))):
        if m is None:
            continue
        cu = bpy.data.curves.new(f"txt{k}", "FONT")
        cu.body = body
        if font:
            cu.font = font
        cu.size = size
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.extrude = 0.03
        cu.offset = extra
        o = bpy.data.objects.new(f"txt{k}", cu)
        bpy.context.scene.collection.objects.link(o)
        o.parent = parent
        o.location = (loc[0], loc[1] + off, loc[2])
        o.rotation_euler = (math.pi / 2, 0, 0)
        o.data.materials.append(m)
        objs.append(o)
    return objs


# ---------------------------------------------------------------- characters
SKIN_UNCLE, SKIN_DOST = (232, 190, 152), (244, 204, 164)
EYE = (40, 26, 22)


def face(head, r, mood, skin):
    """Big chibi eyes, brows, nose, mouth on the front (-y) of a head of radius r."""
    parts = {}
    eye_m, white = flat(EYE), flat((255, 255, 255))
    for side in (-1, 1):
        ex = side * r * 0.36
        sph((ex, -r * 0.86, -r * 0.02), (r * 0.17, r * 0.09, r * 0.24), eye_m, head, ink=0)
        sph((ex + r * 0.06, -r * 0.94, r * 0.08), r * 0.07, white, head, ink=0)
        sph((ex - r * 0.05, -r * 0.94, -r * 0.1), r * 0.035, white, head, ink=0)
        tilt = 0.38 if mood == "angry" else -0.12
        b = box((ex, -r * 0.86, r * 0.34), (r * 0.26, r * 0.06, r * 0.07), flat(EYE), head, rot=(0, side * -tilt * -1 if side < 0 else -tilt, 0), ink=0)
        if side < 0:
            b.rotation_euler = (0, tilt, 0)
        else:
            b.rotation_euler = (0, -tilt, 0)
        parts[f"brow{side}"] = b
        sph((ex * 1.25, -r * 0.8, -r * 0.3), (r * 0.12, r * 0.04, r * 0.06), flat((248, 150, 150)), head, ink=0)   # blush
    sph((0, -r * 0.97, -r * 0.18), r * 0.08, toon(skin), head, ink=0.008)
    parts["mouth"] = sph((0, -r * 0.9, -r * 0.45), (r * 0.16, r * 0.06, r * 0.1), flat((120, 30, 40)), head, ink=0)
    return parts


def uncle():
    root = empty("uncle")
    hips = empty("u_hips", (0, 0, 0.24), root)
    body = empty("u_body", (0, 0, 0), hips)
    white, cream, shoe = toon((246, 242, 228)), toon((226, 214, 186)), toon((110, 64, 40))
    cyl((0, 0, 0.25), 0.3, 0.52, white, body, r2=0.19)                     # kurta
    legs = []
    for side in (-1, 1):
        lp = empty(f"u_leg{side}", (side * 0.1, 0, 0.02), hips)
        cyl((0, 0, -0.1), 0.065, 0.2, cream, lp)
        sph((0, -0.05, -0.21), (0.08, 0.12, 0.05), shoe, lp)
        legs.append(lp)
    head = empty("u_head", (0, 0, 0.84), body)
    r = 0.34
    skin = toon(SKIN_UNCLE)
    sph((0, 0, 0), r, skin, head)
    for side in (-1, 1):
        sph((side * r * 0.98, 0, -0.02), (0.07, 0.05, 0.09), skin, head)
        sph((side * r * 0.88, 0.06, r * 0.32), (0.1, 0.12, 0.09), toon((236, 236, 240)), head)   # white tufts
    parts = face(head, r, "angry", SKIN_UNCLE)
    specs = toon((70, 46, 30))
    for side in (-1, 1):
        torus((side * r * 0.36, -r * 0.93, 0.0), r * 0.25, 0.011, specs, head, rot=(math.pi / 2, 0, 0))
    cyl((0, -r * 0.95, 0.02), 0.01, r * 0.2, specs, head, rot=(0, math.pi / 2, 0), ink=0)
    for side in (-1, 1):                                                   # mustache
        sph((side * 0.07, -r * 0.93, -r * 0.3), (0.085, 0.035, 0.035), toon((240, 240, 244)), head, rot=(0, side * 0.35, 0))
    arms = []
    for side in (-1, 1):
        sh = empty(f"u_arm{side}", (side * 0.2, 0, 0.44), body)
        cyl((0, 0, -0.14), 0.06, 0.28, white, sh)
        sph((0, 0, -0.3), 0.07, skin, sh)
        arms.append(sh)
    cyl((0, 0, -0.3), 0.022, 0.8, toon((150, 92, 48)), arms[1], rot=(math.pi / 2 * 0.15, 0, 0))   # the stick
    return dict(root=root, hips=hips, body=body, head=head, legs=legs, arms=arms, **parts)


def car():
    root = empty("car")
    blue, dark = toon((70, 140, 236)), toon((40, 38, 46))
    box((0, 0, 0.52), (2.6, 1.3, 0.56), blue, root, bevel=0.22)
    box((0.35, 0, 0.86), (1.2, 1.2, 0.2), blue, root, bevel=0.08)
    box((-0.5, 0, 1.02), (0.06, 1.1, 0.42), toon((190, 230, 250)), root, rot=(0, -0.35, 0), bevel=0.02)   # windscreen
    for side in (-1, 1):
        sph((-1.28, side * 0.38, 0.6), (0.06, 0.13, 0.11), flat((255, 240, 160), 1.4), root, ink=0.01)
    box((-1.32, 0, 0.3), (0.12, 1.36, 0.14), toon((210, 210, 220)), root, bevel=0.05)
    wheels = []
    for wx in (-0.82, 0.82):
        for side in (-1, 1):
            w = empty("wheel", (wx, side * 0.6, 0.3), root)
            w.rotation_euler = (math.pi / 2, 0, 0)
            cyl((0, 0, 0), 0.3, 0.22, dark, w)
            cyl((0, 0, side * -0.1), 0.13, 0.05, toon((200, 200, 210)), w)
            box((0, 0.1, side * -0.12), (0.05, 0.14, 0.02), toon((150, 150, 160)), w, ink=0)
            wheels.append(w)
    # the Dost at the wheel
    shirt = toon((250, 172, 44))
    body = empty("d_body", (0.3, 0, 0.82), root)
    cyl((0, 0, 0.22), 0.27, 0.44, shirt, body, r2=0.2)
    head = empty("d_head", (0, 0, 0.78), body)
    r = 0.36
    sph((0, 0, 0), r, toon(SKIN_DOST), head)
    hair = toon((86, 48, 30))
    sph((0, 0.02, r * 0.42), (r * 1.03, r * 1.02, r * 0.66), hair, head)
    for k in range(6):
        a = -1.2 + k * 0.48
        cyl((math.sin(a) * r * 0.5, 0.05, r * 0.95), 0.1, 0.26, hair, head, rot=(0.15, a * 0.8, 0), r2=0.0)
    for side in (-1, 1):
        sph((side * r * 0.98, 0, -0.02), (0.07, 0.05, 0.09), toon(SKIN_DOST), head)
    parts = face(head, r, "happy", SKIN_DOST)
    for side in (-1, 1):
        sh = empty("d_arm", (side * 0.0 - 0.1, side * 0.24, 0.36), body)
        sh.rotation_euler = (0, -1.25, 0)
        cyl((0, 0, -0.17), 0.065, 0.34, shirt, sh)
        sph((0, 0, -0.36), 0.075, toon(SKIN_DOST), sh)
    torus((-0.55, 0, 1.12), 0.2, 0.03, toon((60, 50, 56)), root, rot=(0, -1.2, 0))
    return dict(root=root, wheels=wheels, head=head, body=body, **parts)


# ---------------------------------------------------------------- the set
def street():
    road = toon((92, 92, 104), shadow=0.7)
    box((0, 0.2, -0.05), (60, 4.0, 0.1), road, ink=0)
    for k in range(-15, 16):
        box((k * 2.0, -0.9, 0.005), (1.0, 0.12, 0.01), flat((250, 250, 240)), ink=0)
    box((0, 3.4, 0.05), (60, 2.4, 0.2), toon((214, 196, 170)), ink=0)
    box((0, -7.0, 0.05), (60, 9.6, 0.2), toon((214, 196, 170)), ink=0)
    for k in range(-30, 31):
        box((k * 1.0, -2.3, 0.152), (0.03, 0.4, 0.004), flat((180, 160, 136)), ink=0)
    pal = [(244, 206, 150), (238, 170, 140), (180, 210, 200), (250, 226, 180), (206, 186, 226), (246, 190, 120)]
    x = -16.0
    k = 0
    while x < 16:
        w = rng.uniform(2.6, 4.0)
        h = rng.uniform(4.5, 9.0)
        c = pal[k % len(pal)]
        box((x + w / 2, 6.4, h / 2), (w - 0.2, 3.0, h), toon(c), ink=0.03)
        for row in range(int(h // 1.4)):
            for col in range(int((w - 0.6) // 0.9)):
                box((x + 0.55 + col * 0.9 + 0.15, 4.88, 1.2 + row * 1.4), (0.5, 0.04, 0.7), toon((150, 200, 236)), ink=0.012)
        box((x + w / 2, 4.86, h + 0.05), (w, 0.3, 0.18), toon(tuple(int(v * 0.8) for v in c)), ink=0.02)
        x += w
        k += 1
    for tx in (-5.5, 2.8, 8.0):                                            # round trees on the far pavement
        cyl((tx, 3.6, 0.7), 0.1, 1.4, toon((120, 76, 44)))
        sph((tx, 3.6, 1.8), 0.75, toon((96, 186, 96)))


def sky(scene):
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = lin((255, 232, 206))
    ramp.color_ramp.elements[1].color = lin((120, 190, 246))
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_lit = nt.nodes.new("ShaderNodeBackground")
    bg_lit.inputs["Color"].default_value = (0.08, 0.08, 0.1, 1)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], bg_cam.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mixs.inputs[0])
    nt.links.new(bg_lit.outputs[0], mixs.inputs[1])
    nt.links.new(bg_cam.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], out.inputs["Surface"])


# ---------------------------------------------------------------- animation
def key(o, path, f, value):
    setattr(o, path, value)
    o.keyframe_insert(path, frame=f)


def clock(f):
    """Story time with the hit-stop: the world freezes for a few frames at the hit."""
    if f <= HIT:
        return f
    if f <= HIT + FREEZE:
        return HIT
    return f - FREEZE


def animate(u, c, cam, tgt, fx):
    wheel_angle = 0.0
    last_cx = None
    flight_end = None
    for f in range(1, FRAMES + 1):
        s = clock(f)
        frozen = HIT < f <= HIT + FREEZE
        # ---- uncle
        if s < HIT:
            ux = -2.7 + 2.4 * (s - 1) / (HIT - 1)
            hop = 0.07 * abs(math.sin(math.pi * s / 7))
            key(u["root"], "location", f, Vector((ux, 0.2, hop)))
            key(u["root"], "rotation_euler", f, Vector((0, 0, 0.55)))
            key(u["root"], "scale", f, Vector((1, 1, 1)))
            key(u["body"], "rotation_euler", f, Vector((0, 0.1 + 0.05 * math.sin(s * 0.45), 0)))
            for k, lp in enumerate(u["legs"]):
                key(lp, "rotation_euler", f, Vector((0, 0.55 * math.sin(math.pi * s / 7 + k * math.pi), 0)))
            key(u["arms"][1], "rotation_euler", f, Vector((0, -2.45 + 0.4 * math.sin(s * 0.75), 0)))
            key(u["arms"][0], "rotation_euler", f, Vector((0, 0.9 + 0.35 * math.sin(s * 0.75 + 1.3), 0)))
            key(u["head"], "rotation_euler", f, Vector((0.06 * math.sin(s * 0.9), 0, 0)))
            key(u["mouth"], "scale", f, Vector((0.34 * 0.16 * 1.2, 0.34 * 0.06, 0.34 * 0.1 * (1.0 + 0.9 * abs(math.sin(s * 0.5))))))
        elif frozen:
            key(u["root"], "scale", f, Vector((0.72, 1, 1.12)))                 # squashed against the bumper
            key(u["mouth"], "scale", f, Vector((0.34 * 0.12, 0.34 * 0.06, 0.34 * 0.22)))
        else:
            q = (s - HIT) / 52
            if q <= 1:
                ux = -0.3 - 2.6 * q
                uy = 0.2 + 10 * q
                uz = 9.5 * (1 - (1 - q) ** 2)
                key(u["root"], "location", f, Vector((ux, uy, uz)))
                key(u["root"], "rotation_euler", f, Vector((q * 2.5, -q * 6 * math.pi, 0.55)))
                sq = 1 + 0.25 * math.exp(-(s - HIT) / 3)
                key(u["root"], "scale", f, Vector((1 / sq, 1, sq)))
                key(u["arms"][1], "rotation_euler", f, Vector((0, -2.9 + 0.6 * math.sin(s * 1.4), 0)))
                key(u["arms"][0], "rotation_euler", f, Vector((0, 2.9 + 0.6 * math.sin(s * 1.4 + 2), 0)))
                for k, lp in enumerate(u["legs"]):
                    key(lp, "rotation_euler", f, Vector((0, 0.9 * math.sin(s * 1.6 + k * math.pi), 0)))
                flight_end = (ux, uy, uz)
            else:
                key(u["root"], "scale", f, Vector((0, 0, 0)))
        # ---- car
        if s < 56:
            cx = 10.0
        elif s <= HIT:
            cx = 10.0 - 8.8 * (s - 56) / (HIT - 56)
        else:
            v = min(1.0, (s - HIT) / 26)
            cx = 1.2 - 2.6 * (1 - (1 - v) ** 2)
        if last_cx is not None and not frozen:
            wheel_angle += (last_cx - cx) / 0.3
        last_cx = cx
        key(c["root"], "location", f, Vector((cx, -0.7, 0.0)))
        squash = 0.9 if frozen else 1.0
        key(c["root"], "scale", f, Vector((squash, 1, 2 - squash)))
        nose = 0.0
        if s > HIT:
            nose = -0.06 * math.exp(-(s - HIT) / 8) * math.cos((s - HIT) * 0.6)
        if 104 < s < 118:
            nose += 0.05 * math.sin((s - 104) / 14 * math.pi)                # the skid stop
        key(c["root"], "rotation_euler", f, Vector((0, nose, 0)))
        for w in c["wheels"]:
            key(w, "rotation_euler", f, Vector((math.pi / 2, wheel_angle, 0)))
        shocked = s >= HIT
        key(c["mouth"], "scale", f, Vector((0.36 * (0.11 if shocked else 0.18), 0.36 * 0.06,
                                             0.36 * (0.2 if shocked else 0.07))))
        key(c["head"], "rotation_euler", f, Vector((-0.35 * ease((s - 120) / 10) if s > 120 else 0.0, 0, 0)))
        # ---- BOOM, smoke, flash, twinkle
        b = fx["boom"]
        if f < HIT:
            bs = 0.0
        else:
            t = f - HIT
            bs = (1.25 * ease(t / 3) - 0.25 * ease((t - 3) / 3)) if t < 30 else max(0.0, 1 - (t - 30) / 5)
        bs *= 0.62
        key(b, "scale", f, Vector((bs, bs, bs)))
        key(b, "rotation_euler", f, Vector((0, 0.08 * math.sin(f * 0.4), 0)))
        for k, p in enumerate(fx["puffs"]):
            t = f - HIT
            ps = 0.0 if t < 0 else max(0.0, (0.75 + 0.3 * (k % 3) / 2) * ease(t / 6) * (1 - ease((t - 25) / 15)))
            key(p, "scale", f, Vector((ps, ps, ps)))
            a = k / len(fx["puffs"]) * 2 * math.pi
            d = 0.35 + 0.8 * ease(max(0, t) / 30)
            key(p, "location", f, Vector((-0.2 + math.cos(a) * d, -0.2 + 0.3 * math.sin(a), 0.6 + math.sin(a) * d * 0.7 + 0.02 * max(0, t))))
        fl = 1.0 if HIT <= f <= HIT + 1 else 0.0
        key(fx["flash"], "scale", f, Vector((fl, fl, fl)))
        tw = fx["twinkle"]
        if flight_end and 137 <= f <= 152:
            t = (f - 137) / 15
            ts = math.sin(t * math.pi) * 1.4
            tw.location = flight_end
            tw.keyframe_insert("location", frame=f)
        else:
            ts = 0.0
        key(tw, "scale", f, Vector((ts, ts, ts)))
        key(tw, "rotation_euler", f, Vector((0, f * 0.15, 0)))
        # ---- camera: follow the uncle, shake on the hit, look up at the flight, whip back to the Dost
        if s < HIT:
            ux_now = -2.7 + 2.4 * (s - 1) / (HIT - 1)
            look = Vector((ux_now + 0.55, 0, 1.1))
            pos = Vector((ux_now + 0.3, -5.6 + 0.4 * s / HIT, 0.7))
        else:
            up = ease((f - (HIT + FREEZE + 4)) / 34)
            back = ease((f - 152) / 10)
            sky_look = Vector((-1.6, 6.0, 7.0))
            ground_look = Vector((0.25, 0, 1.1))
            car_look = Vector((cx + 0.3, -0.7, 1.5))
            look = ground_look.lerp(sky_look, up).lerp(car_look, back)
            pos = Vector((0.0, -5.2, 0.7)).lerp(Vector((-0.4, -7.5, 1.6)), up).lerp(Vector((cx - 0.6, -4.2, 1.8)), back)
        if FLAT:                                                           # look a little down: the road shows as a band
            ground = 1.0 if s < HIT else (1 - up) + up * back
            pos = Vector((pos.x, pos.y, look.z + 1.3 * ground))
        shake = 0.18 * math.exp(-(f - HIT) / 6) if f >= HIT else 0.0
        jitter = Vector((rng.uniform(-1, 1), 0, rng.uniform(-1, 1))) * shake
        key(tgt, "location", f, look + jitter)
        key(cam, "location", f, pos + jitter * 0.4)
        if FLAT:
            if s < HIT:
                zoom = 4.4
            else:
                zoom = 4.4 + (11.0 - 4.4) * up
                zoom += (2.9 - zoom) * back
            cam.data.ortho_scale = zoom
            cam.data.keyframe_insert("ortho_scale", frame=f)


def build():
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = ARGS.get("width", 1080), ARGS.get("height", 1920)
    scene.render.fps = ARGS.get("fps", 30)
    scene.frame_start, scene.frame_end = ARGS.get("start", 1), ARGS.get("end", FRAMES)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / "frames" / "f_")
    scene.eevee.taa_render_samples = ARGS.get("samples", 24)
    scene.render.use_motion_blur = True
    if hasattr(scene.render, "motion_blur_shutter"):
        scene.render.motion_blur_shutter = 0.45
    scene.view_settings.view_transform = "Standard"
    sky(scene)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)

    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    if hasattr(sun, "angle"):
        sun.angle = 0.06
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), math.radians(-28), math.radians(-35))

    street()
    u = uncle()
    c = car()

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 34
    if FLAT:
        cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    tgt = empty("target")
    tr = cam.constraints.new("TRACK_TO")
    tr.target = tgt
    tr.track_axis, tr.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"

    boom = empty("boom", (-0.2, -2.2, 1.35))
    star("burst_out", 12, 1.25, 0.8, flat((255, 214, 60)), boom, y=0.02)
    star("burst_in", 10, 0.95, 0.62, flat((255, 140, 40)), boom, y=0.0)
    text("BOOM!", 0.62, flat((226, 36, 40)), boom, (0, -0.05, -0.02), back=flat((60, 14, 20)))
    puffs = [sph((0, 0, 0), 1.0, toon((240, 236, 244), shadow=0.72), ink=0.012) for _ in range(9)]
    for p in puffs:
        p.scale = (0, 0, 0)
    flash_plane = None
    bpy.ops.mesh.primitive_plane_add(size=4)
    flash_plane = bpy.context.object
    flash_plane.parent = cam
    flash_plane.location = (0, 0, -0.3)
    flash_plane.data.materials.append(flat((255, 252, 236), 2.0))
    tw = empty("twinkle")
    star("twinkle_star", 4, 0.9, 0.18, flat((255, 250, 200), 2.0), tw)
    animate(u, c, cam, tgt, dict(boom=boom, puffs=puffs, flash=flash_plane, twinkle=tw))
    return scene


if __name__ == "__main__":
    sc = build()
    if ARGS.get("stills"):
        for fr in ARGS["stills"]:
            sc.frame_set(fr)
            sc.render.filepath = str(OUT / "stills" / f"f_{fr:04d}.png")
            bpy.ops.render.render(write_still=True)
    elif ARGS.get("render", True):
        bpy.ops.render.render(animation=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps({"frames": FRAMES, "hit": HIT, "freeze": FREEZE}))
