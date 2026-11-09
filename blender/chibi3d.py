"""Chibi 3D kit for Blender scene scripts: toon materials, outlined shapes, rigged chibi characters with
faces (moods, blinks, lip-sync), arm poses, the sets and props of the Positive Bhai skit.

Two looks from one scene: configure(flat=False) gives toon shading (two-tone cel ramps, perspective);
configure(flat=True) gives the 2D look (flat colours, thicker ink, orthographic camera in the director).
Characters are built from primitives with their scale applied, so outlines (inverted hulls) are in metres.
"""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Poppins-ExtraBold.ttf"
FLAT = False
REAL = False            # the "real" look: grown-up proportions, cel shadows, richer colours (2026-11-06)
_mats = {}
_font = None
rng = random.Random(11)


def configure(flat: bool, real: bool = False):
    global FLAT, REAL
    FLAT, REAL = flat, real


def lin(c):
    if REAL:                                   # richer: more saturation, pastels pulled down a little
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c[:3]))
        s = min(1.0, s * 1.35 + (0.04 if s > 0.05 else 0.0))
        v = v * (0.93 if v > 0.8 else 0.98)
        c = tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))
    return tuple((v / 255) ** 2.2 for v in c) + (1.0,)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def backout(u):
    u = min(1.0, max(0.0, u))
    s = 1.6
    u -= 1
    return u * u * ((s + 1) * u + s) + 1


def lerp(a, b, u):
    return a + (b - a) * u


# ---------------------------------------------------------------- materials
def toon(rgb, shadow=0.64, ghost=False):
    if ghost:
        rgb = tuple(int(v + (236 - v) * 0.55) for v in rgb)
    key = ("toon", rgb, shadow)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"toon_{len(_mats)}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    lit = lin(rgb)
    if FLAT and not REAL:
        em.inputs["Color"].default_value = lit
    else:
        dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
        s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        tint = (0.86, 0.84, 1.0)
        sh = (1 - (1 - shadow) * 0.6) if REAL else shadow
        dark = tuple(lit[i] * sh * tint[i] for i in range(3)) + (1.0,)
        cr = ramp.color_ramp
        cr.interpolation = "CONSTANT"
        cr.elements[0].position, cr.elements[0].color = 0.0, dark
        cr.elements[1].position, cr.elements[1].color = (0.16 if REAL else 0.32), lit
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


def stripes(c1, c2, per_m=13.0, shadow=0.64, ghost=False):
    """Horizontal stripes along each part's own z (jail clothes), shaded like toon()."""
    if ghost:
        c1, c2 = (tuple(int(v + (236 - v) * 0.55) for v in c) for c in (c1, c2))
    key = ("stripes", c1, c2, per_m, shadow)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"stripes_{len(_mats)}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation, mul.inputs[1].default_value = "MULTIPLY", per_m
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    band = nt.nodes.new("ShaderNodeValToRGB")
    cr = band.color_ramp
    cr.interpolation = "CONSTANT"
    cr.elements[0].position, cr.elements[0].color = 0.0, lin(c1)
    cr.elements[1].position, cr.elements[1].color = 0.5, lin(c2)
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mul.inputs[0])
    nt.links.new(mul.outputs[0], fr.inputs[0])
    nt.links.new(fr.outputs[0], band.inputs[0])
    if FLAT and not REAL:
        nt.links.new(band.outputs["Color"], em.inputs["Color"])
    else:
        dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
        s2r = nt.nodes.new("ShaderNodeShaderToRGB")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        sh = (1 - (1 - shadow) * 0.6) if REAL else shadow
        r = ramp.color_ramp
        r.interpolation = "CONSTANT"
        r.elements[0].position, r.elements[0].color = 0.0, (sh * 0.86, sh * 0.84, sh, 1.0)
        r.elements[1].position, r.elements[1].color = (0.16 if REAL else 0.32), (1, 1, 1, 1)
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "MULTIPLY"
        nt.links.new(dif.outputs[0], s2r.inputs[0])
        nt.links.new(s2r.outputs["Color"], ramp.inputs[0])
        nt.links.new(band.outputs["Color"], vm.inputs[0])
        nt.links.new(ramp.outputs["Color"], vm.inputs[1])
        nt.links.new(vm.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    _mats[key] = m
    return m


def cloth(c, ghost=False):
    """toon() for an rgb colour, stripes() for a pair of colours."""
    if isinstance(c[0], (tuple, list)):
        return stripes(tuple(c[0]), tuple(c[1]), ghost=ghost)
    return toon(c, ghost=ghost)


def ink_mat():
    if "ink" not in _mats:
        m = bpy.data.materials.new("ink")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = lin((34, 22, 30))
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        m.use_backface_culling = True
        _mats["ink"] = m
    return _mats["ink"]


def _finish(o, mat, ink=0.018, smooth=True):
    o.data.materials.append(mat)
    if o.type == "MESH":
        if smooth:
            for p in o.data.polygons:
                p.use_smooth = True
        if ink:
            o.data.materials.append(ink_mat())
            sol = o.modifiers.new("ink", "SOLIDIFY")
            sol.thickness = ink * (1.9 if FLAT and not REAL else (1.15 if REAL else 1.0))
            sol.offset = 1.0
            sol.use_flip_normals = True
            sol.material_offset = 1
    return o


# ---------------------------------------------------------------- shapes
def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    e.rotation_euler = rot
    return e


def _place(o, loc, scale, rot, parent):
    o.parent = parent
    o.location = loc
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def sph(loc, r, mat, parent=None, rot=(0, 0, 0), ink=0.018, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1)
    o = bpy.context.object
    r = r if isinstance(r, tuple) else (r, r, r)
    _place(o, loc, r, rot, parent)
    return _finish(o, mat, ink)


def cyl(loc, r, depth, mat, parent=None, rot=(0, 0, 0), r2=None, ink=0.018, verts=32):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth)
    o = bpy.context.object
    _place(o, loc, (1, 1, 1), rot, parent)
    return _finish(o, mat, ink)


def box(loc, size, mat, parent=None, rot=(0, 0, 0), bevel=0.0, ink=0.018):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    _place(o, loc, size, rot, parent)
    if bevel:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width, b.segments = bevel, 4
    return _finish(o, mat, ink, smooth=bool(bevel))


def torus(loc, R, r, mat, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=10)
    o = bpy.context.object
    _place(o, loc, (1, 1, 1), rot, parent)
    return _finish(o, mat, 0)


