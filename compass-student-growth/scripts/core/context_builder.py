"""Build bounded context without exposing backend details to users."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_context(
    archive: Mapping[str, Any] | None,
    memories: Sequence[Mapping[str, Any]] | None,
    attachments: Sequence[Any] | None,
) -> dict[str, Any]:
    archive = dict(archive or {})
    return {
        "profile": archive.get("profile") or archive.get("explicit_profile") or {},
        "career": archive.get("career") or archive.get("confirmed_goal") or {},
        "academic": archive.get("academic") or {},
        "exam": archive.get("exam") or {},
        "current_plan": archive.get("current_plan") or {},
        "learning_strategy": archive.get("learning_strategy") or {},
        "known_facts": archive.get("known_facts") or {},
        "preferred_name": archive.get("preferred_name") or "",
        "current_growth_stage": archive.get("current_growth_stage") or "",
        "question_history": archive.get("question_history") or {"asked_fields": [], "question_only_streak": 0},
        "recent_memories": [dict(item) for item in (memories or [])[:8]],
        "attachments": list(attachments or []),
    }
