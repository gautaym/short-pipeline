"""Canvas size, timing and the standard 9:16 layout shared by the vertical formats.

The layout puts the hook title at the top, a HUD row underneath, and the play arena below that.
"""
W, H = 1080, 1920
FPS = 30

# The simulation runs in fixed ticks, independent of the video frame rate. Normally a frame
# advances TICKS_PER_FRAME ticks; slow motion advances fewer, so it never changes the outcome.
TICK_HZ = 120
TICK = 1 / TICK_HZ
TICKS_PER_FRAME = TICK_HZ // FPS

ARENA_L, ARENA_R = 40, W - 40
ARENA_T = 340
LOST_Y = H - 40

INTRO_S = 1.5     # opening hook card; play starts after it
OUTRO_S = 2.8     # seconds the end card stays up
LOOP_S = 0.5      # last part of the outro crossfades back to the first frame
MIN_VIDEO_S = 20.0  # default shortest reel; a run that ends sooner holds its end card
