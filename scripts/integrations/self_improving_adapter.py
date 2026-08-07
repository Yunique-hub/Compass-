"""Stable boundary for upstream-inspired LEARNINGS/ERRORS promotion."""
from scripts.improvement.improvement_engine import ImprovementEngine


class SelfImprovingAdapter:
    def __init__(self, runtime_dir: str) -> None: self.engine = ImprovementEngine(runtime_dir)
    def record(self, event: dict) -> dict:
        return self.engine.observe_event(**event)
    def recall(self, user_id: str = "system", *, area: str = "") -> list[dict]:
        return self.engine.retrieve(user_id, category=area)


__all__ = ["ImprovementEngine", "SelfImprovingAdapter"]
