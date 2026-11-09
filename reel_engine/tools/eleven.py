"""Voice a skit's lines with ElevenLabs (eleven_v3), one mp3 per line, skipping lines already made.

    python -m reel_engine.tools.eleven out/<date>/<skit>/eleven/lines.json [--force N ...]

lines.json: {"voices": {"kid": "<voice_id>", ...}, "model": "eleven_v3",
             "lines": [{"n": 0, "who": "kid", "text": "[excited] ..."}, ...]}
Writes <dir>/NN_<who>.mp3 next to lines.json. Before calling, it prints the characters it will spend.

The key comes from $ELEVENLABS_API_KEY, or secrets/elevenlabs_key.txt on the PC. In a cloud session the network
proxy injects the saved key, so any placeholder works there. The key is never printed.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

from ..config import REPO_ROOT

API = "https://api.elevenlabs.io/v1"


def key() -> str:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    f = REPO_ROOT / "secrets" / "elevenlabs_key.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else "proxy-injected"


def call(path: str, body: dict | None = None) -> bytes:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def credits() -> tuple[int, int]:
    d = json.loads(call("/user/subscription"))
    return d["character_count"], d["character_limit"]


def main(spec_path: Path, force: set[int]):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out = spec_path.parent
    todo = [L for L in spec["lines"] if L["n"] in force or not (out / f"{L['n']:02d}_{L['who']}.mp3").exists()]
    used, limit = credits()
    cost = sum(len(L["text"]) for L in todo)
    print(f"{len(todo)} lines, ~{cost} credits; {limit - used} of {limit} left before")
    for L in todo:
        body = {"text": L["text"], "model_id": spec.get("model", "eleven_v3"),
                "voice_settings": {"stability": L.get("stability", spec.get("stability", 0.5))}}
        audio = call(f"/text-to-speech/{spec['voices'][L['who']]}?output_format=mp3_44100_128", body)
        (out / f"{L['n']:02d}_{L['who']}.mp3").write_bytes(audio)
        print(f"  {L['n']:02d} {L['who']:6s} {L['text']}")
    used, limit = credits()
    print(f"{limit - used} of {limit} credits left")


if __name__ == "__main__":
    args = sys.argv[1:]
    force = {int(a) for a in args[args.index("--force") + 1:]} if "--force" in args else set()
    main(Path(args[0]), force)
