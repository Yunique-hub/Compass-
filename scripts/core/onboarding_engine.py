"""Cold-start coordinator: identity, quick profile, stage, sufficiency and action."""
from __future__ import annotations

from typing import Any, Mapping

from .action_selector import select_action
from .known_facts import fact_value
from .profile_sufficiency import evaluate_profile_sufficiency
from .stage_detector import detect_stage


def evaluate_onboarding(*, archive_exists: bool, archive: Mapping[str, Any], facts: Mapping[str, Any], intent: str) -> dict[str, Any]:
    usage = fact_value(facts, "preferred_name_usage", archive.get("preferred_name_usage", True))
    preferred_name = fact_value(facts, "preferred_name", archive.get("preferred_name", ""))
    name_ready = bool(preferred_name) or usage is False
    stage = detect_stage(facts)
    sufficiency = evaluate_profile_sufficiency(facts, intent=intent, stage=stage.stage.value)
    action = select_action(
        preferred_name_ready=name_ready, intent=intent, sufficiency=sufficiency.to_dict(), facts=facts,
        returning_user=archive_exists and bool(archive.get("onboarding_complete")),
    )
    state = "ASKING_PREFERRED_NAME" if not name_ready else ("ACTION_READY" if sufficiency.action_ready else "QUICK_PROFILE")
    return {
        "new_user": not archive_exists,
        "returning_user": archive_exists,
        "preferred_name": preferred_name,
        "preferred_name_usage": usage,
        "state": state,
        "stage": stage.to_dict(),
        "sufficiency": sufficiency.to_dict(),
        "action": action.value,
    }
