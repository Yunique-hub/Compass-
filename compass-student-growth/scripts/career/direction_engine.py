"""Automatic, evidence-backed career direction scoring."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from scripts.career.profile_engine import StudentFeatureProfile
from scripts.models import clamp


ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = {
    "major_foundation": 0.25,
    "verified_skills": 0.25,
    "interest_match": 0.20,
    "experience_match": 0.15,
    "constraint_match": 0.15,
}
DIRECTION_HINTS = {
    "java-backend": {"java", "后端", "数据结构", "数据库", "sql", "工程", "调试"},
    "python-backend": {"python", "后端", "数据结构", "数据库", "api", "工程"},
    "data-analysis": {"python", "数据分析", "sql", "统计", "表格", "可视化"},
    "test-development": {"python", "测试", "质量", "自动化", "api", "数据结构"},
    "product-assistant": {"产品", "沟通", "需求", "分析", "文档", "用户"},
    "it-support": {"it支持", "技术支持", "网络", "服务器", "windows", "linux", "故障排查", "python", "自动化"},
    "network-operations": {"网络运维", "路由交换", "网络安全", "服务器", "linux", "故障排查", "监控"},
    "devops-support": {"devops", "linux", "python", "自动化", "git", "容器", "脚本", "监控"},
}


def _tokens(values: Iterable[str]) -> set[str]:
    text = " ".join(str(value).lower() for value in values)
    return {token for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff+#.]+", text) if token}


def _ratio(hints: set[str], values: Iterable[str]) -> float:
    text = " ".join(str(value).lower() for value in values)
    matched = sum(1 for hint in hints if hint in text)
    return clamp(matched / max(2, min(5, len(hints))))


def _score(profile: StudentFeatureProfile, knowledge: dict[str, Any]) -> tuple[float, dict[str, float], dict[str, list[str]]]:
    hints = DIRECTION_HINTS.get(knowledge["direction_id"], set())
    major_text = " ".join(profile.major_features).lower()
    major = 0.75 if any(word in major_text for word in ("计算机", "软件", "数据", "信息")) else (0.45 if major_text else 0.0)
    verified = _ratio(hints, profile.verified_skill_features + profile.course_features)
    interest = _ratio(hints, profile.interest_features + profile.work_style)
    experience = _ratio(hints, profile.project_features)
    constraint = 0.8 if profile.weekly_hours >= 8 else (0.6 if profile.weekly_hours >= 4 else (0.35 if profile.weekly_hours else 0.5))
    breakdown = {
        "major_foundation": major,
        "verified_skills": verified,
        "interest_match": interest,
        "experience_match": experience,
        "constraint_match": constraint,
    }
    entry_penalty = clamp(float(knowledge.get("entry_cost_score", 0.5))) * 0.10
    score = clamp(sum(breakdown[key] * weight for key, weight in WEIGHTS.items()) - entry_penalty)
    evidence = {
        "major_foundation": profile.evidence.get("major", []),
        "verified_skills": profile.evidence.get("verified_skills", []) + profile.evidence.get("courses", []),
        "interest_match": profile.evidence.get("interests", []),
        "experience_match": profile.evidence.get("projects", []),
        "constraint_match": profile.constraints,
    }
    return round(score, 4), breakdown, evidence


def analyze(profile: StudentFeatureProfile, *, limit: int = 4) -> list[dict[str, Any]]:
    directions: list[dict[str, Any]] = []
    for path in sorted((ROOT / "reference" / "career_directions").glob("*.json")):
        knowledge = json.loads(path.read_text(encoding="utf-8"))
        score, breakdown, evidence = _score(profile, knowledge)
        missing = [key for key, values in evidence.items() if not values]
        directions.append(
            {
                "direction_id": knowledge["direction_id"],
                "direction_name": knowledge["direction_name"],
                "fit_score": score,
                "fit_breakdown": breakdown,
                "evidence": evidence,
                "missing_evidence": missing,
                "current_strengths": [text for values in evidence.values() for text in values][:6],
                "risks": list(knowledge.get("risk_notes", [])),
                "entry_cost": float(knowledge.get("entry_cost_score", 0.5)),
                "exploration_task": knowledge["exploration_task"],
                "is_confirmed": False,
            }
        )
    directions.sort(key=lambda item: (-item["fit_score"], item["direction_id"]))
    return directions[: max(2, min(4, int(limit)))]
