"""Extract evidence-backed knowledge-point importance from course materials."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def _candidate_lines(text: str) -> list[str]:
    candidates: list[str] = []
    for line in text.splitlines():
        value = re.sub(r"^[#\d.、（）()\-\s]+", "", line).strip(" ：:")
        if 2 <= len(value) <= 80 and not value.startswith(("答案", "解析")):
            candidates.append(value)
    return candidates


def analyze_exam(materials: list[dict[str, Any]], *, course: str = "未命名课程") -> list[dict[str, Any]]:
    evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for material in materials:
        if not material.get("text"):
            continue
        for point in _candidate_lines(str(material["text"])):
            evidence[point].append({
                "source": material.get("name", ""),
                "source_type": material.get("source_type", "course_notes"),
                "priority": int(material.get("priority", 0)),
            })
    results = []
    for name, sources in evidence.items():
        exam_count = sum(item["source_type"] == "past_exam" for item in sources)
        importance = min(1.0, (max(item["priority"] for item in sources) / 100) * 0.7 + min(len(sources), 3) * 0.1)
        results.append({
            "course": course,
            "chapter": "待按课程结构确认",
            "name": name,
            "importance": round(importance, 3),
            "source_count": len(sources),
            "exam_frequency": exam_count,
            "mastery": None,
            "mistakes": 0,
            "last_reviewed": "",
            "evidence": sources,
        })
    return sorted(results, key=lambda item: (-item["importance"], -item["source_count"], item["name"]))
