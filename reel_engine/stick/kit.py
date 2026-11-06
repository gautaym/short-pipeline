"""Stick Katha: a kit for stick-figure reels drawn entirely in code (no image model, no anatomy surprises).

A figure stands with its feet at (x, y) and is drawn from a pose: joint angles in radians, 0 pointing
straight down and positive swinging the way the figure faces. Moods set the brows and mouth; extras
mark who is who (Durvasa's beard and top knot, Shri Krishna's peacock feather, Draupadi's braid).
"""
import math
from dataclasses import dataclass, field

THIGH, SHIN, TORSO, UPPER, FORE, HEAD = 72, 70, 125, 62, 56, 40


@dataclass
class Pose:
    legs: tuple = (0.12, 0.0, -0.12, 0.0)        # back thigh, back shin, front thigh, front shin (shin relative)
    arms: tuple = (0.25, 0.1, -0.25, -0.1)        # upper, lower for each arm (lower relative)
    lean: float = 0.0
    lift: float = 0.0                             # the whole body raised (between steps)
    belly: float = 0.0                            # 0 thin, 1 round


def stand(t: float = 0.0) -> Pose:
    b = math.sin(t * 2.2) * 0.04
    return Pose(arms=(0.22 + b, 0.15, -0.22 - b, -0.15))


def walk(phase: float, stride: float = 0.5, angry: bool = False, tiptoe: bool = False) -> Pose:
    """phase advances by pi per step. Angry: leaning in, fists pumping, slamming down. Tiptoe: high knees."""
    s = math.sin(phase)
    if tiptoe:
        k = max(0.0, s), max(0.0, -s)
        return Pose(legs=(0.15 + 0.9 * k[1], -1.4 * k[1], 0.15 + 0.9 * k[0], -1.4 * k[0]),
                    arms=(-0.9, 1.9, -0.6, 1.7), lean=0.12, lift=abs(s) * 18)
    back = (-stride * s, -max(0.0, s) * 0.9 - 0.1)
    front = (stride * s, -max(0.0, -s) * 0.9 - 0.1)
    arm = (0.75 if angry else 0.45) * s
    lower = 1.5 if angry else 0.35
    return Pose(legs=(back[0], back[1], front[0], front[1]),
                arms=(arm, lower, -arm, lower), lean=0.22 if angry else 0.06,
                lift=abs(s) * (24 if angry else 12))


def point(t: float = 0.0) -> Pose:
    """The front arm straight out, the other on the hip."""
    return Pose(arms=(1.45 + 0.05 * math.sin(t * 6), 0.0, -0.6, -1.9), lean=0.08)


def hold(t: float = 0.0) -> Pose:
    """Both hands forward at chest height, holding something."""
    return Pose(arms=(0.9, 0.7, 0.75, 0.85))


def shock(t: float = 0.0) -> Pose:
    j = math.sin(t * 40) * 0.05
    return Pose(arms=(2.4 + j, 0.5, -2.4 - j, -0.5), legs=(0.25, 0.0, -0.25, 0.0))


def on_phone(t: float = 0.0) -> Pose:
    """The front hand up at the ear, the other on the hip."""
    return Pose(arms=(1.4, 1.9, -0.6, -1.9))


def facepalm(t: float = 0.0) -> Pose:
    return Pose(arms=(1.9, 1.6, -0.25, -0.15), lean=0.1)


def namaste(t: float = 0.0) -> Pose:
    return Pose(arms=(0.5, 2.3, 0.2, 2.5))


def throw(k: float) -> Pose:
    """Winding up (k 0..0.5) and flinging down (k 0.5..1) with the front arm."""
    a = 2.8 * min(1.0, k * 2) if k < 0.5 else 2.8 - 2.2 * min(1.0, (k - 0.5) * 3)
    return Pose(arms=(a, 0.3, -0.6, -1.9), lean=0.25 if k > 0.5 else -0.05)


def joint(p, ang, length, face):
    return (p[0] + face * math.sin(ang) * length, p[1] + math.cos(ang) * length)


