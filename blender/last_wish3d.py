"""The Last Wish (a jail skit) in Blender: the jailer and three prisoners in the 2D chibi look, in front of
painted backgrounds (the gallows yard, the jail gate) made locally with Z-Image.

    blender --background --factory-startup --python blender/last_wish3d.py -- params.json

params (written by reel_engine/toon/last_wish.py): out_dir, style ("flat" or "real"), mode ("lineup" or
"scene"), width, height, fps, samples, frames, story_end, freeze, lines [{start, len, voice, who, env}],
plates {name: png}, optional stills [frame numbers]. In "scene" mode every frame is posed by a frame-change
handler from the line being spoken: mouths follow each voice's loudness, the camera cuts and snap-zooms
per line, the prisoners run out through the gate and back, and the last lines end in a fight cloud.
The "lineup" mode renders the four characters side by side for a look check.
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
STYLE = ARGS.get("style", "flat")
K.configure(STYLE in ("flat", "real"), STYLE == "real")
FPS = ARGS.get("fps", 30)

KHAKI = (196, 164, 104)
JAIL_W, JAIL_D = (244, 240, 230), (58, 60, 72)          # the stripes: off-white and charcoal

JAILER = dict(skin=(214, 160, 112), top=("uniform", KHAKI), legs=KHAKI, shoes=(36, 30, 28), belly=True,
              hair=("bald", (30, 24, 24)), mustache=(28, 22, 22), mustache_k=(1.45, 1.6), cap=KHAKI, R=0.42, size=1.08)
P1 = dict(skin=(242, 202, 162), top=("prison", (JAIL_W, JAIL_D)), legs=(JAIL_W, JAIL_D), shoes=(120, 90, 70),
          hair=("neat", (50, 34, 26)), number="101", R=0.4, size=0.94)               # innocent
P2 = dict(skin=(190, 138, 96), top=("prison", (JAIL_W, JAIL_D)), legs=(JAIL_W, JAIL_D), shoes=(120, 90, 70),
          hair=("spiky", (26, 22, 24)), mustache=(26, 22, 24), beard=True, number="102", R=0.4, size=1.02)  # confident
P3 = dict(skin=(226, 180, 134), top=("prison", (JAIL_W, JAIL_D)), legs=(JAIL_W, JAIL_D), shoes=(120, 90, 70),
          hair=("slick", (24, 22, 28)), mustache=(24, 22, 28), mustache_k=(1.1, 0.42), number="420", R=0.38,
          size=0.96)                                                                  # the clever one
CAST = [("jailer", JAILER), ("p1", P1), ("p2", P2), ("p3", P3)]


def lathi(rig):
    """The jailer's bamboo stick in his right fist, hanging down and out like a cane (returns its empty)."""
    hand, side = rig.arms[0][2], rig.arms[0][3]
    ln, r = (0.78, 0.016) if K.REAL else (0.34, 0.024)
    th = side * (math.pi - 0.3)
    st = K.empty("lathi", (0, -0.01, 0), hand, rot=(0, th, 0))
    K.cyl((0, 0, ln * 0.42), r, ln, K.toon((170, 120, 60)), st, ink=r * 0.5)
    for k in range(4):
        K.cyl((0, 0, ln * (0.0 + 0.24 * k)), r * 1.2, r * 1.2, K.toon((120, 80, 40)), st, ink=0)
    return st


# ================================================================ lineup (the look check)
def lineup():
    sc = bpy.context.scene
    K.setup_render(sc, ARGS.get("width", 1920), ARGS.get("height", 1080), 30, ARGS.get("samples", 32),
                   str(OUT / f"lineup_{STYLE}.png"))
    sc.render.use_motion_blur = False
    if ARGS.get("transparent"):
        sc.render.film_transparent = True
        sc.render.filepath = str(OUT / f"lineup_{STYLE}_alpha.png")
    else:
        K.box((0, 1.5, 1.5), (12, 0.1, 5), K.flat((226, 218, 204)), ink=0)
        K.ground(0, 12, (196, 186, 170))
    poses = {"jailer": ("rest", "angry", 0.15), "p1": ("rest", "innocent", 0.05), "p2": ("fold", "happy", -0.05),
             "p3": ("point", "smirk", -0.18)}
    gap = 0.95 if K.REAL else 1.0
    for k, (name, spec) in enumerate(CAST):
        rig = K.chibi(name, spec)
        rig.root.location = ((k - 1.5) * gap, 0, 0)
        pose, mood, yaw = poses[name]
        rig.root.rotation_euler = (0, 0, yaw)
        K.pose_arms(rig, *K.POSES[pose])
        K.set_face(rig, mood)
        if name == "jailer":
            lathi(rig)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "VERTICAL"
    cam_data.ortho_scale = 2.3 if K.REAL else 2.45
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (0, -12, 1.0 if K.REAL else 1.08)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.render.render(write_still=True)


