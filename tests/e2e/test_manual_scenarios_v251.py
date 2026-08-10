"""Executable acceptance suite for the Compass 2.5.1 manual scenarios A–T."""

from __future__ import annotations

from pathlib import Path

from scripts.academic.major_engine import MajorMentionType, classify_major_mention, identify_academic_profile
from scripts.compass_engine import CompassEngine
from scripts.learning.assessment_engine import AssessmentEngine
from scripts.memory.memory_engine import MemoryEngine
from scripts.resource_matcher import match_resources


def _run(root: Path, case: str, message: str) -> dict:
    return CompassEngine(root).run({"user_id": case, "message": message})["data"]


def _business(data: dict) -> dict:
    return data["response"]["details"]["business"]


def test_scenario_a_major_false_positive_and_direct_help(tmp_path: Path) -> None:
    data = _run(tmp_path, "A", "算法学得很痛苦。")
    profile = _business(data)["growth_context"]["academic_profile"]
    tutor = _business(data)["tutor"]
    memory = MemoryEngine(CompassEngine(tmp_path)._paths("A")[1]).load_user_context(user_id="A")
    assert profile["raw_major"] == ""
    assert "major" not in memory["profile"]
    assert data["intent"] == "START_LEARNING"
    assert tutor["status"] == "lesson_active" and tutor["skill"] == "算法"


def test_scenario_b_major_negation(tmp_path: Path) -> None:
    data = _run(tmp_path, "B", "我不是法学专业。")
    memory = MemoryEngine(CompassEngine(tmp_path)._paths("B")[1]).load_user_context(user_id="B")
    assert _business(data)["growth_context"]["academic_profile"]["raw_major"] == ""
    assert "major" not in memory["profile"]


def test_scenario_c_third_party_major(tmp_path: Path) -> None:
    data = _run(tmp_path, "C", "我的同学是法学专业。")
    memory = MemoryEngine(CompassEngine(tmp_path)._paths("C")[1]).load_user_context(user_id="C")
    assert _business(data)["growth_context"]["academic_profile"]["raw_major"] == ""
    assert "major" not in memory["profile"]


def test_scenario_d_target_major_is_not_current_major() -> None:
    mention = classify_major_mention("我想转法学。")
    profile = identify_academic_profile("我想转法学。")
    assert mention.mention_type is MajorMentionType.TARGET_MAJOR
    assert profile.raw_major == ""
    assert profile.transition_target == "法学"


def test_scenario_e_nursing_isolated_domain(tmp_path: Path) -> None:
    data = _run(tmp_path, "E", "我是护理学大二，想提升专业能力。")
    business = _business(data)
    combined = f"{data['text']}\n{business}"
    assert business["growth_context"]["academic_profile"]["taxonomy_domain"] == "nursing"
    assert "护理评估" in combined and "患者安全" in combined
    assert "鉴别诊断" not in combined and "Java" not in combined


def test_scenario_f_pharmacy_domain_authenticity(tmp_path: Path) -> None:
    data = _run(tmp_path, "F", "我是药学大二，想提升专业能力。")
    business = _business(data)
    combined = f"{data['text']}\n{business}"
    assert business["growth_context"]["academic_profile"]["taxonomy_domain"] == "pharmacy"
    assert "药理" in combined and "合理用药" in combined
    assert "鉴别诊断" not in combined


def test_scenario_g_chemistry_not_mathematics(tmp_path: Path) -> None:
    data = _run(tmp_path, "G", "我是应用化学大二，想提升专业能力。")
    business = _business(data)
    combined = f"{data['text']}\n{business}"
    assert business["growth_context"]["academic_profile"]["taxonomy_domain"] == "chemistry"
    assert "化学" in combined and "实验" in combined
    assert "数学证明" not in combined


def test_scenario_h_materials_not_mechanical_cad(tmp_path: Path) -> None:
    data = _run(tmp_path, "H", "我是材料科学大二。")
    business = _business(data)
    assert business["growth_context"]["academic_profile"]["taxonomy_domain"] == "chemical_materials_engineering"
    assert "机械 CAD" not in f"{data['text']}\n{business}"


def test_scenario_i_psychology_graduate_school(tmp_path: Path) -> None:
    data = _run(tmp_path, "I", "我是心理学大二，准备以后读研。")
    business = _business(data)
    combined = f"{data['text']}\n{business}"
    assert business["growth_context"]["target_pathway"] == "graduate_school"
    assert all(term in combined for term in ("统计", "研究方法", "文献", "证据"))


