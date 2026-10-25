"""algo_race: the same maze, three search algorithms, one exit. "Which one escapes first?"

Each lane runs a different algorithm (BFS, DFS, A*, greedy best-first) on an identical seeded
maze, expanding cells at the same pace. The winner is the one that needs the fewest steps,
which depends on the maze, so it is not always A*. A twist can give the slowest a turbo boost.
"""
import heapq
import math
from collections import deque

import numpy as np

from ..core.audio import SR, SoundBank, overlay, tone
from ..core.canvas import ARENA_L, W
from ..core.text import outlined
from . import EndCard, Format, Option, Twist, register

NODES_W, NODES_H = 24, 10            # maze nodes; the cell grid is (2n+1) in each direction
CELL = 20
LANE_X = (W - (2 * NODES_W + 1) * CELL) // 2
LANE_Y = [430, 900, 1370]
LANE_H = (2 * NODES_H + 1) * CELL
WIN_AT = (14.0, 20.0)                # seconds of play when the winner finds the exit
AFTER_WIN_S = 2.5                    # the others keep searching this long after the winner
PATH_DRAW_S = 0.8
DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]
MIN_APART = 10                       # minimum node distance between start and exit

ALGOS = {
    "BFS": ((70, 170, 255), "explores evenly in every direction"),
    "DFS": ((255, 90, 160), "picks a path and goes deep"),
    "A*": ((120, 230, 90), "weighs distance travelled and distance left"),
    "GREEDY": ((255, 190, 40), "always rushes towards the exit"),
    "RIGHT HAND": ((190, 140, 255), "keeps one hand on the wall"),
}
LINEUP_WEIGHT = {"BFS": 0.5, "DFS": 1.0, "A*": 1.0, "GREEDY": 1.0, "RIGHT HAND": 1.0}
WIN_RATE = {"GREEDY": 0.89, "A*": 0.31, "DFS": 0.26, "RIGHT HAND": 0.11, "BFS": 0.06}  # measured, 200 races
WALK_CAP = 6                          # a wall follower that walks this many times the open cells is lost


def make_maze(rng, loops: int) -> np.ndarray:
    """Recursive-backtracker maze (True = wall) with a few extra openings so routes differ."""
    g = np.ones((2 * NODES_H + 1, 2 * NODES_W + 1), dtype=bool)
    stack, seen = [(0, 0)], {(0, 0)}
    g[1, 1] = False
    while stack:
        r, c = stack[-1]
        nbrs = [(r + dr, c + dc) for dr, dc in DIRS
                if 0 <= r + dr < NODES_H and 0 <= c + dc < NODES_W and (r + dr, c + dc) not in seen]
        if not nbrs:
            stack.pop()
            continue
        nr, nc = rng.choice(nbrs)
        g[2 * nr + 1, 2 * nc + 1] = False
        g[r + nr + 1, c + nc + 1] = False
        seen.add((nr, nc))
        stack.append((nr, nc))
    opened = 0
    while opened < loops:
        r, c = rng.randrange(1, 2 * NODES_H), rng.randrange(1, 2 * NODES_W)
        if g[r, c] and (r % 2) != (c % 2):
            g[r, c] = False
            opened += 1
    return g


def search(g, start, goal, kind: str, dfs_dirs) -> tuple[list, dict]:
    """Cells in the order the algorithm expands them, and the parent links to rebuild its path."""
    order, parent = [], {start: None}
    if kind == "RIGHT HAND":
        return wall_follow(g, start, goal)

    def h(p):
        return abs(goal[0] - p[0]) + abs(goal[1] - p[1])

    if kind in ("A*", "GREEDY"):
        cost = {start: 0}
        heap = [(h(start), 0, start)]
        done = set()
        while heap:
            _, _, p = heapq.heappop(heap)
            if p in done:
                continue
            done.add(p)
            order.append(p)
            if p == goal:
                break
            for dr, dc in DIRS:
                q = (p[0] + dr, p[1] + dc)
                if g[q] or q in done:
                    continue
                if kind == "A*":
                    if q not in cost or cost[p] + 1 < cost[q]:
                        cost[q], parent[q] = cost[p] + 1, p
                        heapq.heappush(heap, (cost[q] + h(q), len(order), q))
                elif q not in parent:
                    parent[q] = p
                    heapq.heappush(heap, (h(q), len(order), q))
        return order, parent
    box, seen = deque([start]), {start}
    while box:
        p = box.popleft() if kind == "BFS" else box.pop()
        order.append(p)
        if p == goal:
            break
        for dr, dc in (DIRS if kind == "BFS" else dfs_dirs[::-1]):
            q = (p[0] + dr, p[1] + dc)
            if not g[q] and q not in seen:
                seen.add(q)
                parent[q] = p
                box.append(q)
    return order, parent


