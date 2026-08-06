"""将岗位实际要求与用户可验证证据对齐并计算学习优先级。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:
    from .io_utils import result, run_cli
    from .models import CompetencyGap, clamp
except ImportError:
    from io_utils import result, run_cli
    from models import CompetencyGap, clamp

MODULE = "competency_gap"
ROOT = Path(__file__).resolve().parents[1]


def calculate_priority(frequency: float, weight: float, gap: float, urgency: float, evidence_value: float, cost: float, epsilon: float = 1e-6) -> float:
    return max(0.0, frequency * weight * gap * urgency * evidence_value / max(cost, epsilon))


def build_gaps(
    skill_statistics: Mapping[str, Mapping[str, Any]],
    verified_skills: Mapping[str, Mapping[str, Any]],
    *,
    deadline_urgency: float = 0.5,
) -> dict[str, Any]:
    weights = json.loads((ROOT / "reference" / "job_roles" / "requirement_weights.json").read_text(encoding="utf-8"))
    raw_items: list[tuple[CompetencyGap, float]] = []
    for index, (skill, stats) in enumerate(skill_statistics.items(), start=1):
        user = verified_skills.get(skill, {})
        user_level = clamp(float(user.get("level", 0.0))) if user.get("evidence") else 0.0
        target = clamp(float(weights.get(skill, {}).get("target_level", 0.7)))
        gap = clamp(target - user_level)
        category = str(weights.get(skill, {}).get("category", "high_frequency"))
        req_weight = clamp(float(weights.get(skill, {}).get("requirement_weight", 0.7)))
        evidence_value = clamp(float(weights.get(skill, {}).get("evidence_value", 0.8)))
        cost = clamp(float(weights.get(skill, {}).get("learning_cost", 0.5)))
        freq = clamp(float(stats.get("frequency", 0.0)))
        raw_priority = calculate_priority(freq, req_weight, gap, clamp(deadline_urgency), evidence_value, cost)
        item = CompetencyGap(
            competency_id=f"gap-{index}", competency_name=skill, category=category,
            job_evidence=list(stats.get("job_ids", stats.get("jd_ids", []))), job_frequency=freq,
            requirement_weight=req_weight, user_evidence=list(user.get("evidence", [])), user_level=user_level,
            target_level=target, gap_level=gap, deadline_urgency=deadline_urgency,
            evidence_value=evidence_value, learning_cost=cost,
            validation_method=f"提交可运行的 {skill} 小型作品，并用自动化检查或演示记录验收。",
            priority_breakdown={"job_frequency": freq, "requirement_weight": req_weight, "user_gap": gap, "deadline_urgency": clamp(deadline_urgency), "evidence_value": evidence_value, "learning_cost": cost},
        )
        raw_items.append((item, raw_priority))
    maximum = max((raw for _, raw in raw_items), default=0.0)
    for item, raw in raw_items:
        item.priority_score = round(raw / maximum, 4) if maximum else 0.0
    items = sorted((item for item, _ in raw_items), key=lambda value: (-value.priority_score, value.competency_name))
    return result(MODULE, {"gaps": [item.to_dict() for item in items], "evidence_rule": "没有可验证用户证据时标记为暂无证据，不自动判定掌握。"})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return build_gaps(raw.get("skill_statistics", {}), raw.get("verified_skills", {}), deadline_urgency=float(raw.get("deadline_urgency", 0.5)))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
