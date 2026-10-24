#!/usr/bin/env python3
"""Backwards-compatible entry point: `python brickreel.py --mode escape ...` runs `reel render`.

The original single-file script is kept in legacy/brickreel_v0.py for the parity check.
"""
import sys

from reel_engine.cli import main

if __name__ == "__main__":
    sys.exit(main())
