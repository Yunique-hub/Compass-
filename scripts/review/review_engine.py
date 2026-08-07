"""Review Brain facade adapted from final-review's evidence-priority workflow."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .exam_analyzer import analyze_exam
from .material_processor import process_materials
from .question_engine import generate_questions


class ReviewEngine:
    def build(self, *, course: str, material_paths: list[str | Path], source_types: dict[str, str] | None = None, question_limit: int = 10) -> dict[str, Any]:
        materials = process_materials(material_paths, source_types)
        points = analyze_exam(materials, course=course)
        practice = generate_questions(points, limit=question_limit)
        warnings = [warning for item in materials for warning in item.get("warnings", [])]
        return {
            "course": course,
            "materials": materials,
            "knowledge_points": points,
            "questions": practice["questions"],
            "answers": practice["answers"],
            "review_sequence": [item["name"] for item in points[:10]],
            "warnings": warnings,
            "provenance": {"upstream": "lucianwhy/final-review", "mode": "rule adaptation; no copied private content"},
        }
