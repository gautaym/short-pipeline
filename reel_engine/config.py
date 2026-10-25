"""Settings loaded from configs/default.yaml (or a file passed with --config)."""
from dataclasses import dataclass, fields
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


@dataclass
class RenderSettings:
    output_dir: str = "out"
    workers: int = 1
    scout: int = 1
    min_length: float = 20.0
    music: bool = True
    music_level: float = 0.55
    crf: int = 20
    preset: str = "veryfast"
    audio_bitrate: str = "160k"


def load_settings(path: str | None = None) -> RenderSettings:
    """Read the `render:` section of a YAML config; missing keys keep their defaults."""
    cfg = Path(path) if path else DEFAULT_CONFIG
    if not cfg.exists():
        if path:
            raise SystemExit(f"config file not found: {cfg}")
        return RenderSettings()
    data = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("render", {}) or {}
    known = {f.name for f in fields(RenderSettings)}
    unknown = set(data) - known
    if unknown:
        raise SystemExit(f"{cfg}: unknown render settings: {', '.join(sorted(unknown))}")
    return RenderSettings(**data)
