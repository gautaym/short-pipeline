"""food_wars: colour wars where the teams are Indian foods. "BIRYANI vs DOSA vs PAV BHAJI"

Each food's ball converts the other foods' squares; the name floats over its territory so
viewers can follow their pick. Matchups stay within one category (mains, street food, sweets,
drinks) and every category has clearly different colours.
"""
import numpy as np

from ...core.text import outlined
from .. import EndCard, Option, register
from .wars import WarsGame

CATEGORIES = {
    "mains": ("dish", [("BIRYANI", (255, 140, 30)), ("DOSA", (245, 220, 90)), ("PAV BHAJI", (225, 50, 60)),
                       ("CHOLE BHATURE", (160, 110, 230))]),
    "street": ("street food", [("VADA PAV", (250, 190, 40)), ("PANI PURI", (80, 200, 110)),
                               ("MOMOS", (110, 170, 255)), ("SAMOSA", (230, 110, 50))]),
    "sweets": ("sweet", [("JALEBI", (255, 150, 20)), ("GULAB JAMUN", (190, 70, 60)), ("RASGULLA", (240, 240, 230)),
                         ("BARFI", (120, 210, 150))]),
    "drinks": ("drink", [("CHAI", (215, 145, 80)), ("COFFEE", (150, 100, 70)), ("LASSI", (245, 245, 235)),
                         ("NIMBU PANI", (190, 235, 80))]),
}


@register
class FoodWars(WarsGame):
    name = "food_wars"
    order = 70
    options = WarsGame.options + (Option("--category", "food_wars: " + ", ".join(CATEGORIES),
                                         {"choices": list(CATEGORIES), "default": None}),)
    cta = "Comment your favourite!"

    def setup(self) -> None:
        self.category = getattr(self.opts, "category", None) or self.rng.choice(sorted(CATEGORIES))
        super().setup()
        self.label_surfs = None

    def team_pool(self):
        return CATEGORIES[self.category][1]

    def title_hooks(self) -> list[str]:
        names = [n for n, _ in self.teams]
        noun = CATEGORIES[self.category][0]
        return [" vs ".join(names), f"Which {noun} takes the board?", "Comment your favourite before it ends!",
                f"{' vs '.join(names)}: who wins?"]

    def draw_world(self, screen, t: float) -> None:
        super().draw_world(screen, t)
        if self.label_surfs is None:
            self.label_surfs = [outlined(self.pg, self.fonts.mid, n, (255, 255, 255), 3) for n, _ in self.teams]
        for i, surf in enumerate(self.label_surfs):
            mine = self.owner == i
            if not mine.any():
                continue
            r, c = np.argwhere(mine).mean(axis=0)
            x, y = self.bx0 + (c + 0.5) * self.cell, self.by0 + (r + 0.5) * self.cell
            screen.blit(surf, surf.get_rect(center=(x, y)))

    def end_card(self) -> EndCard:
        i = self.winner()
        pct = round(100 * self.counts[i] / self.counts.sum())
        return EndCard(f"{self.teams[i][0]} WINS!", f"took {pct}% of the plate")

    def outcome(self):
        return {**super().outcome(), "category": self.category}
