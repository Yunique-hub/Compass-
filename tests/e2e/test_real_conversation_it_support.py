from __future__ import annotations

from pathlib import Path

import pytest

from scripts.compass_engine import CompassEngine


@pytest.fixture
def conversation(tmp_path: Path) -> tuple[CompassEngine, str]:
    return CompassEngine(tmp_path / "runtime"), "it-support-student"


def _turn(engine: CompassEngine, user_id: str, message: str, **extra: object) -> dict:
    return engine.run({"user_id": user_id, "message": message, **extra})["data"]


def test_real_it_support_conversation_reaches_action_without_reasking(conversation: tuple[CompassEngine, str]) -> None:
    engine, user_id = conversation

    turn1 = _turn(engine, user_id, "你好")
    assert turn1["state"] == "ASKING_PREFERRED_NAME"
    assert "怎么称呼" in turn1["text"]
    assert turn1["archive"]["question_history"]["asked_fields"] == ["preferred_name"]

    turn2 = _turn(engine, user_id, "叫我小宇。")
    assert turn2["archive"]["preferred_name"] == "小宇"
    assert "专业" in turn2["text"] and "年级" in turn2["text"]

    turn3 = _turn(engine, user_id, "我现在是一名专科生大二计算机网络技术专业，明年实习，现在该怎么去做")
    assert turn3["archive"]["current_growth_stage"] == "INTERNSHIP_PREPARATION_STAGE"
    assert "实习准备期" in turn3["text"]
    questions3 = turn3["response"]["mentor_sections"]["questions"]
    assert len(questions3) <= 3

    turn4 = _turn(
        engine,
        user_id,
        "学过路由交换、网络安全、服务器配置，实习方向是网络运维、it支持，对Python比较感兴趣，毕业后直接就业。",
    )
    directions = turn4["response"]["details"]["business"]["directions"]
    assert {item["direction_id"] for item in directions[:3]} >= {"it-support", "network-operations"}
    assert "目前主要学过" not in turn4["text"]
    assert "Python水平" not in turn4["text"]
    assert "未来发展" not in turn4["text"]

    turn5 = _turn(engine, user_id, "IT支持方向，每天大概能学习6小时。")
    facts = turn5["archive"]["known_facts"]
    assert facts["career_direction"]["value"] == "IT支持"
    assert facts["direction_status"]["value"] == "confirmed"
    assert facts["direction_status"]["confidence"] == 1.0
    assert turn5["archive"]["profile_sufficiency"]["action_ready"] is True
    plan = turn5["response"]["details"]["business"]["goal_plan"]
    assert plan["primary_goal"]
    assert len(plan["stage_goals"]) == 4
    assert 1 <= len(plan["weekly_core_tasks"]) <= 3
    assert all(task["acceptance_criteria"] for task in plan["weekly_core_tasks"])
    capacity = turn5["archive"]["realistic_capacity"]
    assert capacity["stated_weekly_hours"] == 42
    assert capacity["planned_weekly_hours"] <= 42 * 0.7
    assert "公司类型" not in turn5["text"]
    assert "目标城市" in turn5["text"] or "哪个城市" in turn5["text"]

    turn6 = _turn(engine, user_id, "互联网公司，喜欢写代码，Python有简单项目经验。")
    facts = turn6["archive"]["known_facts"]
    assert facts["company_preference"]["value"] == "互联网公司"
    assert facts["coding_interest"]["value"] is True
    assert facts["python_project_experience"]["value"] is True
    assert turn6["archive"]["onboarding_complete"] is True
    assert "Python" in turn6["text"] or "自动化" in turn6["text"]
    assert "目前主要学过" not in turn6["text"]


def test_returning_user_resumes_name_and_plan_without_onboarding(conversation: tuple[CompassEngine, str]) -> None:
    engine, user_id = conversation
    for message in (
        "你好",
        "叫我小宇。",
        "我是专科大二计算机网络技术专业，明年实习。",
        "学过路由交换、网络安全、服务器配置，想做IT支持，会点Python，每天6小时。",
    ):
        _turn(engine, user_id, message)

    reopened = CompassEngine(engine.runtime)
    resumed = _turn(reopened, user_id, "继续上次。")
    assert resumed["state"] == "ACTION_READY"
    assert "小宇" in resumed["text"]
    assert "继续" in resumed["text"]
    assert "怎么称呼" not in resumed["text"]


def test_feedback_exam_priority_and_direction_change(conversation: tuple[CompassEngine, str]) -> None:
    engine, user_id = conversation
    for message in (
        "你好",
        "叫我小宇。",
        "我是专科大二计算机网络技术专业，明年实习。",
        "学过路由交换、网络安全、服务器配置，想做IT支持，会点Python，每天6小时。",
    ):
        planned = _turn(engine, user_id, message)

    overloaded = _turn(engine, user_id, "这个星期任务太多了。")
    assert overloaded["response"]["details"]["business"]["improvement"]
    assert len(overloaded["response"]["do_now"]) <= 2
    assert "降载" in overloaded["text"]

    exam = _turn(engine, user_id, "考试还有5天。")
    assert exam["archive"]["current_growth_stage"] == "EXAM_SPRINT_STAGE"
    assert exam["response"]["details"]["business"]["review"]
    assert exam["archive"]["realistic_capacity"]["allocation"]["review_hours"] > exam["archive"]["realistic_capacity"]["allocation"]["career_hours"]

    changed = _turn(engine, user_id, "我不想做IT支持了。")
    assert changed["archive"]["known_facts"]["direction_status"]["value"] == "changed"
    assert changed["archive"]["academic"]["current_plan"]["status"] == "invalidated"
    assert changed["response"]["details"]["business"]["action"] == "EXPLORE_CAREER"
    assert all(item["direction_id"] != "it-support" for item in changed["response"]["details"]["business"]["directions"])


def test_question_budget_and_semantic_duplicate_rate(conversation: tuple[CompassEngine, str]) -> None:
    engine, user_id = conversation
    outputs = [
        _turn(engine, user_id, "你好"),
        _turn(engine, user_id, "叫我小宇。"),
        _turn(engine, user_id, "我是专科大二计算机网络技术专业，明年实习。"),
        _turn(engine, user_id, "学过路由交换、网络安全、服务器配置，网络运维和IT支持都可以，对Python感兴趣。"),
        _turn(engine, user_id, "IT支持方向，每天6小时。"),
    ]
    question_counts = [len(item["response"]["mentor_sections"].get("questions", [])) for item in outputs]
    assert max(question_counts) <= 3
    assert outputs[-1]["archive"]["question_history"]["question_only_streak"] <= 2
    final_text = outputs[-1]["text"]
    assert "IT支持还是运维" not in final_text
    assert "每天能学习多久" not in final_text
    assert "每天能投入多长时间" not in final_text
