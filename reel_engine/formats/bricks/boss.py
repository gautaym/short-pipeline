"""boss: a giant block with a big HP counter, ringed by power-up bricks."""
import numpy as np

from ...core.canvas import ARENA_T, FPS
from ...core.palette import hsv255
from ...core.physics import bounce_rect
from ...core.text import fit_width
from .. import EndCard, Option, Twist, register
from .classic import ClassicGame
from .shapes import uv


@register
class BossGame(ClassicGame):
    name = "boss"
    order = 30
    default_duration = 40.0
    options = (Option("--boss-hp", "boss mode starting HP", {"type": int, "default": None}),)

    series = "Boss Fight"
    tags = ("brick breaker", "boss fight", "satisfying", "simulation", "hp challenge")
    hashtags = ("satisfying", "bossfight", "simulation")

    @classmethod
    def titles(cls, o):
        hp, left, t = o["boss_hp_start"], o["boss_hp_left"], o["play_time"]
        if o["result"] == "win":
            return [f"{hp} HP boss down in {t}s", f"1 ball beat a {hp} HP boss", f"The {hp} HP block fell at {t}s",
                    f"Can 1 ball break {hp} HP? ({t}s)"]
        return [f"The boss survived on {left} HP", f"{hp} HP boss: {left} HP left at the buzzer",
                f"So close: boss lived with {left} HP", f"1 ball vs {hp} HP: the boss held on"]

    @classmethod
    def describe(cls, o):
        if o["result"] == "win":
            return f"One ball took down a {o['boss_hp_start']} HP boss in {o['play_time']} seconds."
        return f"The {o['boss_hp_start']} HP boss survived with {o['boss_hp_left']} HP left."

    def setup(self) -> None:
        self.grid(40, 4, 26, ARENA_T + 50)
        self.boss_hp0 = self.boss_hp = getattr(self.opts, "boss_hp", None) or self.rng.choice([160, 200, 250, 300])
        c0, c1 = self.cols // 2 - 4, self.cols // 2 + 4
        r0, r1 = 7, 15
        self.boss_cells = (r0, r1, c0, c1)
        self.boss_rect = (self.bx0 + c0 * self.cell + 2, self.by0 + r0 * self.cell + 2,
                          self.bx0 + (c1 + 1) * self.cell - 2, self.by0 + (r1 + 1) * self.cell - 2)
        u, v = uv(self.cols, self.rows)
        mask = u * u + v * v <= 0.97 ** 2
        mask[r0:r1 + 1, c0:c1 + 1] = False
        self.hp[:] = np.where(mask, self.nrng.choice([1, 2], size=mask.shape, p=[0.75, 0.25]), 0)
        self.place_powers(mask, 0.09)
        self.total = self.left = int(mask.sum())
        self.hp0 = self.hp.copy()
        self.make_palette()
        self.boss_col = hsv255((self.hue + 0.5) % 1, 0.75, 0.85)
        self.shake = 0.0
        self.shape, self.text = "boss", ""

    def title_hooks(self) -> list[str]:
        hp = self.boss_hp0
        return [f"1 ball vs a {hp} HP block", f"Can it break the {hp} HP boss?",
                f"{hp} HP. {int(self.max_play)} seconds. Go."]

    def twists(self) -> list[Twist]:
        return [Twist("rage", "the boss is furious", self._rage, lambda: self.boss_hp < 0.35 * self.boss_hp0,
                      banner="RAGE MODE!"),
                Twist("storm", "+15 BALLS!", lambda t: f"+{self.multiball(15)} BALLS!",
                      lambda: len(self.balls) <= 4)]

    def _rage(self, t: float) -> str:
        heal = int(0.3 * self.boss_hp0)
        self.boss_hp += heal
        n = self.regrow(0.25)
        return f"boss healed +{heal} HP and {n} bricks grew back"

    def on_destroy(self, r, c, t: float) -> None:
        pass

    def extra_collide(self, b, t: float) -> None:
        if self.boss_hp <= 0:
            return
        if bounce_rect(b, *self.boss_rect):
            self.boss_hp -= 1
            self.shake = 0.12
            self.sfx(t, "boss")
            if self.boss_hp <= 0:
                x0, y0, x1, y1 = self.boss_rect
                for _ in range(10):
                    self.fx.burst(self.fx.rng.uniform(x0, x1), self.fx.rng.uniform(y0, y1), self.boss_col, 8, 1.6)
                self.fx.flash = 1.0
                self.fx.shake(18, 0.7)
                self.mark("decisive")

    def draw_extra(self, screen, t: float) -> None:
        if self.boss_hp <= 0:
            return
        pg = self.pg
        x0, y0, x1, y1 = self.boss_rect
        self.shake = max(0.0, self.shake - 1 / FPS)
        j = 6 if self.shake > 0 else 0
        ox, oy = self.fx.rng.randint(-j, j), self.fx.rng.randint(-j, j)
        frac = self.boss_hp / self.boss_hp0
        col = tuple(int(c * (0.45 + 0.55 * frac)) for c in self.boss_col)
        rect = pg.Rect(x0 + ox, y0 + oy, x1 - x0, y1 - y0)
        pg.draw.rect(screen, col, rect, border_radius=14)
        pg.draw.rect(screen, (255, 255, 255), rect, 4, border_radius=14)
        num = fit_width(pg, self.fonts.huge.render(str(self.boss_hp), True, (255, 255, 255)), rect.width - 30)
        screen.blit(num, num.get_rect(center=rect.center))
        lab = self.fonts.mid.render("HP", True, (255, 255, 255))
        screen.blit(lab, lab.get_rect(midtop=(rect.centerx, rect.centery + 70)))
        bar = pg.Rect(rect.x + 20, rect.bottom - 30, rect.width - 40, 12)
        pg.draw.rect(screen, (40, 40, 50), bar, border_radius=6)
        pg.draw.rect(screen, (255, 90, 90), (bar.x, bar.y, int(bar.width * frac), bar.height), border_radius=6)

    def check_end(self, t: float):
        if self.boss_hp <= 0:
            return "win"
        if not self.balls:
            self.mark("decisive")
            return "fail"
        if self.play_t >= self.max_play:
            return "time"
        return None

    def stats(self) -> list[str]:
        return [f"BOSS HP {max(0, self.boss_hp)}", f"BALLS {len(self.balls)}", self.clock(self.play_t)]

    def progress(self) -> float:
        return 1 - max(0, self.boss_hp) / self.boss_hp0

    def end_card(self) -> EndCard:
        if self.done == "win":
            return EndCard("BOSS DOWN!", f"in {self.play_t:.1f} seconds")
        if self.done == "fail":
            return EndCard("OUT OF BALLS", f"boss had {self.boss_hp} HP left")
        return EndCard("TIME UP!", f"boss survived with {self.boss_hp} HP")

    def outcome(self):
        return {"result": self.done, "play_time": round(self.play_t, 1), "twist": self.twist_fired,
                "boss_hp_start": self.boss_hp0, "boss_hp_left": max(0, self.boss_hp)}
