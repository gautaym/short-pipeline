"""Canvas size and the standard 9:16 layout shared by the vertical formats.

The layout puts the hook title at the top, a HUD row underneath, and the play arena below that.
"""
W, H = 1080, 1920
FPS = 30

ARENA_L, ARENA_R = 40, W - 40
ARENA_T = 340
LOST_Y = H - 40

INTRO_S = 1.2     # seconds of still frame before play starts
OUTRO_S = 2.8     # seconds the end card stays up