def tube(points, r, mat, parent=None, loc=(0, 0, 0), name="tube"):
    """A thin round line through points (a curve with a bevel): smiles, frowns, strings."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points):
        p.co = (c[0], c[1], c[2], 1)
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    o.data.materials.append(mat)
    return o


def star(name, pts, r_out, r_in, mat, parent=None, loc=(0, 0, 0), y=0.0, jag=0.3):
    """A flat star in the x-z plane (facing the camera)."""
    me = bpy.data.meshes.new(name)
    verts = [(0, y, 0)]
    for k in range(pts * 2):
        a = math.pi * k / pts + math.pi / 2
        rr = (r_out if k % 2 == 0 else r_in) * (1 - jag / 2 + jag * rng.random())
        verts.append((math.cos(a) * rr, y, math.sin(a) * rr))
    n = len(verts) - 1
    me.from_pydata(verts, [], [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)])
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    o.data.materials.append(mat)
    return o


def text(body, size, mat, parent=None, loc=(0, 0, 0), back=None, rot=(math.pi / 2, 0, 0)):
    global _font
    if _font is None and FONT.exists():
        _font = bpy.data.fonts.load(str(FONT))
    objs = []
    for k, (m, off, extra) in enumerate(((mat, 0.0, 0.0), (back, 0.03, size * 0.06))):
        if m is None:
            continue
        cu = bpy.data.curves.new("txt", "FONT")
        cu.body = body
        if _font:
            cu.font = _font
        cu.size = size
        cu.align_x, cu.align_y = "CENTER", "CENTER"
        cu.extrude = size * 0.05
        cu.offset = extra
        o = bpy.data.objects.new("txt", cu)
        bpy.context.scene.collection.objects.link(o)
        o.parent = parent
        o.location = (loc[0], loc[1] + off, loc[2])
        o.rotation_euler = rot
        o.data.materials.append(m)
        objs.append(o)
    return objs


def show(o, k):
    o.scale = (k, k, k)


# ---------------------------------------------------------------- characters
DOST = dict(skin=(244, 204, 164), top=("tee", (250, 172, 44)), legs=(64, 96, 176), shoes=(246, 246, 246),
            hair=("spiky", (86, 48, 30)), R=0.4)
BHAI = dict(skin=(222, 176, 128), top=("kurta", (126, 84, 196)), legs=(216, 202, 172), shoes=(110, 64, 40),
            hair=("neat", (40, 30, 60)), specs=(60, 40, 30), R=0.4)
UNCLE = dict(skin=(232, 190, 152), top=("kurta", (246, 242, 228)), legs=(226, 214, 186), shoes=(110, 64, 40),
             hair=("bald", (236, 236, 240)), specs=(70, 46, 30), mustache=(240, 240, 244), R=0.36, size=0.8)
DADAJI = dict(skin=(226, 182, 140), top=("kurta", (236, 222, 190)), legs=(240, 236, 226), shoes=(90, 60, 40),
              hair=("bald", (236, 236, 240)), specs=(40, 30, 30), mustache=(244, 244, 248), beard=True, R=0.36, size=0.82,
              shawl=(150, 92, 60))
AUNTY = dict(skin=(236, 196, 160), lady=True, saree=(226, 70, 130), border=(250, 200, 60), blouse=(120, 40, 90),
             hair=("bun", (204, 204, 212)), bindi=True, R=0.37, size=0.8)
AUNTY_NEW = dict(AUNTY, saree=(250, 196, 40), border=(220, 40, 90), blouse=(200, 40, 80))
AUNTY_BURNT = dict(AUNTY, skin=(104, 88, 86), saree=(170, 60, 90), border=(110, 90, 50), blouse=(80, 30, 50),
                   hair=("frizzy", (150, 148, 150)))                 # after BHADAAM: soot, frizz
DADI = dict(AUNTY, saree=(160, 40, 64), border=(250, 200, 60), blouse=(50, 130, 96), hair=("bun", (226, 226, 232)))

# arm poses: (out, forward, elbow bend) in radians, one per arm (right, left)
POSES = {
    "rest": ((0.12, 0.05, 0.2), (0.12, 0.05, 0.2)),
    "explain": ((0.35, 0.55, 1.25), (0.12, 0.05, 0.2)),
    "explain2": ((0.4, 0.6, 1.3), (0.4, 0.6, 1.3)),
    "present": ((1.0, 0.35, 0.35), (0.12, 0.05, 0.2)),
    "thumb": ((0.35, 0.25, 2.0), (0.12, 0.05, 0.2)),
    "point": ((1.3, 0.6, 0.1), (0.12, 0.05, 0.2)),
    "chest": ((0.0, 0.45, 2.25), (0.12, 0.05, 0.2)),
    "clutch": ((0.0, 0.5, 2.25), (0.0, 0.5, 2.25)),
    "up": ((2.5, 0.2, 0.35), (2.5, 0.2, 0.35)),
    "shrug": ((0.6, 0.35, 1.7), (0.6, 0.35, 1.7)),
    "scratch": ((1.0, 0.1, 2.75), (0.12, 0.05, 0.2)),
    "wipe": ((0.15, 0.7, 2.6), (0.15, 0.7, 2.6)),
    "hold": ((0.08, 0.95, 1.0), (0.08, 0.95, 1.0)),
    "phone": ((0.35, 0.25, 2.75), (0.12, 0.05, 0.2)),
    "wave": ((2.1, 0.2, 0.9), (0.12, 0.05, 0.2)),
    "fold": ((0.05, 0.55, 1.9), (0.05, 0.55, 1.9)),
    "reach": ((0.9, 0.5, 0.3), (0.12, 0.05, 0.2)),
    "reach_l": ((0.12, 0.05, 0.2), (0.9, 0.5, 0.3)),
    "stick": ((0.25, 0.45, 0.7), (0.12, 0.05, 0.2)),
}


class Rig:
    pass


def face(rig, head, R, spec, ghost):
    eye_m, white = flat((40, 26, 22)), flat((255, 255, 255))
    rig.eyes, rig.plus, rig.brows = [], [], []
    for side in (-1, 1):
        ex = side * R * 0.36
        e = empty("eye", (ex, -R * 0.86, -R * 0.02), head)
        sph((0, 0, 0), (R * 0.16, R * 0.09, R * 0.23), eye_m, e, ink=0)
        sph((R * 0.06, -R * 0.08, R * 0.09), R * 0.065, white, e, ink=0, seg=16)
        sph((-R * 0.05, -R * 0.08, -R * 0.1), R * 0.032, white, e, ink=0, seg=12)
        rig.eyes.append(e)
        pl = empty("plus", (ex, -R * 0.9, -R * 0.02), head)
        box((0, 0, 0), (R * 0.3, R * 0.04, R * 0.07), eye_m, pl, ink=0)
        box((0, 0, 0), (R * 0.07, R * 0.04, R * 0.3), eye_m, pl, ink=0)
        pl.rotation_euler = (0, math.pi / 4, 0)
        show(pl, 0)
        rig.plus.append(pl)
        b = empty("brow", (ex, -R * 0.84, R * 0.36), head)
        box((0, 0, 0), (R * 0.27, R * 0.06, R * 0.065), eye_m, b, bevel=0.01, ink=0)
        rig.brows.append(b)
        sph((ex * 1.28, -R * 0.78, -R * 0.3), (R * 0.12, R * 0.04, R * 0.06), flat((250, 160, 160)), head, ink=0, seg=12)
    sph((0, -R * 0.97, -R * 0.16), R * 0.075, toon(spec["skin"], ghost=ghost), head, ink=0.006, seg=16)
    m = empty("mouth", (0, -R * 0.9, -R * 0.42), head)
    sph((0, 0, 0), (R * 0.17, R * 0.07, R * 0.12), flat((120, 30, 40)), m, ink=0)
    sph((0, -R * 0.02, -R * 0.05), (R * 0.1, R * 0.06, R * 0.05), flat((236, 110, 110)), m, ink=0, seg=12)
    rig.mouth = m
    dark = flat((60, 26, 30))
    arc = [(math.cos(a) * R * 0.17, 0, -math.sin(a) * R * 0.1) for a in [math.pi * (0.12 + 0.76 * k / 10) for k in range(11)]]
    rig.smile = tube(arc, R * 0.022, dark, head, (0, -R * 0.94, -R * 0.36), "smile")
    rig.frown = tube([(x, y, -z - R * 0.1) for x, y, z in arc], R * 0.022, dark, head, (0, -R * 0.94, -R * 0.36), "frown")


def human_face(rig, head, R, spec, ghost):
    """A grown-up face: white eyes with irises, thin brows, a nose, a small mouth (same pivots as the chibi face)."""
    white, iris, hl = flat((250, 248, 244)), flat((52, 32, 24)), flat((255, 255, 255))
    brow_m = flat(tuple(int(v * 0.7) for v in spec["hair"][1]) if spec["hair"][0] != "bald" else (90, 80, 80))
    rig.eyes, rig.plus, rig.brows = [], [], []
    for side in (-1, 1):
        ex = side * R * 0.37
        e = empty("eye", (ex, -R * 0.84, R * 0.02), head)
        sph((0, 0, 0), (R * 0.19, R * 0.07, R * 0.12), white, e, ink=0.004, seg=20)
        sph((0, -R * 0.05, -R * 0.005), (R * 0.095, R * 0.04, R * 0.105), iris, e, ink=0, seg=16)
        sph((R * 0.035, -R * 0.085, R * 0.04), R * 0.028, hl, e, ink=0, seg=10)
        rig.eyes.append(e)
        pl = empty("plus", (ex, -R * 0.9, R * 0.02), head)
        box((0, 0, 0), (R * 0.28, R * 0.04, R * 0.06), iris, pl, ink=0)
        box((0, 0, 0), (R * 0.06, R * 0.04, R * 0.28), iris, pl, ink=0)
        pl.rotation_euler = (0, math.pi / 4, 0)
        show(pl, 0)
        rig.plus.append(pl)
        b = empty("brow", (ex, -R * 0.86, R * 0.36), head)
        box((0, 0, 0), (R * 0.32, R * 0.05, R * 0.055), brow_m, b, bevel=0.004, ink=0)
        rig.brows.append(b)
    skin = toon(spec["skin"], ghost=ghost)
    sph((0, -R * 0.98, -R * 0.22), (R * 0.085, R * 0.12, R * 0.17), skin, head, ink=0.004, seg=16)       # the nose
    m = empty("mouth", (0, -R * 0.9, -R * 0.55), head)
    sph((0, 0, 0), (R * 0.15, R * 0.06, R * 0.09), flat((110, 34, 40)), m, ink=0)
    sph((0, -R * 0.02, -R * 0.04), (R * 0.09, R * 0.05, R * 0.04), flat((220, 110, 110)), m, ink=0, seg=12)
    rig.mouth = m
    dark = flat((96, 40, 40))
    arc = [(math.cos(a) * R * 0.15, 0, -math.sin(a) * R * 0.07) for a in [math.pi * (0.12 + 0.76 * k / 10) for k in range(11)]]
    rig.smile = tube(arc, R * 0.02, dark, head, (0, -R * 0.93, -R * 0.5), "smile")
    rig.frown = tube([(x, y, -z - R * 0.07) for x, y, z in arc], R * 0.02, dark, head, (0, -R * 0.93, -R * 0.5), "frown")


def human(name, spec, ghost=False):
    """The grown-up build: about five heads tall, a neck, knees, thinner limbs, a smaller head (same Rig pivots
    as chibi(), so every pose, face and prop works on both). The head sits where the chibi's face was."""
    rig = Rig()
    rig.spec, rig.ghost = spec, ghost
    R = spec.get("R", 0.4) * 0.375
    f = R / 0.4                                      # for the hair's absolute sizes
    T = lambda c: cloth(c, ghost)
    INK = 0.009
    skin = T(spec["skin"])
    root = empty(name)
    rig.root = root
    hz = 0.72
    rig.hips_z, rig.arm_len = hz, (0.25, 0.24)
    hips = empty("hips", (0, 0, hz), root)
    body = empty("body", (0, 0, 0), hips)
    rig.hips, rig.body = hips, body
    lady = spec.get("lady")
    rig.legs, rig.knees = [], []
    if lady:
        cyl((0, 0, -0.3), 0.27, 0.86, T(spec["saree"]), body, r2=0.17, ink=INK)                 # the saree, to the floor
        torus((0, 0, -0.7), 0.26, 0.022, T(spec["border"]), body)
        cyl((0, 0, 0.27), 0.15, 0.34, T(spec["blouse"]), body, r2=0.17, ink=INK)
        sph((0, 0, 0.43), (0.18, 0.12, 0.08), T(spec["blouse"]), body, ink=INK)
        box((0.02, -0.16, 0.15), (0.1, 0.04, 0.66), T(spec["saree"]), body, rot=(0, 0.62, 0), bevel=0.02, ink=INK)   # the pallu
        box((0.05, -0.183, 0.14), (0.022, 0.012, 0.64), T(spec["border"]), body, rot=(0, 0.62, 0), ink=0)
    else:
        top, col = spec["top"]
        if top in ("kurta", "prison"):
            cyl((0, 0, 0.12), 0.2, 0.66, T(col), body, r2=0.17, ink=INK)                         # to mid-thigh
            if top == "kurta":
                for k in range(3):
                    sph((0, -0.175, 0.4 - k * 0.07), 0.012, flat((250, 240, 220)), body, ink=0, seg=10)
        else:
            cyl((0, 0, 0.04), 0.15, 0.12, T(spec["legs"]), body, ink=INK)
            cyl((0, 0, 0.26), 0.16, 0.38, T(col), body, r2=0.18, ink=INK)
        if spec.get("belly"):
            sph((0, -0.05, 0.22), (0.175, 0.15, 0.17), T(col), body, ink=INK)
        if top == "uniform":
            dk = tuple(int(v * 0.72) for v in col)
            torus((0, -0.01, 0.09), 0.17, 0.024, T((70, 44, 30)), body)                              # the belt
            box((0, -0.19 if spec.get("belly") else -0.17, 0.09), (0.055, 0.02, 0.04), T((230, 186, 70)), body, ink=INK * 0.5)
            for side in (-1, 1):
                box((side * 0.075, -0.168, 0.34), (0.06, 0.014, 0.06), T(dk), body, ink=INK * 0.5)       # pockets
                box((side * 0.15, 0, 0.452), (0.08, 0.07, 0.016), T(dk), body, ink=INK * 0.5)            # epaulettes
            for k in range(3):
                sph((0, -0.177, 0.4 - k * 0.07), 0.01, T((230, 186, 70)), body, ink=0, seg=10)
        if spec.get("number"):
            box((-0.075, -0.176, 0.3), (0.12, 0.012, 0.066), flat((250, 248, 240)), body, ink=INK * 0.5)
            text(spec["number"], 0.045, flat((30, 30, 36)), body, (-0.075, -0.184, 0.3), back=None)
        sph((0, 0, 0.43), (0.2, 0.12, 0.08), T(col), body, ink=INK)
        if spec.get("shawl"):
            torus((0, 0, 0.47), 0.15, 0.05, T(spec["shawl"]), body)
        for side in (-1, 1):
            lp = empty("leg", (side * 0.085, 0, 0.0), hips)
            cyl((0, 0, -0.17), 0.068, 0.36, T(spec["legs"]), lp, r2=0.075, ink=INK)
            kn = empty("knee", (0, 0, -0.34), lp)
            cyl((0, 0, -0.17), 0.05, 0.34, T(spec["legs"]), kn, r2=0.062, ink=INK)
            sph((0, -0.05, -0.355), (0.055, 0.11, 0.04), T(spec["shoes"]), kn, ink=INK)
            rig.legs.append(lp)
            rig.knees.append(kn)
    cyl((0, 0, 0.52), 0.045, 0.1, skin, body, ink=INK)                                            # the neck
    head = empty("head", (0, 0, 0.56 + R * 1.02), body)
    rig.head = head
    rig.head_z = hz + 0.56 + R * 1.02
    sph((0, 0, 0), (R * 0.92, R * 0.95, R * 1.12), skin, head, ink=INK)
    for side in (-1, 1):
        sph((side * R * 0.9, 0.02, -0.02), (0.065 * f, 0.05 * f, 0.1 * f), skin, head, ink=INK * 0.6, seg=16)
    style, hc = spec["hair"]
    H = T(hc)
    cap = ((0, R * 0.12, R * 0.22), (R * 1.0, R * 1.0, R * 1.02))
    if style == "spiky":                                                                   # short and messy
        sph(cap[0], cap[1], H, head, ink=INK)
        for k in range(7):
            a = -1.2 + k * 0.4
            cyl((math.sin(a) * R * 0.7, -R * 0.1, R * 1.05 - abs(a) * 0.12), 0.07 * f, 0.18 * f, H, head,
                rot=(-0.5, a * 0.8, 0), r2=0.0, ink=INK)
    elif style == "neat":
        sph(cap[0], cap[1], H, head, ink=INK)
        sph((-R * 0.2, -R * 0.45, R * 0.86), (R * 0.6, R * 0.35, R * 0.22), H, head, rot=(0, 0.2, 0), ink=INK)
    elif style == "slick":                                                                 # combed back, a quiff in front
        sph(cap[0], cap[1], H, head, ink=INK)
        sph((R * 0.1, -R * 0.5, R * 0.92), (R * 0.62, R * 0.42, R * 0.3), H, head, rot=(0.35, 0.15, 0), ink=INK)
    elif style == "bald":
        for side in (-1, 1):
            sph((side * R * 0.8, 0.06, R * 0.25), (0.07 * f, 0.13 * f, 0.1 * f), H, head, seg=16, ink=INK)
    elif style == "frizzy":
        sph((0, 0.04, R * 0.4), (R * 1.1, R * 1.06, R * 0.85), H, head, ink=INK)
        for k in range(16):
            a = -1.9 + k * (3.8 / 15)
            cyl((math.sin(a) * R * 0.98, 0.06 + 0.1 * f * (k % 2), math.cos(a) * R * 0.95), 0.08 * f, 0.26 * f, H, head,
                rot=(0.3 * (k % 2), a, 0), r2=0.0, ink=INK)
    elif style == "bun":
        sph(cap[0], cap[1], H, head, ink=INK)
        sph((0, R * 0.95, R * 0.0), R * 0.45, H, head, ink=INK)                                   # the bun, at the back
    human_face(rig, head, R, spec, ghost)
    if spec.get("cap"):
        police_cap(head, R, 1.12, spec["cap"], T, INK)
    if spec.get("specs"):
        sp = T(spec["specs"])
        for side in (-1, 1):
            torus((side * R * 0.37, -R * 0.93, R * 0.02), R * 0.24, 0.006, sp, head, rot=(math.pi / 2, 0, 0))
        cyl((0, -R * 0.96, R * 0.04), 0.006, R * 0.2, sp, head, rot=(0, math.pi / 2, 0), ink=0, verts=8)
    if spec.get("mustache"):
        mw, mh = spec.get("mustache_k", (1.0, 1.0))
        for side in (-1, 1):
            sph((side * R * 0.15 * mw, -R * 0.93, -R * 0.38), (R * 0.2 * mw, R * 0.07, R * 0.07 * mh), T(spec["mustache"]), head,
                rot=(0, side * 0.3, 0), seg=16, ink=INK * 0.5)
    if spec.get("beard"):
        sph((0, -R * 0.55, -R * 0.85), (R * 0.5, R * 0.36, R * 0.4), T(spec["mustache"]), head, ink=INK)
    if spec.get("bindi"):
        sph((0, -R * 1.0, R * 0.22), R * 0.05, flat((220, 30, 40)), head, ink=0, seg=12)
    rig.arms = []
    sleeve = T(spec["blouse"] if lady else spec["top"][1])
    long_sleeve = not lady and spec["top"][0] in ("kurta", "prison", "uniform")
    for side in (1, -1):
        sh = empty("shoulder", (side * 0.2, 0, 0.45), body)
        cyl((0, 0, -0.065), 0.05, 0.13, sleeve, sh, ink=INK)
        cyl((0, 0, -0.18), 0.04, 0.14, sleeve if long_sleeve else skin, sh, ink=INK)
        el = empty("elbow", (0, 0, -0.25), sh)
        cyl((0, 0, -0.11), 0.036, 0.22, sleeve if long_sleeve else skin, el, r2=0.04, ink=INK)
        hand = empty("hand", (0, 0, -0.26), el)
        sph((0, 0, 0), (0.04, 0.03, 0.055), skin, hand, seg=16, ink=INK)
        sph((side * -0.03, -0.03, 0.02), (0.015, 0.015, 0.03), skin, hand, rot=(0.3, 0, 0), seg=10, ink=INK * 0.5)
        rig.arms.append((sh, el, hand, side))
    if ghost:
        torus((0, 0.05, R * 1.35), R * 0.55, 0.02, flat((255, 210, 60), 1.4), head, rot=(0.25, 0, 0))
        if not lady:
            for lp in rig.legs:
                show(lp, 0)
            cyl((0, 0, -0.32), 0.17, 0.64, toon((240, 244, 255)), hips, r2=0.03, rot=(math.pi, 0, 0), ink=INK)
    rig.R = R
    rig.root.scale = (spec.get("size", 1.0),) * 3
    return rig