# ================================================================ the scene (v3, 2026-11-07)
# 101 and 102 get their wish and amble off across the yard; 420 asks for them to be called back; they hear it, can't
# believe it (a laugh plays while they look at each other), turn murderous, storm back and slap him silly; the
# jailer: "No backsies!"; the camera pulls out on the slapping as the laugh plays again.
LINES = ARGS.get("lines", [])
STORY_END = ARGS.get("story_end", 0.0)
PULL = ARGS.get("pull", 1e9)                    # the pull-out starts here
BEAT0 = ARGS.get("beat0", 1e9)                  # the reaction beat after 420's wish starts here
BEAT = ARGS.get("beat", {})
SLAP0, SLAP_DT, SLAP_END = ARGS.get("slap0", 1e9), ARGS.get("slap_dt", 0.28), ARGS.get("slap_end", 1e9)
PH, PW = 7.6, 7.6 * 896 / 1600                  # a plate's size in metres (the painted backgrounds are 896 x 1600)
PLATE_Z0 = -1.19                                # the plate's bottom edge, so the painted floor meets the feet
HOME = {"jailer": (-1.1, 0.42), "p1": (0.05, -0.3), "p2": (0.92, -0.25), "p3": (1.6, -0.35)}
AWAY = {"p1": (-0.42, 1.2, 0.95, 0.6), "p2": (0.42, 1.2, 1.0, 0.58)}       # far across the yard: x, y, z, scale
SLAPPER = {"p2": (0.85, 1.15, -0.15), "p1": (2.12, -0.9, 0.45)}         # at 420: x, yaw, y (101 behind him, right)
TALK = {0: "point", 1: "explain", 2: "chest", 3: "shrug", 4: "up", 5: "point", 6: "explain", 7: "shrug", 8: "up",
        9: "point", 10: "explain", 11: "point", 12: "up", 13: "fold"}
IDLE = {"jailer": "rest", "p1": "rest", "p2": "fold", "p3": "fold"}
MOODS = {
    0: dict(jailer="angry", p1="fear", p2="shock", p3="shock"),
    1: dict(jailer="angry", p1="fear", p2="happy", p3="smirk"),
    2: dict(jailer="angry", p1="innocent"),
    3: dict(jailer="happy", p1="shock", p2="shock", p3="smirk"),
    4: dict(jailer="happy", p1="goofy", p2="happy"),
    5: dict(jailer="angry", p2="happy"),
    7: dict(jailer="happy", p2="shock"),
    8: dict(jailer="happy", p2="laugh"),
    9: dict(jailer="angry", p3="smirk"),
    11: dict(jailer="deadpan", p3="fear"),
}


def mood_of(i, who):
    for k in range(i, -1, -1):
        if who in MOODS.get(k, {}):
            return MOODS[k][who]
    return "happy"


def plate(name, path, x0):
    """A painted background on a plane behind the action (drawn 1.6x larger, its edge pixels repeated, so a
    camera shake never shows its border)."""
    img = bpy.data.images.load(path)
    m = bpy.data.materials.new("plate_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Cubic"
    tex.extension = "EXTEND"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.6, 1.6, 1)
    mp.inputs["Location"].default_value = (-0.3, -0.3, 0)
    nt.links.new(tc.outputs["UV"], mp.inputs[0])
    nt.links.new(mp.outputs[0], tex.inputs[0])
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.object
    o.name = "plate_" + name
    o.data.materials.append(m)
    o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = (x0, 3.0, PLATE_Z0 + PH / 2)
    o.scale = (PW * 1.6, PH * 1.6, 1)
    return o


def shadow(rig):
    return K.sph((0, 0.25, 0.015), (0.36, 0.01, 0.075), K.flat((70, 40, 52)), rig.root, ink=0, seg=24)


