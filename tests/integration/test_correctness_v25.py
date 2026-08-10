from __future__ import annotations

from pathlib import Path

import pytest

from scripts.academic.major_engine import MajorMentionType, classify_major_mention, identify_academic_profile
from scripts.compass_engine import CompassEngine
from scripts.core.known_facts import extract_known_facts, fact_value
from scripts.core.intent_router import Intent, route_intent
from scripts.memory.memory_engine import MemoryEngine
from scripts.safety_router import route_safety


@pytest.mark.parametrize(
    ("message", "topic"),
    [
        ("算法学得很痛苦", "算法"),
        ("医学英语很难", "医学英语"),
        ("我最近在学金融", "金融"),
        ("统计学不会", "统计学"),
    ],
)
def test_topic_mentions_never_become_confirmed_major(message: str, topic: str) -> None:
    mention = classify_major_mention(message)
    profile = identify_academic_profile(message)
    facts = extract_known_facts(message)

    assert mention.mention_type is MajorMentionType.DOMAIN_TOPIC
    assert mention.current_topic == topic
    assert mention.persistable is False
    assert profile.raw_major == ""
    assert "major" not in facts
    assert fact_value(facts, "current_topic") == topic


def test_explicit_major_and_topic_are_kept_separate() -> None:
    mention = classify_major_mention("我是法学专业，算法也学得很痛苦")
    facts = extract_known_facts("我是法学专业，算法也学得很痛苦")

    assert mention.mention_type is MajorMentionType.EXPLICIT_MAJOR
    assert mention.raw_major == "法学"
    assert mention.current_topic == "算法"
    assert mention.persistable is True
    assert fact_value(facts, "major") == "法学"
    assert fact_value(facts, "current_topic") == "算法"
    assert facts["major"]["source"] == "user_explicit"


def test_topic_does_not_overwrite_existing_major() -> None:
    previous = identify_academic_profile("我的专业是金融")
    updated = identify_academic_profile("最近在学计算机", previous.to_dict())

    assert updated.raw_major == "金融"
    assert updated.profile_source == "explicit"


def test_explicit_major_persists_but_topic_collision_does_not(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    collision = CompassEngine(runtime).run({"user_id": "collision", "message": "算法学得很痛苦"})["data"]
    collision_profile = collision["archive"]["profile"]
    collision_context = collision["response"]["details"]["business"]["growth_context"]
    collision_memory = MemoryEngine(CompassEngine(runtime)._paths("collision")[1]).load_user_context(user_id="collision")

    assert "major" not in collision["archive"]["known_facts"]
    assert "major" not in collision_profile
    assert collision_context["academic_profile"]["raw_major"] == ""
    assert "major" not in collision_memory["profile"]

    engine = CompassEngine(runtime)
    engine.run({"user_id": "explicit", "message": "我的专业是金融"})
    reopened = CompassEngine(runtime).run({"user_id": "explicit", "message": "我最近在学计算机"})["data"]
    reopened_context = reopened["response"]["details"]["business"]["growth_context"]
    explicit_memory = MemoryEngine(CompassEngine(runtime)._paths("explicit")[1]).load_user_context(user_id="explicit")

    assert reopened_context["academic_profile"]["raw_major"] == "金融"
    assert reopened_context["academic_profile"]["current_topic"] == "计算机"
    assert explicit_memory["profile"]["major"] == "金融"


@pytest.mark.parametrize(
    "message",
    ["算法学得很痛苦", "完全看不懂有机化学", "做题总错", "看懂了但不会做", "越学越乱", "卡了很久"],
)
def test_learning_difficulty_routes_to_tutor(message: str) -> None:
    assert route_intent(message) is Intent.START_LEARNING


def test_legal_learning_question_is_not_blocked_as_legal_advice() -> None:
    assert route_safety("法律诉讼程序怎么理解")["data"]["stop_learning_plan"] is False


def test_active_dcf_exercise_accepts_natural_language_submission(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "dcf-natural", "message": "我是金融专业，现在带我学 DCF。"})
    output = engine.run(
        {
            "user_id": "dcf-natural",
            "message": "提交练习：我预测了 5 年 FCFF，用 WACC 折现，计算了终值，也做了敏感性分析。",
        }
    )["data"]
    assessment = output["response"]["details"]["business"]["assessment"]["assessment"]

    assert assessment["passed"] is True
    assert all(item["status"] == "MET" for item in assessment["criteria"])


def test_archive_separates_profile_and_business_state_with_compatibility_views(tmp_path: Path) -> None:
    output = CompassEngine(tmp_path).run({"user_id": "state-boundary", "message": "我是教育学大二，想提升教学设计。"})["data"]
    archive = output["archive"]

    assert archive["profile_state"]["profile"] == archive["profile"]
    assert archive["business_state"]["academic"] == archive["academic"]
    assert "career" not in archive["profile_state"]
    assert "known_facts" not in archive["business_state"]
