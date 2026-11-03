"""Narration with Maya Research's Maya 2 Native (Apache 2.0), inside the maya-tts Docker container
(see docker/maya/Dockerfile), in one batch so the model loads once:

    docker exec maya-tts python /work/ai/tts_maya.py /work/<lines.json>

lines.json: {"language": "hi", "voice": "Abhay" or a clip name,
             "ref": "/work/models/voice_refs/aman.wav", "ref_text": "...", "ref_lang": "hi",
             "lines": [{"text": "...", "out": "/work/models/voice_cache/x.wav"}, ...]}

With "ref", the voice is cloned from that clip (3-10 s and its exact transcript), so one character
can speak Hindi and English in the same voice; otherwise "voice" is one of Maya's built-in voices.
"""
import json
import sys
import time
from pathlib import Path

import soundfile as sf
from maya3 import Maya3TTS


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    t0 = time.time()
    tts = Maya3TTS.from_pretrained("maya-research/maya2-native", max_seats=1)
    voice = spec["voice"]
    if spec.get("ref"):
        tts.register_voice(voice, ref_audio=spec["ref"], ref_text=spec["ref_text"], lang=spec.get("ref_lang", "hi"))
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    for line in spec["lines"]:
        t = time.time()
        wav = tts.generate(line["text"], lang=spec["language"], voice=voice)
        Path(line["out"]).parent.mkdir(parents=True, exist_ok=True)
        sf.write(line["out"], wav, 24000)
        print(f"{line['out']} {len(wav) / 24000:.1f}s audio in {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