def build():
    sc = bpy.context.scene
    K.setup_render(sc, ARGS.get("width", 1080), ARGS.get("height", 1920), FPS, ARGS.get("samples", 16),
                   str(OUT / "frames" / "f_"))
    sc.render.use_motion_blur = False
    sc.frame_start, sc.frame_end = 1, ARGS["frames"]
    W = {}
    plate("yard", ARGS["plates"]["yard"], 0.0)
    for name, spec in CAST:
        W[name] = K.chibi(name, spec)
        shadow(W[name])
    W["lathi"] = lathi(W["jailer"])
    W["vein"] = {k: K.anger_vein(W[k].head, W[k].R, 1 if k == "p2" else -1) for k in ("p1", "p2")}
    W["dust"] = K.Pool(lambda k: K.sph((0, 0, 0), 1.0, K.toon((200, 160, 130), shadow=0.8), ink=0.014), 12)
    W["stars"] = K.Pool(lambda k: K.star(f"st{k}", 5, 0.12, 0.05, K.flat((255, 222, 70), 1.6), jag=0.0), 6)
    W["sweat"] = K.Pool(lambda k: K.sph((0, 0, 0), (0.05, 0.03, 0.08), K.flat((140, 200, 255)), ink=0.008, seg=12), 3)
    W["cheek"] = K.sph((0, 0, 0), (0.09, 0.02, 0.07), K.flat((255, 70, 80)), W["p3"].head, ink=0, seg=16)
    W["cheek"].location = (W["p3"].R * 0.62, -W["p3"].R * 0.86, -W["p3"].R * 0.25)
    K.show(W["cheek"], 0)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 36
    cam_data.clip_end = 100
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_euler = (math.pi / 2, 0, 0)
    W["cam"] = cam
    return W


# ---------------------------------------------------------------- helpers
def line_at(t):
    i = 0
    for k, L in enumerate(LINES):
        if L["start"] <= t:
            i = k
    return i, t - LINES[i]["start"]


def at(i, frac=0.0):
    return LINES[i]["start"] + frac * LINES[i]["voice"]


def after(i, dt=0.0):
    return LINES[i]["start"] + LINES[i]["voice"] + dt


def blink(t, ph, per=3.3):
    return ((t + ph) % per) < 0.12


def walk_cycle(rig, t, speed=8.0, amp=0.5, arms=True):
    s = math.sin(t * speed)
    for k, lp in enumerate(rig.legs):
        lp.rotation_euler = ((1 if k else -1) * amp * s, 0, 0)
    if arms:
        K.pose_arms(rig, (0.15, 0.4 * s, 0.3), (0.15, -0.4 * s, 0.3))
    rig.hips.location.z = rig.hips_z + 0.035 * abs(math.cos(t * speed))


def still_legs(rig):
    for lp in rig.legs:
        lp.rotation_euler = (0, 0, 0)


def face(rig, mood, talk, t, ph):
    if mood == "deadpan":
        K.set_face(rig, "deadpan")
        if talk > 0.08:                                    # deadpan, but the mouth still moves
            rig.mouth.scale = (0.8, 1, 0.2 + 0.8 * talk)
            K.show(rig.frown, 0)
        return
    K.set_face(rig, mood, talk, blink(t, ph))


def place(rig, x, yaw, y=0.0, z=0.0, k=1.0):
    rig.root.location = (x, y, z)
    rig.root.rotation_euler = (0, 0, yaw)
    s = rig.spec.get("size", 1.0) * k
    rig.root.scale = (s, s, s)


def lerp_ang(a, b, u):
    return a + (b - a) * min(1.0, max(0.0, u))


def walker_state(who, t):
    """101 / 102 after their wish: (x, y, z, k, yaw, walking). They amble off until the thud, then stand there."""
    line = 4 if who == "p1" else 8
    t0 = after(line, 0.25)
    if t < t0:
        return None
    hx, hyaw = HOME[who]
    ax, ay, az, ak = AWAY[who]
    turn = min(1.0, (t - t0) / 0.25)
    u = min(1.0, max(0.0, (t - t0 - 0.25) / max(0.5, BEAT0 - t0 - 0.25)))
    u = u * (0.7 + 0.3 * u)                                 # a slow amble, a little quicker as they go
    return (K.lerp(hx, ax, u), K.lerp(0.0, ay, u), K.lerp(0.0, az, u), K.lerp(1.0, ak, u),
            lerp_ang(hyaw, math.pi, turn), t < BEAT0)


