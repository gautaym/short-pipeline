"""The ledger: a small SQLite file recording every reel rendered (and, later, uploaded).

It gives each format a running series number ("Brick Escape #14") and guarantees that no two
reels share a title.
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id           INTEGER PRIMARY KEY,
    created_at   TEXT NOT NULL,
    format       TEXT NOT NULL,
    seed         INTEGER NOT NULL,
    series_no    INTEGER NOT NULL,
    path         TEXT NOT NULL,
    duration     REAL,
    hook         TEXT,
    title        TEXT NOT NULL UNIQUE,
    description  TEXT,
    tags         TEXT,
    outcome      TEXT,
    score        REAL,
    uploaded_at  TEXT,
    platform_ids TEXT
);
CREATE INDEX IF NOT EXISTS videos_format ON videos(format);
"""


@dataclass
class Entry:
    format: str
    seed: int
    series_no: int
    path: str
    duration: float
    hook: str
    title: str
    description: str
    tags: list[str]
    outcome: dict[str, Any]
    score: float


class Ledger:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    def next_series_no(self, fmt: str) -> int:
        row = self.db.execute("SELECT MAX(series_no) FROM videos WHERE format = ?", (fmt,)).fetchone()
        return (row[0] or 0) + 1

    def title_used(self, title: str) -> bool:
        return self.db.execute("SELECT 1 FROM videos WHERE title = ?", (title,)).fetchone() is not None

    def recent_cores(self, fmt: str, n: int = 12) -> list[str]:
        """Title texts (without the series suffix) of the format's last n reels."""
        rows = self.db.execute("SELECT title FROM videos WHERE format = ? ORDER BY id DESC LIMIT ?", (fmt, n))
        return [r[0].split(" | ")[0] for r in rows]

    def add(self, e: Entry) -> int:
        cur = self.db.execute(
            "INSERT INTO videos (created_at, format, seed, series_no, path, duration, hook, title, description,"
            " tags, outcome, score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), e.format, e.seed, e.series_no, e.path,
             e.duration, e.hook, e.title, e.description, json.dumps(e.tags), json.dumps(e.outcome), e.score))
        self.db.commit()
        return cur.lastrowid

    def recent(self, n: int = 20) -> list[tuple]:
        return self.db.execute("SELECT id, created_at, format, series_no, title, path, uploaded_at FROM videos"
                               " ORDER BY id DESC LIMIT ?", (n,)).fetchall()
