"""Build evidence-producing course tasks within an assigned capacity."""

from __future__ import annotations

from typing import Any, Sequence


def build_course_tasks(course: str, topics: Sequence[str], hours: float) -> list[dict[str, Any]]:
    budget = max(0.0, float(hours))
    selected = list(topics)[:3] or ["课程核心概念"]
    per_task = round(budget / len(selected), 2) if selected else 0.0
    return [
        {
            "title": f"完成 {course}：{topic} 的可检查练习",
            "reason": "用产出验证理解，而不是只记录观看时长。",
            "hours": per_task,
            "output": f"{topic} 概念卡、一道例题和一段复盘",
            "acceptance": ["概念表述可复述", "例题有过程和结果", "记录一个易错点"],
            "resources": [],
            "dependency": "已确认课程范围",
            "priority": round(1.0 - index * 0.1, 2),
        }
        for index, topic in enumerate(selected)
    ]
