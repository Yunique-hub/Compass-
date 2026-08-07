"""Build question and answer sheets separately from supplied evidence."""
from __future__ import annotations

from typing import Any


def generate_questions(points: list[dict[str, Any]], *, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
    questions: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []
    for index, point in enumerate(points[: max(0, limit)], 1):
        qid = f"Q{index:03d}"
        name = str(point["name"])
        questions.append({
            "question_id": qid,
            "type": "subjective",
            "prompt": f"请解释“{name}”的核心概念、适用条件，并给出一个例子。",
            "knowledge_point": name,
            "difficulty": "medium" if point.get("importance", 0) < 0.9 else "high",
            "source_refs": point.get("evidence", []),
        })
        answers.append({
            "question_id": qid,
            "answer_basis": "仅依据所附资料评分；资料不足时由教师或用户补充标准答案",
            "must_include": [name, "适用条件", "示例"],
            "scoring": [{"item": "概念准确", "points": 4}, {"item": "条件完整", "points": 3}, {"item": "示例有效", "points": 3}],
            "common_mistakes": ["只背定义而未说明条件", "示例与概念不匹配"],
        })
    return {"questions": questions, "answers": answers}
