"""Live queue tracker: one row per reel, one column per task, refreshed every few seconds.

    reel track persephone dhruva ra ...      # the reels in queue order

Writes out/_tracker/status.json and serves out/_tracker/index.html (which reads it) on
http://localhost:8765. A task counts as done only if it happened after the tracker started (or
after --since), so last week's videos do not show as finished.
"""
from __future__ import annotations

import http.server
import json
import subprocess
import threading
import time
from datetime import datetime
from functools import partial
from pathlib import Path

from ..config import REPO_ROOT

OUT = REPO_ROOT / "out"
TRACKER = OUT / "_tracker"
PORT = 8765
LANGS = ("en", "hi")


def spoken_lines(sc: dict, lang: str) -> list[tuple[str, str]]:
    """(text, voice) for every line the reel speaks, as the story format voices them."""
    from ..formats.story import load_story
    lib = load_story("_library")
    pair = lib["segments"].get(sc.get("segment", ""), {})
    voices = lib.get("voices", {})
    narrator = voices.get(pair.get("narrator"), {}).get(lang)
    asker = voices.get(pair.get("asker"), {}).get(lang)
    lines = []
    if pair and sc.get("ask", True) is not False:
        lines.append(("[excited] " + sc["title"][lang], asker))
        reply = sc.get("reply", lib.get("replies", {}).get(pair["narrator"], {}))
        if reply.get(lang):
            lines.append((reply[lang], narrator))
    else:
        lines.append((sc["title"][lang], narrator))
    return lines + [(b[lang], narrator) for b in sc["beats"]]


def voiced(sc: dict, lang: str) -> tuple[int, int]:
    from ..core import voice as V
    lines = [(t, v) for t, v in spoken_lines(sc, lang) if v and V.backend(v.partition("@")[0])]
    done = sum(V._cached(t, v.partition("@")[0]).exists() for t, v in lines)
    return done, len(lines)


def art_missing(sc: dict) -> int:
    from ..story import art
    needed = {a["puppet"] for b in sc["beats"] for a in b["stage"].get("actors", {}).values()}
    seg = art.segment(sc)
    if seg:
        needed |= {seg["narrator"]} | ({seg["asker"]} if sc.get("ask", True) is not False else set())
    missing = sum(not art.puppet_file(sc["id"], p).exists() for p in needed)
    backdrops = {b["stage"]["backdrop"] for b in sc["beats"]}
    return missing + sum(not art.backdrop_file(sc["id"], b).exists() for b in backdrops)


def newest(pattern: str) -> Path | None:
    found = sorted(OUT.glob(pattern), key=lambda p: p.stat().st_mtime)
    return found[-1] if found else None


def after(path: Path | None, since: float) -> bool:
    return bool(path) and path.exists() and path.stat().st_mtime >= since


def maya_busy() -> bool:
    try:
        r = subprocess.run(["docker", "exec", "maya-tts", "pgrep", "-f", "tts_maya.py"], capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def status(queue: list[str], since: float) -> dict:
    from ..formats.story import load_story
    rows, now_busy = [], maya_busy()
    for sid in queue:
        sc = load_story(sid)
        row = {"id": sid, "title": sc["title"]["en"], "art": art_missing(sc), "tasks": {}}
        for lang in LANGS:
            done, total = voiced(sc, lang)
            video = newest(f"*/story_{sid}_{lang}_1/story_{sid}_{lang}_1.mp4")
            preview = newest(f"*/story_{sid}_{lang}_1/story_{sid}_{lang}_1_preview.mp4")
            writing = bool(video) and time.time() - video.stat().st_mtime < 30 and not after(preview, since)
            row["tasks"][lang] = {"voices": [done, total], "video": after(video, since) and not writing,
                                  "rendering": writing, "preview": after(preview, since),
                                  "preview_path": str(preview.relative_to(REPO_ROOT)) if after(preview, since) else None}
        rows.append(row)
    total = 2 * len(queue)
    finished = sum(r["tasks"][l]["preview"] for r in rows for l in LANGS)
    current = next((r["id"] for r in rows if not all(r["tasks"][l]["preview"] for l in LANGS)), None)
    for r in rows:
        r["now"] = ("drawing" if r["art"] else "voicing" if now_busy else "rendering") if r["id"] == current else (
            "done" if all(r["tasks"][l]["preview"] for l in LANGS) else "waiting")
    return {"updated": datetime.now().strftime("%H:%M:%S"), "since": datetime.fromtimestamp(since).strftime("%H:%M"),
            "finished": finished, "total": total, "current": current, "rows": rows}


def track(queue: list[str], since: float | None = None, every: float = 5.0, serve: bool = True) -> None:
    TRACKER.mkdir(parents=True, exist_ok=True)
    page = Path(__file__).with_name("tracker.html")
    (TRACKER / "index.html").write_text(page.read_text(encoding="utf-8"), encoding="utf-8")
    since = since if since is not None else time.time()
    if serve:
        handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO_ROOT))
        handler.log_message = lambda *a, **k: None
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"tracker on http://localhost:{PORT}/out/_tracker/index.html", flush=True)
    while True:
        s = status(queue, since)
        tmp = TRACKER / "status.json.tmp"
        tmp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        tmp.replace(TRACKER / "status.json")
        time.sleep(every)
