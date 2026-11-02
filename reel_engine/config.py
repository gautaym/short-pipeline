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
    ledger: str | None = None          # default: <output_dir>/ledger.sqlite
    voice: bool = True
    voice_name: str = "am_michael"
    voice_speed: float = 1.05
    voice_level: float = 1.8           # voice loudness relative to the background (music + effects)
    voice_name_hi: str = "hm_omega"    # Hindi narrator for story reels

    def ledger_path(self) -> str:
        import os
        return self.ledger or os.path.join(self.output_dir, "ledger.sqlite")
    crf: int = 20
    preset: str = "veryfast"
    audio_bitrate: str = "160k"


def load_channel(path: str | None = None) -> dict:
    """The `channel:` section: name, made_for_kids (deliberately no default), tags, hashtags."""
    cfg = Path(path) if path else DEFAULT_CONFIG
    if not cfg.exists():
        return {"made_for_kids": None, "tags": [], "hashtags": []}
    data = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("channel", {}) or {}
    data.setdefault("made_for_kids", None)
    data["tags"] = data.get("tags") or []
    data["hashtags"] = data.get("hashtags") or []
    return data


def load_settings(path: str | None = None) -> RenderSettings:
    """Read the `render:` section of a YAML config; missing keys keep their defaults."""
    cfg = Path(path) if path else DEFAULT_CONFIG
    if not cfg.exists():
        if path:
            raise SystemExit(f"config file not found: {cfg}")
        return RenderSettings(output_dir=str(REPO_ROOT / "out"))
    data = (yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}).get("render", {}) or {}
    known = {f.name for f in fields(RenderSettings)}
    unknown = set(data) - known
    if unknown:
        raise SystemExit(f"{cfg}: unknown render settings: {', '.join(sorted(unknown))}")
    settings = RenderSettings(**data)
    # relative paths mean "inside the project", wherever reel is run from
    if not Path(settings.output_dir).is_absolute():
        settings.output_dir = str(REPO_ROOT / settings.output_dir)
    if settings.ledger and not Path(settings.ledger).is_absolute():
        settings.ledger = str(REPO_ROOT / settings.ledger)
    return settings
