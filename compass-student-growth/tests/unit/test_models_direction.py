from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.career_direction_analyzer import analyze_directions, calculate_fit
from scripts.direction_confirmation import formal_plan_gate, update_confirmation
from scripts.models import DirectionConfirmation, DirectionStatus, UserProfile
from scripts.profile_parser import parse_profile

ROOT = Path(__file__).resolve().parents[2]


def test_user_profile_roundtrip_and_json() -> None:
    profile = UserProfile(user_id="u1", major="计算机", weekly_hours=8, interests=["后端"])
    restored = UserProfile.from_dict(json.loads(profile.to_json()))
    assert restored.to_dict() == profile.to_dict()


def test_enum_legal_and_illegal() -> None:
    assert DirectionConfirmation.from_dict({"status": "CONFIRMED"}).status is DirectionStatus.CONFIRMED
    with pytest.raises(ValueError):
        DirectionConfirmation.from_dict({"status": "UNKNOWN"})


def test_invalid_fields_and_negative_hours() -> None:
    with pytest.raises(ValueError, match="未知字段"):
        UserProfile.from_dict({"user_id": "u", "mystery": 1}, strict=True)
    with pytest.raises(ValueError, match="不能为负数"):
        UserProfile(user_id="u", weekly_hours=-1)


def test_claimed_skill_is_not_verified() -> None:
    raw = json.loads((ROOT / "tests" / "fixtures" / "profile_xiaoming.json").read_text(encoding="utf-8"))
    parsed = parse_profile(raw, "DIRECTION_ANALYSIS")
    assert all(item.get("name") != "Python" for item in parsed["data"]["verified_skills"])
    assert any("Python" in item for item in parsed["data"]["pending_confirmations"])


def test_unknown_profile_field_warns_not_crashes() -> None:
    parsed = parse_profile({"user_id": "u", "unknown": 1})
    assert parsed["ok"] and parsed["warnings"][0]["code"] == "UNKNOWN_FIELDS"


def test_fit_calculation_and_entry_penalty() -> None:
    weights = {"a": 0.5, "b": 0.5}
    score, parts = calculate_fit({"a": 1, "b": 1}, weights, 0.2)
    assert score == pytest.approx(0.8)
    assert parts == {"a": 1.0, "b": 1.0}


def test_fit_boundaries() -> None:
    assert calculate_fit({"a": 3}, {"a": 1}, -2)[0] == 1.0
    assert calculate_fit({"a": -3}, {"a": 1}, 1)[0] == 0.0


def test_analyzer_returns_two_to_four_with_missing_evidence() -> None:
    output = analyze_directions({}, limit=3)
    assert len(output["data"]["directions"]) == 3
    assert output["data"]["stage"] == "当前为探索阶段"
    assert all(item["missing_evidence"] for item in output["data"]["directions"])


def test_unconfirmed_formal_gate() -> None:
    output = formal_plan_gate({})
    assert not output["ok"]
    assert output["errors"][0]["code"] == "DIRECTION_NOT_CONFIRMED"


def test_partial_confirmation_requests_destination() -> None:
    output = update_confirmation({}, {"primary_direction": "java-backend"})
    assert output["data"]["computed_status"] == "PARTIALLY_CONFIRMED"
    assert "target_city" in output["data"]["missing_for_formal_plan"]


def test_direction_change_records_history_and_invalidates_plan() -> None:
    current = {"primary_direction": "data-analysis", "target_city": "杭州", "job_search_period": "2027", "status": "CONFIRMED"}
    output = update_confirmation(current, {"primary_direction": "java-backend"})
    assert output["data"]["status"] == "CHANGED"
    assert output["data"]["history"][0]["old"] == "data-analysis"
    assert "current_plan" in output["data"]["invalidated"]
