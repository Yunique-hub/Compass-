"""Turn repeated observable feedback into candidate strategy adjustments."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .pattern_store import PatternStore


class ImprovementEngine:
    def __init__(self, runtime_dir: str | Path) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "config" / "improvement_policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8")) if policy_path.exists() else {"promotion_threshold": 3}
        self.store = PatternStore(Path(runtime_dir) / "improvement-patterns.json", promotion_threshold=int(policy["promotion_threshold"]))

    def observe(self, **event: Any) -> dict[str, Any]:
        pattern = self.store.record(**event)
        suggestion = None
        if pattern["promoted"]:
            suggestion = {
                "kind": "strategy_candidate",
                "pattern_key": pattern["pattern_key"],
                "change": f"针对“{pattern['signal']}”增加更小的任务粒度或替代资源",
                "requires_trial": True,
                "auto_apply": False,
            }
        return {"pattern": pattern, "suggestion": suggestion}

    def observe_event(self, *, event_type: str, pattern_key: str, summary: str, area: str, source: str = "runtime", priority: str = "medium", user_id: str = "system", task_id: str = "runtime") -> dict[str, Any]:
        if event_type not in {"error", "correction", "best_practice", "feature_request"}:
            raise ValueError("INVALID_IMPROVEMENT_EVENT_TYPE")
        sanitized = " ".join(str(summary).replace("\n", " ").split())[:240]
        output = self.observe(user_id=user_id, task_id=task_id, category=area, signal=pattern_key, context={"reason_code": event_type})
        return {"event": {"event_type": event_type, "pattern_key": pattern_key, "summary": sanitized, "area": area, "source": source, "priority": priority, "status": "pending"}, **output}

    def retrieve(self, user_id: str, *, category: str = "") -> list[dict[str, Any]]:
        items = self.store.list(user_id)
        return [item for item in items if not category or item.get("category") == category]
