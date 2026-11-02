"""Generate images with Stable Diffusion XL on the local GPU. Runs in the aienv environment.

    aienv/Scripts/python.exe ai/imagegen.py jobs.json

jobs.json: {"model": "stabilityai/stable-diffusion-xl-base-1.0" (or e.g. "Tongyi-MAI/Z-Image-Turbo"), "jobs": [
    {"prompt": "...", "negative": "...", "seed": 1, "width": 768, "height": 1344, "steps": 30,
     "guidance": 6.5, "out": "path/to/image.png"}, ...]}

Models are cached in models/hf (git-ignored). Writes a timing line per image to stdout.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "hf"))

import torch  # noqa: E402
from diffusers import AutoencoderKL, DiffusionPipeline, StableDiffusionXLPipeline  # noqa: E402

DEFAULT_NEGATIVE = ("photo, photorealistic, 3d render, blurry, low quality, watermark, signature, text, letters, "
                    "logo, deformed, extra limbs, extra fingers, bad anatomy, cropped")


def load(model: str):
    if "stable-diffusion-xl" not in model:
        # newer models (Z-Image, FLUX.2 klein) are too big for 12 GB at once: parts move to the GPU in turn
        pipe = DiffusionPipeline.from_pretrained(model, torch_dtype=torch.bfloat16)
        pipe.enable_model_cpu_offload()
        pipe.set_progress_bar_config(disable=True)
        return pipe
    pipe = StableDiffusionXLPipeline.from_pretrained(model, torch_dtype=torch.float16, variant="fp16",
                                                     use_safetensors=True)
    pipe.vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)
    return pipe


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    t0 = time.time()
    model = spec.get("model", "stabilityai/stable-diffusion-xl-base-1.0")
    sdxl = "stable-diffusion-xl" in model
    pipe = load(model)
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    for job in spec["jobs"]:
        t = time.time()
        g = torch.Generator("cuda").manual_seed(int(job.get("seed", 0)))
        extra = {"negative_prompt": job.get("negative", DEFAULT_NEGATIVE)} if "negative" in job or sdxl else {}
        img = pipe(prompt=job["prompt"], width=job.get("width", 768), height=job.get("height", 1344),
                   num_inference_steps=job.get("steps", 30 if sdxl else 9),
                   guidance_scale=job.get("guidance", 6.5 if sdxl else 0.0), generator=g, **extra).images[0]
        Path(job["out"]).parent.mkdir(parents=True, exist_ok=True)
        img.save(job["out"])
        print(f"{job['out']} {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
