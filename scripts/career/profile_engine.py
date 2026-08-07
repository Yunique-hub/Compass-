"""Extract evidence-backed student features for automatic career scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass
class StudentFeatureProfile:
    major_features: list[str] = field(default_factory=list)
    course_features: list[str] = field(default_factory=list)
    skill_features: list[str] = field(default_factory=list)
    verified_skill_features: list[str] = field(default_factory=list)
    project_features: list[str] = field(default_factory=list)
    interest_features: list[str] = field(default_factory=list)
    work_style: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)
    weekly_hours: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _names(items: Any) -> list[str]:
    result: list[str] = []
    for item in items or []:
        if isinstance(item, Mapping):
            name = item.get("name") or item.get("title") or item.get("skill")
            if name:
                result.append(str(name))
        elif item:
            result.append(str(item))
    return result


def extract_features(profile: Mapping[str, Any] | None, message: str = "") -> StudentFeatureProfile:
    profile = profile or {}
    major = [str(profile.get("major", "")), str(profile.get("grade", ""))]
    courses = _names(profile.get("courses"))
    verified = _names(profile.get("verified_skills"))
    claimed = _names(profile.get("claimed_skills"))
    projects = _names(profile.get("projects"))
    interests = _names(profile.get("interests"))
    text = str(message or "")
    keyword_features = [
        keyword
        for keyword in (
            "Python",
            "Java",
            "数据结构",
            "数据库",
            "SQL",
            "测试",
            "产品",
            "后端",
            "数据分析",
        )
        if keyword.lower() in text.lower()
    ]
    verified_evidence = [
        str(item.get("evidence"))
        for item in profile.get("verified_skills", [])
        if isinstance(item, Mapping) and item.get("evidence")
    ]
    weekly_hours = max(0.0, float(profile.get("weekly_hours", 0) or 0))
    constraints = _names(profile.get("career_constraints"))
    if weekly_hours:
        constraints.append(f"每周可投入 {weekly_hours:g} 小时")
    return StudentFeatureProfile(
        major_features=[item for item in major if item],
        course_features=courses,
        skill_features=sorted(set(claimed + keyword_features)),
        verified_skill_features=verified,
        project_features=projects,
        interest_features=sorted(set(interests + keyword_features)),
        work_style=_names(profile.get("preferred_tasks")) + _names(profile.get("disliked_work_styles")),
        constraints=constraints,
        evidence={
            "major": [item for item in major if item],
            "courses": courses,
            "verified_skills": verified_evidence,
            "projects": projects,
            "interests": interests,
        },
        weekly_hours=weekly_hours,
    )

