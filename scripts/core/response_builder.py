"""Create the concise, human-facing four-part Compass response."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_response(
    judgment: str,
    reason: str,
    actions: Sequence[str] | None = None,
    next_step: str = "",
    *,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "current_judgment": judgment,
        "why": reason,
        "do_now": list(actions or []),
        "next_step": next_step,
    }
    if details:
        response["details"] = dict(details)
    return response


def render_text(response: Mapping[str, Any]) -> str:
    actions = response.get("do_now") or []
    lines = [
        f"当前判断：{response.get('current_judgment', '')}",
        f"为什么：{response.get('why', '')}",
        "现在做什么：" + ("；".join(str(item) for item in actions) if actions else "先补充必要信息"),
        f"下一步：{response.get('next_step', '')}",
    ]
    return "\n".join(lines)