@dataclass
class Look:
    head: tuple = (255, 255, 255)
    extras: tuple = ()
    mood: str = "neutral"
    blush: float = 0.0
    width: int = 9
    body: tuple | None = None                     # a coloured garment line over the torso (a dhoti, a sari)
    extra_colour: dict = field(default_factory=dict)
    shirt: tuple | None = None                    # clothes: a chunky coloured torso and sleeves
    pants: tuple | None = None                    # and coloured legs; without them the figure is a plain stick
    skin: tuple | None = None                     # forearms and hands
    hair: tuple | None = None
    shoes: tuple | None = None


def figure(pg, surf, x, y, s, pose: Pose, look: Look, ink, face=1, t=0.0):
    """Draw a stick figure with its feet on (x, y), scale s, facing +1 (right) or -1 (left). Returns
    useful points: head centre, hands, mouth."""
    w = max(2, int(look.width * s))
    hip = (x, y - (THIGH + SHIN) * s * math.cos(0.1) - pose.lift * s)
    neck = joint(hip, math.pi - pose.lean, TORSO * s, face)
    head = (neck[0] + face * 6 * s, neck[1] - HEAD * s * 0.95)

    def line(a, b, width=w, colour=ink):
        pg.draw.line(surf, colour, a, b, width)
        pg.draw.circle(surf, colour, (int(a[0]), int(a[1])), width // 2)
        pg.draw.circle(surf, colour, (int(b[0]), int(b[1])), width // 2)

    def limb(a, b, fill, k):
        """A filled limb with an ink outline (k times the stick width), or a plain stick without fill."""
        if fill is None:
            line(a, b)
        else:
            line(a, b, int(w * k) + 2 * max(2, w // 2), ink)
            line(a, b, int(w * k), fill)

    if "braid" in look.extras:
        tip = joint(head, -0.55, HEAD * 2.6 * s, face)
        line(joint(head, math.pi + 2.2, HEAD * s * 0.85, face), tip, int(w * 1.6))
        pg.draw.circle(surf, look.extra_colour.get("braid", (230, 60, 60)), (int(tip[0]), int(tip[1])), int(7 * s))
    feet = []
    for th, sh in ((pose.legs[0], pose.legs[1]), (pose.legs[2], pose.legs[3])):
        knee = joint(hip, th, THIGH * s, face)
        foot = joint(knee, th + sh, SHIN * s, face)
        limb(hip, knee, look.pants, 2.3)
        limb(knee, foot, look.pants, 2.1)
        if look.shoes:
            line(foot, (foot[0] + face * 22 * s, foot[1]), int(w * 2.2) + 4, ink)
            line(foot, (foot[0] + face * 22 * s, foot[1]), int(w * 2.2), look.shoes)
        else:
            line(foot, (foot[0] + face * 16 * s, foot[1]))
        feet.append(foot)
    shoulder = joint(hip, math.pi - pose.lean, TORSO * s * 0.85, face)
    arms = [(pose.arms[0], pose.arms[1]), (pose.arms[2], pose.arms[3])]
    if "four_arms" in look.extras:                        # Bhagwan Vishnu's upper pair, raised and holding his emblems
        sway = math.sin(t * 1.5) * 0.06
        arms += [(2.2 + sway, 0.5), (-2.2 - sway, -0.5)]
    hands = [None] * len(arms)

    def arm(j):
        up, lo = arms[j]
        elbow = joint(shoulder, up, UPPER * s, face)
        hand = joint(elbow, up + lo, FORE * s, face)
        limb(shoulder, elbow, look.shirt, 2.0)
        limb(elbow, hand, look.skin, 1.5)
        hr = int(w * (1.2 if look.mood == "angry" else 0.8)) + (int(w * 0.5) if look.skin else 0)
        pg.draw.circle(surf, ink, (int(hand[0]), int(hand[1])), hr + (max(2, w // 2) if look.skin else 0))
        if look.skin:
            pg.draw.circle(surf, look.skin, (int(hand[0]), int(hand[1])), hr)
        hands[j] = hand

    if look.shirt:
        arm(1)                                            # the far arm goes behind the body
    limb(hip, neck, look.shirt, 3.6)
    if look.body:                                         # a sash / dhoti: a thick coloured band at the hips
        pg.draw.line(surf, look.body, joint(hip, math.pi - pose.lean, TORSO * s * 0.12, face),
                     joint(hip, pose.lean * 0.3, 34 * s, face), int(w * 2.6))
    if pose.belly > 0.01:
        mid = joint(hip, math.pi - pose.lean, TORSO * s * 0.42, face)
        r = int(pose.belly * 52 * s)
        c = (mid[0] + face * r * 0.55, mid[1])
        pg.draw.circle(surf, look.head, c, r)
        pg.draw.circle(surf, ink, c, r, w)
    for j in range(len(arms)):
        if hands[j] is None:
            arm(j)

    r = int(HEAD * s)
    hx, hy = head
    pg.draw.circle(surf, look.head, (int(hx), int(hy)), r)
    pg.draw.circle(surf, ink, (int(hx), int(hy)), r, w)
    if look.hair:                                         # a cap of hair with a fringe towards the face
        hr_ = pg.Rect(0, 0, int(r * 2.1), int(r * 2.1))
        hr_.center = (int(hx), int(hy - r * 0.05))
        pts = [(hx + math.cos(a) * r * 1.06, hy - math.sin(a) * r * 1.06) for a in [k * math.pi / 14 for k in range(-1, 16)]]
        pts += [(hx - face * r * 0.95, hy - r * 0.05), (hx - face * r * 0.3, hy - r * 0.55),
                (hx + face * r * 0.2, hy - r * 0.42), (hx + face * r * 0.75, hy - r * 0.55), (hx + face * r * 1.0, hy - r * 0.1)]
        pg.draw.polygon(surf, look.hair, pts)
        pg.draw.polygon(surf, ink, pts, max(2, w // 2))
    if "topknot" in look.extras:
        pg.draw.circle(surf, look.extra_colour.get("topknot", (250, 250, 250)), (int(hx - face * r * 0.2), int(hy - r * 1.15)), int(r * 0.42))
        pg.draw.circle(surf, ink, (int(hx - face * r * 0.2), int(hy - r * 1.15)), int(r * 0.42), max(2, w // 2))
    if "feather" in look.extras:                          # a peacock feather standing up behind the head
        fx, fy = hx - face * r * 0.4, hy - r * 1.3
        pg.draw.line(surf, (40, 120, 60), (hx - face * r * 0.2, hy - r * 0.8), (fx, fy), max(2, w // 2))
        pg.draw.ellipse(surf, (30, 150, 90), (fx - r * 0.35, fy - r * 0.6, r * 0.7, r * 0.95))
        pg.draw.ellipse(surf, (40, 90, 210), (fx - r * 0.2, fy - r * 0.38, r * 0.4, r * 0.5))
        pg.draw.circle(surf, (250, 200, 60), (int(fx), int(fy - r * 0.12)), int(r * 0.1))
    if "crown" in look.extras:
        cw = r * 1.2
        pts = [(hx - cw / 2, hy - r * 0.8), (hx - cw / 2, hy - r * 1.35), (hx - cw / 4, hy - r * 1.05),
               (hx, hy - r * 1.45), (hx + cw / 4, hy - r * 1.05), (hx + cw / 2, hy - r * 1.35), (hx + cw / 2, hy - r * 0.8)]
        pg.draw.polygon(surf, (250, 200, 60), pts)
        pg.draw.polygon(surf, ink, pts, max(2, w // 2))
    if "tilak" in look.extras:
        pg.draw.line(surf, (220, 40, 30), (hx + face * r * 0.25, hy - r * 0.7), (hx + face * r * 0.25, hy - r * 0.35), max(2, w // 2))

    # the face, turned the way the figure faces
    ex = [hx + face * r * 0.05, hx + face * r * 0.5]
    ey = hy - r * 0.08
    m = look.mood
    er = max(2, int(r * 0.11))
    for i, x0 in enumerate(ex):
        if m == "happy":
            pg.draw.arc(surf, ink, (x0 - r * 0.14, ey - r * 0.1, r * 0.28, r * 0.24), 0.3, 2.8, max(2, w // 2))
        elif m == "closed":
            pg.draw.line(surf, ink, (x0 - r * 0.12, ey), (x0 + r * 0.12, ey), max(2, w // 2))
        else:
            pg.draw.circle(surf, ink, (int(x0), int(ey)), er if m != "shock" else int(er * 1.4))
        inner = (i == 0) == (face > 0)                    # which end of the brow is nearer the nose
        lo, hi = (r * 0.06, -r * 0.16)
        if m == "angry":
            a = (x0 - r * 0.17, ey - r * (0.38 if inner else 0.2) + (0 if inner else 0))
            b = (x0 + r * 0.17, ey - r * 0.2)
            a, b = ((x0 - r * 0.17, ey - r * 0.38), (x0 + r * 0.17, ey - r * 0.2)) if (face > 0) == (i == 0) else \
                   ((x0 - r * 0.17, ey - r * 0.2), (x0 + r * 0.17, ey - r * 0.38))
            pg.draw.line(surf, ink, a, b, max(3, int(w * 0.9)))
        elif m in ("worried", "shy"):
            a, b = ((x0 - r * 0.17, ey - r * 0.3), (x0 + r * 0.17, ey - r * 0.42)) if (face > 0) == (i == 0) else \
                   ((x0 - r * 0.17, ey - r * 0.42), (x0 + r * 0.17, ey - r * 0.3))
            pg.draw.line(surf, ink, a, b, max(2, int(w * 0.7)))
        elif m == "shock":
            pg.draw.arc(surf, ink, (x0 - r * 0.16, ey - r * 0.55, r * 0.32, r * 0.25), 0.3, 2.8, max(2, int(w * 0.6)))
    mx, my = hx + face * r * 0.3, hy + r * 0.42
    if m == "angry":
        rect = pg.Rect(0, 0, int(r * 0.7), int(r * 0.28))
        rect.center = (int(mx), int(my))
        pg.draw.rect(surf, (255, 255, 255), rect)
        pg.draw.rect(surf, ink, rect, max(2, w // 2))
        for k in range(1, 4):
            xx = rect.left + rect.width * k / 4
            pg.draw.line(surf, ink, (xx, rect.top), (xx, rect.bottom), max(1, w // 4))
    elif m == "shock":
        pg.draw.ellipse(surf, ink, (mx - r * 0.14, my - r * 0.18, r * 0.28, r * 0.38))
    elif m in ("happy", "neutral"):
        pg.draw.arc(surf, ink, (mx - r * 0.28, my - r * 0.3, r * 0.56, r * 0.4), math.pi + 0.3, 2 * math.pi - 0.3, max(2, w // 2))
    elif m in ("worried", "shy", "closed"):
        pts = [(mx - r * 0.22 + k * r * 0.11, my + (r * 0.05 if k % 2 else -r * 0.03)) for k in range(5)]
        pg.draw.lines(surf, ink, False, pts, max(2, w // 2))
    if "mustache" in look.extras:
        for side in (-1, 1):
            pg.draw.ellipse(surf, ink, (mx + side * r * 0.19 - r * 0.2, my - r * 0.24, r * 0.4, r * 0.15))
    if "beard" in look.extras:                            # a white sage's beard hanging from the jaw
        pts = [(hx - face * r * 0.35, hy + r * 0.62), (hx + face * r * 0.85, hy + r * 0.55),
               (hx + face * r * 0.3, hy + r * 1.95)]
        pg.draw.polygon(surf, (250, 250, 250), pts)
        pg.draw.polygon(surf, ink, pts, max(2, w // 2))
    if look.blush > 0:
        b = pg.Surface((int(r * 0.6), int(r * 0.3)), pg.SRCALPHA)
        pg.draw.ellipse(b, (255, 90, 110, int(170 * look.blush)), b.get_rect())
        for x0 in ex:
            surf.blit(b, b.get_rect(center=(x0, ey + r * 0.32)))
    return {"head": head, "hands": hands, "mouth": (mx, my), "feet": feet, "r": r, "neck": neck}
