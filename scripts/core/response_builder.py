"""Canonical user-facing response model and adaptive text renderer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MentorResponse:
    """One response contract shared by all Compass handlers.

    Fields may be empty for simple questions. Complex growth turns should fill
    judgment, goal, actions, reasoning and next step.
    """

    current_judgment: str = ""
    current_goal: str = ""
    do_now: list[str] = field(default_factory=list)
    why: str = ""
    next_step: str = ""
    questions: list[str] = field(default_factory=list)
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_response(
    judgment: str,
    reason: str,
    actions: Sequence[str] | None = None,
    next_step: str = "",
    *,
    goal: str = "",
    questions: Sequence[str] | None = None,
    text: str = "",
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = MentorResponse(
        current_judgment=judgment,
        current_goal=goal,
        do_now=list(actions or []),
        why=reason,
        next_step=next_step,
        questions=list(questions or []),
        text=text,
    ).to_dict()
    if not response["text"]:
        response["text"] = render_text(response)
    if details:
        response["details"] = dict(details)
    return response


def normalize_response(response: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize legacy handler output without forcing a verbose template."""
    normalized = dict(response)
    normalized.setdefault("current_judgment", "")
    normalized.setdefault("current_goal", "")
    normalized.setdefault("do_now", [])
    normalized.setdefault("why", "")
    normalized.setdefault("next_step", "")
    normalized.setdefault("questions", [])
    normalized.setdefault("text", "")
    normalized["do_now"] = [str(item) for item in normalized["do_now"] if str(item).strip()]
    normalized["questions"] = [str(item) for item in normalized["questions"] if str(item).strip()][:1]
    if not normalized["text"]:
        normalized["text"] = render_text(normalized)
    return normalized


def render_text(response: Mapping[str, Any]) -> str:
    actions = response.get("do_now") or []
    questions = response.get("questions") or []
    lines = []
    for label, value in (
        ("当前判断", response.get("current_judgment")),
        ("当前目标", response.get("current_goal")),
        ("现在做什么", "；".join(str(item) for item in actions)),
        ("为什么", response.get("why")),
        ("下一步", response.get("next_step")),
        ("需要确认", "；".join(str(item) for item in questions)),
    ):
        if value:
            lines.append(f"{label}：{value}")
    return "\n".join(lines)
