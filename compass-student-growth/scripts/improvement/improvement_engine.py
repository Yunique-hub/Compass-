"""Turn repeated observable feedback into candidate strategy adjustments."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .pattern_store import PatternStore


class ImprovementEngine:
    def __init__(self, runtime_dir: str | Path) -> None:
        self.store = PatternStore(Path(runtime_dir) / "improvement-patterns.json")

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
