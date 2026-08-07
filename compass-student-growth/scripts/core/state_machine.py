"""Conversation state transitions shared by every Compass brain."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from scripts.core.intent_router import Intent
from scripts.models import ConversationState


def next_state(
    intent: Intent | str,
    archive: Mapping[str, Any] | None = None,
    *,
    safety_routed: bool = False,
) -> ConversationState:
    if safety_routed:
        return ConversationState.SAFETY_ROUTED
    intent = Intent(intent)
    archive = archive or {}
    career = archive.get("career") or archive.get("confirmed_goal") or {}
    mapping = {
        Intent.CAREER_EXPLORE: ConversationState.AWAITING_DIRECTION_CONFIRMATION,
        Intent.RECRUITMENT_ANALYSIS: ConversationState.RECRUITMENT_ANALYSIS,
        Intent.JD_ANALYSIS: ConversationState.RECRUITMENT_ANALYSIS,
        Intent.CAREER_GAP: ConversationState.GAP_ANALYSIS,
        Intent.LEARNING_PLAN: ConversationState.PLAN_READY,
        Intent.WEEKLY_PLAN: ConversationState.PLAN_READY,
        Intent.COURSE_LEARNING: ConversationState.COURSE_ANALYSIS,
        Intent.EXAM_REVIEW: ConversationState.EXAM_ANALYSIS,
        Intent.QUESTION_PRACTICE: ConversationState.QUESTION_PRACTICE,
        Intent.MISTAKE_REVIEW: ConversationState.MISTAKE_REVIEW,
        Intent.MEMORY_QUERY: ConversationState.MEMORY_REVIEW,
        Intent.MEMORY_UPDATE: ConversationState.MEMORY_REVIEW,
        Intent.MEMORY_FORGET: ConversationState.MEMORY_REVIEW,
        Intent.STRATEGY_FEEDBACK: ConversationState.STRATEGY_REVIEW,
        Intent.PROGRESS_REVIEW: ConversationState.REVIEW,
    }
    if intent is Intent.CAREER_CONFIRM:
        return (
            ConversationState.RECRUITMENT_ANALYSIS
            if career.get("target_city") and (career.get("job_search_period") or career.get("graduation_date"))
            else ConversationState.AWAITING_DESTINATION
        )
    if intent is Intent.DESTINATION_CONFIRM:
        return (
            ConversationState.RECRUITMENT_ANALYSIS
            if career.get("primary_direction") and (career.get("job_search_period") or career.get("graduation_date"))
            else ConversationState.AWAITING_DESTINATION
        )
    return mapping.get(intent, ConversationState.PROFILE_INCOMPLETE)

