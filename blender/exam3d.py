"""Maths Test (a silent classroom skit) in Blender: five students and the teacher in the 2D chibi look.

    blender --background --factory-startup --python blender/exam3d.py -- params.json

params (written by reel_engine/toon/maths_test.py): out_dir, mode ("lineup" or "scene"), width, height, fps,
samples, frames, beats {name: seconds}, plates {front, back: png}, papers {bunty, golu: png}, optional stills.

Two cameras share one set. The front camera looks at the students (the back wall behind them); the reverse camera
looks from behind the students at Madam and the board. Whatever would block the shot (the board plate, Madam, the
back wall) is hidden for that camera. Characters move on twos; the camera moves on ones.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chibi3d as K  # noqa: E402

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
OUT = Path(ARGS["out_dir"])
K.configure(True)
FPS = ARGS.get("fps", 30)

SHIRT, TIE, PANT, SHOE = (246, 246, 240), (40, 56, 120), (96, 100, 112), (34, 30, 30)
SCHOOL = dict(top=("shirt", SHIRT), tie=TIE, legs=PANT, shoes=SHOE)

BUNTY = dict(SCHOOL, skin=(222, 172, 122), hair=("spiky", (36, 26, 22)), R=0.41)                  # the "psst" one
GOLU = dict(SCHOOL, skin=(240, 198, 156), hair=("neat", (54, 36, 26)), belly=True, R=0.44, size=1.04)  # his chubby friend
PINKY = dict(SCHOOL, skin=(236, 190, 150), legs=(70, 80, 130), hair=("plaits", (28, 22, 24)), specs=(150, 40, 60),
             ribbon=(230, 50, 80), R=0.4, size=0.96)                                          # the topper
SONU = dict(SCHOOL, skin=(200, 150, 108), hair=("slick", (30, 26, 26)), R=0.4)                   # the sleepy one
CHINTU = dict(SCHOOL, skin=(232, 186, 140), hair=("frizzy", (60, 40, 30)), R=0.39, size=0.94)    # the nervous one
MADAM = dict(skin=(214, 166, 124), lady=True, saree=(40, 120, 110), border=(236, 180, 60), blouse=(150, 40, 60),
             hair=("bun", (26, 22, 24)), specs=(40, 30, 30), bindi=True, R=0.39, size=1.12)       # the teacher
CAST = [("madam", MADAM), ("bunty", BUNTY), ("golu", GOLU), ("pinky", PINKY), ("sonu", SONU), ("chintu", CHINTU)]

EYE_K = 1.3                       # bigger eyes than the kit's default (2026-11-08 direction)
# seats: (x, y, z); the back row sits on a riser so their heads show between the front row's
SEAT = {"pinky": (-1.05, 0.0, 0.0), "bunty": (0.0, 0.0, 0.0), "golu": (1.05, 0.0, 0.0),
        "sonu": (-0.55, 1.3, 0.42), "chintu": (0.55, 1.3, 0.42)}
MADAM_AT = (-1.95, -2.6, 0.0)     # at the front, beside the board, clear of the rows in the reverse shots
DESK_TOP = 0.66
HELD = (0.3 * 1.15, 0.413 * 1.15, 1)


def ruler(rig):
    """A wooden ruler in the teacher's right hand."""
    hand = rig.arms[0][2]
    r = K.empty("ruler", (0, -0.02, 0), hand, rot=(0, math.pi - 0.25, 0))
    K.box((0, 0, 0.2), (0.07, 0.015, 0.5), K.toon((214, 170, 96)), r, bevel=0.005, ink=0.01)
    for k in range(9):
        K.box((-0.025, -0.009, 0.0 + k * 0.05), (0.02, 0.002, 0.004), K.flat((70, 50, 30)), r, ink=0)
    return r


def eyes(rig, look=(0.0, 0.0), k=EYE_K):
    """Bigger eyes, and the eyes looking somewhere: look = (sideways, up), each about -1..1 (sideways is the
    character's own left/right as the camera sees it)."""
    if not hasattr(rig, "eye_home"):
        rig.eye_home = [tuple(e.location) for e in rig.eyes]
    R = rig.R
    for e, (x, y, z) in zip(rig.eyes, rig.eye_home):
        e.scale = (e.scale[0] * k, e.scale[1], e.scale[2] * k)
        e.location = (x + look[0] * R * 0.13, y, z + look[1] * R * 0.1)


