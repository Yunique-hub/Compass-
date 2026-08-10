from __future__ import annotations

from pathlib import Path

from scripts.compass_engine import CompassEngine
from scripts.memory.memory_engine import MemoryEngine


def _turn(engine: CompassEngine, user_id: str, message: str, **extra: object) -> dict:
    return engine.run({"user_id": user_id, "message": message, **extra})["data"]


def test_first_actionable_message_delivers_value_before_optional_name(tmp_path: Path) -> None:
    output = _turn(
        CompassEngine(tmp_path),
        "new-student",
        "我是大二计算机专业，Python 会一点，明年想找后端实习，现在怎么准备？",
    )

    response = output["response"]
    assert output["state"] == "ACTION_READY"
    assert response["do_now"]
    assert response["current_goal"]
    assert "怎么称呼" not in output["text"] or response["do_now"]


def test_questions_are_minimized_when_current_advice_is_possible(tmp_path: Path) -> None:
    output = _turn(
        CompassEngine(tmp_path),
        "minimal-questions",
        "计算机大二，学过 Python，明年准备找后端实习，现在怎么规划？",
    )

    questions = output["response"].get("questions", [])
    assert len(questions) <= 1
    assert not any(field in output["text"] for field in ("年龄", "GPA", "学校", "姓名"))
    assert output["response"]["do_now"]


def test_inference_is_not_persisted_as_verified_fact(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    user_id = "fact-boundary"
    engine = CompassEngine(runtime)
    _turn(engine, user_id, "算法学得很痛苦。")

    archive_path, memory_path, _ = engine._paths(user_id)
    archive_text = archive_path.read_text(encoding="utf-8")
    memory = MemoryEngine(memory_path).load_user_context(user_id=user_id, query="算法")
    assert "algorithm_level" not in archive_text
    assert "algorithm_level" not in str(memory)
    assert "poor" not in str(memory)


def test_repeated_goal_is_deduplicated(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    user_id = "dedupe"
    message = "我的长期目标是明年找 Python 后端实习。"
    for _ in range(3):
        _turn(engine, user_id, message)

    _, memory_path, _ = engine._paths(user_id)
    records = MemoryEngine(memory_path).load(user_id=user_id, query="Python 后端")["data"]["results"]
    ids = [item["record"]["record_id"] for item in records]
    assert len(ids) == len(set(ids))


def test_complex_growth_response_uses_one_action_contract(tmp_path: Path) -> None:
    output = _turn(
        CompassEngine(tmp_path),
        "response-contract",
        "计算机大二，学过 Python 和数据库，明年准备找后端实习，每周能学 10 小时，现在怎么规划？",
    )

    response = output["response"]
    assert response["current_judgment"]
    assert response["current_goal"]
    assert response["do_now"]
    assert response["why"]
    assert response["next_step"]


def test_simple_knowledge_question_is_not_forced_into_growth_template(tmp_path: Path) -> None:
    output = _turn(CompassEngine(tmp_path), "knowledge", "Python 列表和元组有什么区别？")

    assert output["intent"] == "KNOWLEDGE_QA"
    assert "列表" in output["text"] and "元组" in output["text"]
    assert "未来 12 个月" not in output["text"]
    assert len(output["response"].get("do_now", [])) <= 1


def test_research_without_live_source_marks_uncertainty(tmp_path: Path) -> None:
    output = _turn(CompassEngine(tmp_path), "research-boundary", "现在后端实习市场最看重什么？")

    assert output["intent"] == "RECRUITMENT_ANALYSIS"
    assert any(term in output["text"] for term in ("需验证", "不确定", "样本不足", "insufficient"))


def test_persisted_state_restores_on_next_engine_instance(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    first = CompassEngine(runtime)
    _turn(first, "resume", "叫我小宇，我是计算机大二，学过 Python，每周学习 8 小时，明年找后端实习。")

    resumed = _turn(CompassEngine(runtime), "resume", "继续上次计划。")
    assert "怎么称呼" not in resumed["text"]
    assert resumed["archive"]["preferred_name"] == "小宇"
    assert resumed["response"]["next_step"]
