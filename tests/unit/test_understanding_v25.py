from __future__ import annotations

from scripts.core.intent_router import Intent
from scripts.core.understanding import understand_message


def test_learning_difficulty_keeps_known_inferred_unknown_separate() -> None:
    result = understand_message("算法最近很痛苦，完全看不懂")

    assert result.primary_intent == Intent.START_LEARNING.value
    assert result.current_topic == "算法"
    assert result.academic_major is None
    assert result.known["learning_difficulty"]
    assert "difficulty_cause" in result.inferred
    assert "actual_mastery_level" in result.unknown


def test_multi_intent_prioritizes_decision_and_keeps_secondary_signals() -> None:
    result = understand_message("算法最近很痛苦，但明年要找后端实习，我应该先刷题还是做项目？")

    assert result.primary_intent == Intent.LEARNING_PLAN.value
    assert Intent.START_LEARNING.value in result.secondary_intents
    assert result.target_role == "后端"
    assert result.current_topic == "算法"
    assert result.user_goal


def test_active_exercise_natural_evidence_uses_assessment_fallback() -> None:
    result = understand_message("我预测了5年 FCFF，用 WACC 折现，也算了终值和敏感性。", active_exercise=True)

    assert result.primary_intent == Intent.SUBMIT_EXERCISE.value
    assert result.fallback_used is True
