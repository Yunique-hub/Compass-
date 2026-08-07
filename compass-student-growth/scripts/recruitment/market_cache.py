"""Versioned market snapshot cache with explicit staleness."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class MarketSnapshotCache:
    def __init__(self, root: str | Path, *, ttl_hours: int = 168) -> None:
        self.root, self.ttl = Path(root), timedelta(hours=ttl_hours); self.root.mkdir(parents=True, exist_ok=True)
    def _path(self, city: str, job: str, window: str = "default") -> Path: return self.root / f"{hashlib.sha256(f'{city}|{job}|{window}'.encode()).hexdigest()[:24]}.json"
    def save(self, city: str, job: str, data: dict[str, Any], *, window: str = "default") -> dict[str, Any]:
        now = datetime.now(timezone.utc); value = {**data, "collected_at": data.get("collected_at", now.isoformat()), "expires_at": (now + self.ttl).isoformat(), "content_hash": hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
        self._path(city, job, window).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); return value
    def load(self, city: str, job: str, *, window: str = "default") -> dict[str, Any] | None:
        path = self._path(city, job, window)
        if not path.exists(): return None
        value = json.loads(path.read_text(encoding="utf-8")); value["stale"] = datetime.now(timezone.utc) >= datetime.fromisoformat(value["expires_at"]); return value
