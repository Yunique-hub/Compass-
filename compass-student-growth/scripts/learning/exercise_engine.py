"""Evidence-producing exercise builder."""
from __future__ import annotations

from typing import Any


class ExerciseEngine:
    def build(self, *, skill: str, difficulty: str, acceptance_criteria: list[str] | None = None) -> dict[str, Any]:
        criteria = acceptance_criteria or ["提交可打开或可运行的产出", "说明关键步骤", "记录一次验证或故障排查"]
        return {"exercise_id": f"exercise:{skill}:{difficulty}", "skill": skill, "difficulty": difficulty, "prompt": f"完成一个 {skill} 的最小岗位场景实验，并保留操作与验证记录。", "acceptance_criteria": criteria, "expected_evidence_type": "project"}
