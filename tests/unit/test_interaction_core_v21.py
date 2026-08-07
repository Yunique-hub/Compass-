from scripts.core.duplicate_question_guard import DuplicateQuestionGuard
from scripts.core.known_facts import extract_known_facts, fact_value, merge_known_facts
from scripts.core.profile_sufficiency import evaluate_profile_sufficiency
from scripts.core.question_policy import select_questions
from scripts.core.stage_detector import GrowthStage, detect_stage
from scripts.academic.capacity_engine import calculate_realistic_capacity
from scripts.core.goal_planner import build_goal_plan
from scripts.core.mentor_diagnosis import build_mentor_diagnosis
from scripts.core.mentor_response_builder import action_response


def test_extracts_real_it_support_profile_and_confirmation() -> None:
    facts = extract_known_facts("我是专科大二计算机网络技术专业，明年实习，学过路由交换、网络安全和服务器配置。")
    facts = merge_known_facts(facts, extract_known_facts("IT支持方向，每天大概能学习6小时。"))
    assert fact_value(facts, "education_level") == "专科"
    assert fact_value(facts, "grade") == "大二"
    assert fact_value(facts, "major") == "计算机网络技术"
    assert fact_value(facts, "direction_status") == "confirmed"
    assert fact_value(facts, "daily_learning_hours") == 6


def test_stage_detector_required_cases() -> None:
    internship = extract_known_facts("专科大二，明年实习，毕业直接就业")
    assert detect_stage(internship).stage is GrowthStage.INTERNSHIP_PREPARATION_STAGE
    job_search = extract_known_facts("本科大四，正在秋招找工作")
    assert detect_stage(job_search).stage is GrowthStage.JOB_SEARCH_STAGE
    exam = extract_known_facts("操作系统考试还有5天")
    assert detect_stage(exam).stage is GrowthStage.EXAM_SPRINT_STAGE


def test_sufficiency_is_action_ready_without_city() -> None:
    facts = extract_known_facts("计算机网络技术大二，明年实习，学过路由交换和服务器，每天6小时")
    result = evaluate_profile_sufficiency(facts, intent="LEARNING_PLAN", stage="INTERNSHIP_PREPARATION_STAGE")
    assert result.action_ready is True
    assert "target_city" in result.missing_non_blocking
    assert result.planning_mode == "PRELIMINARY_PLAN"


def test_major_only_is_not_sufficient() -> None:
    result = evaluate_profile_sufficiency(extract_known_facts("我是软件工程专业"), intent="GENERAL_SUPPORT")
    assert result.action_ready is False
    assert result.missing_blocking


def test_formal_market_plan_still_requires_city() -> None:
    facts = extract_known_facts("软件工程大三，明年实习，IT支持方向，学过Python")
    result = evaluate_profile_sufficiency(facts, intent="RECRUITMENT_ANALYSIS", stage="INTERNSHIP_PREPARATION_STAGE")
    assert result.action_ready is False
    assert "target_city" in result.missing_blocking


def test_duplicate_question_guard_uses_field_semantics() -> None:
    facts = merge_known_facts(
        extract_known_facts("IT支持方向，每天6小时"),
        extract_known_facts("Python有简单项目经验"),
    )
    guard = DuplicateQuestionGuard(facts)
    assert guard.can_ask("career_direction") is False
    assert guard.can_ask("daily_learning_hours") is False
    assert guard.can_ask("python_project_experience") is False


def test_question_budget_never_exceeds_three_and_respects_history() -> None:
    facts = extract_known_facts("专科")
    output = select_questions(
        ["major", "grade", "primary_need", "skills", "career_direction", "daily_learning_hours"],
        facts, asked_fields=["major"],
    )
    assert len(output["questions"]) <= 3
    assert "major" not in output["asked_fields"]
    assert select_questions(["skills"], facts, question_only_streak=2)["questions"] == []


def test_cold_start_capacity_does_not_fill_six_hours_per_day() -> None:
    capacity = calculate_realistic_capacity(daily_hours=6, cold_start=True)
    assert capacity["stated_weekly_hours"] == 42
    assert capacity["planned_weekly_hours"] <= 42 * 0.70
    assert capacity["capacity_confidence"] == "low"


def test_goal_plan_has_three_levels_and_at_most_three_executable_tasks() -> None:
    facts = extract_known_facts("专科大二计算机网络技术，明年实习，IT支持方向，学过路由交换和Python，每天6小时，喜欢写代码")
    stage = detect_stage(facts).to_dict()
    capacity = calculate_realistic_capacity(daily_hours=6, cold_start=True)
    plan = build_goal_plan(facts, stage, capacity)
    assert plan["primary_goal"]
    assert len(plan["stage_goals"]) == 4
    assert 1 <= len(plan["weekly_core_tasks"]) <= 3
    assert all(task["acceptance_criteria"] and task["output"] and task["fallback"] for task in plan["weekly_core_tasks"])
    assert "批量 Ping" in " ".join(task["title"] for task in plan["weekly_core_tasks"])


def test_mentor_response_contains_judgment_and_action_without_internal_score() -> None:
    facts = extract_known_facts("专科大二计算机网络技术，明年实习，IT支持方向，学过路由交换和Python，每天6小时，喜欢写代码")
    stage = detect_stage(facts).to_dict()
    capacity = calculate_realistic_capacity(daily_hours=6, cold_start=True)
    plan = build_goal_plan(facts, stage, capacity)
    diagnosis = build_mentor_diagnosis(facts, stage, planning_confidence="medium")
    response = action_response("小宇", diagnosis, plan, capacity)
    assert "【我对你当前状态的判断】" in response["text"]
    assert "【这周只做这3件事】" in response["text"]
    assert "profile score" not in response["text"].casefold()
