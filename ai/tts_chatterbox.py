"""Narration with Resemble AI's Chatterbox Multilingual (MIT, V3 where installed, else V2). Runs in the cbenv environment,
in one batch so the model loads once:

    cbenv/Scripts/python.exe ai/tts_chatterbox.py lines.json

lines.json: {"language": "hi", "voice": "ref.wav" (optional), "hindi_pack": true (optional),
             "exaggeration": 0.5, "cfg_weight": 0.5, "check": true (optional),
             "lines": [{"text": "...", "seed": 1, "out": "x.wav"}, ...]}

"voice" is a short clip (5-10 s) whose voice the narration takes on; without it the model's
built-in voice is used. "hindi_pack" swaps in Resemble's Hindi-only finetune of the text model.
Every file carries Resemble's inaudible Perth watermark.

The model now and then garbles a line or babbles past its end. With "check", each line is
transcribed by Whisper (small, local) and compared with the script; a line scoring under
MATCH_OK is made again with a new seed, up to TRIES times, and the best take is kept.
"""
import difflib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "hf"))

import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: E402

MATCH_OK = 0.62     # good Hindi takes score 0.70-0.86 (Whisper's own spelling is loose); garbled ones ~0.5
TRIES = 4


def match(model, wav, sr: int, text: str, language: str) -> float:
    """How closely Whisper's transcript of the take matches the script, 0 to 1."""
    import numpy as np
    audio = np.interp(np.arange(int(len(wav) * 16000 / sr)) / 16000, np.arange(len(wav)) / sr, wav)
    heard = model.transcribe(audio.astype(np.float32), language=language, fp16=True)["text"]
    def norm(t: str) -> str:
        return re.sub(r"[^\w]", "", t.lower())
    return difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()


def hindi_pack(model) -> None:
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    state = load_file(hf_hub_download("ResembleAI/Chatterbox-Multilingual-hi", "t3_hi.safetensors"))
    missing, unexpected = model.t3.load_state_dict(state, strict=False)
    print(f"hindi pack: {len(state)} tensors, {len(missing)} missing, {len(unexpected)} unexpected", flush=True)


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
    except TypeError:                       # releases before V3 (chatterbox-tts 0.1.x) ship V2 only
        model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    if spec.get("hindi_pack"):
        hindi_pack(model)
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    kwargs = {"language_id": spec.get("language", "hi"),
              "exaggeration": spec.get("exaggeration", 0.5), "cfg_weight": spec.get("cfg_weight", 0.5)}
    if spec.get("voice"):
        kwargs["audio_prompt_path"] = spec["voice"]
    checker = None
    if spec.get("check"):
        import whisper
        checker = whisper.load_model("small", device=device, download_root=str(ROOT / "models" / "whisper"))
    for line in spec["lines"]:
        t = time.time()
        best, best_score = None, -1.0
        for attempt in range(TRIES if checker else 1):
            torch.manual_seed(int(line.get("seed", 0)) + 1000 * attempt)
            wav = model.generate(line["text"], **kwargs).squeeze().cpu().numpy()
            score = match(checker, wav, model.sr, line["text"], kwargs["language_id"]) if checker else 1.0
            if score > best_score:
                best, best_score = wav, score
            if score >= MATCH_OK:
                break
        Path(line["out"]).parent.mkdir(parents=True, exist_ok=True)
        sf.write(line["out"], best, model.sr)
        note = f", match {best_score:.2f} after {attempt + 1} take(s)" if checker else ""
        print(f"{line['out']} {len(best) / model.sr:.1f}s audio in {time.time() - t:.1f}s{note}", flush=True)


if __name__ == "__main__":
    main()
