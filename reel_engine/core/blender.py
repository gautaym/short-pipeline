"""Run Blender headless on one of the scene scripts in blender/ and collect what it reports.

Blender renders 3D frames (Eevee, on the GPU); reel_engine then adds the hook card, title, voice,
music and end card on top like any other format. A scene script reads a params JSON file and writes
result.json (and, unless params["render"] is false, PNG frames) to params["out_dir"].
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from ..config import REPO_ROOT

SCRIPTS = REPO_ROOT / "blender"
STORE_ALIAS = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "blender-launcher.exe"


def find_blender() -> str:
    """Blender from $BLENDER, PATH, or the Microsoft Store install."""
    for cand in (os.environ.get("BLENDER"), shutil.which("blender"), str(STORE_ALIAS) if STORE_ALIAS.exists() else None):
        if cand:
            return cand
    raise SystemExit("Blender not found. Install it (blender.org or the Microsoft Store) or set BLENDER to blender.exe")


def run(script: str, params: dict, timeout: float = 3600) -> dict:
    """Run blender/<script>.py with params; returns its result.json."""
    out = Path(params["out_dir"]).resolve()
    params = {**params, "out_dir": str(out)}          # Blender resolves relative paths its own way
    out.mkdir(parents=True, exist_ok=True)
    pfile = out / "params.json"
    pfile.write_text(json.dumps(params), encoding="utf-8")
    (out / "result.json").unlink(missing_ok=True)
    with open(out / "blender.log", "w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.run([find_blender(), "--background", "--factory-startup", "--python",
                               str(SCRIPTS / f"{script}.py"), "--", str(pfile)],
                              stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    result = out / "result.json"
    if proc.returncode != 0 or not result.exists():
        raise RuntimeError(f"Blender scene {script} failed; see {out / 'blender.log'}")
    return json.loads(result.read_text(encoding="utf-8"))
