import shutil

import pytest

from reel_engine.core.render import init_pygame


@pytest.fixture(scope="session")
def pg():
    return init_pygame()


needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg/ffprobe not on PATH")
