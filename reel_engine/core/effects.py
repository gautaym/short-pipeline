"""Visual effects shared by every format: particle bursts, floating text, flash, screen shake
and a slow-motion vignette.

Effects draw randomness from their own RNG stream, never the gameplay one, so switching them
off (as seed scouting does for speed) cannot change how a reel plays out.
"""
import math

import numpy as np

from .canvas import H, W

_vignette = None


def vignette(pg):
    """A dark radial edge, transparent in the middle, built once per process."""
    global _vignette
    if _vignette is None:
        x = (np.arange(W) - W / 2) / (W / 2)
        y = (np.arange(H) - H / 2) / (H / 2)
        d = np.sqrt(x[:, None] ** 2 + y[None, :] ** 2)
        alpha = (np.clip((d - 0.55) / 0.85, 0, 1) ** 1.6 * 230).astype(np.uint8)
        _vignette = pg.Surface((W, H), pg.SRCALPHA)
        _vignette.fill((0, 0, 0, 255))
        pg.surfarray.pixels_alpha(_vignette)[:] = alpha
    return _vignette


class Effects:
    def __init__(self, pg, rng, fonts):
        self.pg, self.rng, self.fonts = pg, rng, fonts
        self.enabled = True
        self.particles: list[list] = []      # [x, y, vx, vy, life, colour]
        self.floaters: list[list] = []       # [x, y, surface, life]
        self.flash = 0.0
        self.shake_amp = 0.0
        self.shake_left = 0.0
        self.shake_total = 1.0

    def burst(self, x: float, y: float, colour, n: int = 7, power: float = 1.0) -> None:
        if not self.enabled:
            return
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(120, 420) * power
            self.particles.append([x, y, sp * math.cos(a), sp * math.sin(a) - 150,
                                   self.rng.uniform(0.4, 0.9), colour])

    def floater(self, x: float, y: float, text: str, colour=(255, 236, 120), font=None, life: float = 1.0) -> None:
        if not self.enabled:
            return
        surf = (font or self.fonts.floater).render(text, True, colour)
        self.floaters.append([x, y, surf, life])

    def shake(self, amp: float, duration: float) -> None:
        """Shake the play area by up to amp pixels, fading out over duration seconds."""
        if amp >= self.current_shake():
            self.shake_amp, self.shake_left, self.shake_total = amp, duration, duration

    def current_shake(self) -> float:
        return self.shake_amp * self.shake_left / self.shake_total if self.shake_left > 0 else 0.0

    def shake_offset(self) -> tuple[int, int]:
        a = self.current_shake()
        if a < 0.5:
            return 0, 0
        return round(self.rng.uniform(-a, a)), round(self.rng.uniform(-a, a))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 900 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[1] -= 70 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.shake_left = max(0.0, self.shake_left - dt)

    def draw_particles(self, screen) -> None:
        for p in self.particles:
            size = max(2, int(10 * p[4]))
            self.pg.draw.rect(screen, p[5], (p[0], p[1], size, size))

    def draw_floaters(self, screen) -> None:
        for f in self.floaters:
            f[2].set_alpha(int(255 * min(1, f[3] * 1.6)))
            screen.blit(f[2], f[2].get_rect(center=(f[0], f[1])))

    def draw_flash(self, screen) -> None:
        if self.flash > 0:
            veil = self.pg.Surface((W, H), self.pg.SRCALPHA)
            veil.fill((255, 255, 255, int(150 * self.flash)))
            screen.blit(veil, (0, 0))

    def draw_vignette(self, screen, strength: float) -> None:
        v = vignette(self.pg)
        v.set_alpha(int(255 * max(0.0, min(1.0, strength))))
        screen.blit(v, (0, 0))
