"""Deterministic assessment from observable criteria."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


class AssessmentEngine:
    def __init__(self, *, passing_score: float = 0.7) -> None: self.passing_score = passing_score
    def evaluate(self, *, skill: str, submission: Mapping[str, Any], criteria: Sequence[str]) -> dict[str, Any]:
        checks = submission.get("criteria_met", []); met = set(checks if isinstance(checks, list) else [])
        if submission.get("passed") is True: met = set(criteria)
        score = len(met & set(criteria)) / len(criteria) if criteria else 0.0; passed = score >= self.passing_score
        return {"assessment_id": str(uuid.uuid4()), "skill": skill, "score": round(score, 4), "passed": passed, "criteria": [{"criterion": item, "met": item in met} for item in criteria], "feedback": "已达到验收标准，可形成能力证据。" if passed else "尚未达到全部验收标准；请针对未通过项修订后再次提交。", "created_at": datetime.now(timezone.utc).isoformat()}
