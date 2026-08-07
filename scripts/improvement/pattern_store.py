"""Store observable feedback patterns; never store hidden reasoning."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class PatternStore:
    def __init__(self, path: str | Path, *, promotion_threshold: int = 3) -> None:
        self.path = Path(path)
        self.promotion_threshold = max(2, int(promotion_threshold))
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
        key = hashlib.sha256(f"{category}\0{signal}".encode()).hexdigest()[:20]
        now = datetime.now(timezone.utc).isoformat()
        data = self._load()
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        item = data["patterns"].setdefault(key, {"pattern_key": key, "user_hashes": [], "category": category, "signal": signal, "events": [], "promoted": False, "first_seen": now, "status": "pending"})
        item["user_hashes"] = list(dict.fromkeys([*item.get("user_hashes", []), user_hash]))
        safe_context = {key: value for key, value in (context or {}).items() if key in {"stage", "provider", "domain", "reason_code", "task_type"}}
        event = {"task_id": task_id, "observed_at": now, "context": safe_context, "user_hash": user_hash}
        item["events"].append(event)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = [event for event in item["events"] if datetime.fromisoformat(event["observed_at"]) >= cutoff]
        unique_tasks = {event["task_id"] for event in recent}
        item["recurrence_count"] = len(recent)
        item["unique_tasks"] = len(unique_tasks)
        item["promoted"] = len(recent) >= self.promotion_threshold and len(unique_tasks) >= 2
        item["last_seen"] = now
        item["status"] = "promoted" if item["promoted"] else "pending"
        self._save(data)
        return item

    def list(self, user_id: str) -> list[dict[str, Any]]:
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        return [item for item in self._load()["patterns"].values() if user_hash in item.get("user_hashes", [])]