def police_cap(head, R, top, col, T, ink):
    """A peaked uniform cap: crown, dark band, brim and a plain star."""
    ht = R * top
    cyl((0, R * 0.04, ht * 0.84), R * 0.96, ht * 0.42, T(col), head, rot=(-0.12, 0, 0), r2=R * 1.12, ink=ink)
    cyl((0, R * 0.02, ht * 0.62), R * 1.0, R * 0.17, T((60, 46, 40)), head, rot=(-0.12, 0, 0), ink=ink)
    sph((0, -R * 0.82, ht * 0.5), (R * 0.72, R * 0.42, R * 0.05), T((40, 34, 32)), head, rot=(0.3, 0, 0), ink=ink * 0.7)
    star("cap_star", 5, R * 0.17, R * 0.07, flat((240, 196, 70)), head, (0, -R * 1.04, ht * 0.78), jag=0.0)


def chibi(name, spec, ghost=False):
    """Build a chibi character standing at the origin, facing -y. Returns a Rig of its pivots and face."""
    if REAL:
        return human(name, spec, ghost)
    rig = Rig()
    rig.hips_z, rig.arm_len, rig.knees = 0.27, (0.2, 0.24), []
    rig.spec, rig.ghost = spec, ghost
    R = spec.get("R", 0.4)
    T = lambda c: cloth(c, ghost)
    skin = T(spec["skin"])
    root = empty(name)
    rig.root = root
    hips_z = 0.27
    hips = empty("hips", (0, 0, hips_z), root)
    body = empty("body", (0, 0, 0), hips)
    rig.hips, rig.body = hips, body
    lady = spec.get("lady")
    rig.legs = []
    if lady:
        cyl((0, 0, 0.12 - hips_z + 0.2), 0.38, 0.6, T(spec["saree"]), body, r2=0.24)              # the saree skirt
        torus((0, 0, 0.12 - hips_z - 0.06), 0.37, 0.028, T(spec["border"]), body)
        sph((0, 0, 0.3), (0.27, 0.22, 0.27), T(spec["blouse"]), body)
        box((0.02, -0.2, 0.22), (0.14, 0.05, 0.62), T(spec["saree"]), body, rot=(0, 0.62, 0), bevel=0.04)   # the pallu
        box((0.06, -0.235, 0.2), (0.03, 0.02, 0.6), T(spec["border"]), body, rot=(0, 0.62, 0), ink=0)
    else:
        top, col = spec["top"]
        sph((0, 0, 0.3), (0.3, 0.25, 0.33), T(col), body)
        if spec.get("belly"):
            sph((0, -0.06, 0.22), (0.27, 0.24, 0.24), T(col), body)
        if top in ("kurta", "prison"):
            cyl((0, 0, -0.04), 0.3, 0.26, T(col), body, r2=0.27)
            if top == "kurta":
                for k in range(3):
                    sph((0, -0.25, 0.42 - k * 0.1), 0.018, flat((250, 240, 220)), body, ink=0, seg=10)
        if top == "uniform":
            dk = tuple(int(v * 0.72) for v in col)
            fy = -0.3 if spec.get("belly") else -0.215
            torus((0, -0.03 if spec.get("belly") else 0, 0.1), 0.27 if spec.get("belly") else 0.25, 0.035, T((70, 44, 30)), body)
            box((0, fy, 0.1), (0.09, 0.03, 0.065), T((230, 186, 70)), body, ink=0.012)
            for side in (-1, 1):
                box((side * 0.12, -0.235, 0.4), (0.085, 0.02, 0.08), T(dk), body, rot=(0.25, 0, side * 0.35), ink=0.01)
                box((side * 0.2, 0, 0.6), (0.12, 0.1, 0.025), T(dk), body, rot=(0, side * 0.5, 0), ink=0.01)
        if top == "shirt":                                  # school shirt: a collar, buttons, a tie (spec "tie")
            fy = -0.3 if spec.get("belly") else -0.235
            for side in (-1, 1):
                box((side * 0.07, fy + 0.01, 0.55), (0.11, 0.03, 0.06), T(col), body, rot=(0.2, 0, side * -0.5), ink=0.01)
            if spec.get("tie"):
                tie = T(spec["tie"])
                box((0, fy - 0.005, 0.53), (0.055, 0.03, 0.05), tie, body, ink=0.01)
                box((0, fy - 0.005, 0.38), (0.07, 0.025, 0.26), tie, body, bevel=0.01, ink=0.01)
                for k in range(3):
                    box((0, fy - 0.022, 0.46 - k * 0.07), (0.072, 0.004, 0.018), flat((236, 190, 70)), body, ink=0)
        if spec.get("number"):
            box((-0.11, -0.235, 0.36), (0.17, 0.02, 0.1), flat((250, 248, 240)), body, rot=(0.3, 0, 0.3), ink=0.01)
            text(spec["number"], 0.065, flat((30, 30, 36)), body, (-0.112, -0.25, 0.36), back=None,
                 rot=(math.pi / 2 + 0.3, 0, 0.3))
        if spec.get("shawl"):
            torus((0, 0, 0.5), 0.24, 0.07, T(spec["shawl"]), body)
        for side in (-1, 1):
            lp = empty("leg", (side * 0.11, 0, 0.0), hips)
            cyl((0, 0, -0.12), 0.075, 0.24, T(spec["legs"]), lp)
            sph((0, -0.05, -0.25), (0.085, 0.13, 0.055), T(spec["shoes"]), lp)
            rig.legs.append(lp)
    head = empty("head", (0, 0, 0.58 + R * 0.92), body)
    rig.head = head
    sph((0, 0, 0), R, skin, head)
    for side in (-1, 1):
        sph((side * R * 0.98, 0.02, -0.02), (0.065, 0.05, 0.085), skin, head, seg=16)
    style, hc = spec["hair"]
    H = T(hc)
    if style == "spiky":
        sph((0, 0.08, R * 0.52), (R * 1.03, R * 0.98, R * 0.6), H, head)
        for k in range(7):                                                                  # spikes on top
            a = -1.3 + k * 0.43
            cyl((math.sin(a) * R * 0.62, 0.1, R * 0.98 - abs(a) * 0.05), 0.13, 0.36, H, head, rot=(0.25, a * 0.85, 0), r2=0.0)
        for k in range(3):                                                                  # a spiky fringe
            cyl((-R * 0.25 + k * R * 0.25, -R * 0.62, R * 0.62), 0.09, 0.22, H, head, rot=(1.0, (k - 1) * 0.4, 0), r2=0.0)
    elif style == "neat":
        sph((0, 0.08, R * 0.5), (R * 1.04, R * 1.0, R * 0.62), H, head)
        sph((-R * 0.3, -R * 0.62, R * 0.6), (R * 0.42, R * 0.2, R * 0.2), H, head, rot=(0, 0.35, 0))
    elif style == "slick":
        sph((0, 0.08, R * 0.5), (R * 1.04, R * 1.0, R * 0.62), H, head)
        sph((R * 0.12, -R * 0.55, R * 0.78), (R * 0.6, R * 0.4, R * 0.32), H, head, rot=(0.4, 0.2, 0))
    elif style == "bald":
        for side in (-1, 1):
            sph((side * R * 0.86, 0.08, R * 0.3), (0.1, 0.13, 0.09), H, head, seg=16)
    elif style == "frizzy":                                                               # blown-up hair
        sph((0, 0.04, R * 0.42), (R * 1.08, R * 1.06, R * 0.74), H, head)
        for k in range(16):
            a = -1.9 + k * (3.8 / 15)
            cyl((math.sin(a) * R * 0.95, 0.06 + 0.1 * (k % 2), math.cos(a) * R * 0.9), 0.1, 0.3, H, head,
                rot=(0.3 * (k % 2), a, 0), r2=0.0)
    elif style == "plaits":                                                               # two oiled plaits with ribbons
        sph((0, 0.06, R * 0.42), (R * 1.04, R * 1.02, R * 0.7), H, head)
        sph((0, -R * 0.6, R * 0.62), (R * 0.75, R * 0.25, R * 0.22), H, head)
        rib = T(spec.get("ribbon", (230, 40, 60)))
        for side in (-1, 1):
            for k in range(4):
                sph((side * R * 0.95, 0.12, -R * 0.15 - k * R * 0.24), R * (0.17 - k * 0.012), H, head, seg=16)
            sph((side * R * 0.95, 0.12, -R * 1.1), (R * 0.2, R * 0.12, R * 0.12), rib, head, seg=16)
    elif style == "bun":
        sph((0, 0.04, R * 0.36), (R * 1.04, R * 1.04, R * 0.72), H, head)
        sph((R * 0.88, 0.12, R * 0.22), R * 0.36, H, head)                                   # the side bun
        torus((R * 0.72, 0.1, R * 0.22), R * 0.17, 0.02, T(spec["saree"]), head, rot=(0, math.pi / 2, 0))
    face(rig, head, R, spec, ghost)
    if spec.get("cap"):
        police_cap(head, R, 1.0, spec["cap"], T, 0.018)
    if spec.get("specs"):
        sp = T(spec["specs"])
        for side in (-1, 1):
            torus((side * R * 0.36, -R * 0.93, 0.0), R * 0.25, 0.012, sp, head, rot=(math.pi / 2, 0, 0))
        cyl((0, -R * 0.96, 0.02), 0.011, R * 0.22, sp, head, rot=(0, math.pi / 2, 0), ink=0, verts=8)
    if spec.get("mustache"):
        mw, mh = spec.get("mustache_k", (1.0, 1.0))
        for side in (-1, 1):
            sph((side * 0.07 * mw, -R * 0.93, -R * 0.28), (0.085 * mw, 0.035, 0.035 * mh), T(spec["mustache"]), head,
                rot=(0, side * 0.35, 0), seg=16)
    if spec.get("beard"):
        sph((0, -R * 0.62, -R * 0.78), (R * 0.42, R * 0.3, R * 0.3), T(spec["mustache"]), head)
    if spec.get("bindi"):
        sph((0, -R * 0.97, R * 0.2), R * 0.045, flat((220, 30, 40)), head, ink=0, seg=12)
    rig.arms = []
    sleeve = T(spec["blouse"] if lady else spec["top"][1])
    for side in (1, -1):                                                                     # right first
        sh = empty("shoulder", (side * 0.26, 0, 0.47), body)
        cyl((0, 0, -0.1), 0.068, 0.2, sleeve, sh)
        el = empty("elbow", (0, 0, -0.2), sh)
        cyl((0, 0, -0.1), 0.06, 0.2, skin if lady else sleeve, el)
        hand = empty("hand", (0, 0, -0.24), el)
        sph((0, 0, 0), 0.08, skin, hand, seg=20)
        sph((side * -0.05, -0.06, 0.02), (0.03, 0.03, 0.05), skin, hand, rot=(0.3, 0, 0), seg=12)
        rig.arms.append((sh, el, hand, side))
    if ghost:
        torus((0, 0.05, R * 1.25), R * 0.5, 0.03, flat((255, 210, 60), 1.4), head, rot=(0.25, 0, 0))
        if not lady:
            for lp in rig.legs:
                show(lp, 0)
            cyl((0, 0, -0.12), 0.25, 0.3, toon((240, 244, 255)), hips, r2=0.03, rot=(math.pi, 0, 0))
    rig.R = R
    rig.head_z = 0.27 + 0.58 + R * 0.92
    rig.root.scale = (spec.get("size", 1.0),) * 3
    return rig


