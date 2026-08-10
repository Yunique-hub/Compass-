"""Typed state shared by the phases of one Compass turn."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass
class TurnContext:
    """Carry one turn through safety, restore, decision, action and persistence."""

    request: Mapping[str, Any]
    user_id: str
    message: str
    attachments: list[Any]
    archive_path: Path
    memory_path: Path
    strategy_dir: Path
    statuses: dict[str, str] = field(default_factory=dict)
    flow: list[str] = field(default_factory=list)
    archive_exists: bool = False
    safety: dict[str, Any] = field(default_factory=dict)
    archive: dict[str, Any] = field(default_factory=dict)
    memory: Any = None
    persistent_context: dict[str, Any] = field(default_factory=dict)
    recalled: dict[str, Any] = field(default_factory=dict)
    intent: Any = None
    understanding: Any = None
    incoming: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    onboarding: dict[str, Any] = field(default_factory=dict)
    stage: dict[str, Any] = field(default_factory=dict)
    sufficiency: dict[str, Any] = field(default_factory=dict)
    academic_profile: Any = None
    pathway: Any = None
    growth_context: Any = None
    action: Any = None
    history: dict[str, Any] = field(default_factory=dict)
    growth_cycle: dict[str, Any] | None = None
    memory_change: dict[str, Any] = field(default_factory=dict)
    business: dict[str, Any] = field(default_factory=dict)
    questions: list[dict[str, Any]] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        request: Mapping[str, Any],
        *,
        archive_path: Path,
        memory_path: Path,
        strategy_dir: Path,
    ) -> "TurnContext":
        user_id = str(request.get("user_id", "")).strip()
        if not user_id:
            raise ValueError("user_id 不能为空")
        return cls(
            request=request,
            user_id=user_id,
            message=str(request.get("message", "")).strip(),
            attachments=list(request.get("attachments") or []),
            archive_path=archive_path,
            memory_path=memory_path,
            strategy_dir=strategy_dir,
            archive_exists=archive_path.exists(),
        )
