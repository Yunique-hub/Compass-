"""Choose one user-facing action after sufficiency and stage detection."""
from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

from .known_facts import fact_value


class MentorAction(str, Enum):
    ASK_NAME = "ASK_NAME"
    ASK_MINIMUM_PROFILE = "ASK_MINIMUM_PROFILE"
    ASK_BLOCKING_FIELD = "ASK_BLOCKING_FIELD"
    GIVE_STAGE_DIAGNOSIS = "GIVE_STAGE_DIAGNOSIS"
    EXPLORE_CAREER = "EXPLORE_CAREER"
    CONFIRM_DIRECTION = "CONFIRM_DIRECTION"
    CREATE_PRELIMINARY_PLAN = "CREATE_PRELIMINARY_PLAN"
    REQUEST_DESTINATION = "REQUEST_DESTINATION"
    RUN_MARKET_ANALYSIS = "RUN_MARKET_ANALYSIS"
    CREATE_FORMAL_PLAN = "CREATE_FORMAL_PLAN"
    RUN_REVIEW = "RUN_REVIEW"
    RUN_PROGRESS_REVIEW = "RUN_PROGRESS_REVIEW"


def select_action(*, preferred_name_ready: bool, intent: str, sufficiency: Mapping[str, Any], facts: Mapping[str, Any], returning_user: bool = False) -> MentorAction:
    if not preferred_name_ready:
        return MentorAction.ASK_NAME
    if intent in {"EXAM_REVIEW", "QUESTION_PRACTICE"} and sufficiency.get("action_ready"):
        return MentorAction.RUN_REVIEW
    if intent == "PROGRESS_REVIEW" or (intent == "MEMORY_QUERY" and returning_user):
        return MentorAction.RUN_PROGRESS_REVIEW
    if intent in {"RECRUITMENT_ANALYSIS", "JD_ANALYSIS"}:
        return MentorAction.RUN_MARKET_ANALYSIS if sufficiency.get("action_ready") else MentorAction.REQUEST_DESTINATION
    if not sufficiency.get("action_ready"):
        return MentorAction.ASK_BLOCKING_FIELD if sufficiency.get("known_fields") else MentorAction.ASK_MINIMUM_PROFILE
    direction_status = fact_value(facts, "direction_status")
    if direction_status == "changed":
        return MentorAction.EXPLORE_CAREER
    if direction_status == "confirmed":
        return MentorAction.CREATE_FORMAL_PLAN if fact_value(facts, "target_city") and fact_value(facts, "deadline_time") else MentorAction.CREATE_PRELIMINARY_PLAN
    if intent == "CAREER_EXPLORE" or fact_value(facts, "career_direction"):
        return MentorAction.EXPLORE_CAREER
    return MentorAction.GIVE_STAGE_DIAGNOSIS
