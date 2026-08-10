"""Bounded question selection with semantic field history."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .duplicate_question_guard import DuplicateQuestionGuard

ROOT = Path(__file__).resolve().parents[2]

QUESTION_TEXT = {
    "preferred_name": "以后我怎么称呼你比较合适？",
    "major": "你现在主要学什么专业或领域？",
    "grade": "你现在是几年级或处于什么阶段？",
    "primary_need": "最近最想先解决学习、考试、实习就业，还是方向迷茫？",
    "skills": "目前主要学过或做过哪些技术、课程或项目？",
    "career_direction": "目前有没有值得优先探索的工作方向？",
    "confirmed_direction": "在这些候选里，你想先把哪一个作为主方向？",
    "daily_learning_hours": "每天大概能稳定投入多少学习时间？",
    "weekly_learning_hours": "每周大概能稳定投入多少学习时间？",
    "target_city": "以后比较想在哪个城市实习或就业？",
    "course": "这次要复习或学习哪门课程？",
    "exam_days": "距离考试还有多少天？",
    "deadline_time": "你计划什么时候开始实习或求职？",
}


def select_questions(
    fields: Sequence[str], known_facts: Mapping[str, Any], asked_fields: Sequence[str] | None = None,
    *, question_only_streak: int = 0, allow_non_blocking: bool = True,
) -> dict[str, Any]:
    policy = json.loads((ROOT / "config" / "mentor_policy.json").read_text(encoding="utf-8"))
    if question_only_streak >= int(policy["max_consecutive_question_only_turns"]):
        return {"questions": [], "asked_fields": [], "budget": 0, "reason": "question_only_streak_limit"}
    guard = DuplicateQuestionGuard(known_facts, asked_fields)
    normalized: list[str] = []
    for field in fields:
        if field == "skills_or_time_or_deadline":
            normalized.extend(("skills", "daily_learning_hours"))
        else:
            normalized.append(field)
    filtered = guard.filter_fields(list(dict.fromkeys(normalized)))
    max_questions = min(1, int(policy["max_questions_per_turn"]))
    selected = filtered[:max_questions]
    questions = [{"field": field, "text": QUESTION_TEXT.get(field, f"请告诉我 {field}。"), "blocking": not allow_non_blocking} for field in selected]
    return {"questions": questions, "asked_fields": selected, "budget": max_questions, "reason": "selected" if selected else "no_new_field"}
