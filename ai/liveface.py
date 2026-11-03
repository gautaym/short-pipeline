"""A living face for a puppet picture, with LivePortrait (MIT), in lpenv:

    lpenv/Scripts/python ai/liveface.py <jobs.json>

jobs.json: [{"src": "stories/art/x/puppet_rama.png", "face": [cx, cy, size], "out": "dir",
             "seconds": 2.4, "fps": 30, "nod": 2.5, "turn": 3.0, "blinks": 1}, ...]

face is the face's centre and width as fractions of the picture (marked by hand when the puppet is
picked), so LivePortrait's InsightFace detector (non-commercial weights) is never used. The face crop
is animated with LivePortrait's own models: a gentle nod and turn of the head, and blinks via its
eye retargeting, as one loop that starts and ends on the still picture. Each frame is the whole
picture with only the face replaced (feathered in), saved as out/0000.png ...; the reel engine cuts
them out with the still picture's own outline.
"""
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
LP = ROOT / "models" / "LivePortrait"
sys.path.insert(0, str(LP))

from src.config.inference_config import InferenceConfig  # noqa: E402
from src.live_portrait_wrapper import LivePortraitWrapper  # noqa: E402
from src.utils.camera import get_rotation_matrix  # noqa: E402

OPEN_EYES = 0.35          # eye-open ratio assumed for a painted face (the landmark model is for photos)


def face_box(img: np.ndarray, face) -> tuple[int, int, int]:
    """The square crop around the face, a little larger than it so the head can move."""
    h, w = img.shape[:2]
    cx, cy, size = face
    side = int(size * w * 1.6)
    x0 = int(cx * w - side / 2)
    y0 = int(cy * h - side / 2)
    return x0, y0, side


def crop(img: np.ndarray, x0: int, y0: int, side: int) -> np.ndarray:
    h, w = img.shape[:2]
    pad = side
    padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    return padded[y0 + pad:y0 + pad + side, x0 + pad:x0 + pad + side]


def feather(side: int) -> np.ndarray:
    """A soft round mask: the animated face fades into the still picture towards the crop's edge."""
    yy, xx = np.mgrid[0:side, 0:side]
    r = np.hypot(xx - side / 2, yy - side / 2) / (side / 2)
    return np.clip((0.95 - r) / 0.3, 0, 1)[..., None]


def blink_amount(t: float, seconds: float, blinks: int) -> float:
    """0 = open, 1 = closed: quick blinks spaced through the loop (none at its seam)."""
    best = 0.0
    for i in range(blinks):
        centre = seconds * (i + 1) / (blinks + 1)
        d = abs(t - centre)
        best = max(best, max(0.0, 1 - d / 0.09))
    return best


def animate(lp: LivePortraitWrapper, job: dict) -> int:
    img = cv2.cvtColor(cv2.imread(str(ROOT / job["src"])), cv2.COLOR_BGR2RGB)
    x0, y0, side = face_box(img, job["face"])
    face = crop(img, x0, y0, side)
    src = lp.prepare_source(cv2.resize(face, (256, 256)))
    f_s = lp.extract_feature_3d(src)
    info = lp.get_kp_info(src)
    x_s = lp.transform_keypoint(info)
    seconds, fps = float(job.get("seconds", 2.4)), int(job.get("fps", 30))
    nod, turn, blinks = float(job.get("nod", 2.5)), float(job.get("turn", 3.0)), int(job.get("blinks", 1))
    n = int(seconds * fps)
    out = ROOT / job["out"]
    out.mkdir(parents=True, exist_ok=True)
    mask = feather(side)
    pitch0, yaw0, roll0 = info["pitch"], info["yaw"], info["roll"]
    for i in range(n):
        t = i / fps
        phase = 2 * math.pi * t / seconds
        pitch = pitch0 + nod * math.sin(phase)
        yaw = yaw0 + turn * math.sin(phase + 1.3)
        roll = roll0 + 0.6 * nod * math.sin(phase + 2.1)
        R = get_rotation_matrix(pitch, yaw, roll)
        x_d = info["scale"] * (info["kp"] @ R + info["exp"]) + info["t"]
        x_d = lp.stitching(x_s, x_d)
        b = blink_amount(t, seconds, blinks)
        if b > 0 and lp.stitching_retargeting_module is not None:
            ratio = torch.tensor([[OPEN_EYES, OPEN_EYES, OPEN_EYES * (1 - b)]], device=x_s.device, dtype=x_s.dtype)
            x_d = x_d + lp.retarget_eye(x_s, ratio)
        rendered = lp.parse_output(lp.warp_decode(f_s, x_s, x_d)["out"])[0]
        rendered = cv2.resize(rendered, (side, side), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        frame = img.copy()
        h, w = img.shape[:2]
        ax0, ay0, ax1, ay1 = max(0, x0), max(0, y0), min(w, x0 + side), min(h, y0 + side)
        sx0, sy0 = ax0 - x0, ay0 - y0
        part = rendered[sy0:sy0 + ay1 - ay0, sx0:sx0 + ax1 - ax0]
        m = mask[sy0:sy0 + ay1 - ay0, sx0:sx0 + ax1 - ax0]
        base = frame[ay0:ay1, ax0:ax1].astype(np.float32)
        frame[ay0:ay1, ax0:ax1] = (part * m + base * (1 - m)).astype(np.uint8)
        cv2.imwrite(str(out / f"{i:04d}.png"), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    return n


def main() -> None:
    jobs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    t0 = time.time()
    cfg = InferenceConfig()
    cfg.flag_use_half_precision = True
    lp = LivePortraitWrapper(inference_cfg=cfg)
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    for job in jobs:
        t = time.time()
        with torch.no_grad(), lp.inference_ctx():
            n = animate(lp, job)
        print(f"{job['out']}: {n} frames in {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
