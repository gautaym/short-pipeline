"""Escape mazes.

Each maze is a list of strokes (polylines in normalised u/v space) plus the point where the
ball starts. Strokes reaching v < -1 open into the paddle area.
"""
import math


def _spiral():
    pts = [(0.0, -1.2), (0.0, -0.72)]
    turns, steps = 1.85, 90
    for i in range(1, steps + 1):
        k = i / steps
        a = -math.pi / 2 - k * turns * 2 * math.pi
        r = 0.72 - k * 0.58
        pts.append((r * math.cos(a), r * math.sin(a)))
    return [pts], pts[-1]


MAZES = {
    "trident": lambda: ([[(-0.72, 0.55), (0.72, 0.55)], [(0, 0.55), (0, -1.2)],
                         [(-0.1, 0.45), (-0.72, -0.2)], [(0.1, 0.45), (0.72, -0.2)]], (0, 0.55)),
    "arrow": lambda: ([[(0, -1.2), (0, 0.6)], [(-0.55, 0.05), (0, 0.62), (0.55, 0.05)]], (0, 0.5)),
    "zigzag": lambda: ([[(0, -1.2), (0, -0.65), (-0.65, -0.3), (0.65, 0.05), (-0.65, 0.4), (0.45, 0.68)]],
                       (0.45, 0.68)),
    "tree": lambda: ([[(0, -1.2), (0, 0.62)], [(0, -0.15), (-0.62, 0.3)], [(0, -0.15), (0.62, 0.3)],
                      [(0, 0.25), (-0.42, 0.6)], [(0, 0.25), (0.42, 0.6)]], (0, 0.62)),
    "lightning": lambda: ([[(0, -1.2), (0.05, -0.55), (-0.38, -0.2), (0.32, 0.18), (-0.12, 0.66)]],
                          (-0.12, 0.66)),
    "plus": lambda: ([[(0, -1.2), (0, 0.65)], [(-0.68, 0.12), (0.68, 0.12)]], (0, 0.65)),
    "box": lambda: ([[(0, -1.2), (0, -0.45)],
                     [(-0.58, -0.45), (0.58, -0.45), (0.58, 0.55), (-0.58, 0.55), (-0.58, -0.45)]],
                    (0, 0.55)),
    "spiral": _spiral,
}