def pose_arms(rig, right, left):
    """Set each arm from (out, forward, bend)."""
    for (sh, el, hand, side), (out, fwd, bend) in zip(rig.arms, (right, left)):
        sh.rotation_euler = (-fwd, -side * out, 0)
        el.rotation_euler = (-bend, 0, 0)


def blend_pose(a, b, u):
    return tuple(tuple(lerp(a[i][j], b[i][j], u) for j in range(3)) for i in range(2))


BROW = {"happy": (0.12, 0.0), "goofy": (0.22, 0.05), "sad": (-0.4, 0.02), "shock": (0.0, 0.08), "angry": (0.42, -0.03),
        "dead": (0.0, 0.0), "fear": (-0.3, 0.07), "laugh": (0.2, 0.04), "innocent": (-0.32, 0.06), "smirk": (0.1, 0.0)}


def set_face(rig, mood, talk=0.0, blink=False):
    R = rig.R
    rig.smile.rotation_euler = (0, 0, 0)
    rig.smile.location.x = 0.0
    if mood == "deadpan":                                  # gag-anime blank stare: dot eyes, flat brows, a flat line
        for k, e in enumerate(rig.eyes):
            e.scale = (0.34, 1, 0.34)
            show(rig.plus[k], 0)
        for b in rig.brows:
            b.rotation_euler = (0, 0, 0)
            b.location.z = R * 0.3
        rig.mouth.scale = (0, 0, 0)
        show(rig.smile, 0)
        rig.frown.scale = (0.7, 1, 0.08)
        return
    dead = mood == "dead"
    for k, e in enumerate(rig.eyes):
        big = 1.22 if mood in ("shock", "fear") else 1.0
        z = 0.1 if blink and not dead else (0.82 if mood == "sad" else 1.0)
        e.scale = (0, 0, 0) if dead else (big, 1, big * z)
        show(rig.plus[k], 1 if dead else 0)
    tilt, up = BROW.get(mood, (0.1, 0.0))
    for k, b in enumerate(rig.brows):
        side = -1 if k == 0 else 1
        b.rotation_euler = (0, side * tilt * -1 if side < 0 else -tilt, 0)
        b.rotation_euler = (0, tilt if side < 0 else -tilt, 0)
        b.location.z = R * 0.36 + up * R
    talking = talk > 0.08
    if talking:
        rig.mouth.scale = (1.0, 1, 0.25 + 1.15 * talk)
    elif mood in ("shock", "fear"):
        rig.mouth.scale = (0.7, 1, 0.9)
    elif mood in ("goofy", "laugh"):
        rig.mouth.scale = (1.15, 1, 0.55)
    else:
        rig.mouth.scale = (0, 0, 0)
    smile = not talking and mood in ("happy", "goofy", "laugh", "innocent", "smirk")
    show(rig.smile, (1.25 if mood == "goofy" else 1.0) if smile and mood != "goofy" else 0)
    if mood == "smirk":                                    # one brow up, lids half down, a crooked half-smile
        for k, e in enumerate(rig.eyes):
            e.scale = (1, 1, 0.1 if blink else 0.62)
        rig.brows[0].location.z = R * 0.48
        rig.brows[0].rotation_euler = (0, -0.15, 0)
        rig.brows[1].rotation_euler = (0, -0.3, 0)
        if not talking:
            rig.smile.scale = (0.75, 1, 1.1)
            rig.smile.rotation_euler = (0, -0.35, 0)
            rig.smile.location.x = R * 0.1
    show(rig.frown, 0.8 if not talking and mood in ("sad", "dead", "angry") else 0)


