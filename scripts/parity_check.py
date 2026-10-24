#!/usr/bin/env python3
"""Check that reel_engine renders exactly what the original brickreel.py rendered.

Runs a matrix of formats, seeds and option variants in parallel and prints one line per case.
Exits non-zero if any case differs.

    python scripts/parity_check.py               # standard matrix
    python scripts/parity_check.py --quick       # a few short cases
"""
import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reel_engine.formats.bricks.mazes import MAZES  # noqa: E402
from reel_engine.formats.bricks.shapes import SHAPES  # noqa: E402
from reel_engine.tools.parity import compare  # noqa: E402


def cases(quick: bool) -> list[tuple[str, int, dict]]:
    if quick:
        return [(m, s, {"max_play": 3}) for m in ("classic", "escape", "boss", "wars") for s in (1, 2)]
    out = []
    for m in ("classic", "escape", "boss", "wars"):
        out += [(m, s, {"max_play": 8}) for s in range(20)]
        out += [(m, s, {}) for s in (100, 101)]                     # full length
    out += [("classic", 7, {"shape": sh, "max_play": 5}) for sh in SHAPES]
    out += [("classic", 8, {"shape": "text", "text": "win", "max_play": 5})]
    out += [("escape", 9, {"shape": mz, "max_play": 12}) for mz in MAZES]
    out += [("wars", 10, {"teams": n, "max_play": 10}) for n in (2, 3, 4)]
    out += [("boss", 11, {"boss_hp": 40, "max_play": 20}), ("boss", 12, {"boss_hp": 999, "max_play": 5})]
    out += [("classic", 13, {"title": "Custom hook line here", "max_play": 3})]
    return out


def run(case):
    mode, seed, kw = case
    return case, compare(mode, seed, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = ap.parse_args()
    todo = cases(args.quick)
    start, failed = time.time(), 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for (mode, seed, kw), (ok, msg) in ex.map(run, todo):
            failed += not ok
            print(f"{'OK  ' if ok else 'FAIL'} {mode:8} seed={seed:<4} {kw}  {msg}", flush=True)
    print(f"\n{len(todo) - failed}/{len(todo)} cases identical in {time.time() - start:.0f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
