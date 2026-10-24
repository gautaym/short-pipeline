#!/usr/bin/env python3
"""Backwards-compatible entry point: `python brickreel.py --mode escape ...` runs `reel render`.

The original single-file script is in git history (commit 15cf46f).
"""
import sys

from reel_engine.cli import main

if __name__ == "__main__":
    sys.exit(main())