def wall_follow(g, start, goal) -> tuple[list, dict]:
    """Right-hand rule: turn right if you can, else straight, else left, else back.

    In a maze with loops the walker can circle an island forever; then it gives up (is lost)
    after WALK_CAP times the number of open cells.
    """
    order, parent = [start], {start: None}
    cap = WALK_CAP * int((~g).sum())
    p, d = start, 0
    while p != goal and len(order) < cap:
        for turn in (1, 0, 3, 2):                  # right, straight, left, back
            nd = (d + turn) % 4
            q = (p[0] + DIRS[nd][0], p[1] + DIRS[nd][1])
            if not g[q]:
                if q not in parent:
                    parent[q] = p
                p, d = q, nd
                order.append(p)
                break
    return order, parent


def weighted_lineup(rng, k: int = 3) -> list[str]:
    pool, picked = sorted(ALGOS), []
    while len(picked) < k:
        names = [n for n in pool if n not in picked]
        picked.append(rng.choices(names, [LINEUP_WEIGHT[n] for n in names])[0])
    return picked


class Lane:
    def __init__(self, name, order, parent, goal):
        self.name = name
        self.colour, self.blurb = ALGOS[name]
        self.order = order
        self.steps = len(order)
        self.path = []
        p = goal if goal in parent else None
        while p is not None:
            self.path.append(p)
            p = parent[p]
        self.path.reverse()
        self.reached = goal in parent
        self.lost = False
        self.shown = 0.0          # cells expanded so far (fractional)
        self.boost = 1.0
        self.finish_t: float | None = None     # play time it found the exit
        self.finish_video: float | None = None
        self.rank: int | None = None
        self.painted = 0          # cells already painted onto the lane surface (drawing only)


