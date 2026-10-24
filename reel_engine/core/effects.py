"""Visual effects shared by every format: particle bursts, floating text and a white flash."""
import math

from .canvas import H, W


class Effects:
    def __init__(self, pg, rng, fonts):
        self.pg, self.rng, self.fonts = pg, rng, fonts
        self.particles: list[list] = []      # [x, y, vx, vy, life, colour]
        self.floaters: list[list] = []       # [x, y, surface, life]
        self.flash = 0.0

    def burst(self, x: float, y: float, colour, n: int = 7, power: float = 1.0) -> None:
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            sp = self.rng.uniform(120, 420) * power
            self.particles.append([x, y, sp * math.cos(a), sp * math.sin(a) - 150,
                                   self.rng.uniform(0.4, 0.9), colour])

    def floater(self, x: float, y: float, text: str, colour=(255, 236, 120), font=None, life: float = 1.0) -> None:
        surf = (font or self.fonts.floater).render(text, True, colour)
        self.floaters.append([x, y, surf, life])

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
