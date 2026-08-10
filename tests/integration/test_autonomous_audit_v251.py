from __future__ import annotations

from pathlib import Path

import pytest

from scripts.academic.major_engine import MajorMentionType, classify_major_mention, identify_academic_profile
from scripts.compass_engine import CompassEngine
from scripts.core.known_facts import extract_known_facts
from scripts.learning.assessment_engine import AssessmentEngine
from scripts.memory.memory_engine import MemoryEngine
from scripts.resource_matcher import match_resources


def test_major_attribution_rejects_negation_and_third_party() -> None:
    for message in ("我不是法学专业。", "我的同学是法学专业。"):
        mention = classify_major_mention(message)
        assert mention.persistable is False
        assert identify_academic_profile(message).raw_major == ""
        assert "major" not in extract_known_facts(message)


def test_major_attribution_separates_target_past_and_completed_transition() -> None:
    target = classify_major_mention("我想转法学。")
    target_profile = identify_academic_profile("我想转法学。")
    assert target.mention_type is MajorMentionType.TARGET_MAJOR
    assert target.persistable is False
    assert target_profile.raw_major == ""
    assert target_profile.transition_target == "法学"

    previous = identify_academic_profile("我以前学材料。")
    assert previous.raw_major == ""
    assert previous.previous_majors == ["材料"]

    changed = identify_academic_profile("我从材料转到了计算机。")
    assert changed.raw_major == "计算机"
    assert changed.previous_majors == ["材料"]


def test_assessment_resolves_postposed_negation_partial_and_uncertainty() -> None:
    criteria = ["列出 FCFF 预测及关键假设", "使用 WACC 折现显性期现金流", "计算终值", "完成至少一组敏感性分析"]
    negated = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "FCFF我做完了，但是WACC折现还没做，终值和敏感性分析也没有做。"},
        criteria=criteria,
    )
    assert [item["status"] for item in negated["criteria"]] == ["MET", "MISSING", "MISSING", "MISSING"]

    partial = AssessmentEngine().evaluate(
        skill="DCF", submission={"text": "WACC折现只做了一半。"}, criteria=[criteria[1]]
    )
    assert partial["criteria"][0]["status"] == "PARTIAL"

    uncertain = AssessmentEngine().evaluate(
        skill="DCF", submission={"text": "WACC我算了，但是不确定方法对不对。"}, criteria=[criteria[1]]
    )
    assert uncertain["criteria"][0]["status"] in {"PARTIAL", "UNCLEAR"}
    assert uncertain["criteria"][0]["confidence"] < 0.9


@pytest.mark.parametrize(
    ("message", "required", "forbidden"),
    [
        ("我是护理学大二，想提升专业能力。", ("护理评估", "患者安全"), ("鉴别诊断", "Java")),
        ("我是药学大二，想提升专业能力。", ("药理", "合理用药"), ("鉴别诊断", "Java")),
        ("我是应用化学大二，想提升专业能力。", ("化学", "实验"), ("机械 CAD", "FastAPI")),
        ("我是材料科学大二，想提升专业能力。", ("材料", "表征"), ("机械 CAD", "FastAPI")),
    ],
)
def test_taxonomy_first_planning_prevents_domain_crosstalk(
    tmp_path: Path, message: str, required: tuple[str, ...], forbidden: tuple[str, ...]
) -> None:
    data = CompassEngine(tmp_path).run({"user_id": message, "message": message})["data"]
    text = data["text"]
    task_text = str(data["response"]["details"]["business"]["goal_plan"]["weekly_core_tasks"])
    combined = f"{text}\n{task_text}"
    assert all(term in combined for term in required)
    assert all(term not in combined for term in forbidden)


def test_resource_relevance_is_never_backfilled_across_domains() -> None:
    for competency in ("英语写作", "护理评估"):
        names = [item["name"] for item in match_resources([competency], minimum=2)["data"]["resources"]]
        assert all(term not in " ".join(names) for term in ("Java", "服务端", "Spring"))
    legal = match_resources(["法律检索"], minimum=2)["data"]["resources"]
    assert len(legal) == 1
    assert "IRAC" in legal[0]["name"]


@pytest.mark.parametrize("question", ("什么是机会成本？", "IRAC是什么？", "什么是 p 值？", "什么是 WACC？"))
def test_simple_qa_answers_without_onboarding_or_planning(tmp_path: Path, question: str) -> None:
    data = CompassEngine(tmp_path).run({"user_id": question, "message": question})["data"]
    assert data["intent"] == "KNOWLEDGE_QA"
    assert "怎么称呼" not in data["text"]
    assert "请提供具体概念" not in data["text"]
    assert not data["response"].get("questions")


def test_renderer_hides_internal_labels_and_does_not_claim_three_tasks(tmp_path: Path) -> None:
    data = CompassEngine(tmp_path).run({"user_id": "render", "message": "我是护理学大二，想提升专业能力。"})["data"]
    text = data["text"]
    assert "这周只做这3件事" not in text
    assert "【questions】" not in text
    assert "skill_development" not in text
    assert "以后比较想在哪个城市" not in text


