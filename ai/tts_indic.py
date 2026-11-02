"""Hindi (and other Indian-language) narration with AI4Bharat's Indic Parler-TTS (Apache 2.0).

Runs in its own ttsenv environment (parler-tts pins an older transformers that breaks diffusers in aienv),
in one batch so the model loads once:

    ttsenv/Scripts/python.exe ai/tts_indic.py lines.json

lines.json: {"speaker": "Rohit", "style": "...", "lines": [{"text": "...", "seed": 1, "out": "x.wav"}, ...]}
A line may set its own "speaker" and "style" to override the batch's.

The model is gated on Hugging Face: the token is read from secrets/hf_token.txt (never printed).
Generation samples randomly, so each line is seeded for repeatable output.
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "hf"))
token_file = ROOT / "secrets" / "hf_token.txt"
if token_file.exists():
    os.environ.setdefault("HF_TOKEN", token_file.read_text(encoding="utf-8").strip())

import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from parler_tts import ParlerTTSForConditionalGeneration  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402

MODEL = "ai4bharat/indic-parler-tts"
STYLE = ("{speaker} speaks in a calm, warm storytelling voice with a slightly expressive tone, at a moderate pace. "
         "The recording is very clear and close up, with no background noise.")


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL).to(device)
    tok = AutoTokenizer.from_pretrained(MODEL)
    desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    for line in spec["lines"]:
        t = time.time()
        style = line.get("style") or spec.get("style") or STYLE
        desc = style.format(speaker=line.get("speaker") or spec.get("speaker", "Rohit"))
        d = desc_tok(desc, return_tensors="pt").to(device)
        torch.manual_seed(int(line.get("seed", 0)))
        p = tok(line["text"], return_tensors="pt").to(device)
        audio = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                               prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        wav = audio.cpu().numpy().squeeze()
        Path(line["out"]).parent.mkdir(parents=True, exist_ok=True)
        sf.write(line["out"], wav, model.config.sampling_rate)
        print(f"{line['out']} {len(wav) / model.config.sampling_rate:.1f}s audio in {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
