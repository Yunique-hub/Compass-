"""Deterministic market requirement minus verified competency gap."""
from __future__ import annotations

from typing import Any, Mapping


class GapEngine:
    def __init__(self, *, weights: Mapping[str, float] | None = None) -> None:
        self.weights = {"frequency": 1.0, "importance": 1.0, "urgency": 1.0, "evidence": 1.0, "dependency": 1.0, **dict(weights or {})}

    def calculate(self, skill_statistics: list[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]], competencies: Mapping[str, Mapping[str, Any]], *, deadline_urgency: float = 0.5) -> list[dict[str, Any]]:
        stats = [{"skill": key, **value} for key, value in skill_statistics.items()] if isinstance(skill_statistics, Mapping) else [dict(item) for item in skill_statistics]
        items: list[dict[str, Any]] = []
        for item in stats:
            skill = str(item.get("skill", "")); competency = competencies.get(skill, {}); verified = float(competency.get("verified_level", 0.0)) if competency.get("evidence") else 0.0
            frequency = max(0.0, min(1.0, float(item.get("frequency", 0.0)))); importance = max(0.0, min(1.0, float(item.get("importance", 0.8)))); required = max(0.0, min(1.0, float(item.get("required_level", 0.7)))); gap = max(0.0, required - verified)
            learning_cost = max(0.05, min(1.0, float(item.get("learning_cost", 0.5)))); dependency = max(0.0, min(1.0, float(item.get("dependency_weight", 1.0)))); evidence_value = max(0.0, min(1.0, float(item.get("evidence_value", 0.8)))); urgency = max(0.0, min(1.0, deadline_urgency))
            priority = frequency * importance * gap * urgency * evidence_value * dependency / learning_cost
            items.append({"gap_id": f"Gap:{skill}", "skill": skill, "market_frequency": frequency, "market_importance": importance, "required_level": required, "claimed_level": float(competency.get("claimed_level", 0.0)), "verified_level": verified, "gap_level": round(gap, 4), "priority_score": priority, "job_evidence": list(item.get("job_ids", [])), "user_evidence": list(competency.get("evidence", [])), "learning_dependency": list(item.get("dependencies", [])), "learning_cost": learning_cost, "deadline_urgency": urgency})
        maximum = max((item["priority_score"] for item in items), default=0.0)
        for item in items: item["priority_score"] = round(item["priority_score"] / maximum, 4) if maximum else 0.0
        return sorted(items, key=lambda item: (-item["priority_score"], item["skill"].casefold()))
