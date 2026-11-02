"""Jointed paper-cut puppets, drawn in code.

A puppet is a torso with a profile head, two-piece arms and legs, a costume, jewellery,
headwear and an optional prop. Poses are joint angles in degrees; a limb angle of 0 points
straight down and positive angles swing forwards (towards the way the puppet faces), so 90 is
held out in front and 180 is straight up. Puppets hang from strings and bob gently, like a
puppet theatre. All designs here are original.
"""
import math
from dataclasses import dataclass, field

Colour = tuple[int, int, int]

INK = (40, 28, 30)
GOLD = (236, 190, 80)
STRING = (230, 225, 215, 45)


@dataclass
class Look:
    skin: Colour = (238, 214, 186)
    garment: Colour = (236, 196, 60)
    garment_trim: Colour = (190, 60, 50)
    hair: Colour = (40, 30, 34)
    headwear: str | None = None           # jata, crown, bun, turban, or None
    extras: tuple[str, ...] = ()          # moon, snake, tiger, third_eye, sash, beard
    prop: str | None = None               # trident, bow, bowl, pot, lotus, sword, staff
    skirt: str = "dhoti"                  # dhoti (to the knee) or saree (to the ankle)
    height: float = 600.0                 # standing height in pixels at scale 1
    silhouette: Colour | None = None      # draw as a flat shadow puppet in this colour


PRESETS = {
    "shiva": Look(skin=(214, 226, 238), garment=(214, 140, 60), garment_trim=(60, 40, 30), hair=(48, 36, 40),
                  headwear="jata", extras=("moon", "snake", "tiger", "third_eye"), prop="trident"),
    "parvati": Look(skin=(236, 198, 160), garment=(196, 40, 60), garment_trim=GOLD, hair=(30, 22, 26),
                    headwear="bun", extras=("sash",), skirt="saree", height=560),
    "vishnu": Look(skin=(96, 140, 210), garment=(246, 206, 70), garment_trim=(200, 60, 60), headwear="crown",
                   extras=("sash",), prop="lotus"),
    "king": Look(skin=(222, 186, 150), garment=(150, 60, 140), garment_trim=GOLD, headwear="crown", extras=("sash",),
                 prop="sword"),
    "sage": Look(skin=(220, 184, 150), garment=(232, 150, 60), garment_trim=(200, 110, 40), hair=(230, 228, 222),
                 headwear="bun", extras=("beard",), prop="staff"),
    "villager": Look(skin=(206, 160, 120), garment=(90, 140, 190), garment_trim=(240, 240, 230), headwear="turban"),
    "deva": Look(silhouette=(232, 196, 120), headwear="crown"),
    "asura": Look(silhouette=(150, 50, 60), headwear="turban"),
}

POSES: dict[str, dict[str, float]] = {
    #            torso  neck  far arm      near arm     far leg       near leg
    "stand":   dict(t=0, n=0, fs=-8, fe=10, ns=10, ne=12, fh=-4, fk=0, nh=6, nk=0),
    "hold":    dict(t=0, n=0, fs=-8, fe=10, ns=40, ne=50, fh=-4, fk=0, nh=6, nk=0),
    "raise":   dict(t=-4, n=-8, fs=-6, fe=8, ns=165, ne=8, fh=-4, fk=0, nh=8, nk=0),
    "point":   dict(t=3, n=4, fs=-10, fe=8, ns=95, ne=4, fh=-6, fk=0, nh=10, nk=0),
    "drink":   dict(t=-6, n=-14, fs=-6, fe=10, ns=120, ne=105, fh=-4, fk=0, nh=6, nk=0),
    "hands_up": dict(t=-6, n=-10, fs=150, fe=20, ns=160, ne=20, fh=-8, fk=0, nh=10, nk=0),
    "afraid":  dict(t=10, n=10, fs=70, fe=110, ns=80, ne=115, fh=-12, fk=10, nh=12, nk=-10),
    "namaste": dict(t=4, n=6, fs=40, fe=100, ns=45, ne=95, fh=-4, fk=0, nh=6, nk=0),
    "throat":  dict(t=4, n=0, fs=-6, fe=10, ns=110, ne=120, fh=-4, fk=0, nh=6, nk=0),
    "pull":    dict(t=-18, n=-6, fs=80, fe=10, ns=85, ne=5, fh=-22, fk=10, nh=20, nk=-14),
    "walk":    dict(t=2, n=0, fs=-20, fe=12, ns=20, ne=14, fh=-20, fk=10, nh=20, nk=-6),
    "kneel":   dict(t=10, n=10, fs=40, fe=100, ns=45, ne=95, fh=-80, fk=-70, nh=60, nk=-100),
    "sit":     dict(t=0, n=0, fs=20, fe=60, ns=25, ne=60, fh=85, fk=-95, nh=90, nk=-90),
}


