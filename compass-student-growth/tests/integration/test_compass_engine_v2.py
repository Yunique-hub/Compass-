from pathlib import Path

from scripts.archive_v2 import migrate_archive
from scripts.compass_engine import CompassEngine


EXPECTED_FLOW = [
    "SAFETY", "MEMORY_LOAD", "INTENT", "STATE", "CONTEXT", "BUSINESS", "REVIEW",
    "RESEARCH", "IMPROVEMENT", "EVOLUTION", "PROACTIVE", "MEMORY_WRITE", "ARCHIVE", "RESPONSE",
]


def test_engine_runs_exact_flow_and_auto_scores_directions(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path / "runtime")
    first = engine.run({"user_id": "student-1", "message": "你好"})["data"]
    assert first["state"] == "ASKING_PREFERRED_NAME"
    engine.run({"user_id": "student-1", "message": "叫我小宇"})
    output = engine.run({"user_id": "student-1", "message": "计算机专业大二，学过 Python，我对职业方向挺迷茫"})["data"]
    assert [step["step"] for step in output["trace"]] == EXPECTED_FLOW
    assert output["intent"] == "CAREER_EXPLORE"
    assert len(output["response"]["details"]["business"]["directions"]) >= 2
    assert "scores" not in output
    assert output["archive"]["archive_version"] == "2.1.0"


def test_engine_safety_stops_before_business(tmp_path: Path) -> None:
    output = CompassEngine(tmp_path).run({"user_id": "student", "message": "我不想活了"})["data"]
    assert output["state"] == "SAFETY_ROUTED"
    assert [step["step"] for step in output["trace"]] == ["SAFETY"]


def test_archive_v1_migration_preserves_unknown_fields() -> None:
    migrated = migrate_archive({"archive_version": "1.0.0", "explicit_profile": {"major": "软件工程"}, "future_field": {"x": 1}}, user_id="u")
    assert migrated["profile"]["major"] == "软件工程"
    assert migrated["extensions"]["future_field"] == {"x": 1}
    assert migrated["extensions"]["migrated_from"] == "1.0.0"


def test_resource_research_requires_explicit_url(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "student", "message": "你好"})
    engine.run({"user_id": "student", "message": "叫我小宇"})
    engine.run({"user_id": "student", "message": "我是计算机专业大二，学过 Python，每天学习 2 小时，最近想提升学习"})
    output = engine.run({"user_id": "student", "message": "帮我找资料"})["data"]
    assert output["intent"] == "RESOURCE_SEARCH"
    assert output["response"]["details"]["business"]["mode"] == "explicit-url-required"
    assert next(step for step in output["trace"] if step["step"] == "RESEARCH")["status"] == "explicit-url-required"


def test_forget_resets_archive_continuity_data(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "student", "message": "计算机专业，我对职业方向挺迷茫"})
    output = engine.run({"user_id": "student", "message": "忘记我的所有记忆"})["data"]
    assert output["archive"]["career"]["directions"] == []
    assert output["archive"]["profile"] == {}
