"""Spoken lines (the hook, the result) with Kokoro, an open text-to-speech model (Apache 2.0).

The model files live in models/ (git-ignored): kokoro-v1.0.onnx and voices-v1.0.bin from the
kokoro-onnx releases. If they are missing, reels render without a voice.

Two larger local models run as batch scripts in their own environments instead:
  "chatterbox:<lang>[:<ref>]"     Resemble AI's Chatterbox Multilingual (MIT), ai/tts_chatterbox.py
                                  in cbenv. <ref> names models/voice_refs/<ref>.wav, a short clip whose
                                  voice it takes on (none: the model's own voice). Every line is checked
                                  with Whisper and remade if it comes out garbled.
  "indic:<Speaker>[:<style>]"     AI4Bharat's Indic Parler-TTS (Apache 2.0), ai/tts_indic.py in ttsenv.
Their lines are made in one batch per story (prepare) and cached on disk in models/voice_cache, so
a story is only ever voiced once.
"""
import hashlib
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT
from .audio import SR

MODEL = REPO_ROOT / "models" / "kokoro-v1.0.onnx"
VOICES = REPO_ROOT / "models" / "voices-v1.0.bin"
KEEP_CAPS = {"BFS", "DFS", "HP"}          # read letter by letter
CACHE = REPO_ROOT / "models" / "voice_cache"
REFS = REPO_ROOT / "models" / "voice_refs"
BACKENDS = {                              # voice prefix -> (environment's python, batch script)
    "indic": (REPO_ROOT / "ttsenv" / "Scripts" / "python.exe", REPO_ROOT / "ai" / "tts_indic.py"),
    "chatterbox": (REPO_ROOT / "cbenv" / "Scripts" / "python.exe", REPO_ROOT / "ai" / "tts_chatterbox.py"),
    "maya": (None, REPO_ROOT / "ai" / "tts_maya.py"),   # runs in the maya-tts Docker container
}
MAYA_CONTAINER = "maya-tts"
INDIC_STYLES = {
    "warm": ("{speaker} speaks in a calm, warm storytelling voice with a slightly expressive tone, at a moderate pace. "
             "The recording is very clear and close up, with no background noise."),
    "deep": ("{speaker} speaks in a deep, slow, dramatic storytelling voice with an expressive tone, like narrating "
             "an epic. The recording is very clear and close up, with no background noise."),
}
_engine = None
_cache: dict[tuple, np.ndarray] = {}


def backend(voice: str) -> str | None:
    """"indic" or "chatterbox" for voices made by a batch script, None for Kokoro voices."""
    prefix = voice.split(":", 1)[0]
    return prefix if ":" in voice and prefix in BACKENDS else None


def available(voice: str = "") -> bool:
    voice = voice.partition("@")[0]
    if backend(voice) == "maya":
        found = subprocess.run(["docker", "ps", "-q", "-f", f"name={MAYA_CONTAINER}"], capture_output=True, text=True)
        return bool(found.stdout.strip())
    if backend(voice):
        return all(p.exists() for p in BACKENDS[backend(voice)])
    if not (MODEL.exists() and VOICES.exists()):
        return False
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        return False
    return True


def speakable(text: str) -> str:
    """Turn on-screen text (often in capitals) into something that reads naturally aloud."""
    text = text.replace("A*", "A star").replace(" vs ", " versus ").replace("%", " percent")
    words = []
    for w in text.split():
        core = re.sub(r"[^A-Za-z]", "", w)
        words.append(w if core in KEEP_CAPS else w.lower())
    out = " ".join(words)
    out = re.sub(r"([.!?:]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out[:1].upper() + out[1:]


def language(voice: str) -> str:
    """Kokoro voice names start with a language letter: a = US, b = UK English, h = Hindi."""
    return {"b": "en-gb", "h": "hi"}.get(voice[:1], "en-us")


def _cached(text: str, voice: str) -> Path:
    return CACHE / (hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:16] + ".wav")


def _batch_spec(voice: str) -> dict:
    kind, *args = voice.split(":")
    if kind == "indic":
        return {"speaker": args[0], "style": INDIC_STYLES[args[1] if len(args) > 1 else "warm"]}
    if kind == "maya":                        # maya:<lang>:<clip in voice_refs, cloned> or a built-in voice name
        spec = {"language": args[0], "voice": args[1], "check": True}
        ref, text = REFS / f"{args[1]}.wav", REFS / f"{args[1]}.txt"
        if ref.exists() and text.exists():
            spec.update(ref=_in_container(ref), ref_text=text.read_text(encoding="utf-8").strip(),
                        ref_lang=(REFS / f"{args[1]}.lang").read_text().strip()
                        if (REFS / f"{args[1]}.lang").exists() else "hi")
        return spec
    spec = {"language": args[0], "check": True}
    if len(args) > 1:
        spec["voice"] = str(REFS / f"{args[1]}.wav")
    return spec