def blend(a: dict[str, float], b: dict[str, float], k: float) -> dict[str, float]:
    k = k * k * (3 - 2 * k)                      # ease in and out
    return {j: a[j] + (b[j] - a[j]) * k for j in a}


@dataclass
class Actor:
    """A puppet on stage: where it stands, which way it faces, its pose and its state."""
    look: Look
    x: float
    y: float                                     # ground line (feet)
    scale: float = 1.0
    face: int = 1                                # 1 faces right, -1 faces left
    pose: dict[str, float] = field(default_factory=lambda: dict(POSES["stand"]))
    alpha: float = 1.0
    phase: float = 0.0                           # offsets the idle bob between puppets
    flags: set[str] = field(default_factory=set)  # blue_throat, glow


def capsule(pg, surf, a, b, w, fill, outline=INK, line=3):
    """A limb segment: a thick rounded bar from a to b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    d = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / d * w / 2, dx / d * w / 2
    poly = [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)]
    if outline:
        pg.draw.polygon(surf, outline, poly, 0)
        pg.draw.circle(surf, outline, a, w / 2 + line * 0.6)
        pg.draw.circle(surf, outline, b, w / 2 + line * 0.6)
        inner = [(ax + nx * 0.82, ay + ny * 0.82), (bx + nx * 0.82, by + ny * 0.82),
                 (bx - nx * 0.82, by - ny * 0.82), (ax - nx * 0.82, ay - ny * 0.82)]
        pg.draw.polygon(surf, fill, inner)
        pg.draw.circle(surf, fill, a, w / 2 - line * 0.4)
        pg.draw.circle(surf, fill, b, w / 2 - line * 0.4)
    else:
        pg.draw.polygon(surf, fill, poly)
        pg.draw.circle(surf, fill, a, w / 2)
        pg.draw.circle(surf, fill, b, w / 2)


def limb(origin, ang_deg, length, face, parent=0.0):
    """End point of a limb from origin; angle 0 points down, positive swings forwards."""
    a = math.radians(ang_deg + parent)
    return (origin[0] + face * math.sin(a) * length, origin[1] + math.cos(a) * length)


def draw(pg, surf, actor: Actor, t: float) -> dict[str, tuple[float, float]]:
    """Draw the puppet onto surf; returns key points (head, hands, throat) for effects."""
    lk, p, s, f = actor.look, actor.pose, actor.scale * actor.look.height / 600, actor.face
    bob = math.sin(t * 1.7 + actor.phase) * 5 * s
    sway = math.sin(t * 1.1 + actor.phase) * 1.5
    shadow = lk.silhouette
    skin = shadow or lk.skin
    cloth = shadow or lk.garment
    trim = shadow or lk.garment_trim
    ink = shadow and tuple(int(c * 0.6) for c in shadow) or INK

    thigh, shin = 92 * s, 92 * s
    hip = (actor.x, actor.y - (thigh + shin) * 0.98 + bob)
    lean = p["t"] + sway
    up = (math.sin(math.radians(lean)) * f, -math.cos(math.radians(lean)))
    torso_len = 168 * s
    neck = (hip[0] + up[0] * torso_len, hip[1] + up[1] * torso_len)
    shoulder_far = (neck[0] - f * 10 * s, neck[1] + 18 * s)
    shoulder_near = (neck[0] + f * 6 * s, neck[1] + 22 * s)
    hip_far, hip_near = (hip[0] - f * 8 * s, hip[1]), (hip[0] + f * 8 * s, hip[1])
    pts: dict[str, tuple[float, float]] = {}

    def arm(shoulder, sh, el, colour, far):
        elbow = limb(shoulder, sh, 78 * s, f)
        hand = limb(elbow, el, 72 * s, f, parent=sh)
        dark = tuple(int(c * 0.85) for c in colour) if far and not shadow else colour
        capsule(pg, surf, shoulder, elbow, 24 * s, dark, ink, max(2, 3 * s))
        capsule(pg, surf, elbow, hand, 20 * s, dark, ink, max(2, 3 * s))
        if not shadow:
            for frac, pt0, pt1 in ((0.25, shoulder, elbow), (0.85, elbow, hand)):
                bx, by = pt0[0] + (pt1[0] - pt0[0]) * frac, pt0[1] + (pt1[1] - pt0[1]) * frac
                pg.draw.circle(surf, GOLD, (bx, by), 9 * s, max(2, int(4 * s)))
        pg.draw.circle(surf, dark, hand, 12 * s)
        pg.draw.circle(surf, ink, hand, 12 * s, max(1, int(2 * s)))
        return hand

    def leg(h, hip_a, knee_a, far):
        knee = limb(h, hip_a, thigh, f)
        foot = limb(knee, knee_a, shin, f, parent=hip_a)
        col = tuple(int(c * 0.85) for c in skin) if far and not shadow else skin
        capsule(pg, surf, h, knee, 30 * s, col, ink, max(2, 3 * s))
        capsule(pg, surf, knee, foot, 22 * s, col, ink, max(2, 3 * s))
        toe = (foot[0] + f * 26 * s, foot[1] + 2 * s)
        capsule(pg, surf, foot, toe, 14 * s, col, ink, max(2, 2 * s))
        if not shadow:
            pg.draw.circle(surf, GOLD, (foot[0], foot[1] - 8 * s), 7 * s, max(2, int(3 * s)))
        return knee, foot

    # far side first (a saree hides the legs, so only the feet show beneath it)
    far_knee, far_foot = leg(hip_far, p["fh"], p["fk"], True)
    pts["far_hand"] = arm(shoulder_far, p["fs"], p["fe"], skin, True)

    # torso, drawn side-on: chest in front, curved back behind
    fwd = (math.cos(math.radians(lean)) * f, math.sin(math.radians(lean)))

    def L(x, y):                                     # local (forward, up) from the hip -> screen
        return (hip[0] + (x * fwd[0] + y * up[0]) * s, hip[1] + (x * fwd[1] + y * up[1]) * s)

    female = lk.skirt == "saree"
    chest = 34 if female else 44
    torso = [L(-30, 0), L(-36, 60), L(-32, 122), L(-24, 166), L(6, 174), L(chest - 8, 152), L(chest, 118),
             L(chest - 14, 80), L(30, 38), L(26, 0)]
    pg.draw.polygon(surf, ink, torso)
    inner = [L(x * 0.9, y * 0.97 + 2) for x, y in
             [(-30, 0), (-36, 60), (-32, 122), (-24, 166), (6, 174), (chest - 8, 152), (chest, 118), (chest - 14, 80),
              (30, 38), (26, 0)]]
    pg.draw.polygon(surf, skin, inner)
    if not shadow:
        light = tuple(min(255, int(c * 1.08) + 8) for c in skin)
        pg.draw.polygon(surf, light, [L(0, 40), L(chest - 18, 84), L(chest - 6, 120), L(chest - 12, 148), L(4, 156)])
        pg.draw.polygon(surf, trim, [L(-34, 2), L(28, 2), L(30, 22), L(-36, 22)])          # waistband

    # lower garment, shaped around the legs
    near_knee = limb(hip_near, p["nh"], thigh, f)
    if female:
        hem = actor.y - 6 * s
        skirt = [L(-38, 18), L(32, 18), (far_knee[0] + f * 70 * s, hem), (far_knee[0] - f * 62 * s, hem)]
    else:
        skirt = [L(-38, 18), L(32, 18), (near_knee[0] + f * 26 * s, near_knee[1] + 6 * s),
                 (far_knee[0] - f * 30 * s, far_knee[1] + 10 * s)]
    pg.draw.polygon(surf, ink, skirt)
    cx_, cy_ = sum(x for x, _ in skirt) / 4, sum(y for _, y in skirt) / 4
    pg.draw.polygon(surf, cloth, [(x + (cx_ - x) * 0.06, y + (cy_ - y) * 0.06) for x, y in skirt])
    if not shadow:
        pg.draw.line(surf, trim, skirt[2], skirt[3], max(3, int(9 * s)))                   # hem border
        if "tiger" in lk.extras:
            for k in range(6):
                u = (k + 0.5) / 6
                x0 = skirt[0][0] + (skirt[1][0] - skirt[0][0]) * u
                y0 = skirt[0][1] + (skirt[1][1] - skirt[0][1]) * u
                x1 = skirt[3][0] + (skirt[2][0] - skirt[3][0]) * u
                y1 = skirt[3][1] + (skirt[2][1] - skirt[3][1]) * u
                pg.draw.line(surf, INK, (x0 + (x1 - x0) * 0.2, y0 + (y1 - y0) * 0.2),
                             (x0 + (x1 - x0) * 0.55 + f * 8 * s, y0 + (y1 - y0) * 0.55), max(2, int(6 * s)))
        else:
            for k in range(1, 4):                                                          # dotted pattern
                u = k / 4
                for v in (0.35, 0.65):
                    x0 = skirt[0][0] + (skirt[1][0] - skirt[0][0]) * u
                    y0 = skirt[0][1] + (skirt[1][1] - skirt[0][1]) * u
                    x1 = skirt[3][0] + (skirt[2][0] - skirt[3][0]) * u
                    y1 = skirt[3][1] + (skirt[2][1] - skirt[3][1]) * u
                    pg.draw.circle(surf, trim, (x0 + (x1 - x0) * v, y0 + (y1 - y0) * v), max(2, 4 * s))

    if not female:
        near_knee, near_foot = leg(hip_near, p["nh"], p["nk"], False)
    if female and not shadow:                                                           # the pallu over the shoulder
        pg.draw.polygon(surf, ink, [L(-30, 160), L(-10, 172), L(40, 60), L(20, 40)])
        pg.draw.polygon(surf, cloth, [L(-26, 158), L(-10, 168), L(36, 62), L(22, 46)])
        pg.draw.line(surf, GOLD, L(-10, 170), L(38, 62), max(2, int(5 * s)))

    # necklace, sash, snake
    if not shadow:
        pg.draw.arc(surf, GOLD, (neck[0] - 34 * s, neck[1] - 4 * s, 68 * s, 50 * s), math.pi * 1.05, math.pi * 1.95,
                    max(2, int(5 * s)))
        if "sash" in lk.extras and lk.skirt != "saree":
            pg.draw.line(surf, trim, (shoulder_far[0], shoulder_far[1] + 4 * s), (hip_near[0], hip_near[1] - 6 * s),
                         max(4, int(16 * s)))

    # head
    head_c = (neck[0] + up[0] * 50 * s, neck[1] + up[1] * 50 * s)
    head_c = (head_c[0] + f * math.sin(math.radians(p["n"])) * 6 * s, head_c[1])
    throat = (neck[0] + f * 4 * s, neck[1] - 6 * s)
    pts["throat"] = throat
    neck_col = (90, 140, 255) if "blue_throat" in actor.flags and not shadow else skin
    capsule(pg, surf, (neck[0], neck[1] + 8 * s), (head_c[0] - f * 6 * s, head_c[1] + 20 * s), 26 * s, neck_col, ink,
            max(2, 3 * s))
    draw_head(pg, surf, lk, head_c, s, f, p["n"], ink, skin, shadow)
    pts["head"] = head_c

    if "snake" in lk.extras and not shadow:
        green, belly = (70, 150, 110), (200, 220, 150)
        coil = [(neck[0] + math.cos(a) * 36 * s, neck[1] + 12 * s + math.sin(a) * 12 * s)
                for a in [math.pi * k / 10 for k in range(0, 21)]]
        pg.draw.lines(surf, INK, False, coil, max(4, int(15 * s)))
        pg.draw.lines(surf, green, False, coil, max(3, int(10 * s)))
        hood_base = (neck[0] - f * 30 * s, neck[1] + 6 * s)
        hood = (hood_base[0] - f * 26 * s, hood_base[1] - 70 * s)
        capsule(pg, surf, hood_base, hood, 14 * s, green, INK, max(2, 2 * s))
        pg.draw.ellipse(surf, INK, (hood[0] - 26 * s, hood[1] - 30 * s, 52 * s, 50 * s))
        pg.draw.ellipse(surf, green, (hood[0] - 22 * s, hood[1] - 26 * s, 44 * s, 42 * s))
        pg.draw.ellipse(surf, belly, (hood[0] - 10 * s, hood[1] - 16 * s, 20 * s, 30 * s))

    # near arm and prop last
    pts["near_hand"] = arm(shoulder_near, p["ns"], p["ne"], skin, False)
    if lk.prop and not shadow:
        draw_prop(pg, surf, lk.prop, pts["near_hand"], s, f)
    return pts


def draw_head(pg, surf, lk: Look, c, s, f, nod, ink, skin, shadow) -> None:
    cx, cy = c
    r = 36 * s
    if lk.headwear == "jata":                       # tall coil of matted hair
        for k in range(5):
            w = (40 - k * 4) * s
            pg.draw.ellipse(surf, ink, (cx - f * 10 * s - w, cy - r - (22 + k * 18) * s - 14 * s, 2 * w, 34 * s))
            pg.draw.ellipse(surf, lk.hair if not shadow else skin,
                            (cx - f * 10 * s - w + 3 * s, cy - r - (22 + k * 18) * s - 11 * s, 2 * w - 6 * s, 28 * s))
        if "moon" in lk.extras and not shadow:
            mx, my = cx + f * 18 * s, cy - r - 70 * s
            pg.draw.circle(surf, (255, 246, 210), (mx, my), 16 * s)
            pg.draw.circle(surf, lk.hair, (mx + f * 7 * s, my - 4 * s), 14 * s)
    elif lk.headwear == "bun":
        pg.draw.circle(surf, ink, (cx - f * 28 * s, cy - 18 * s), 24 * s)
        pg.draw.circle(surf, lk.hair if not shadow else skin, (cx - f * 28 * s, cy - 18 * s), 20 * s)
        if not shadow:
            for k in range(3):
                pg.draw.circle(surf, (250, 250, 240), (cx - f * (16 + k * 10) * s, cy - 36 * s + k * 6 * s), 5 * s)
    # skull and hair cap
    pg.draw.circle(surf, ink, c, r + 3 * s)
    pg.draw.circle(surf, skin, c, r)
    if not shadow and lk.headwear not in ("crown", "turban"):
        pg.draw.ellipse(surf, lk.hair, (cx - r - f * 4 * s, cy - r - 4 * s, 2 * r, r * 1.1))
    # profile: nose, lips, chin
    nose = [(cx + f * (r - 4 * s), cy - 6 * s), (cx + f * (r + 12 * s), cy + 8 * s), (cx + f * (r - 2 * s), cy + 12 * s)]
    pg.draw.polygon(surf, skin, nose)
    pg.draw.lines(surf, ink, False, nose, max(1, int(2 * s)))
    if not shadow:
        ex, ey = cx + f * (r * 0.45), cy - 2 * s
        pg.draw.ellipse(surf, (250, 250, 245), (ex - 9 * s, ey - 4 * s, 18 * s, 9 * s))
        pg.draw.circle(surf, INK, (ex + f * 3 * s, ey), 3.5 * s)
        pg.draw.arc(surf, INK, (ex - 11 * s, ey - 11 * s, 22 * s, 14 * s), 0.3, math.pi - 0.3, max(1, int(2 * s)))
        pg.draw.line(surf, (170, 60, 60), (cx + f * (r - 6 * s), cy + 20 * s), (cx + f * (r + 2 * s), cy + 19 * s),
                     max(2, int(3 * s)))
        pg.draw.circle(surf, GOLD, (cx - f * 4 * s, cy + 14 * s), 7 * s, max(2, int(3 * s)))      # earring
        if "third_eye" in lk.extras:
            pg.draw.ellipse(surf, (200, 40, 50), (cx + f * (r * 0.55) - 3 * s, cy - 24 * s, 6 * s, 11 * s))
        if "beard" in lk.extras:
            pg.draw.polygon(surf, lk.hair, [(cx + f * (r - 10 * s), cy + 16 * s), (cx + f * (r + 4 * s), cy + 22 * s),
                                            (cx + f * 10 * s, cy + 70 * s), (cx - f * 12 * s, cy + 24 * s)])
    if lk.headwear == "crown":
        crown = [(cx - r, cy - 10 * s), (cx - r * 0.8, cy - r - 40 * s), (cx - r * 0.3, cy - r - 14 * s),
                 (cx, cy - r - 54 * s), (cx + r * 0.3, cy - r - 14 * s), (cx + r * 0.8, cy - r - 40 * s), (cx + r, cy - 10 * s)]
        pg.draw.polygon(surf, ink, crown)
        pg.draw.polygon(surf, GOLD if not shadow else skin, [(x, y + 3 * s) for x, y in crown])
        if not shadow:
            pg.draw.circle(surf, (200, 40, 60), (cx, cy - r - 4 * s), 6 * s)
    elif lk.headwear == "turban":
        pg.draw.ellipse(surf, ink, (cx - r - 6 * s, cy - r - 18 * s, 2 * r + 12 * s, r * 1.3))
        pg.draw.ellipse(surf, lk.garment if not shadow else skin, (cx - r - 3 * s, cy - r - 15 * s, 2 * r + 6 * s, r * 1.2))


def draw_prop(pg, surf, prop: str, hand, s, f) -> None:
    hx, hy = hand
    if prop == "trident":
        top, bot = (hx, hy - 230 * s), (hx, hy + 150 * s)
        capsule(pg, surf, bot, top, 10 * s, (150, 110, 70), INK, max(2, 2 * s))
        pg.draw.lines(surf, INK, False, [(hx - 34 * s, top[1] - 40 * s), (hx - 30 * s, top[1]), (hx + 30 * s, top[1]),
                                         (hx + 34 * s, top[1] - 40 * s)], max(4, int(9 * s)))
        pg.draw.lines(surf, (220, 225, 235), False, [(hx - 34 * s, top[1] - 40 * s), (hx - 30 * s, top[1]),
                                                     (hx + 30 * s, top[1]), (hx + 34 * s, top[1] - 40 * s)], max(2, int(5 * s)))
        pg.draw.polygon(surf, (220, 225, 235), [(hx - 6 * s, top[1]), (hx, top[1] - 62 * s), (hx + 6 * s, top[1])])
        pg.draw.ellipse(surf, (200, 160, 110), (hx - 16 * s, top[1] + 30 * s, 32 * s, 20 * s))          # small drum
    elif prop == "bow":
        rect = (hx - f * 40 * s - 30 * s, hy - 170 * s, 60 * s, 340 * s)
        pg.draw.arc(surf, INK, rect, -math.pi / 2 if f > 0 else math.pi / 2, math.pi / 2 if f > 0 else 3 * math.pi / 2,
                    max(5, int(12 * s)))
        pg.draw.line(surf, (230, 230, 220), (hx - f * 10 * s, hy - 165 * s), (hx - f * 10 * s, hy + 165 * s), max(1, int(2 * s)))
    elif prop == "bowl":
        pg.draw.ellipse(surf, INK, (hx - 26 * s, hy - 20 * s, 52 * s, 28 * s))
        pg.draw.ellipse(surf, (90, 60, 130), (hx - 22 * s, hy - 18 * s, 44 * s, 18 * s))
    elif prop == "pot":
        pg.draw.circle(surf, INK, (hx, hy - 30 * s), 34 * s)
        pg.draw.circle(surf, (200, 120, 60), (hx, hy - 30 * s), 30 * s)
        pg.draw.rect(surf, GOLD, (hx - 16 * s, hy - 74 * s, 32 * s, 16 * s))
    elif prop == "lotus":
        for k in range(5):
            a = math.pi * (0.15 + 0.175 * k)
            tip = (hx + math.cos(a) * 34 * s * f, hy - 10 * s - math.sin(a) * 40 * s)
            pg.draw.polygon(surf, (240, 140, 170), [(hx - 8 * s, hy - 8 * s), tip, (hx + 8 * s, hy - 8 * s)])
    elif prop == "sword":
        tip = (hx + f * 40 * s, hy - 200 * s)
        capsule(pg, surf, (hx, hy), tip, 12 * s, (220, 225, 235), INK, max(2, 2 * s))
        pg.draw.line(surf, GOLD, (hx - 24 * s, hy - 6 * s), (hx + 24 * s, hy + 6 * s), max(4, int(9 * s)))
    elif prop == "staff":
        capsule(pg, surf, (hx, hy + 140 * s), (hx + f * 10 * s, hy - 220 * s), 12 * s, (130, 90, 60), INK, max(2, 2 * s))


def strings(pg, surf, pts: dict[str, tuple[float, float]], top: float = 0.0) -> None:
    """Puppet-theatre strings from above to the head and hands."""
    for key in ("head", "near_hand"):
        if key in pts:
            x, y = pts[key]
            pg.draw.line(surf, STRING, (x, top), (x, y - (60 if key == "head" else 10)), 2)
