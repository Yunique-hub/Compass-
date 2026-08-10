"""Decide whether Compass can help now, rather than whether a profile is complete."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .known_facts import fact_value


@dataclass
class ProfileSufficiencyResult:
    score: float
    known_fields: list[str]
    missing_blocking: list[str]
    missing_non_blocking: list[str]
    action_ready: bool
    confidence: str
    next_questions: list[str]
    planning_mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _known(facts: Mapping[str, Any], key: str) -> bool:
    value = fact_value(facts, key)
    return value not in (None, "", [], {})


def evaluate_profile_sufficiency(facts: Mapping[str, Any], *, intent: str = "GENERAL_SUPPORT", stage: str = "") -> ProfileSufficiencyResult:
    known = sorted(key for key in facts if _known(facts, key))
    career_context = any(token in intent for token in ("CAREER", "RECRUITMENT", "JD", "LEARNING_PLAN", "WEEKLY_PLAN")) or "INTERNSHIP" in stage or "JOB_SEARCH" in stage
    exam_context = "EXAM" in intent or "QUESTION" in intent or "EXAM" in stage
    formal_market = intent in {"RECRUITMENT_ANALYSIS", "JD_ANALYSIS"}

    if exam_context:
        blocking = [field for field in ("primary_need",) if not _known(facts, field)]
        non_blocking = [field for field in ("course", "exam_days", "materials") if not _known(facts, field)]
        mode = "REVIEW_PLAN"
    elif formal_market:
        blocking = [field for field in ("career_direction", "target_city", "deadline_time") if not _known(facts, field)]
        non_blocking = [field for field in ("company_preference", "specific_company") if not _known(facts, field)]
        mode = "FORMAL_JOB_MARKET_PLAN" if not blocking else "PRELIMINARY_PLAN"
    elif career_context:
        need = str(fact_value(facts, "primary_need", ""))
        has_explicit_goal = need not in {"", "实习准备", "就业准备"} or any(_known(facts, field) for field in ("career_direction", "target_job", "transition_target"))
        blocking = [field for field in ("major",) if not _known(facts, field)]
        if not has_explicit_goal:
            blocking.extend(field for field in ("grade", "skills") if not _known(facts, field))
        if not (_known(facts, "primary_need") or stage):
            blocking.append("primary_need")
        non_blocking = [field for field in ("grade", "skills", "career_direction", "daily_learning_hours", "target_city", "company_preference") if not _known(facts, field)]
        mode = "PRELIMINARY_PLAN"
    else:
        blocking = [field for field in ("major", "grade", "primary_need") if not _known(facts, field)]
        if not any(_known(facts, field) for field in ("skills", "daily_learning_hours", "weekly_learning_hours", "deadline_time")):
            blocking.append("skills_or_time_or_deadline")
        non_blocking = [field for field in ("career_direction", "target_city", "company_preference") if not _known(facts, field)]
        mode = "PRELIMINARY_PLAN"

    categories = [
        _known(facts, "preferred_name") or fact_value(facts, "preferred_name_usage") is False,
        _known(facts, "major"), _known(facts, "grade"), _known(facts, "primary_need"),
        _known(facts, "skills"), _known(facts, "career_direction") or _known(facts, "coding_interest"),
        any(_known(facts, key) for key in ("daily_learning_hours", "weekly_learning_hours", "deadline_time", "exam_days")),
    ]
    score = round(sum(categories) / len(categories), 2)
    action_ready = not blocking
    confidence = "high" if score >= 0.85 else ("medium" if score >= 0.65 else "low")
    return ProfileSufficiencyResult(score, known, list(dict.fromkeys(blocking)), non_blocking, action_ready, confidence, list(dict.fromkeys([*blocking, *non_blocking]))[:3], mode)
