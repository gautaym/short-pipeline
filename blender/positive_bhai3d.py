"""Positive Bhai (the 48 s recut) in Blender: the chibi cast in 3D, as toon 3D or flat 2D.

    blender --background --factory-startup --python blender/positive_bhai3d.py -- params.json

params (written by reel_engine/toon/positive_bhai_3d.py): out_dir, style ("toon" or "flat"), width, height,
fps, samples, frames, story_end, lines [{start, len, who, orig, env}], optional stills [frame numbers].
Every frame is posed by a frame-change handler from the line being spoken at that moment: mouths follow
each voice line's loudness, gestures land on its stressed beats, and the flashbacks are cut-aways to their
own sets (the street, the aunty's gate, the clouds, the park). Lines are keyed by their number in the full
script (orig), as in positive_bhai.py. Writes PNG frames to out_dir/frames/ and out_dir/result.json.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chibi3d as K  # noqa: E402

ARGS = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
OUT = Path(ARGS["out_dir"])
FPS = ARGS.get("fps", 30)
LINES = ARGS["lines"]
STORY_END = ARGS["story_end"]
K.configure(ARGS.get("style") in ("flat", "real"), ARGS.get("style") == "real")
FLAT = K.FLAT

X_ST, X_G, X_SKY, X_P = 100.0, 200.0, 300.0, 400.0
DOST_X, BHAI_X = -0.62, 0.62
HIT_T, FREEZE_T = 2.3, 0.13
REACT = {2, 4, 6, 9, 14}                 # lines followed by a held reaction beat in the courtyard (see positive_bhai_3d.py)
W_ASPECT = ARGS.get("width", 1080) / ARGS.get("height", 1920)
FLIGHT_T, TWINKLE_T = 1.35, 0.4


def talk_poses(who, n):
    if who == "p2":
        if n == 11:
            return ["scratch"]
        if n == 6:
            return ["shrug"]
        if n == 15:
            return ["explain2"]
        if n == 16:
            return ["rest"]
        return ["present", "thumb", "explain", "explain2"]
    if n == 8:
        return ["wipe"]
    if n >= 14:
        return ["hold"]
    if n >= 10:
        return ["up", "shrug", "explain"]
    return ["chest", "explain"]


def idle(who, n):
    if who == "p2":
        return "thumb" if n < 14 else "rest"
    if n >= 14:
        return "hold"
    return "rest" if n <= 9 else "scratch"


def plan():
    out = []
    for L in LINES:
        n, env, dur = L["orig"], L["env"], L["len"]
        per = {}
        for who in ("p1", "p2"):
            rest = idle(who, n)
            keys = [(0.0, rest)]
            if who == L["who"]:
                poses = talk_poses(who, n)
                keys.append((0.08, poses[0]))
                last, k = 0.08, 0
                for f in range(1, len(env) - 1):
                    tt = f / FPS
                    if env[f] > 0.75 and env[f] >= env[f - 1] and env[f] >= env[f + 1] and tt - last > 0.9 and tt < dur - 0.7:
                        k += 1
                        keys.append((tt, poses[k % len(poses)]))
                        last = tt
                if len(poses) > 1:
                    keys.append((max(last + 0.4, dur - 0.3), rest))
            per[who] = keys
        out.append(per)
    return out


PLAN = plan()


def arms_at(i, who, since):
    keys = PLAN[i][who]
    j = max(k for k, key in enumerate(keys) if key[0] <= max(0.0, since))
    cur = K.POSES[keys[j][1]]
    prev = K.POSES[keys[j - 1][1]] if j else cur
    u = K.backout((since - keys[j][0]) / 0.3)
    return K.blend_pose(prev, cur, u)


# ---------------------------------------------------------------- build
def build():
    scene = bpy.context.scene
    K.setup_render(scene, ARGS.get("width", 1080), ARGS.get("height", 1920), FPS, ARGS.get("samples", 24),
                   str(OUT / "frames" / "f_"))
    scene.frame_start, scene.frame_end = 1, ARGS["frames"]
    W = {}
    K.courtyard(0.0)
    K.street(X_ST)
    K.gate_house(X_G)
    W["rays"] = K.heaven(X_SKY)
    K.park(X_P)
    W["dost"] = K.chibi("dost", K.DOST)
    W["bhai"] = K.chibi("bhai", K.BHAI)
    W["dost"].root.location = (DOST_X, 0, 0)
    W["bhai"].root.location = (BHAI_X, 0, 0)
    W["box"] = K.patakhe_box(W["dost"].body)
    W["phone"] = K.phone(W["bhai"].head, W["bhai"].R)
    W["board"] = K.vision_board((0, 1.0, 2.12))
    W["drop"] = K.empty("sweat", (W["bhai"].R * 0.95, -W["bhai"].R * 0.3, W["bhai"].R * 0.5), W["bhai"].head)
    K.sph((0, 0, 0), (0.05, 0.03, 0.07), K.flat((120, 190, 255)), W["drop"], ink=0.008, seg=12)
    K.cyl((0, 0, 0.07), 0.05, 0.08, K.flat((120, 190, 255)), W["drop"], r2=0.0, ink=0.008, verts=12)
    # the street
    W["uncle"] = K.chibi("uncle", K.UNCLE)
    stick_hand = W["uncle"].arms[0][2]
    K.cyl((0, 0, 0.1), 0.022, 0.8, K.toon((150, 92, 48)), stick_hand, rot=(0.2, 0, 0))
    W["car"], W["wheels"] = K.car(X_ST + 10)
    W["driver"] = K.chibi("driver", K.DOST)
    W["driver"].root.parent = W["car"]
    W["driver"].root.location = (0.32, 0, 0.3 - (W["driver"].hips_z - 0.27))
    W["boom"] = K.boom_burst((X_ST - 0.2, -2.2, 1.35))
    tw = K.empty("twinkle")
    K.star("twinkle_star", 4, 0.9, 0.18, K.flat((255, 250, 200), 2.0), tw, jag=0.0)
    W["twinkle"] = tw
    # the gate
    W["aunty"] = K.chibi("aunty", K.AUNTY)
    W["aunty_burnt"] = K.chibi("aunty_burnt", K.AUNTY_BURNT)
    W["bundle"] = K.saree_bundle(W["aunty_burnt"].body)
    W["aunty_ghost"] = K.chibi("aunty_ghost", K.AUNTY, ghost=True)
    # heaven and the park
    W["uncle_ghost"] = K.chibi("uncle_ghost", K.UNCLE, ghost=True)
    W["aunty_ghost2"] = K.chibi("aunty_ghost2", K.AUNTY, ghost=True)
    W["dadaji"] = K.chibi("dadaji", K.DADAJI)
    W["dadi"] = K.chibi("dadi", K.DADI, ghost=True)
    # effects
    sc = [(255, 230, 90), (255, 150, 40), (255, 90, 60), (255, 255, 220)]
    W["sparks"] = K.Pool(lambda k: K.sph((0, 0, 0), 0.035, K.flat(sc[k % 4], 2.5), ink=0, seg=8), 48)
    W["puffs"] = K.Pool(lambda k: K.sph((0, 0, 0), 1.0, K.toon((238, 234, 242), shadow=0.74), ink=0.012), 12)
    W["smoke"] = K.Pool(lambda k: K.sph((0, 0, 0), 1.0, K.toon((96, 92, 98), shadow=0.8), ink=0.01), 12)
    W["glints"] = K.Pool(lambda k: K.star(f"glint{k}", 4, 0.12, 0.03, K.flat((255, 246, 190), 2.0), jag=0.0), 16)
    W["tears"] = K.Pool(lambda k: K.sph((0, 0, 0), (0.035, 0.02, 0.05), K.flat((110, 180, 255)), ink=0.006, seg=10), 8)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 36
    cam_data.clip_end = 300
    if FLAT:
        cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    tgt = K.empty("target")
    tr = cam.constraints.new("TRACK_TO")
    tr.target = tgt
    tr.track_axis, tr.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    W["cam"], W["tgt"] = cam, tgt
    W["bd"] = {name: K.backdrop(name, path, cam) for name, path in ARGS.get("backdrops", {}).items()}
    W["pale"] = K.pale_lines(W["bhai"].head, W["bhai"].R)
    W["vein"] = K.anger_vein(W["aunty_burnt"].head, W["aunty_burnt"].R)
    if FLAT:
        scene.render.use_motion_blur = False             # crisp, like TV animation
    return W


# ---------------------------------------------------------------- per frame
def line_at(t):
    if t >= STORY_END:
        return len(LINES) - 1, LINES[-1]["len"] + (t - STORY_END), LINES[-1]["len"]
    i = 0
    for k, L in enumerate(LINES):
        if L["start"] <= t:
            i = k
    L = LINES[i]
    return i, t - L["start"], L["len"]


def blink(t, ph, per):
    return ((t + ph) % per) < 0.12


def pose_rig(rig, pose, mood, talk, t, ph=0.0, per=3.5, bob=0.0):
    K.pose_arms(rig, *K.POSES[pose]) if isinstance(pose, str) else K.pose_arms(rig, *pose)
    K.set_face(rig, mood, talk, blink(t, ph, per))
    rig.body.scale = (1, 1, 1 + 0.012 * math.sin(t * 2.4 + ph))
    rig.head.rotation_euler = (-0.08 * talk + 0.02 * math.sin(t * 1.7 + ph), 0, 0.04 * math.sin(t * 0.9 + ph))
    rig.hips.location.z = rig.hips_z + bob


def place(rig, loc, rot_z=0.0, k=None):
    rig.root.location = loc
    rig.root.rotation_euler = (0, 0, rot_z)
    s = rig.spec.get("size", 1.0) if k is None else k * rig.spec.get("size", 1.0)
    rig.root.scale = (s, s, s)


def update(scene, depsgraph=None):
    W = WORLD
    fr = scene.frame_current
    t_true = (fr - 1 + scene.frame_subframe) / FPS
    t = (int((fr - 1) / 2) * 2) / FPS if FLAT else t_true     # the characters move on twos, like TV animation
    i, since, length = line_at(t)
    L = LINES[i]
    n, who_speaks = L["orig"], L["who"]
    u = since / length if length else 0.0
    fi = int(since * FPS)
    env = L["env"]
    talk = env[fi] if 0 <= fi < len(env) and t < STORY_END else 0.0
    end = t >= STORY_END

    sparks, puffs, glints, smoke = [], [], [], []
    # ---- the friends in the courtyard
    rs = since - L.get("voice", length)
    react = n in REACT and rs >= 0 and not end
    dmood = "fear" if n == 16 else ("sad" if n <= 9 else "goofy")
    bmood = "shock" if n in (15, 16) else "happy"
    if react and n in (2, 4, 6):
        dmood = "deadpan"                                  # the blank stare after each of Bhai's spins
    if react and n == 9:
        dmood = "goofy"                                    # "मिलन!": his face lights up
    if n == 6 and since < L.get("beat", 1.0):
        bmood = "deadpan"                                  # "ओह... ok."
    if end:
        dmood, bmood = "goofy", "happy"
    dpose = arms_at(i, "p1", since)
    bpose = arms_at(i, "p2", since)
    if end:
        bpose = K.POSES["wave"]
    bounce = 0.05 * abs(math.sin(since * 9)) if (n == 10 and who_speaks == "p1") else 0.0
    if react and n in (2, 4, 6):
        dpose = K.POSES["rest"]
    if react and n == 9:
        dpose = K.POSES["chest"]
    pose_rig(W["dost"], dpose, dmood, talk if who_speaks == "p1" else 0.0, t, 0.0, 3.4, bounce)
    pose_rig(W["bhai"], bpose, bmood, talk if who_speaks == "p2" else 0.0, t, 2.3, 3.7)
    if end:
        sh, el, hand, side = W["bhai"].arms[0]
        el.rotation_euler = (-0.9 - 0.5 * math.sin(t * 9), 0, 0)
    place(W["dost"], (DOST_X, 0, 0), 0.0 if (react and n in (2, 4, 6, 9)) else 0.32)    # stares into the camera
    place(W["bhai"], (BHAI_X, 0, 0), -0.32 + (0.12 if bmood == "shock" else 0.0))
    W["bhai"].body.rotation_euler = (0, 0.08 if bmood == "shock" else 0.0, 0)
    if n == 16 and not end:                                    # the hand really holds the phone at his ear
        bh = W["bhai"]
        K.reach(bh, 1, Vector(bh.head.location) + Vector((-bh.R * 0.97 - 0.03, -bh.R * 0.3, -bh.R * 0.3)), (-1.0, -0.2, -0.7))
    K.show(W["box"], 1 if (n >= 14 or end) else 0)
    K.show(W["phone"], 1 if n == 16 and not end else 0)
    K.show(W["board"], 0)
    if n == 11:                                         # "आ... आ... ओह..." wide-eyed, then a forced smile
        K.set_face(W["bhai"], "shock" if since < L.get("mark", 2.0) else "happy",
                   talk if who_speaks == "p2" else 0.0, False)
    K.show(W["drop"], 1 if (bmood == "shock" or n == 11) and not end else 0)
    if react and n == 14:                                   # "dadaji": the smile freezes... then he keels over
        K.set_face(W["bhai"], "happy", 0.0, False)
        K.pose_arms(W["bhai"], *K.POSES["rest"])
        if rs >= 0.6:
            k = K.ease((rs - 0.6) / 0.22)
            bounce_back = 0.08 * math.sin(max(0.0, rs - 0.82) * 22) * math.exp(-max(0.0, rs - 0.82) * 6)
            W["bhai"].root.rotation_euler = (-1.5 * k + bounce_back, 0, -0.2)
    K.show(W["pale"], 1 if ((react and n == 14) or n == 15) and not end else 0)
    K.show(W["vein"], (0.9 + 0.3 * abs(math.sin(t * 10))) if n == 2 else 0)
    if react and n == 9:                                    # sparkly eyes
        R = W["dost"].R
        hz = W["dost"].head_z
        for k, side in enumerate((-1, 1)):
            glints.append(((DOST_X + side * R * 0.36, -R * 1.05, hz), 1.6 + 0.4 * math.sin(t * 12 + k)))
    tears = []
    if n == 8:
        R = W["dost"].R
        for k in range(8):
            side = -1 if k % 2 else 1
            d = ((t * 1.6 + k * 0.27) % 1.0)
            tears.append(((DOST_X + side * R * 0.42 * 1 + 0.06, -R * 0.8, W["dost"].head_z - R * 0.2 - d * 0.35 * (R / 0.4)), 1.0 - d * 0.5))
    W["tears"].place(tears)

    # ---- the street: the uncle, the car, BOOM
    car_x, ux = X_ST + 10, X_ST - 2.7
    uncle_loc, uncle_rot, uncle_k = (ux, 0.2, 0.0), (0, 0, 0.55), 1.0
    boom_k, tw_k = 0.0, 0.0
    tw_loc = (0, 0, 0)
    shake = 0.0
    if n == 7:
        s = since
        hit = HIT_T
        if s < hit:
            ux = X_ST - 2.7 + 2.4 * s / hit
            hop = 0.07 * abs(math.sin(math.pi * s * 30 / 7))
            uncle_loc = (ux, 0.2, hop)
            W["uncle"].body.rotation_euler = (0, 0.1 + 0.05 * math.sin(s * 13), 0)
            for k, lp in enumerate(W["uncle"].legs):
                lp.rotation_euler = (0, 0.55 * math.sin(math.pi * s * 30 / 7 + k * math.pi), 0)
            K.pose_arms(W["uncle"], (2.45 - 0.4 * math.sin(s * 22), 0.1, 0.3), (0.9 + 0.35 * math.sin(s * 22 + 1.3), 0.3, 0.6))
            K.set_face(W["uncle"], "angry", 0.4 + 0.5 * abs(math.sin(s * 15)), False)
        elif s < hit + FREEZE_T:
            uncle_loc = (X_ST - 0.3, 0.2, 0)
            uncle_k = 1.0
            W["uncle"].root.scale = (0.72 * 0.8, 0.8, 1.12 * 0.8)
            K.set_face(W["uncle"], "shock", 0.0, False)
        else:
            q = (s - hit - FREEZE_T) / FLIGHT_T
            if q <= 1:
                uncle_loc = (X_ST - 0.3 - 2.6 * q, 0.2 + 10 * q, 9.5 * (1 - (1 - q) ** 2))
                uncle_rot = (q * 2.5, -q * 6 * math.pi, 0.55)
                K.pose_arms(W["uncle"], (2.9, 0.2 + 0.6 * math.sin(s * 40), 0.3), (2.9, 0.2 + 0.6 * math.sin(s * 40 + 2), 0.3))
                K.set_face(W["uncle"], "shock", 0.0, False)
            else:
                uncle_k = 0.0
                uncle_loc = (X_ST - 2.9, 10.2, 9.5)
            if q > 0.9 and q < 1 + TWINKLE_T / FLIGHT_T:
                v = (q - 0.9) / (0.1 + TWINKLE_T / FLIGHT_T)
                tw_k = math.sin(v * math.pi) * 1.4
                tw_loc = (X_ST - 2.9, 10.2, 9.5)
        # the car
        if s < hit - 0.95:
            car_x = X_ST + 10
        elif s <= hit:
            car_x = X_ST + 10 - 8.8 * (s - hit + 0.95) / 0.95
        elif s < hit + FREEZE_T:
            car_x = X_ST + 1.2
        else:
            v = min(1.0, (s - hit - FREEZE_T) / 0.85)
            car_x = X_ST + 1.2 - 2.6 * (1 - (1 - v) ** 2)
        frozen = hit <= s < hit + FREEZE_T
        W["car"].location = (car_x, -0.7, 0)
        sq = 0.9 if frozen else 1.0
        W["car"].scale = (sq, 1, 2 - sq)
        nose = -0.06 * math.exp(-(s - hit) / 0.27) * math.cos((s - hit) * 18) if s > hit else 0.0
        W["car"].rotation_euler = (0, nose, 0)
        for w in W["wheels"]:
            w.rotation_euler = (math.pi / 2, -(car_x - X_ST) / 0.3, 0)
        drv = W["driver"]
        K.pose_arms(drv, *K.POSES["hold"])
        K.set_face(drv, "shock" if s >= hit else "goofy", 0.0, blink(t, 1.0, 3.0))
        if s >= hit:
            e = s - hit
            boom_k = 0.62 * ((1.25 * K.ease(e / 0.1) - 0.25 * K.ease((e - 0.1) / 0.1)) if e < 1.0 else max(0.0, 1 - (e - 1.0) / 0.17))
            for k in range(9):
                a = k / 9 * 2 * math.pi
                d = 0.35 + 0.8 * K.ease(e / 1.0)
                ps = max(0.0, (0.75 + 0.15 * (k % 3)) * K.ease(e / 0.2) * (1 - K.ease((e - 0.8) / 0.5)))
                puffs.append(((X_ST - 0.2 + math.cos(a) * d, -0.2 + 0.3 * math.sin(a), 0.6 + math.sin(a) * d * 0.7 + 0.6 * e), ps))
            shake = 0.18 * math.exp(-e / 0.2)
    W["uncle"].root.location = uncle_loc
    W["uncle"].root.rotation_euler = uncle_rot
    if not (n == 7 and HIT_T <= since < HIT_T + FREEZE_T):
        s0 = 0.8 * uncle_k
        W["uncle"].root.scale = (s0, s0, s0)
    if n != 7:
        W["car"].location = (X_ST + 10, -0.7, 0)
    K.show(W["boom"], boom_k)
    W["boom"].rotation_euler = (0, 0.08 * math.sin(t * 12), 0)
    K.show(W["twinkle"], tw_k)
    W["twinkle"].location = tw_loc
    W["twinkle"].rotation_euler = (0, t * 4.5, 0)

    # ---- the aunty's gate (after BHADAAM she is soot-black and frizzy: the picture contradicts Positive Bhai)
    A, B, AG = W["aunty"], W["aunty_burnt"], W["aunty_ghost"]
    place(A, (X_G, 0, 0), 0.0)
    place(B, (X_G, 0, 0), 0.0, 0.0)
    place(AG, (X_G, 0, 0), 0.0, 0.0)
    A.body.rotation_euler = (0, 0, 0)
    B.body.rotation_euler = (0, 0, 0)
    K.show(W["bundle"], 0)
    pose_rig(A, "fold", "happy", 0.0, t, 0.7, 3.2)
    pose_rig(B, "rest", "angry", 0.0, t, 0.4, 3.0)
    rng = random.Random(fr * 7 + int(scene.frame_subframe * 10))
    mark = L.get("mark", length * 0.6)

    def hair_smoke(x):
        for k in range(6):
            v = (since * 0.6 + k / 6) % 1.0
            smoke.append(((x - 0.25 + 0.1 * k + 0.08 * math.sin(t * 3 + k), 0.05, 1.3 + v * 0.7), 0.12 * (1 - v) + 0.03))

    if n == 1:
        if u < 0.45:
            if u > 0.2:
                for k in range(14):
                    sparks.append(((X_G + 0.25 + rng.uniform(-0.15, 0.15), -0.35 + rng.uniform(-0.1, 0.1), 0.05 + rng.uniform(0, 0.35)), 1.0))
        else:
            v = (u - 0.45) / 0.3
            jump = 1.0 * math.sin(math.pi * min(1.0, v)) if v < 1 else 0.0
            place(A, (X_G, 0, jump), 0.0)
            pose_rig(A, "up" if v < 1 else "shrug", "shock", 0.0, t, 0.7, 3.2)
            A.root.scale = (0.8 * (0.95 if v < 1 else 1.05), 0.8, 0.8 * (1.08 if v < 1 else 0.95))
            if v < 0.6:
                for k in range(40):
                    a_, r = rng.uniform(0, 2 * math.pi), rng.uniform(0.1, 0.9) * (0.4 + v)
                    sparks.append(((X_G + math.cos(a_) * r, -0.4, 0.1 + abs(math.sin(a_)) * r), 1.6))
            e = (u - 0.45) * length
            for k in range(8):
                a_ = k / 8 * 2 * math.pi
                d = 0.55 + 0.6 * K.ease(e / 1.2)
                ps = max(0.0, 0.2 * K.ease(e / 0.15) * (1 - K.ease((e - 1.0) / 0.6)))
                puffs.append(((X_G + math.cos(a_) * d, 0.1, 0.15 + abs(math.sin(a_)) * d * 0.4 + 0.3 * e), ps))
    elif n == 2:                                       # "new saree mili hogi": soot, frizz, shaking with rage
        place(A, (X_G, 0, 0), 0.0, 0.0)
        place(B, (X_G, 0, 0), 0.0)
        pose_rig(B, "hold", "angry", 0.0, t, 0.4, 3.0)
        B.body.rotation_euler = (0, 0.025 * math.sin(t * 40), 0)
        K.show(W["bundle"], 1)
        hair_smoke(X_G)
    elif n == 3:
        x = X_G - 0.9 + 1.2 * u
        place(A, (x, 0, 0.02 * abs(math.sin(since * 6))), 0.9)
        pose_rig(A, "rest", "sad", 0.0, t, 0.7, 3.2)
        A.body.rotation_euler = (0.22, 0, 0)
    elif n == 4:                                       # "fun aur excitement": running, screaming, crackers chasing
        place(A, (X_G, 0, 0), 0.0, 0.0)
        x = X_G - 1.5 + 3.0 * min(1.0, max(0.0, (since / L.get("voice", length) - 0.35) / 0.65))
        place(B, (x, 0, 0.15 * abs(math.sin(since * 10))), 0.6)
        w = 0.5 * math.sin(since * 14)
        K.pose_arms(B, (2.4 + w, 0.3, 0.4), (2.4 - w, 0.3, 0.4))
        K.set_face(B, "shock", 0.55 + 0.45 * abs(math.sin(since * 7)), False)
        for k in range(30):
            sparks.append(((x - 0.45 - rng.uniform(0, 0.6), -0.2 + rng.uniform(-0.15, 0.15), 0.03 + rng.uniform(0, 0.35)), 1.3))
        for k in range(4):
            v = (since * 1.5 + k / 4) % 1.0
            puffs.append(((x - 0.5 - v * 0.8, 0.1, 0.12 + v * 0.3), 0.12 * (1 - v)))
        hair_smoke(x)
    elif n in (5, 6):                                  # the heart attack: she falls sideways, her soul rises
        place(A, (X_G, 0, 0), 0.0, 0.0)
        place(B, (X_G, 0, 0), 0.0)
        v = (since - mark) / max(0.3, length - mark) if n == 5 else 2.0
        fall = K.ease((v - 0.15) / 0.3)
        pose_rig(B, "clutch", "shock" if v < 0.15 else "dead", 0.0, t, 0.4, 3.0)
        B.root.rotation_euler = (0, -1.45 * fall, 0)
        B.root.location = (X_G - 0.25 * fall, 0, 0.06 * fall)
        rise = K.ease((v - 0.4) / 0.6) if n == 5 else 1.0
        gz = 0.3 + 1.0 * rise + (0.25 * since if n == 6 else 0.0)
        if rise > 0:
            place(AG, (X_G + 0.1, -0.1, gz + 0.05 * math.sin(t * 3)), 0.0, min(1.0, rise * 1.3))
            if n == 5:
                pose_rig(AG, "rest", "dead", 0.0, t, 0.2, 3.0)
            else:
                pose_rig(AG, "wave", "happy", 0.0, t, 0.2, 3.0)
                sh, el, hand, side = AG.arms[0]
                el.rotation_euler = (-0.9 - 0.5 * math.sin(since * 9), 0, 0)

    # ---- heaven: the reunion
    UG, AG2 = W["uncle_ghost"], W["aunty_ghost2"]
    W["rays"].rotation_euler = (0, t * 0.15, 0)
    if n == 9:
        g = K.ease(u / 0.4)
        bob = 0.04 * math.sin(t * 3)
        place(UG, (X_SKY - 0.95 + 0.6 * g, 0, 0.62 + bob), 0.35)
        place(AG2, (X_SKY + 0.95 - 0.6 * g, 0, 0.62 - bob), -0.35)
        pose_rig(UG, "reach" if g > 0.8 else "wave", "happy", 0.0, t, 0.3, 3.1)
        pose_rig(AG2, "reach_l" if g > 0.8 else "rest", "laugh", 0.0, t, 1.3, 3.3)
        for k in range(10):
            glints.append(((X_SKY + rng.uniform(-1.3, 1.3), -0.8, rng.uniform(0.5, 2.4)), abs(math.sin(since * 4 + k * 1.7))))
    else:
        place(UG, (X_SKY - 0.35, 0, 0.62), 0.35)
        place(AG2, (X_SKY + 0.35, 0, 0.62), -0.35)
        pose_rig(UG, "rest", "happy", 0.0, t)
        pose_rig(AG2, "rest", "happy", 0.0, t)

    # ---- the park: dadaji alone, dadi's soul waving
    D, DI = W["dadaji"], W["dadi"]
    place(D, (X_P - 0.2, 0.32, 0.25 - (D.hips_z - 0.27) * 0.82), 0.15)    # sitting on the bench
    pose_rig(D, "fold", "sad", 0.0, t, 0.5, 4.0)
    D.head.rotation_euler = (0.25, 0, 0)
    for lp in D.legs:
        lp.rotation_euler = (-1.45, 0, 0)
    for kn in D.knees:
        kn.rotation_euler = (1.45, 0, 0)
    place(DI, (X_P + 0.7, 0.0, 0.95 + 0.06 * math.sin(t * 2.6)), -0.3)
    pose_rig(DI, "wave", "happy", 0.0, t, 1.0, 3.0)
    sh, el, hand, side = DI.arms[0]
    el.rotation_euler = (-0.9 - 0.5 * math.sin(t * 8), 0, 0)

    W["sparks"].place(sparks)
    W["puffs"].place(puffs)
    W["glints"].place(glints)
    W["smoke"].place(smoke)

    # ---- the camera (the shot is chosen on whole frames, so motion blur never smears across a cut)
    i2, since2, length2 = line_at(t_true)                  # the camera moves on every frame
    n2 = LINES[i2]["orig"]
    camera(W, fr, t_true, i2, since2, length2, since2 / length2 if length2 else 0.0, n2, shake)


def shot_for(i, since, length, n, end):
    """(look point, distance, view height, elevation) for this moment. In the real look the heads are smaller,
    so the face shots (looking at face height) come in closer."""
    look, dist, hv, el = _shot_for(i, since, length, n, end)
    if K.REAL and look.z > 1.3 and hv < 3.0:
        hv *= 0.62
        look = Vector((look.x, look.y, look.z + 0.04))
    return look, dist, hv, el


def _shot_for(i, since, length, n, end):
    u = since / length if length else 0.0
    L = LINES[i]
    rs = since - L.get("voice", length)
    two = (Vector((0, 0, 1.12)), 4.6, 3.9, 0.1)
    close_d = (Vector((DOST_X + 0.05, 0, 1.42)), 2.6, 2.4, 0.06)
    close_b = (Vector((BHAI_X - 0.05, 0, 1.42)), 2.6, 2.4, 0.06)
    if end:
        return two
    if n in REACT and rs >= 0:                         # the held beat: a reaction in the courtyard
        if n in (2, 6, 9):
            return close_d                             # the Dost's deadpan stare (or his face lighting up)
        if n == 4:
            return two                                 # deadpan Dost, beaming Bhai
        if n == 14:
            return (close_b[0], 2.6, 2.0, 0.06) if rs < 0.6 else two   # Bhai frozen... then keeling over
    if n == 7:
        s = since
        if s < HIT_T:
            ux = X_ST - 2.7 + 2.4 * s / HIT_T
            return (Vector((ux + 0.75, 0, 1.15)), 5.4, 4.6, -0.04)
        up = K.ease((s - HIT_T - FREEZE_T - 0.1) / 1.1)
        look = Vector((X_ST + 0.25, 0, 1.15)).lerp(Vector((X_ST - 2.2, 6.5, 7.5)), up)
        return (look, 5.4 + 3.0 * up, 4.6 + 4.5 * up, -0.04 + 0.1 * up)
    mark = L.get("mark", length * 0.6)
    if n == 5 and since < mark:                        # suspense: a slow push-in on the Dost
        return (Vector((DOST_X + 0.05, 0, 1.42)), 2.6, 2.5 - 0.8 * K.ease(since / mark), 0.06)
    if n == 6:
        beat = L.get("beat", 1.0)
        if since < beat:                               # "ओह... ok." (deadpan, in the two-shot)
            return two
        if since < beat + 1.0:                         # "कोई नहीं!": snap zoom on Bhai, sparkles behind him
            return (close_b[0], 2.6, 2.2, 0.06)
        return (Vector((X_G - 0.4, 0, 1.3)), 4.2, 3.9, 0.1)
    v = since / L.get("voice", length)
    if n == 1:
        if u < 0.25:                                   # the Dost, guilty
            return close_d
        if u < 0.45:                                   # low on the fuse at her feet
            return (Vector((X_G + 0.25, -0.3, 0.35)), 3.0, 1.3, 0.15)
        return (Vector((X_G, 0, 1.1)), 4.2, 3.6, 0.1)  # BHADAAM
    if n == 2:
        if v < 0.45:                                   # Bhai beaming: "Positive सोचो..."
            return close_b
        q = K.ease((v - 0.45) / 0.55)                  # the reality: a push-in on her soot-black glare
        return (Vector((X_G, 0, 0.95)).lerp(Vector((X_G + 0.05, 0, 1.42)), q), 4.2, K.lerp(2.8, 1.5, q), 0.1)
    if n == 3:                                         # a pan along with her hobble
        return (Vector((X_G - 0.7 + 1.2 * u, 0, 1.0)), 4.2, 2.8, 0.1)
    if n == 4:
        if v < 0.35:                                   # Bhai dreaming of "fun और excitement"
            return close_b
        p4 = min(1.0, (v - 0.35) / 0.65)               # the reality: tracking her screaming run
        return (Vector((X_G - 1.5 + 3.0 * p4, 0, 1.0)), 4.2, 3.2, 0.1)
    if n == 11:                                        # "आ... आ... ओह... हाँ, ठीक ही है।": a slow, awkward push-in
        return (close_b[0], 2.6, 2.9 - 0.9 * K.ease(since / L.get("voice", length)), 0.06)
    if n == 5:
        return (Vector((X_G - 0.55, 0, 1.1)), 4.2, 3.7, 0.12)
    if n == 10:                                        # "ठोक दूँ?": snap in on the Dost, speed lines
        return (close_d[0], 2.6, 2.7, 0.06)
    if n == 16:
        return (Vector((0.05, 0, 1.2)), 4.4, 3.5, 0.1)
    if n == 9:
        return (Vector((X_SKY, 0, 1.25)), 4.2, 3.3 * (1 - 0.06 * u), 0.05)
    if n == 14 and 0.15 < since / L["voice"] < 0.6:
        return (Vector((X_P + 0.25, 0.2, 1.05)), 4.2, 3.3, 0.1)
    if n == 8:
        return close_d
    if n == 15:
        return close_b
    return (two[0], two[1], two[2] * (1 - 0.05 * u), two[3])


def backdrop_for(i, since, n, end):
    """Which gag-anime mood background goes behind the characters now, if any."""
    if end:
        return None
    L = LINES[i]
    rs = since - L.get("voice", L["len"])
    react = n in REACT and rs >= 0
    beat = L.get("beat", 1.0)
    if react:
        if n == 14 and rs < 0.6:
            return "shock"
        return "sparkle" if n in (4, 9) else None
    v = since / L.get("voice", L["len"])
    if (n == 2 and v < 0.45) or (n == 4 and v < 0.35):
        return "sparkle"                               # Bhai's rosy version, before the cut to reality
    if n == 8:
        return "gloom"
    if n == 10:
        return "speed"
    if n == 15:
        return "shock"
    if n == 6 and beat <= since < beat + 1.0:
        return "sparkle"
    return None


def camera(W, fr, t, i, since, length, u, n, shake):
    end = t >= STORY_END
    fs = int(since * FPS) / FPS                       # the shot is decided on whole frames
    look, dist, hv, el = shot_for(i, since if n == 7 else fs, length, n, end)
    blend_t = 0.12 if FLAT else 0.4                   # snappy cuts and zooms in the 2D look
    if not end and n not in (7,) and i > 0:           # a short ease between shots in the courtyard
        prevn = LINES[i - 1]["orig"]
        pl, pd, ph, pe = shot_for(i - 1, LINES[i - 1]["len"], LINES[i - 1]["len"], prevn, False)
        if abs(pl.x - look.x) < 3 and abs(pl.y - look.y) < 3 and since < blend_t:
            q = K.ease(fs / blend_t)
            look, dist, hv, el = pl.lerp(look, q), K.lerp(pd, dist, q), K.lerp(ph, hv, q), K.lerp(pe, el, q)
    if FLAT:
        el = max(el, 0.22)
    rng = random.Random(fr)
    jitter = Vector((rng.uniform(-1, 1), 0, rng.uniform(-1, 1))) * shake
    look = look + jitter
    pos = look + Vector((0, -dist * math.cos(el), dist * math.sin(el)))
    W["tgt"].location = look
    W["cam"].location = pos + jitter * 0.3
    cd = W["cam"].data
    if FLAT:
        cd.ortho_scale = hv
    else:
        cd.lens = 36 * dist / hv
    pick = backdrop_for(i, fs, n, end)
    for name, pl in W["bd"].items():
        if name == pick:
            depth = dist + 0.8
            hp = (hv if FLAT else hv * depth / dist) * 1.2
            pl.location = (0, 0, -depth)
            pl.scale = (hp * W_ASPECT, hp, 1)
        else:
            K.show(pl, 0)


WORLD = None

if __name__ == "__main__":
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
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps({"frames": ARGS["frames"]}), encoding="utf-8")
