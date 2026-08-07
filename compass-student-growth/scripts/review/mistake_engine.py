"""Record mistakes as observable outcomes rather than hidden reasoning."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def record_mistake(*, user_id: str, question: dict[str, Any], answer: str, feedback: str, tags: list[str] | None = None) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id 不能为空")
    return {
        "user_id": user_id,
        "question_id": question.get("question_id", ""),
        "knowledge_point": question.get("knowledge_point", ""),
        "submitted_answer": answer,
        "feedback": feedback,
        "tags": tags or [],
        "status": "open",
        "retry_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def summarize_mistakes(records: list[dict[str, Any]]) -> dict[str, Any]:
    open_items = [item for item in records if item.get("status", "open") == "open"]
    counts: dict[str, int] = {}
    for item in open_items:
        point = str(item.get("knowledge_point") or "未分类")
        counts[point] = counts.get(point, 0) + 1
    return {"open_count": len(open_items), "by_knowledge_point": counts, "next_action": "优先重做错误次数最多的知识点" if open_items else "暂无待重做错题"}