# ================================================================ lineup (the look check)
def lineup():
    sc = bpy.context.scene
    K.setup_render(sc, ARGS.get("width", 2160), ARGS.get("height", 1080), 30, ARGS.get("samples", 32),
                   str(OUT / "lineup.png"))
    sc.render.use_motion_blur = False
    K.box((0, 1.5, 1.5), (14, 0.1, 5), K.flat((236, 222, 170)), ink=0)
    K.ground(0, 14, (170, 172, 176))
    poses = {"madam": ("stick", "angry", 0.1), "bunty": ("point", "smirk", -0.1), "golu": ("fold", "laugh", 0.0),
             "pinky": ("chest", "happy", 0.0), "sonu": ("rest", "deadpan", 0.05), "chintu": ("clutch", "fear", -0.05)}
    for k, (name, spec) in enumerate(CAST):
        rig = K.chibi(name, spec)
        rig.root.location = ((k - 2.5) * 1.02, 0, 0)
        pose, mood, yaw = poses[name]
        rig.root.rotation_euler = (0, 0, yaw)
        K.pose_arms(rig, *K.POSES[pose])
        K.set_face(rig, mood)
        eyes(rig)
        if name == "madam":
            ruler(rig)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.ortho_scale = 6.6
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (0, -12, 1.2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.render.render(write_still=True)


# ================================================================ the scene
B = ARGS.get("beats", {})


def textured(name, path, size, emit=True):
    """A plane showing a picture (emission, so it reads at full brightness), size = (width, height) in metres."""
    img = bpy.data.images.load(path)
    m = bpy.data.materials.new("m_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(m)
    o.scale = (size[0], size[1], 1)
    return o


def plate(name, path, x0, y, ph, z0, flip):
    """A painted wall (896 x 1600) on a plane, drawn 1.6x larger with its edge pixels repeated."""
    pw = ph * 896 / 1600
    o = textured("plate_" + name, path, (pw * 1.6, ph * 1.6))
    nt = o.data.materials[0].node_tree
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.6, 1.6, 1)
    mp.inputs["Location"].default_value = (-0.3, -0.3, 0)
    nt.links.new(tc.outputs["UV"], mp.inputs[0])
    nt.links.new(mp.outputs[0], tex.inputs[0])
    o.rotation_euler = (math.pi / 2, 0, math.pi if flip else 0)
    o.location = (x0, y, z0 + ph / 2)
    return o


def desk(x, y, z):
    wood, dark = K.toon((196, 140, 84)), K.toon((150, 100, 60))
    K.box((x, y - 0.36, z + DESK_TOP - 0.03), (0.92, 0.56, 0.06), wood, bevel=0.01, ink=0.012)
    K.box((x, y - 0.63, z + DESK_TOP / 2 - 0.03), (0.92, 0.03, DESK_TOP - 0.06), dark, ink=0.012)


def build():
    sc = bpy.context.scene
    K.setup_render(sc, ARGS.get("width", 1080), ARGS.get("height", 1920), FPS, ARGS.get("samples", 16),
                   str(OUT / "frames" / "f_"))
    sc.render.use_motion_blur = False
    sc.frame_start, sc.frame_end = 1, ARGS["frames"]
    W = {}
    P = ARGS["plates"]
    W["back"] = plate("back", P["back"], 0.0, 3.2, 7.6, -1.19, False)
    W["front"] = plate("front", P["front"], -0.75, -3.9, 6.4, -0.55, True)
    for name, spec in CAST:
        W[name] = K.chibi(name, spec)
    W["ruler"] = ruler(W["madam"])
    W["vein"] = K.anger_vein(W["madam"].head, W["madam"].R, 1)
    for who, (x, y, z) in SEAT.items():
        desk(x, y, z)
        r = W[who]
        R, hc = r.R, r.spec["hair"][1]
        K.sph((0, R * 0.32, R * 0.02), (R * 0.98, R * 0.72, R * 0.86), K.cloth(hc), r.head)   # hair at the back
        r.root.location = (x, y, z)
        r.root.rotation_euler = (0, 0, 0)
        for lp in r.legs:
            lp.rotation_euler = (math.pi / 2.2, 0, 0)          # sitting: thighs forward, under the desk
    pw, ph = 0.3, 0.413
    W["paper"] = {}
    for who in SEAT:
        src = ARGS["papers"].get(who, ARGS["papers"]["blank"])
        p = textured("paper_" + who, src, (pw, ph))
        x, y, z = SEAT[who]
        p.location = (x + 0.05, y - 0.4, z + DESK_TOP + 0.005)
        p.rotation_euler = (0.55, 0, 0.0)
        W["paper"][who] = p
    for who in ("bunty", "golu"):                               # the sheet held up to show the friend
        p = textured("held_" + who, ARGS["papers"][who], (pw * 1.15, ph * 1.15))
        p.parent = W[who].body
        p.rotation_euler = (math.pi / 2, 0, 0)
        K.show(p, 0)
        W["held_" + who] = p
    W["sweat"] = K.Pool(lambda k: K.sph((0, 0, 0), (0.045, 0.03, 0.075), K.flat((140, 200, 255)), ink=0.008, seg=12), 6)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "VERTICAL"
    cam_data.clip_end = 100
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    W["cam"] = cam
    return W


# ---------------------------------------------------------------- helpers
def seg(t):
    """(name, seconds into it, its length) of the beat t falls in."""
    names = sorted(B, key=B.get)
    cur = names[0]
    for n in names:
        if B[n] <= t:
            cur = n
    nxt = [B[n] for n in names if B[n] > B[cur]]
    return cur, t - B[cur], (nxt[0] if nxt else B[cur] + 5) - B[cur]


def blink(t, ph, per=3.1):
    return ((t + ph) % per) < 0.11


def clamp01(u):
    return min(1.0, max(0.0, u))


def write_hands(rig, t, speed, ph, on=True):
    """Both hands on the desk, the right one scribbling."""
    s = rig.spec.get("size", 1.0)
    wob = (0.03 * math.sin(t * speed + ph), 0.015 * math.sin(t * speed * 1.7 + ph)) if on else (0, 0)
    K.reach(rig, 0, (0.13 + wob[0], -0.36 + wob[1], 0.36 / s + 0.05), (1, 0, -1))
    K.reach(rig, 1, (-0.16, -0.34, 0.36 / s + 0.05), (-1, 0, -1))


def hold_up(rig, side, point=0.0, t=0.0):
    """Hold the sheet up beside the face, turned to the friend; `point` (0..1) moves the near hand to tap a line."""
    hp = (0.2 * side, -0.42, 0.5)
    w = 0.17
    K.reach(rig, 1 if side > 0 else 0, (hp[0] - side * w, hp[1], hp[2] - 0.05), (-side, 0, -1))
    tap = 0.02 * abs(math.sin(t * 14)) if point > 0.99 else 0.0
    far = (hp[0] + side * w, hp[1], hp[2] - 0.05)
    tip = (hp[0] - side * 0.02, hp[1] - 0.06 - tap, hp[2] + 0.02)
    K.reach(rig, 0 if side > 0 else 1, tuple(K.lerp(far[c], tip[c], point) for c in range(3)), (side, 0, -1))
    return hp


def face(rig, mood, t, ph, look=(0.0, 0.0), talk=0.0):
    if mood == "deadpan":
        K.set_face(rig, "deadpan")
    else:
        K.set_face(rig, mood, talk, blink(t, ph))
    eyes(rig, look)


# ---------------------------------------------------------------- the frame
def update(scene, depsgraph=None):
    W = WORLD
    fr = scene.frame_current
    t_cam = (fr - 1) / FPS
    t = int((fr - 1) / 2) * 2 / FPS                             # characters on twos
    name, s, ln = seg(t)
    o = lambda n: t >= B[n]                                     # noqa: E731

    # ---- the background students: Pinky scribbles, Sonu dozes, Chintu sweats
    p = W["pinky"]
    frozen = o("madam")
    write_hands(p, t, 22.0, 0.3, not frozen)
    p.head.rotation_euler = (0.18, 0, 0.05 * math.sin(t * 3))
    face(p, "angry" if frozen else "happy", t, 0.4, (0.0, -0.8) if not frozen else (-0.6, 0.2))
    so = W["sonu"]
    write_hands(so, t, 0, 0, False)
    nod = 0.5 * clamp01(math.sin(t * 0.9) * 1.6) if not frozen else 0.0
    so.head.rotation_euler = (0.25 + nod, 0, 0.1)
    face(so, "deadpan" if nod > 0.2 and not frozen else ("shock" if frozen else "happy"), t, 1.7, (0.0, -0.6))
    c = W["chintu"]
    write_hands(c, t, 9.0, 1.1, not frozen)
    c.head.rotation_euler = (0.12, 0, 0.06 * math.sin(t * 7))
    face(c, "fear", t, 2.2, (0.5 * math.sin(t * 1.3), -0.5))

    # ---- Bunty and Golu
    b, g = W["bunty"], W["golu"]
    W["held_bunty"].scale = (0, 0, 0)
    W["held_golu"].scale = (0, 0, 0)
    for who in ("bunty", "golu"):
        W["paper"][who].scale = (0.3, 0.413, 1)
    by = gy = 0.0
    bmood, gmood = "happy", "happy"
    blook, glook = (0.0, -0.8), (0.0, -0.8)
    write_hands(b, t, 14.0, 0.0, t < B["bunty"] + 0.6)
    write_hands(g, t, 11.0, 0.9, t < B["golu"])
    b.head.rotation_euler = (0.2, 0, 0)
    g.head.rotation_euler = (0.2, 0, 0)
    b.hips.location.z = b.hips_z
    g.hips.location.z = g.hips_z
    if o("bunty") and not o("psst"):                            # stuck: staring at his paper, then scratching his head
        bmood = "shock" if s < 1.0 else "fear"
        blook = (0.0, -1.0)
        if s > 0.9:
            K.pose_arms(b, *K.POSES["scratch"])
            b.head.rotation_euler = (0.2, 0, 0.12 * math.sin(t * 6))
    if o("psst") and not o("show_b"):                           # "psst!": a glance at Madam, then lean to Golu
        by = 0.45 * clamp01(s / 0.25)
        bmood = "smirk"
        blook = (-1.0, 0.2) if s < 0.45 else (1.0, 0.0)
        b.head.rotation_euler = (0.05, 0, 0)
    if o("golu"):                                               # Golu notices
        q = clamp01((t - B["golu"]) / 0.3)
        glook = (K.lerp(0.0, -1.0, q), K.lerp(-0.8, 0.0, q))
        gy = -0.35 * q
        gmood = "shock" if t < B["golu"] + 0.5 else "happy"
        g.head.rotation_euler = (0.05, 0, 0)
    if o("show_b") and not o("golu2"):                          # Bunty holds his sheet up and points at Q3
        by = 0.5
        W["paper"]["bunty"].scale = (0, 0, 0)
        W["held_bunty"].scale = HELD
        hp = hold_up(b, 1, clamp01((t - B["show_b"] - 0.4) / 0.3), t)
        W["held_bunty"].location = hp
        W["held_bunty"].rotation_euler = (math.pi / 2, 0, 0)
        bmood, blook = "fear", (1.0, 0.0)
        glook = (-1.0, -0.4)
        gmood = "shock"
    if o("golu2"):
        by = 0.4
        blook = (1.0, 0.0)
    if o("golu2") and not o("show_g"):                          # Golu reads it... and grins
        gmood = "shock" if s < 0.6 else "smirk"
        glook = (-1.0, -0.3) if s < 0.6 else (0.0, 0.0)
        bmood = "fear"
    if o("show_g") and not o("stare"):                          # Golu holds up his own sheet and taps it
        gy = -0.5
        W["paper"]["golu"].scale = (0, 0, 0)
        W["held_golu"].scale = HELD
        hp = hold_up(g, -1, clamp01((t - B["show_g"] - 0.4) / 0.3), t)
        W["held_golu"].location = hp
        W["held_golu"].rotation_euler = (math.pi / 2, 0, 0)
        gmood, glook = "smirk", (-1.0, 0.0)
        bmood, blook = "shock", (1.0, -0.4)
    if o("stare"):
        by, gy = 0.45, -0.45
        bmood, gmood = "deadpan", "deadpan"
        blook, glook = (1.0, 0.0), (-1.0, 0.0)
    if o("look"):
        bmood = gmood = "deadpan" if s < 0.7 else "smirk"
    cackle = o("laugh") and not o("madam")
    if cackle:                                                  # the cartoon-pest cackle: eyes squeezed shut, mouths
        q = t - B["laugh"]                                      # wide, shaking; pointing at each other, then slapping
        bmood = gmood = "laugh"                                 # the desk, heads thrown back
        b.hips.location.z = b.hips_z + 0.06 * abs(math.sin(q * 22))
        g.hips.location.z = g.hips_z + 0.06 * abs(math.sin(q * 19 + 1))
        b.head.rotation_euler = (-0.35 - 0.12 * math.sin(q * 22), 0, 0.18 * math.sin(q * 9))
        g.head.rotation_euler = (-0.3 - 0.12 * math.sin(q * 19), 0, -0.18 * math.sin(q * 8))
        if q < 1.4:                                             # pointing at each other
            K.pose_arms(b, *K.POSES["point"])
            K.pose_arms(g, K.POSES["rest"][0], K.POSES["point"][0])
            by, gy = 0.55, -0.55
        else:                                                   # banging the desk, hands taking turns
            bang = lambda ph: (0.15, 0.9, 0.6 + 0.9 * abs(math.sin(q * 11 + ph)))   # noqa: E731
            K.pose_arms(b, bang(0.0), bang(1.6))
            K.pose_arms(g, bang(0.8), bang(2.4))
            by, gy = 0.25 * math.sin(q * 5), -0.25 * math.sin(q * 5 + 1)
        blook, glook = (0.0, 0.0), (0.0, 0.0)
    if o("madam"):                                              # frozen mid-laugh, then dread
        q = t - B["madam"]
        bmood = gmood = "laugh" if q < 0.25 else "fear"
        blook = glook = (-1.0, 0.3)
        b.head.rotation_euler = g.head.rotation_euler = (0, 0, 0)
        K.pose_arms(b, *K.POSES["clutch"])
        K.pose_arms(g, (0.6, 0.9, 1.2), (0.6, 0.9, 1.2))
    b.root.rotation_euler = (0, 0, by)
    g.root.rotation_euler = (0, 0, gy)
    face(b, bmood, t, 0.0, blook)
    face(g, gmood, t, 1.3, glook)
    if cackle:                                                  # eyes squeezed to slits, mouths wide open
        for r in (b, g):
            for e in r.eyes:
                e.scale = (e.scale[0] * 1.1, e.scale[1], e.scale[2] * 0.12)
            r.mouth.scale = (1.75, 1, 1.5 + 0.45 * abs(math.sin(t * 24)))
    sw = []
    if o("madam"):
        for who in ("bunty", "golu"):
            h = W[who].head.matrix_world.translation
            for k in range(2):
                q = (t * 1.4 + k / 2) % 1.0
                sw.append(((h.x + (0.4 if k else -0.38), h.y - 0.5, h.z + 0.25 - q * 0.45), 1.0 - 0.5 * q))
    elif o("bunty") and not o("psst"):
        h = b.head.matrix_world.translation
        sw.append(((h.x + 0.42, h.y - 0.5, h.z + 0.2 - ((t * 1.2) % 1.0) * 0.4), 1.0))
    h = W["chintu"].head.matrix_world.translation
    sw.append(((h.x - 0.4, h.y - 0.5, h.z + 0.2 - ((t * 1.5) % 1.0) * 0.4), 0.9))
    W["sweat"].place(sw)

    # ---- Madam: checking papers at the front, then she looks up
    m = W["madam"]
    m.root.location = MADAM_AT
    m.root.rotation_euler = (0, 0, math.pi)                     # facing the class
    K.show(W["vein"], 0)
    if not o("madam"):
        m.head.rotation_euler = (0.35, 0, 0.05 * math.sin(t * 0.7))
        K.pose_arms(m, *K.POSES["stick"])
        face(m, "happy", t, 0.8, (0.0, -1.0))
    else:
        q = t - B["madam"]
        m.head.rotation_euler = (0.35 * (1 - clamp01(q / 0.12)), 0, 0)
        K.pose_arms(m, *K.POSES["stick"])
        face(m, "shock" if q < 0.35 else "angry", t, 0.8, (0.0, 0.0) if q < 0.35 else (0.3 * math.sin(t * 2), 0.0))
        K.show(W["vein"], 1 + 0.15 * math.sin(t * 28) if q > 0.4 else 0)
    camera(W, t_cam)


# ---------------------------------------------------------------- the camera
FRONT = {   # (x, z, vertical size) seen from the front
    "class": (0.0, 1.35, 5.0),
    "bunty": (0.05, 1.38, 2.2),
    "golu": (1.0, 1.42, 2.25),
    "two": (0.52, 1.2, 3.0),
    "two_close": (0.52, 1.3, 2.6),
    "laugh": (0.52, 1.2, 3.1),
}
REVERSE = {   # seen from behind the class (x is the world's x)
    "board": (-0.75, 2.0, 5.6),
    "board_in": (-1.1, 1.85, 4.4),
    "madam": (MADAM_AT[0], 1.45, 2.1),
    "madam_x": (MADAM_AT[0], 1.55, 1.7),
}


def camera(W, t):
    name, s, ln = seg(t)
    rev, shake = False, 0.0
    if name == "open":
        rev, shot = True, lerp3(REVERSE["board"], REVERSE["board_in"], K.ease(s / ln))
    elif name == "cls":
        shot = push(FRONT["class"], 1.0 - 0.06 * s / ln)
    elif name in ("bunty", "psst"):
        shot = push(FRONT["bunty"], 1.0 - 0.1 * clamp01((t - B["bunty"]) / 3.0))
        if name == "psst" and s > 0.4:
            shot = FRONT["two"]
    elif name in ("golu", "golu2"):
        shot = push(FRONT["golu"], 1.0 - 0.08 * s / ln)
    elif name in ("show_b", "show_g", "ins_b", "ins_g"):
        shot = FRONT["two"]
    elif name == "stare":
        shot = FRONT["bunty"] if s > 0.15 else push(FRONT["bunty"], 1.25)    # a snap zoom
        shot = push(FRONT["bunty"], 0.95) if s > 0.15 else shot
    elif name == "look":
        shot = push(FRONT["two_close"], 1.0 - 0.05 * s / ln)
    elif name == "laugh":
        cuts = ["laugh", "bunty", "golu", "laugh", "two_close"]
        k = min(len(cuts) - 1, int(s / 0.95))
        shot = FRONT[cuts[k]]
        shake = 0.012
    elif name == "madam":
        rev = True
        shot = REVERSE["madam"] if s < 0.3 else REVERSE["madam_x"]
        shake = 0.02 if 0.3 <= s < 0.7 else 0.0
    else:                                                       # freeze, end
        shot = push(FRONT["two_close"], 1.0 - 0.06 * clamp01(s / 2.0))
    W["front"].hide_render = not rev
    W["madam"].root.hide_render = False
    for o in W["madam"].root.children_recursive:
        o.hide_render = not rev
    W["back"].hide_render = rev
    jit = random.Random(int(t * FPS))
    cx, cz, hv = shot
    cam = W["cam"]
    cam.location = (cx + jit.uniform(-1, 1) * shake, 12 if rev else -12, cz + jit.uniform(-1, 1) * shake)
    cam.rotation_euler = (math.pi / 2, 0, math.pi if rev else 0)
    cam.data.ortho_scale = hv


def lerp3(a, b, u):
    u = clamp01(u)
    return tuple(K.lerp(a[k], b[k], u) for k in range(3))


def push(a, k):
    return (a[0], a[1], a[2] * k)


WORLD = None

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if ARGS.get("mode", "lineup") == "lineup":
        lineup()
    else:
        WORLD = build()
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(update)
        sc = bpy.context.scene
        if ARGS.get("stills"):
            for fr in ARGS["stills"]:
                sc.frame_set(fr)
                sc.render.filepath = str(OUT / "stills" / f"f_{fr:05d}.png")
                bpy.ops.render.render(write_still=True)
        else:
            sc.frame_start = ARGS.get("start", 1)
            sc.frame_end = ARGS.get("end", ARGS["frames"])
            bpy.ops.render.render(animation=True)
    (OUT / "result.json").write_text(json.dumps({"ok": True, "frames": ARGS.get("frames", 0)}), encoding="utf-8")
