from __future__ import annotations

from scripts.learning.tutor_engine import TutorEngine


def test_tutor_executes_full_learning_loop_with_progressive_hints() -> None:
    result = TutorEngine().start(
        {"task_id": "dcf", "skill": "DCF", "learning_objective": "完成一版 DCF"},
        verified_level=0.1,
    )

    assert result["teaching_loop"] == [
        "DIAGNOSE", "TEACH", "DEMONSTRATE", "PRACTICE", "HINT", "ASSESS", "FEEDBACK", "UPDATE_MASTERY", "NEXT"
    ]
    assert result["diagnosis"]["questions"]
    assert len(result["hint_ladder"]) >= 3
    assert result["hint_ladder"][0]["level"] == 1
    assert "FCFF" in str(result)
    assert result["mastery"]["before"] == 0.1


def test_law_tutor_practice_requires_irac_and_authority() -> None:
    result = TutorEngine().start({"task_id": "law", "skill": "案例分析", "learning_objective": "完成法律案例分析"})
    text = str(result)

    assert "IRAC" in text
    assert "法条" in text
    assert "检索" in text


def test_pharmacology_tutor_uses_mechanism_chain_not_generic_project() -> None:
    result = TutorEngine().start({"task_id": "pharm", "skill": "药理学", "learning_objective": "理解药物机制"})
    text = str(result)

    assert all(term in text for term in ("靶点", "机制", "治疗作用", "不良反应"))
    assert "通用项目" not in text