def test_stress_response_preempts_onboarding_and_halves_real_load(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    first = engine.run({"user_id": "stress", "message": "我是法学大三，准备法考，每周10小时。"})["data"]
    before = first["archive"]["realistic_capacity"]["planned_weekly_hours"]
    stressed = engine.run({"user_id": "stress", "message": "最近压力很大，这周真的学不动。"})["data"]
    after = stressed["archive"]["realistic_capacity"]["planned_weekly_hours"]
    assert "怎么称呼" not in stressed["text"]
    assert after <= before * 0.5
    assert len(stressed["archive"]["academic"]["current_plan"]["weekly_core_tasks"]) <= 1


def test_secondary_goal_produces_its_own_weekly_action(tmp_path: Path) -> None:
    data = CompassEngine(tmp_path).run(
        {"user_id": "portfolio", "message": "我是法学大三，准备法考，也想找律所实习，每周8小时。"}
    )["data"]
    business = data["response"]["details"]["business"]
    portfolio = business["growth_context"]["goal_portfolio"]
    tasks = business["goal_plan"]["weekly_core_tasks"]
    assert portfolio["secondary"]
    assert len(tasks) >= 2
    assert {task["goal_type"] for task in tasks} >= {"professional_qualification", "internship"}


def test_graduate_pathway_understands_temporal_variants(tmp_path: Path) -> None:
    for index, phrase in enumerate(("准备以后读研", "之后考虑读研", "毕业后想读研")):
        data = CompassEngine(tmp_path).run({"user_id": f"grad-{index}", "message": f"我是心理学大二，{phrase}。"})["data"]
        context = data["response"]["details"]["business"]["growth_context"]
        assert context["target_pathway"] == "graduate_school"


def test_learning_difficulty_starts_ad_hoc_tutor_without_formal_plan(tmp_path: Path) -> None:
    data = CompassEngine(tmp_path).run({"user_id": "difficulty", "message": "算法学得很痛苦。"})["data"]
    tutor = data["response"]["details"]["business"]["tutor"]
    assert data["intent"] == "START_LEARNING"
    assert tutor["status"] == "lesson_active"
    assert tutor["skill"] == "算法"
    assert "请先" not in data["text"] or "创建" not in data["text"]


def test_cross_session_state_keeps_only_trustworthy_facts(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "confirmed", "message": "我是护理学专业。"})
    confirmed = CompassEngine(tmp_path).run({"user_id": "confirmed", "message": "继续上次。"})["data"]
    confirmed_profile = confirmed["response"]["details"]["business"]["growth_context"]["academic_profile"]
    assert confirmed_profile["raw_major"] == "护理学"

    engine.run({"user_id": "candidate", "message": "我不是法学专业，我最近在学金融。"})
    candidate = CompassEngine(tmp_path).run({"user_id": "candidate", "message": "继续上次。"})["data"]
    candidate_profile = candidate["response"]["details"]["business"]["growth_context"]["academic_profile"]
    candidate_memory = MemoryEngine(CompassEngine(tmp_path)._paths("candidate")[1]).load_user_context(user_id="candidate")
    assert candidate_profile["raw_major"] == ""
    assert "major" not in candidate_memory["profile"]

    engine.run({"user_id": "topic", "message": "我是教育学专业，最近在学统计。"})
    topic = CompassEngine(tmp_path).run({"user_id": "topic", "message": "继续上次。"})["data"]
    topic_profile = topic["response"]["details"]["business"]["growth_context"]["academic_profile"]
    assert topic_profile["raw_major"] == "教育学"
    assert topic_profile["current_topic"] == ""


def test_changed_goal_becomes_current_and_preserves_history(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "goal-change", "message": "我是金融大三，我想进投行。"})
    changed = engine.run({"user_id": "goal-change", "message": "我做过实习后发现不喜欢投行，现在想做商业分析。"})["data"]
    memory = MemoryEngine(engine._paths("goal-change")[1]).load_user_context(user_id="goal-change")
    assert changed["response"]["details"]["business"]["growth_context"]["target_role"] == "商业分析"
    assert memory["goal"]["target_job"] == "商业分析"
    assert memory["goal"]["previous_target_job"] == "投行"


def test_text_supported_evidence_survives_without_verified_mastery(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "trust", "message": "我是金融专业，现在带我学 DCF。"})
    engine.run({"user_id": "trust", "message": "提交练习：我预测了5年FCFF，用WACC折现，计算了终值，也做了敏感性分析。"})
    context = MemoryEngine(engine._paths("trust")[1]).load_user_context(user_id="trust")
    competency = context["competency"]["DCF"]
    assert competency["last_evidence_level"] == "TEXT_SUPPORTED"
    assert competency["verified_level"] == 0.0