# ---------------------------------------------------------------- props
def car(x0, parent_name="car"):
    root = empty(parent_name, (x0, 0, 0))
    blue, dark = toon((70, 140, 236)), toon((40, 38, 46))
    box((0, 0, 0.52), (2.6, 1.3, 0.56), blue, root, bevel=0.22)
    box((0.35, 0, 0.86), (1.2, 1.2, 0.2), blue, root, bevel=0.08)
    box((-0.5, 0, 1.02), (0.06, 1.1, 0.42), toon((190, 230, 250)), root, rot=(0, -0.35, 0), bevel=0.02)
    for side in (-1, 1):
        sph((-1.28, side * 0.38, 0.6), (0.06, 0.13, 0.11), flat((255, 240, 160), 1.4), root, ink=0.01)
    box((-1.32, 0, 0.3), (0.12, 1.36, 0.14), toon((210, 210, 220)), root, bevel=0.05)
    wheels = []
    for wx in (-0.82, 0.82):
        for side in (-1, 1):
            w = empty("wheel", (wx, side * 0.6, 0.3), root, rot=(math.pi / 2, 0, 0))
            cyl((0, 0, 0), 0.3, 0.22, dark, w)
            cyl((0, 0, side * -0.1), 0.13, 0.05, toon((200, 200, 210)), w)
            box((0, 0.1, side * -0.12), (0.05, 0.14, 0.02), toon((150, 150, 160)), w, ink=0)
            wheels.append(w)
    torus((-0.55, 0, 1.12), 0.2, 0.03, toon((60, 50, 56)), root, rot=(0, -1.2, 0))
    return root, wheels