def test_scenario_j_psychology_ux_is_distinct(tmp_path: Path) -> None:
    data = _run(tmp_path, "J", "我是心理学大二，想做 UX Research。")
    business = _business(data)
    task = business["goal_plan"]["weekly_core_tasks"][0]
    assert business["growth_context"]["target_pathway"] == "employment"
    assert task["task_id"] == "domain:psychology.ux.research"
    assert "产品" in str(task) and "访谈" in str(task)
    assert "心理学研究设计" not in str(task)


def test_scenario_k_multi_goal_and_time_budget(tmp_path: Path) -> None:
    data = _run(tmp_path, "K", "我是法学大三，准备法考，也想找律所实习，每周8小时。")
    business = _business(data)
    tasks = business["goal_plan"]["weekly_core_tasks"]
    assert business["growth_context"]["goal_portfolio"]["secondary"]
    assert {task["goal_type"] for task in tasks} >= {"professional_qualification", "internship"}
    assert sum(task["allocated_hours"] for task in tasks) <= 8.0


def test_scenario_l_assessment_negation() -> None:
    result = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "FCFF我做完了，但是WACC折现还没做，终值和敏感性分析也没有做。"},
        criteria=["列出 FCFF 预测及关键假设", "使用 WACC 折现显性期现金流", "计算终值", "完成至少一组敏感性分析"],
    )
    assert [item["status"] for item in result["criteria"]] == ["MET", "MISSING", "MISSING", "MISSING"]


def test_scenario_m_assessment_uncertainty() -> None:
    result = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "WACC我算了，但是不确定方法对不对。"},
        criteria=["使用 WACC 折现显性期现金流"],
    )
    item = result["criteria"][0]
    assert item["status"] in {"PARTIAL", "UNCLEAR"}
    assert item["confidence"] < 0.9


def test_scenario_n_direct_qa_opportunity_cost(tmp_path: Path) -> None:
    data = _run(tmp_path, "N", "什么是机会成本？")
    assert data["intent"] == "KNOWLEDGE_QA"
    assert "放弃" in data["text"] and "怎么称呼" not in data["text"]


def test_scenario_o_direct_qa_irac(tmp_path: Path) -> None:
    data = _run(tmp_path, "O", "IRAC是什么？")
    assert data["intent"] == "KNOWLEDGE_QA"
    assert all(term in data["text"] for term in ("规则", "分析", "结论"))
    assert "怎么称呼" not in data["text"]


def test_scenario_p_resource_isolation() -> None:
    result = match_resources(["英语写作"], minimum=2)["data"]
    assert "Java" not in str(result) and "Spring" not in str(result)


def test_scenario_q_cross_major_bridge_plan(tmp_path: Path) -> None:
    data = _run(tmp_path, "Q", "我学土木，但想转数据分析。")
    business = _business(data)
    profile = business["growth_context"]["academic_profile"]
    task = business["goal_plan"]["weekly_core_tasks"][0]
    assert profile["raw_major"] == "土木" and profile["transition_target"] == "数据分析"
    assert business["growth_context"]["target_pathway"] == "career_transition"
    assert "桥接" in task["skill"] and "原专业数据" in str(task)


def test_scenario_r_double_major_pathway_comparison(tmp_path: Path) -> None:
    data = _run(tmp_path, "R", "我是数学和经济双专业，不知道走量化还是经济学研究。")
    profile = _business(data)["growth_context"]["academic_profile"]
    assert profile["raw_major"] == "数学" and profile["secondary_major"] == "经济"
    assert data["intent"] == "CAREER_EXPLORE"
    assert "量化" in data["text"] and "经济学研究" in data["text"] and "比较" in data["text"]


def test_scenario_s_unknown_major_uses_honest_fallback(tmp_path: Path) -> None:
    data = _run(tmp_path, "S", "我是葡萄与葡萄酒工程大二，想找行业实习。")
    profile = _business(data)["growth_context"]["academic_profile"]
    assert profile["raw_major"] == "葡萄与葡萄酒工程"
    assert profile["knowledge_source"] == "family_fallback"
    assert "一般培养逻辑" in data["text"] and "需要验证" in data["text"]


def test_scenario_t_stress_reduces_actual_plan_load(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    before = engine.run({"user_id": "T", "message": "我是法学大三，准备法考，每周10小时。"})["data"]
    after = engine.run({"user_id": "T", "message": "最近压力很大，这周真的学不动。"})["data"]
    before_hours = before["archive"]["realistic_capacity"]["planned_weekly_hours"]
    after_hours = after["archive"]["realistic_capacity"]["planned_weekly_hours"]
    tasks = after["archive"]["academic"]["current_plan"]["weekly_core_tasks"]
    assert after_hours <= before_hours * 0.5
    assert len(tasks) <= 1
    assert "压力" in after["text"] and "本周实际计划上限已调整" in after["text"]