def _in_container(path: Path) -> str:
    """A repo path as the maya-tts container sees it (the repo is mounted at /work)."""
    return "/work/" + Path(path).resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def prepare(texts: list[str], voice: str) -> None:
    """Make every missing line for a batch-script voice in one run, so the model loads once."""
    voice = voice.partition("@")[0]
    if not backend(voice):
        return
    missing = [t for t in dict.fromkeys(texts) if not _cached(t, voice).exists()]
    if not missing:
        return
    lines = [{"text": t, "seed": int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:6], 16),
              "out": str(_cached(t, voice))} for t in missing]
    python, script = BACKENDS[backend(voice)]
    CACHE.mkdir(parents=True, exist_ok=True)
    if backend(voice) == "maya":                           # the jobs file must be inside the mounted repo
        for line in lines:
            line["out"] = _in_container(Path(line["out"]))
        jobs = CACHE / "_maya_jobs.json"
        jobs.write_text(json.dumps({**_batch_spec(voice), "lines": lines}, ensure_ascii=False), encoding="utf-8")
        print(f"voicing {len(missing)} line(s) with {voice} ...", flush=True)
        subprocess.run(["docker", "exec", MAYA_CONTAINER, "python", _in_container(script), _in_container(jobs)],
                       check=True, cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    with tempfile.TemporaryDirectory() as tmp:
        jobs = Path(tmp) / "lines.json"
        jobs.write_text(json.dumps({**_batch_spec(voice), "lines": lines}, ensure_ascii=False), encoding="utf-8")
        print(f"voicing {len(missing)} line(s) with {voice} ...", flush=True)
        subprocess.run([str(python), str(script), str(jobs)], check=True, cwd=REPO_ROOT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _load_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        rate, width, n = w.getframerate(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if width == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0, rate
    return np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0, rate


def split_pitch(voice: str) -> tuple[str, float, float]:
    """"af_bella@+3~0.88" -> ("af_bella", 3.0, 0.88): a voice, semitones to raise it, and its pace."""
    base, _, rest = voice.partition("@")
    shift, _, pace = rest.partition("~")
    return base, float(shift) if shift else 0.0, float(pace) if pace else 1.0


def repitch(samples: np.ndarray, rate: int, semis: float, pace: float) -> np.ndarray:
    """Raise the pitch without hurrying the speech, then set its pace (ffmpeg: asetrate + atempo)."""
    from .video import find_tool
    ratio = 2 ** (semis / 12)
    tempo = pace / ratio                                   # undo the speed-up the pitch change brings
    chain = [f"asetrate={int(rate * ratio)}", f"aresample={rate}"]
    while tempo < 0.5:                                     # atempo takes 0.5-2 per stage
        chain.append("atempo=0.5")
        tempo /= 0.5
    chain.append(f"atempo={tempo:.4f}")
    run = subprocess.run([find_tool(), "-v", "error", "-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-",
                          "-af", ",".join(chain), "-f", "f32le", "-"],
                         input=samples.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(run.stdout, dtype=np.float32).copy()


def say(text: str, voice: str = "am_michael", speed: float = 1.05) -> np.ndarray:
    """Speech for the text as float32 at the engine's sample rate, peak-normalised to 0.6.

    A voice written "<voice>@+N~P" is raised N semitones at the same pace, then set to pace P
    (e.g. "af_bella@+3~0.88": a young girl asking, relaxed rather than rushed).

    Results are cached for the life of the process, so a story's narration is synthesised once
    for timing and reused for the final mix.
    """
    global _engine
    key = (text, voice, speed)
    if key in _cache:
        return _cache[key]
    voice, semis, pace = split_pitch(voice)
    if backend(voice):
        prepare([text], voice)
        samples, rate = _load_wav(_cached(text, voice))
    else:
        if _engine is None:
            from kokoro_onnx import Kokoro
            _engine = Kokoro(str(MODEL), str(VOICES))
        lang = language(voice)
        spoken = text if lang == "hi" else speakable(text)
        samples, rate = _engine.create(spoken, voice=voice, speed=speed, lang=lang)
    samples = np.asarray(samples, dtype=np.float32)
    if semis or pace != 1.0:                             # a younger, unhurried voice
        samples = repitch(samples, rate, semis, pace)
    if rate != SR:
        t_out = np.arange(int(len(samples) * SR / rate)) / SR
        samples = np.interp(t_out, np.arange(len(samples)) / rate, samples).astype(np.float32)
    peak = float(np.abs(samples).max()) or 1.0
    _cache[key] = samples * (0.6 / peak)
    return _cache[key]
