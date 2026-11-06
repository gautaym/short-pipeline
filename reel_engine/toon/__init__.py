"""Toon videos: comedy skits in the rich, lit cartoon look (the user's "toon videos", chosen 2026-11-06).

Everything is drawn in code, so there are no image-model anatomy surprises: bean-bodied figures with
round heads, drawn at twice the size and scaled down, with two-tone shading, soft cast shadows, sunlit
patches, a vignette and light grain.

    kit.py            the drawing kit: bean() figures and their looks (saree with the pallu over the head,
                      side plait, bindi, kurta, bald with white tufts, glasses, buck teeth, crowns...),
                      the courtyard set, hens, shading helpers. `python -m reel_engine.toon.kit` makes a test clip.
    sheru.py          Stick Katha episode 2 ("Sheru") redrawn in this look; also the bedroom set, clouds,
                      divine rays, chakra and conch.
    positive_bhai.py  "Talking to a Really POSITIVE Friend" (Positive Bhai, part 1), for a separate channel.

Each skit is a module with LINES, VOICES, Skit and friends; voices, timing, captions, music and the mix
come from the shared skit renderer, reel_engine.stick.pressure_cooker.render.
"""
