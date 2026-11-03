"""Narration with Maya Research's Maya 2 Native (Apache 2.0), inside the maya-tts Docker container
(see docker/maya/Dockerfile), in one batch so the model loads once:

    docker exec maya-tts python /work/ai/tts_maya.py /work/<lines.json>

lines.json: {"language": "hi", "voice": "Akshat" or a clip name, "check": true (optional),
             "ref": "/work/models/voice_refs/aman.wav", "ref_text": "...", "ref_lang": "hi",
             "lines": [{"text": "...", "out": "/work/models/voice_cache/x.wav"}, ...]}

With "ref", the voice is cloned from that clip (3-10 s and its exact transcript), so one character
can speak Hindi and English in the same voice; otherwise "voice" is one of Maya's 20 built-in voices
(Akshat, Nakul, Sreekar, Charvi, Kayal, Nivedita, Vaidehi, Shaunak, ...), each fluent in both.

About one Hindi take in five comes out garbled. With "check", Whisper listens to each take and one
scoring under MATCH_OK is made again with a new seed, up to TRIES times; the best take is kept.

Lines may carry Maya's emotion tags, e.g. "[excited] And here is the surprise!" ([sad], [whispers],
[laughs], [sighs]); the model card calls them best effort, so they are listened to before use.
"""
import difflib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from maya3 import Maya3TTS

RATE = 24000
MATCH_OK = 0.62     # good Hindi takes score 0.67-0.80 (Whisper's own spelling is loose); garbled ones 0.2-0.6
TRIES = 4


def match(model, wav, text: str, language: str) -> float:
    """How closely Whisper's transcript of the take matches the script, 0 to 1."""
    audio = np.interp(np.arange(int(len(wav) * 16000 / RATE)) / 16000, np.arange(len(wav)) / RATE, wav)
    heard = model.transcribe(audio.astype(np.float32), language=language, fp16=True)["text"]
    def norm(t: str) -> str:
        return re.sub(r"[^\w]", "", re.sub(r"\[[a-z ]+\]", "", t.lower()))   # emotion tags are not spoken
    return difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    t0 = time.time()
    tts = Maya3TTS.from_pretrained("maya-research/maya2-native", max_seats=1)
    voice = spec["voice"]
    if spec.get("ref"):
        tts.register_voice(voice, ref_audio=spec["ref"], ref_text=spec["ref_text"], lang=spec.get("ref_lang", "hi"))
    checker = None
    if spec.get("check"):
        import whisper
        checker = whisper.load_model("small", device="cuda", download_root="/work/models/whisper")
    print(f"loaded in {time.time() - t0:.1f}s", flush=True)
    for line in spec["lines"]:
        t = time.time()
        best, best_score = None, -1.0
        for attempt in range(TRIES if checker else 1):
            wav = tts.generate(line["text"], lang=spec["language"], voice=voice, seed=1 + 1000 * attempt)
            score = match(checker, wav, line["text"], spec["language"]) if checker else 1.0
            if score > best_score:
                best, best_score = wav, score
            if score >= MATCH_OK:
                break
        Path(line["out"]).parent.mkdir(parents=True, exist_ok=True)
        sf.write(line["out"], best, RATE)
        note = f", match {best_score:.2f} after {attempt + 1} take(s)" if checker else ""
        print(f"{line['out']} {len(best) / RATE:.1f}s audio in {time.time() - t:.1f}s{note}", flush=True)


if __name__ == "__main__":
    main()
