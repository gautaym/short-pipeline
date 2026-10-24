"""Constant-speed balls and ball-versus-rectangle bounces."""
import math

BALL_R = 10


class Ball:
    __slots__ = ("x", "y", "vx", "vy", "team", "speed", "trail")

    def __init__(self, x: float, y: float, angle: float, speed: float, team: int = 0):
        self.x, self.y = x, y
        self.speed, self.team = speed, team
        self.vx = speed * math.sin(angle)
        self.vy = -speed * math.cos(angle)
        self.trail: list[tuple[float, float]] = []     # recent positions, for drawing only
        self.renormalise()

    def renormalise(self) -> None:
        # constant speed, and no near-horizontal or near-vertical loops that drag on
        sp = math.hypot(self.vx, self.vy) or 1.0
        vx, vy = self.vx / sp, self.vy / sp
        if abs(vy) < 0.3:
            vy = math.copysign(0.3, vy or 1)
            vx = math.copysign(math.sqrt(1 - vy * vy), vx or 1)
        if abs(vx) < 0.08:
            vx = math.copysign(0.08, vx or 1)
            vy = math.copysign(math.sqrt(1 - vx * vx), vy)
        self.vx, self.vy = vx * self.speed, vy * self.speed


def bounce_rect(b: Ball, x0: float, y0: float, x1: float, y1: float, r: float = BALL_R) -> bool:
    """Reflect the ball off an axis-aligned rectangle if they overlap. Returns True on a hit."""
    nx = min(max(b.x, x0), x1)
    ny = min(max(b.y, y0), y1)
    dx, dy = b.x - nx, b.y - ny
    if dx * dx + dy * dy > r * r:
        return False
    if dx == 0 and dy == 0:
        b.vy = -b.vy
    elif abs(dx) > abs(dy):
        b.vx = math.copysign(abs(b.vx), dx)
        b.x = nx + math.copysign(r + 0.5, dx)
    else:
        b.vy = math.copysign(abs(b.vy), dy)
        b.y = ny + math.copysign(r + 0.5, dy)
    b.renormalise()
    return True