# ---------------------------------------------------------------- the frame
def update(scene, depsgraph=None):
    W = WORLD
    fr = scene.frame_current
    t_cam = (fr - 1) / FPS
    t = int((fr - 1) / 2) * 2 / FPS                             # characters on twos, like TV animation
    i, since = line_at(min(t, STORY_END - 0.01))
    L = LINES[i]
    voice = L["voice"]
    fi = int(since * FPS)
    env = L["env"]
    talk = env[fi] if 0 <= fi < len(env) and since < voice else 0.0
    b = t - BEAT0                                               # into the reaction beat (< 0: not yet)
    dash = (t - at(11)) / 0.35 if t >= at(11) else -1.0         # 0 -> 1: storming back to 420
    slapping = t >= SLAP0
    sk = int((t - SLAP0) / SLAP_DT) if slapping else -1          # which slap
    sp = ((t - SLAP0) / SLAP_DT) % 1.0 if slapping else 0.0      # 0 -> 1 within a slap
    slap_on = slapping and t < SLAP_END

    # ---- the jailer
    j = W["jailer"]
    place(j, HOME["jailer"][0], 0.62 if 5 <= i <= 8 else (0.75 if 9 <= i <= 10 else HOME["jailer"][1]))
    still_legs(j)
    jt = talk if L["who"] == "jailer" else 0.0
    jmood = mood_of(i, "jailer")
    if i in (2, 6) and since > voice:
        jmood = "deadpan"                                       # the blank stare before he gives in
    if b >= 0 and i <= 10:
        jmood = "shock" if b < BEAT["kill"] else "deadpan"
    folded = i >= 11 or b >= 0
    idle = K.POSES["fold"] if folded else K.POSES["rest"]
    cur = K.POSES[TALK.get(i, "explain")] if (L["who"] == "jailer" and since < voice and not folded) else idle
    K.pose_arms(j, *(K.blend_pose(idle, cur, K.backout(since / 0.25)) if cur is not idle else idle))
    face(j, jmood, jt, t, 0.0)
    j.head.rotation_euler = (-0.08 * jt, 0, 0.04 * math.sin(t * 0.9))
    W["lathi"].scale = (0, 0, 0) if folded else (1, 1, 1)

    # ---- 101 and 102
    for who in ("p1", "p2"):
        r = W[who]
        ph = 1.1 if who == "p1" else 2.3
        K.show(W["vein"][who], 0)
        ws = walker_state(who, t)
        speaking = L["who"] == who and since < voice
        tk = talk if speaking else 0.0
        if dash >= 0:                                           # storming back, then slapping 420
            ax, ay, az, ak = AWAY[who]
            sx, syaw, sy = SLAPPER[who]
            u = min(1.0, dash)
            e = u * u * (3 - 2 * u)
            place(r, K.lerp(ax, sx, e), syaw, y=K.lerp(ay, sy, e), z=K.lerp(az, 0.0, e), k=K.lerp(ak, 1.0, e))
            K.show(W["vein"][who], 1)
            if u < 1.0:
                walk_cycle(r, t, 22.0, 1.0, arms=False)
                K.pose_arms(r, *K.POSES["up"])
            else:
                still_legs(r)
                mine = (sk % 2 == 0) == (who == "p2")           # they take turns
                if slap_on and mine:                            # wind up -> CHATAAK (at 0.35) -> back
                    wind, hit = (1.5, -0.5, 0.5), (0.7, 1.15, 0.05)
                    q = K.ease(sp / 0.35) if sp < 0.35 else 1.0 - (sp - 0.35) / 0.65
                    K.pose_arms(r, tuple(K.lerp(wind[c], hit[c], q) for c in range(3)), K.POSES["rest"][1])
                else:
                    K.pose_arms(r, (1.5, -0.5, 0.5) if slap_on else K.POSES["rest"][0], K.POSES["rest"][1])
                r.hips.location.z = r.hips_z + (0.03 * abs(math.sin(t * 12)) if slap_on else 0.0)
            face(r, "angry", tk, t, ph)
            r.head.rotation_euler = (-0.1 * tk, 0, 0)
            continue
        if ws is None:                                          # still in the line-up
            place(r, HOME[who][0], 0.75 if (who in ("p1", "p2") and False) else HOME[who][1])
            still_legs(r)
            idle = K.POSES[IDLE[who]]
            cur = K.POSES["clutch" if (who == "p1" and i == 2) else TALK.get(i, "explain")] if speaking else idle
            K.pose_arms(r, *(K.blend_pose(idle, cur, K.backout(since / 0.25)) if speaking else idle))
            mood = mood_of(i, who)
            face(r, mood, tk, t, ph)
            hop = 0.09 * abs(math.sin(since * 9)) if speaking and i in (4, 8) else 0.0
            r.hips.location.z = r.hips_z + hop
            r.head.rotation_euler = (-0.08 * tk + 0.02 * math.sin(t * 1.7 + ph), 0, 0.04 * math.sin(t * 0.9 + ph))
            continue
        x, y, z, k, yaw, walking = ws
        if b >= 0:                                              # they heard it
            other = 1.0 if who == "p1" else -1.0                # turn to face each other (101 is on the left)
            if b < BEAT["surprise"]:
                yaw = math.pi                                   # frozen mid-step at the thud
                mood = "shock"
            elif b < BEAT["kill"]:
                q = min(1.0, (b - BEAT["surprise"]) / 0.25)
                yaw = lerp_ang(math.pi, other * 0.9, q)
                mood = "shock" if b < BEAT["surprise"] + 0.6 or who == "p1" else "goofy"
            else:                                               # murderous: snap round towards 420
                q = min(1.0, (b - BEAT["kill"]) / 0.12)
                yaw = lerp_ang(other * 0.9, 0.35, q)
                mood = "angry"
                K.show(W["vein"][who], 1 + 0.15 * math.sin(t * 30))
            place(r, x, yaw, y=y, z=z, k=k)
            still_legs(r) if b > 0.05 else walk_cycle(r, BEAT0, 8.0, 0.5)
            K.pose_arms(r, *(K.POSES["clutch"] if BEAT["kill"] <= b else K.POSES["rest"]))
            face(r, mood, 0.0, t, ph)
            r.head.rotation_euler = (0, 0, 0.12 * math.sin(t * 18) if b >= BEAT["kill"] else 0.0)
            continue
        place(r, x, yaw, y=y, z=z, k=k)
        if walking and abs(yaw - math.pi) < 0.01:
            walk_cycle(r, t)
        else:
            still_legs(r)
            K.pose_arms(r, *K.POSES["rest"])
        face(r, "happy", 0.0, t, ph)

    # ---- 420
    r = W["p3"]
    sp3 = L["who"] == "p3" and since < voice
    t3 = talk if sp3 else 0.0
    place(r, HOME["p3"][0], HOME["p3"][1] if not slapping else 0.0)
    still_legs(r)
    mood = mood_of(i, "p3")
    if 0 <= b < BEAT["kill"] and i <= 10:
        mood = "smirk"
    elif b >= BEAT["kill"] and i <= 10:
        mood = "fear"
    hand_up = mood == "fear"
    idle = K.POSES["up" if hand_up else "fold"]
    cur = K.POSES[TALK.get(i, "explain")] if sp3 and not hand_up else idle
    K.pose_arms(r, *(K.blend_pose(idle, cur, K.backout(since / 0.25)) if sp3 and not hand_up else idle))
    K.show(W["cheek"], 0)
    if slap_on:                                                 # rocked by each slap, side to side
        side = 1 if sk % 2 == 0 else -1                         # 102 slaps from the left, 101 from the right
        kick = math.exp(-((sp - 0.35) % 1.0) * 7) if sp >= 0.3 else 0.0
        r.head.rotation_euler = (0, side * 0.35 * kick, side * 0.6 * kick)
        r.root.location.x += side * 0.06 * kick
        K.show(W["cheek"], 1)
        mood = "dead" if (sk % 4 == 3 and not sp3) else "fear"
    else:
        r.head.rotation_euler = (-0.08 * t3, 0, 0.04 * math.sin(t * 0.9 + 0.6))
    face(r, mood, t3 if not slap_on else max(t3, 0.3), t, 0.6)
    sw, st = [], []
    if b >= BEAT["kill"] or (dash >= 0 and not slap_on):
        h = r.head.matrix_world.translation
        for k in range(3):
            q = (t * 1.6 + k / 3) % 1.0
            sw.append(((h.x + (0.34 if k % 2 else -0.32), -0.6, h.z + 0.25 - q * 0.5), 1.0 - q * 0.6))
    if slap_on:
        h = r.head.matrix_world.translation
        for k in range(6):
            a = t * 6 + k / 6 * 2 * math.pi
            st.append(((h.x + math.cos(a) * 0.42, -0.7, h.z + 0.5 + 0.1 * math.sin(a)), 1.0))
    W["sweat"].place(sw)
    W["stars"].place(st)
    dust = []
    if 0 <= dash < 1.3:
        for who in ("p1", "p2"):
            x = W[who].root.location.x
            for k in range(4):
                a = (t * 6 + k / 4) % 1.0
                dust.append(((x + (0.3 + a * 0.4) * (-1 if who == "p2" else 1), -0.4, 0.1 + a * 0.3), 0.07 + 0.1 * a))
    W["dust"].place(dust)
    camera(W, t_cam, i, since, voice, b, dash)


