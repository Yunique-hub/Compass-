"""Allocate one weekly budget across review, academic, career, and buffer."""

from __future__ import annotations

from typing import Any


def allocate_weekly_capacity(
    total_hours: float,
    *,
    exam_days: int | None = None,
    exam_urgency: float = 0.0,
    career_urgency: float = 0.5,
    academic_urgency: float = 0.4,
    buffer_ratio: float = 0.1,
) -> dict[str, Any]:
    total = max(0.0, float(total_hours))
    buffer_ratio = min(0.15, max(0.10, float(buffer_ratio))) if total else 0.0
    buffer = round(total * buffer_ratio, 2)
    usable = max(0.0, total - buffer)
    if exam_days is not None and exam_days <= 5:
        review = round(total * 0.6, 2)
        academic = round(total * 0.1, 2)
        career = round(max(0.0, total - buffer - review - academic), 2)
    else:
        review_weight = max(0.0, float(exam_urgency))
        academic_weight = max(0.0, float(academic_urgency))
        career_weight = max(0.0, float(career_urgency))
        weight_sum = review_weight + academic_weight + career_weight or 1.0
        review = round(usable * review_weight / weight_sum, 2)
        academic = round(usable * academic_weight / weight_sum, 2)
        career = round(max(0.0, usable - review - academic), 2)
    return {
        "total_hours": total,
        "academic_hours": academic,
        "career_hours": career,
        "review_hours": review,
        "buffer_hours": round(total - academic - career - review, 2),
        "exam_days": exam_days,
    }

