"""Store observable feedback patterns; never store hidden reasoning."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class PatternStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text('{"patterns":{}}\n', encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def record(self, *, user_id: str, task_id: str, category: str, signal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not all((user_id, task_id, category, signal)):
            raise ValueError("pattern record 缺少必要字段")
        key = hashlib.sha256(f"{user_id}\0{category}\0{signal}".encode()).hexdigest()[:20]
        now = datetime.now(timezone.utc).isoformat()
        data = self._load()
        item = data["patterns"].setdefault(key, {"pattern_key": key, "user_id": user_id, "category": category, "signal": signal, "events": [], "promoted": False})
        event = {"task_id": task_id, "observed_at": now, "context": context or {}}
        item["events"].append(event)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = [event for event in item["events"] if datetime.fromisoformat(event["observed_at"]) >= cutoff]
        unique_tasks = {event["task_id"] for event in recent}
        item["recurrence_count"] = len(recent)
        item["unique_tasks"] = len(unique_tasks)
        item["promoted"] = len(recent) >= 3 and len(unique_tasks) >= 2
        self._save(data)
        return item

    def list(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in self._load()["patterns"].values() if item["user_id"] == user_id]