# ---------------------------------------------------------------- the camera
def shot(name):
    jx = HOME["jailer"][0]
    return {
        "wide": (0.0, PLATE_Z0 + PH / 2, PH),
        "yard": (0.32, 2.0, 6.8),
        "jcu": (jx + 0.1, 1.15, 2.5),
        "jxcu": (jx + 0.12, 1.28, 1.85),
        "p1": (HOME["p1"][0], 0.95, 2.3),
        "p2": (HOME["p2"][0], 1.0, 2.4),
        "p3": (HOME["p3"][0], 0.95, 2.3),
        "trio": (0.85, 1.25, 4.7),
        "back": (0.0, 1.45, 2.9),                       # the two, far across the yard
        "back2": (0.0, 1.6, 2.45),
        "back3": (0.0, 1.62, 2.05),
        "slap": (1.35, 1.1, 3.1),
        "slapx": (1.4, 1.15, 2.5),
    }[name]


def lerp3(a, b, u):
    u = min(1.0, max(0.0, u))
    return tuple(K.lerp(a[k], b[k], u) for k in range(3))


def push(a, k):
    return (a[0], a[1], a[2] * k)


def camera(W, t, i, since, voice, b, dash):
    shake = 0.0
    sv = since / voice if voice else 1.0
    if t >= PULL:                                   # the pull-out on the slapping, as the laugh plays again
        s = lerp3(shot("slap"), shot("yard"), K.ease((t - PULL) / 3.0))
    elif i == 13:
        s = push(shot("jcu"), 1.0 - 0.06 * min(1.0, sv))
    elif dash >= 0:
        s = shot("slap") if i == 11 else push(shot("slapx"), 1.0 - 0.08 * min(1.0, sv))
        shake = 0.02 if t >= SLAP0 else 0.0
    elif b >= 0:                                    # the reaction beat
        if b < BEAT["surprise"]:
            s, shake = shot("back"), 0.03 * max(0.0, 1 - b / 0.4)
        elif b < BEAT["kill"]:
            s = lerp3(shot("back"), shot("back2"), K.ease((b - BEAT["surprise"]) / (BEAT["kill"] - BEAT["surprise"])))
        else:
            s, shake = shot("back3"), 0.035
    elif i == 0:                                    # the hook: the yard and the noose, pushing in, then the hit
        if since < voice:
            s = lerp3(shot("wide"), shot("yard"), K.ease(sv))
        elif since < voice + 0.62:
            s, shake = shot("jxcu"), 0.03
        else:
            s = shot("trio")
    elif i == 1:
        s = push(shot("jcu"), 1.0 - 0.15 * min(1.0, sv))
    elif i in (2, 6):
        s = shot("p1" if i == 2 else "p2") if since < voice else shot("jcu")
    elif i in (3, 7):
        s = push(shot("jcu"), 1.15)
    elif i in (4, 8):
        s = shot("p1" if i == 4 else "p2") if since < voice else shot("yard")
    elif i == 5:
        s = lerp3(shot("jcu"), shot("p2"), K.ease((sv - 0.8) / 0.2)) if sv > 0.8 else shot("jcu")
    elif i == 9:                                    # the drumroll: creeping in on the jailer, then 420
        s = push(shot("jcu"), 1.0 - 0.15 * min(1.0, sv)) if since < voice else \
            push(shot("p3"), 1.0 - 0.25 * min(1.0, (since - voice) / max(0.1, LINES[9]["len"] - voice)))
    elif i == 10:
        s = push(shot("p3"), 0.75 - 0.12 * min(1.0, sv))
    else:
        s = shot("yard")
    jit = random.Random(int(t * FPS))
    cx, cz, hv = s
    W["cam"].location = (cx + jit.uniform(-1, 1) * shake, -12, cz + jit.uniform(-1, 1) * shake)
    W["cam"].data.ortho_scale = hv


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
        elif ARGS.get("render", True):
            sc.frame_start = ARGS.get("start", 1)
            sc.frame_end = ARGS.get("end", ARGS["frames"])
            bpy.ops.render.render(animation=True)
    (OUT / "result.json").write_text(json.dumps({"ok": True, "frames": ARGS.get("frames", 0)}), encoding="utf-8")