def patakhe_box(parent):
    b = empty("patakhe", (0, -0.42, 0.3), parent)
    box((0, 0, 0), (0.46, 0.26, 0.3), toon((222, 40, 44)), b, bevel=0.02)
    text("PATAKHE", 0.085, flat((255, 220, 60)), b, (0, -0.14, 0.0))
    for k in range(4):
        cyl((-0.15 + k * 0.1, 0, 0.21), 0.03, 0.14, toon((250, 200, 60)), b, ink=0.008)
        cyl((-0.15 + k * 0.1, 0, 0.3), 0.006, 0.06, flat((60, 40, 30)), b, ink=0, verts=6)
    return b


def phone(head, R, side=-1):
    """A phone held at one ear (side -1: the left, -x; parented to the head, so it stays there)."""
    p = empty("phone", (side * R * 0.97, -R * 0.34, -R * 0.24), head, rot=(0.12, 0, side * -0.55))
    box((0, 0, 0), (0.1, 0.04, 0.21), toon((44, 44, 56)), p, bevel=0.014, ink=0.012)
    box((0, -0.023, 0.07), (0.04, 0.006, 0.012), flat((150, 150, 170)), p, ink=0)
    return p


def backdrop(name, path, cam):
    """A mood background (an image) on a plane that follows the camera, set behind the characters."""
    img = bpy.data.images.load(path)
    m = bpy.data.materials.new("bd_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.object
    o.name = "bd_" + name
    o.parent = cam
    o.location = (0, 0, -5)
    o.data.materials.append(m)
    show(o, 0)
    return o


def pale_lines(head, R):
    """Blue lines down the forehead: the face going pale."""
    e = empty("pale", (0, -R * 1.02, R * 0.4), head)
    for k in range(5):
        box(((k - 2) * R * 0.13, 0, -abs(k - 2) * R * 0.04), (R * 0.035, R * 0.02, R * 0.34), flat((110, 100, 210)), e, ink=0)
    show(e, 0)
    return e


def anger_vein(head, R, side=1):
    """The throbbing anger mark on the forehead."""
    e = empty("vein", (side * R * 0.48, -R * 1.04, R * 0.5), head)
    red = flat((226, 36, 50))
    for sx, sz in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        tube([(sx * R * 0.03, 0, sz * R * 0.13), (sx * R * 0.06, 0, sz * R * 0.06), (sx * R * 0.13, 0, sz * R * 0.03)], R * 0.028, red, e)
    show(e, 0)
    return e


def saree_bundle(parent):
    """The folded new saree, held out in front."""
    b = empty("bundle", (0, -0.4, 0.28), parent)
    box((0, 0, 0), (0.44, 0.24, 0.14), toon((250, 196, 40)), b, bevel=0.03)
    for z in (-0.045, 0.045):
        box((0, -0.122, z), (0.44, 0.01, 0.018), flat((220, 40, 90)), b, ink=0)
    box((0, -0.124, 0), (0.05, 0.012, 0.15), flat((200, 30, 60)), b, ink=0)
    return b


def reach(rig, arm, target, pole=(1.0, 0.2, -0.6)):
    """Two-bone IK: put the hand of arm (0 right, 1 left) at target, in the body's space."""
    sh, el, hand, side = rig.arms[arm]
    S, T = Vector(sh.location), Vector(target)
    a, b = getattr(rig, "arm_len", (0.2, 0.24))
    d = T - S
    dist = min(max(d.length, 0.05), a + b - 0.002)
    dv = d.normalized()
    A = math.acos(max(-1.0, min(1.0, (a * a + dist * dist - b * b) / (2 * a * dist))))
    p = Vector(pole)
    pp = (p - p.dot(dv) * dv).normalized()
    E = S + a * (math.cos(A) * dv + math.sin(A) * pp)
    u1, u2 = (E - S).normalized(), (S + dv * dist - E).normalized()
    q1 = u1.to_track_quat("-Z", "Y")
    sh.rotation_euler = q1.to_euler("XYZ")
    el.rotation_euler = (q1.inverted() @ u2).to_track_quat("-Z", "Y").to_euler("XYZ")


def vision_board(loc):
    root = empty("vboard", loc)
    box((0, 0, 0), (1.3, 0.06, 0.9), toon((196, 140, 90)), root, bevel=0.02)
    box((0, -0.035, 0), (1.18, 0.02, 0.78), toon((222, 180, 130)), root, ink=0)
    cols = [(255, 236, 120), (150, 220, 255), (255, 170, 200), (180, 240, 170), (255, 200, 120)]
    for k in range(6):
        x, z = -0.4 + (k % 3) * 0.4, 0.17 - (k // 3) * 0.34
        box((x, -0.05, z), (0.26, 0.01, 0.22), flat(cols[k % 5]), root, rot=(0, rng.uniform(-0.15, 0.15), 0), ink=0.006)
        sph((x, -0.07, z + 0.1), 0.025, flat((220, 40, 40)), root, ink=0, seg=10)
    tube([(-0.4, -0.08, 0.27), (0.0, -0.08, -0.07), (0.4, -0.08, 0.27), (0.0, -0.08, -0.07), (-0.4, -0.08, -0.07)], 0.006,
         flat((220, 40, 40)), root)
    text("VISION BOARD", 0.13, flat((255, 255, 255)), root, (0, -0.06, 0.55), back=flat((60, 30, 40)))
    return root


def boom_burst(loc):
    b = empty("boom", loc)
    star("burst_out", 12, 1.25, 0.8, flat((255, 214, 60)), b, y=0.02)
    star("burst_in", 10, 0.95, 0.62, flat((255, 140, 40)), b, y=0.0)
    text("BOOM!", 0.62, flat((226, 36, 40)), b, (0, -0.05, -0.02), back=flat((60, 14, 20)))
    return b


class Pool:
    """A set of small objects placed procedurally each frame (sparks, smoke, sparkles); unused ones hide."""

    def __init__(self, make, n):
        self.objs = [make(k) for k in range(n)]

    def place(self, items):
        for k, o in enumerate(self.objs):
            if k < len(items):
                (x, y, z), s = items[k]
                o.location = (x, y, z)
                show(o, s)
            else:
                show(o, 0)


# ---------------------------------------------------------------- sets
def ground(x0, w, colour, y0=-6, y1=4, z=0.0):
    box((x0, (y0 + y1) / 2, z - 0.05), (w, y1 - y0, 0.1), toon(colour, shadow=0.75), ink=0)


def courtyard(x0=0.0):
    ground(x0, 14, (232, 214, 186))
    for k in range(-7, 8):
        box((x0 + k * 0.9, -1.0, 0.002), (0.02, 10, 0.004), flat((210, 190, 160)), ink=0)
    for k in range(-4, 4):
        box((x0, -0.45 * k - 0.4, 0.002), (14, 0.02, 0.004), flat((210, 190, 160)), ink=0)
    box((x0, 1.7, 2.0), (14, 0.3, 4.0), toon((248, 222, 160)), ink=0.03)                      # the house wall
    box((x0, 1.53, 0.12), (14, 0.06, 0.24), toon((200, 120, 80)), ink=0.02)                   # skirting
    box((x0, 1.5, 1.05), (1.0, 0.12, 2.1), toon((150, 92, 56)), bevel=0.03)                     # door
    box((x0, 1.46, 1.05), (0.84, 0.06, 1.92), toon((176, 110, 66)), ink=0.012)
    sph((x0 + 0.3, 1.4, 1.0), 0.04, toon((250, 210, 80)), ink=0.008, seg=12)
    box((x0, 1.47, 2.2), (1.3, 0.14, 0.16), toon((236, 100, 80)), bevel=0.02)                  # toran above the door
    for k in range(9):
        cyl((x0 - 0.56 + k * 0.14, 1.4, 2.08), 0.035, 0.12, toon((90, 170, 70) if k % 2 else (250, 160, 40)), ink=0.006, r2=0.0,
            rot=(math.pi, 0, 0))
    for wx in (-2.1, 2.1):
        box((x0 + wx, 1.52, 1.55), (1.0, 0.1, 1.1), toon((150, 205, 236)), ink=0.02)
        box((x0 + wx, 1.47, 1.55), (1.1, 0.06, 0.06), toon((80, 150, 110)), ink=0.012)
        box((x0 + wx, 1.47, 1.55), (0.06, 0.06, 1.1), toon((80, 150, 110)), ink=0.012)
        for sx in (-0.68, 0.68):
            box((x0 + wx + sx, 1.45, 1.55), (0.3, 0.06, 1.15), toon((80, 150, 110)), bevel=0.02)
    for px in (-1.45, 1.45):                                                                 # pots with plants
        cyl((x0 + px, 1.0, 0.22), 0.24, 0.44, toon((200, 100, 60)), r2=0.18)
        sph((x0 + px, 1.0, 0.68), (0.36, 0.3, 0.32), toon((90, 176, 90)))
        sph((x0 + px + 0.15, 0.9, 0.86), 0.18, toon((110, 196, 100)))
    bulbs = [(255, 190, 60), (255, 120, 150), (120, 220, 255), (255, 240, 120)]
    pts = [(x0 - 3.5 + k * 0.25, 1.35, 2.75 - 0.25 * math.sin(math.pi * ((k % 14) / 14))) for k in range(29)]
    tube(pts, 0.008, flat((60, 50, 40)))
    for k, p in enumerate(pts):
        if k % 2 == 0:
            sph((p[0], p[1] - 0.02, p[2] - 0.06), 0.045, flat(bulbs[(k // 2) % 4], 2.2), ink=0, seg=12)
    rc = [(240, 60, 90), (255, 190, 40), (60, 170, 220), (250, 250, 250), (140, 60, 200)]
    for k, r in enumerate((0.7, 0.55, 0.42, 0.28, 0.14)):                                   # rangoli
        cyl((x0, -1.0, 0.004 + k * 0.002), r, 0.004, flat(rc[k]), ink=0, verts=48)
    for k in range(8):
        a = k * math.pi / 4
        sph((x0 + math.cos(a) * 0.62, -1.0 + math.sin(a) * 0.62, 0.012), (0.09, 0.09, 0.006), flat(rc[(k + 2) % 5]), ink=0, seg=12)
    diya(x0, -1.0)


def diya(x, y, s=1.0):
    cyl((x, y, 0.04 * s), 0.08 * s, 0.07 * s, toon((200, 100, 50)), r2=0.05 * s, rot=(math.pi, 0, 0), ink=0.008)
    sph((x, y, 0.12 * s), (0.025 * s, 0.025 * s, 0.05 * s), flat((255, 200, 60), 3.0), ink=0, seg=12)


def street(x0):
    road = toon((92, 92, 104), shadow=0.7)
    box((x0, 0.2, -0.05), (60, 4.0, 0.1), road, ink=0)
    for k in range(-15, 16):
        box((x0 + k * 2.0, -0.9, 0.005), (1.0, 0.12, 0.01), flat((250, 250, 240)), ink=0)
    box((x0, 3.4, 0.05), (60, 2.4, 0.2), toon((214, 196, 170)), ink=0)
    box((x0, -7.0, 0.05), (60, 9.6, 0.2), toon((214, 196, 170)), ink=0)
    for k in range(-30, 31):
        box((x0 + k * 1.0, -2.3, 0.152), (0.03, 0.4, 0.004), flat((180, 160, 136)), ink=0)
    pal = [(244, 206, 150), (238, 170, 140), (180, 210, 200), (250, 226, 180), (206, 186, 226), (246, 190, 120)]
    x = x0 - 16.0
    k = 0
    while x < x0 + 16:
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
    for tx in (-5.5, 2.8, 8.0):
        cyl((x0 + tx, 3.6, 0.7), 0.1, 1.4, toon((120, 76, 44)))
        sph((x0 + tx, 3.6, 1.8), 0.75, toon((96, 186, 96)))


def gate_house(x0):
    """The aunty's house front: a pink wall, a green gate, marigolds and diyas."""
    ground(x0, 14, (206, 196, 180))
    box((x0, 1.7, 1.6), (14, 0.3, 3.2), toon((246, 186, 196)), ink=0.03)
    box((x0, 1.52, 3.1), (14, 0.08, 0.14), toon((200, 120, 140)), ink=0.02)
    for wx in (-1.9, 1.9):
        box((x0 + wx, 1.52, 1.7), (0.9, 0.1, 0.9), toon((150, 205, 236)), ink=0.02)
        box((x0 + wx, 1.46, 1.22), (1.1, 0.14, 0.08), toon((255, 250, 240)), ink=0.012)
    box((x0 + 0.95, 1.4, 0.75), (1.4, 0.06, 1.5), toon((70, 150, 110)), ink=0.02)               # the gate
    for k in range(7):
        cyl((x0 + 0.35 + k * 0.2, 1.36, 0.75), 0.02, 1.4, toon((40, 100, 70)), ink=0.006, verts=8)
    for k in range(17):                                                                       # marigold string
        a = k / 16
        sph((x0 - 3 + a * 6, 1.45, 2.9 - 0.3 * math.sin(math.pi * a * 2) ** 2), 0.06, toon((255, 150, 30) if k % 2 else (255, 200, 40)),
            ink=0.008, seg=12)
    for dx in (-1.2, -0.9, 1.9, 2.2):
        diya(x0 + dx, 1.2)
    cyl((x0 - 2.6, 1.1, 0.25), 0.22, 0.5, toon((200, 100, 60)), r2=0.16)
    sph((x0 - 2.6, 1.1, 0.75), (0.3, 0.25, 0.3), toon((90, 176, 90)))


def cloud(x, y, z, s, mat):
    for dx, dz, r in ((0, 0, 0.5), (0.5, -0.08, 0.38), (-0.5, -0.08, 0.4), (0.25, 0.22, 0.36), (-0.25, 0.18, 0.34), (0.85, -0.15, 0.25),
                      (-0.85, -0.15, 0.26)):
        sph((x + dx * s, y, z + dz * s), (r * s, r * s * 0.8, r * s * 0.8), mat, ink=0.02)


def heaven(x0):
    """Clouds and golden rays, for the reunion."""
    white = toon((255, 255, 255), shadow=0.86)
    cloud(x0, 0.0, 0.0, 1.5, white)
    for cx, cy, cz, s in ((-2.2, 3.0, 1.0, 1.2), (2.4, 3.5, 2.2, 1.4), (-1.0, 5.0, 3.4, 1.6), (1.5, 2.0, -0.4, 1.0), (-2.6, 1.5, -0.6, 1.1)):
        cloud(x0 + cx, cy, cz, s, white)
    rays = empty("rays", (x0, 4.0, 1.4))
    for k in range(14):
        a = k * math.pi / 7
        box((math.cos(a) * 3, 0, math.sin(a) * 3), (6, 0.02, 0.5), flat((255, 236, 170), 1.1), rays, rot=(0, -a, 0), ink=0)
    return rays


def park(x0):
    ground(x0, 14, (130, 196, 110), y0=-6, y1=8)
    box((x0, 5.5, 1.0), (14, 0.3, 2.0), toon((200, 170, 150)), ink=0.03)
    for tx, ty, s in ((-2.0, 3.0, 1.2), (2.4, 3.6, 1.4), (0.2, 4.6, 1.0)):
        cyl((x0 + tx, ty, 0.8 * s), 0.12 * s, 1.6 * s, toon((120, 76, 44)))
        sph((x0 + tx, ty, 2.0 * s), 0.9 * s, toon((86, 170, 90)))
        sph((x0 + tx + 0.4 * s, ty - 0.1, 1.7 * s), 0.6 * s, toon((100, 186, 96)))
    box((x0, 0.35, 0.45), (1.6, 0.45, 0.08), toon((150, 96, 56)), bevel=0.02)                  # bench seat
    box((x0, 0.58, 0.8), (1.6, 0.08, 0.5), toon((150, 96, 56)), bevel=0.02)
    for bx in (-0.7, 0.7):
        box((x0 + bx, 0.35, 0.22), (0.08, 0.4, 0.44), toon((70, 60, 60)), ink=0.012)
    cyl((x0 + 1.4, 0.8, 1.3), 0.05, 2.6, toon((60, 60, 70)))
    sph((x0 + 1.4, 0.8, 2.65), 0.16, flat((255, 236, 170), 1.5), ink=0.012)


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


def setup_render(scene, width, height, fps, samples, out_pattern):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.fps = fps
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = out_pattern
    scene.eevee.taa_render_samples = samples
    scene.render.use_motion_blur = True
    if hasattr(scene.render, "motion_blur_shutter"):
        scene.render.motion_blur_shutter = 0.4
    if hasattr(scene.render, "motion_blur_position"):
        scene.render.motion_blur_position = "START"
    scene.view_settings.view_transform = "Standard"
    sky(scene)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    if hasattr(sun, "angle"):
        sun.angle = 0.06
    if REAL:
        sun.use_shadow = False                       # cast shadows speckle the small faces; the cel ramp gives form
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), math.radians(-28), math.radians(-35))