@register
class AlgoRace(Format):
    name = "algo_race"
    order = 80
    default_duration = 30.0
    options = (Option("--algos", "algo_race: three of BFS, DFS, A*, GREEDY, RIGHT HAND, comma separated",
                      {"default": None}),)
    wins = ("found",)
    cta = "Which one did you pick?"

    def setup(self) -> None:
        rng = self.rng
        self.grid = make_maze(rng, loops=rng.randint(12, 40))
        rows, cols = self.grid.shape
        self.start, self.goal = self.place_ends(rng)
        picked = getattr(self.opts, "algos", None)
        names = [a.strip().upper() for a in picked.split(",")] if picked else weighted_lineup(rng)
        if len(names) != 3 or any(n not in ALGOS for n in names):
            raise SystemExit(f"--algos needs three of: {', '.join(ALGOS)}")
        dfs_dirs = rng.sample(DIRS, 4)
        self.lanes = [Lane(n, *search(self.grid, self.start, self.goal, n, dfs_dirs), self.goal) for n in names]
        best = min((lane.steps for lane in self.lanes if lane.reached), default=200)
        self.rate = best / rng.uniform(*WIN_AT)          # cells per second, the same for every lane
        self.done_count = 0
        self.settled = 0
        self.winner: Lane | None = None
        self.end_play: float | None = None

    @staticmethod
    def place_ends(rng) -> tuple[tuple[int, int], tuple[int, int]]:
        """Start and exit anywhere in the maze, far enough apart for a race."""
        while True:
            a = (rng.randrange(NODES_H), rng.randrange(NODES_W))
            b = (rng.randrange(NODES_H), rng.randrange(NODES_W))
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) >= MIN_APART:
                return (2 * a[0] + 1, 2 * a[1] + 1), (2 * b[0] + 1, 2 * b[1] + 1)

    def title_hooks(self) -> list[str]:
        names = " vs ".join(lane.name for lane in self.lanes)
        return ["Same maze. 3 brains. Which escapes first?", f"{names}: who finds the exit?",
                "Pick one before they start!", "Which algorithm solves the maze first?"]

    def twists(self) -> list[Twist]:
        return [Twist("turbo", "the slowest one got a turbo boost", self._turbo, banner="TURBO!")]

    def _turbo(self, t: float) -> str:
        racing = [lane for lane in self.lanes if lane.finish_t is None and not lane.lost]
        if not racing:
            return "too late for a boost"
        slow = max(racing, key=lambda lane: (lane.steps - lane.shown) / lane.boost)
        slow.boost = 2.0
        return f"{slow.name} now searches twice as fast"

    # ---------------------------------------------------------- simulation
    def step(self, dt: float, t: float) -> None:
        for i, lane in enumerate(self.lanes):
            if lane.finish_t is not None or lane.lost:
                continue
            before = int(lane.shown)
            lane.shown = min(lane.steps, lane.shown + self.rate * lane.boost * dt)
            if int(lane.shown) > before:
                frac = lane.shown / lane.steps
                self.sfx(t, "tick", i * 5 + min(4, int(frac * 5)))
            if lane.shown >= lane.steps and not lane.reached:
                lane.lost, lane.finish_video = True, t
                self.settled += 1
                self.sfx(t, "lost", force=True)
                continue
            if lane.shown >= lane.steps:
                self.settled += 1
                self.done_count += 1
                lane.finish_t, lane.finish_video, lane.rank = self.play_t, t, self.done_count
                self.sfx(t, "found", force=True)
                if self.winner is None:
                    self.winner = lane
                    self.mark("decisive")
                    self.end_play = self.play_t + AFTER_WIN_S
                    self.fx.shake(8, 0.3)

    def check_end(self, t: float):
        if self.end_play is not None and (self.play_t >= self.end_play or self.settled == len(self.lanes)):
            return "found"
        if self.settled == len(self.lanes):
            self.mark("decisive")
            return "lost"
        if self.play_t >= self.max_play:
            return "time"
        return None

    def stats(self) -> list[str]:
        return ["SAME MAZE", f"{len(self.lanes)} ALGORITHMS", f"0:{int(self.play_t):02d}"]

    def progress(self) -> float:
        return max(lane.shown / lane.steps for lane in self.lanes)

    def sample(self):
        return tuple(round(lane.shown / lane.steps, 3) for lane in self.lanes)

    def drama_score(self, trace) -> float:
        """Close finishes score best."""
        steps = sorted(lane.steps / lane.boost for lane in self.lanes if lane.reached) + [1e9, 1e9]
        gap = (steps[1] - steps[0]) / steps[0]
        s = 4 * (1 - min(1.0, gap / 0.4))
        if self.winner is not None:
            s += 3 * (1 - WIN_RATE.get(self.winner.name, 0.3))     # rarer winners score higher
        if trace.twist:
            s += 0.5
        return s

    def end_card(self) -> EndCard:
        if self.winner is None:
            return EndCard("NO ONE FOUND IT!", "the maze wins this time")
        return EndCard(f"{self.winner.name} WINS!", f"found the exit in {self.winner.steps} steps")

    def outcome(self):
        return {**super().outcome(), "winner": self.winner.name if self.winner else None,
                "steps": {lane.name: lane.steps for lane in self.lanes}}

    def sounds(self) -> SoundBank:
        ticks = []
        for base in (523.25, 659.25, 783.99):
            ticks += [tone(base * 2 ** (k / 12), 0.05, 60, harm=0.1) * 0.12 for k in (0, 2, 4, 7, 9)]
        clear = np.zeros(int(SR * 1.7), dtype=np.float32)
        for s, d in ((0, 0), (4, 0.08), (7, 0.16), (12, 0.24)):
            note = tone(523.25 * 2 ** (s / 12), 1.4, 3)
            clear[int(SR * d):int(SR * d) + len(note)] += note
        return {"tick": ticks,
                "lost": tone(300, 0.6, 5, chirp=-0.5) * 0.3,
                "found": overlay((0, tone(1046.5, 0.3, 10) * 0.3), (0.08, tone(1568, 0.4, 9) * 0.3)),
                "clear": clear * 0.35, "fail": tone(220, 1.0, 3, chirp=-0.4) * 0.4}

    # ---------------------------------------------------------- drawing
    def build(self) -> None:
        pg = self.pg
        self.bg = pg.Surface((W, 1920))
        self.bg.fill((12, 13, 22))
        rows, cols = self.grid.shape
        self.lane_surfs, self.lane_labels = [], []
        for lane in self.lanes:
            s = pg.Surface((cols * CELL, rows * CELL))
            for r in range(rows):
                for c in range(cols):
                    s.fill((50, 54, 74) if self.grid[r, c] else (14, 16, 26), (c * CELL, r * CELL, CELL, CELL))
            gr, gc = self.goal
            s.fill((255, 214, 64), (gc * CELL, gr * CELL, CELL, CELL))
            sr, sc = self.start
            s.fill((255, 255, 255), (sc * CELL, sr * CELL, CELL, CELL))
            self.lane_surfs.append(s)
            self.lane_labels.append((outlined(pg, self.fonts.stat, lane.name, lane.colour, 3),
                                     self.fonts.small.render(lane.blurb, True, (190, 190, 205))))

    def _paint(self, lane: Lane, surf) -> None:
        upto = int(lane.shown)
        for j in range(lane.painted, upto):
            r, c = lane.order[j]
            if (r, c) in (self.start, self.goal):
                continue
            k = 0.35 + 0.65 * j / max(1, lane.steps)
            col = tuple(int(v * k) for v in lane.colour)
            surf.fill(col, (c * CELL + 2, r * CELL + 2, CELL - 4, CELL - 4))
        lane.painted = max(lane.painted, upto)

    def draw_world(self, screen, t: float) -> None:
        pg = self.pg
        screen.blit(self.bg, (0, 0))
        for lane, surf, (name_s, blurb_s), y in zip(self.lanes, self.lane_surfs, self.lane_labels, LANE_Y):
            self._paint(lane, surf)
            screen.blit(surf, (LANE_X, y))
            screen.blit(name_s, (ARENA_L, y - 62))
            screen.blit(blurb_s, (ARENA_L + name_s.get_width() + 14, y - 44))
            if lane.lost:
                tag = outlined(pg, self.fonts.stat, "LOST!", (255, 90, 90), 3)
                screen.blit(tag, tag.get_rect(topright=(W - ARENA_L, y - 62)))
            elif lane.finish_video is not None:
                k = min(1.0, (t - lane.finish_video) / PATH_DRAW_S)
                pts = [(LANE_X + c * CELL + CELL / 2, y + r * CELL + CELL / 2)
                       for r, c in lane.path[:max(2, int(len(lane.path) * k))]]
                pg.draw.lines(screen, (255, 255, 255), False, pts, 6)
                place = {1: "1st!", 2: "2nd", 3: "3rd"}[lane.rank]
                tag = outlined(pg, self.fonts.stat, f"{place}  {lane.steps} steps",
                               (255, 214, 64) if lane.rank == 1 else (235, 235, 245), 3)
                screen.blit(tag, tag.get_rect(topright=(W - ARENA_L, y - 62)))
            elif int(lane.shown) > 0:
                r, c = lane.order[int(lane.shown) - 1]
                pg.draw.circle(screen, (255, 255, 255), (LANE_X + c * CELL + CELL / 2, y + r * CELL + CELL / 2), 7)
                cnt = self.fonts.mid.render(f"{int(lane.shown)} cells", True, (200, 200, 215))
                screen.blit(cnt, cnt.get_rect(topright=(W - ARENA_L, y - 56)))
        self.fx.draw_particles(screen)
