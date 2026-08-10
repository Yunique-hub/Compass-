from __future__ import annotations

from scripts.academic.major_engine import identify_academic_profile
from scripts.academic.pathway_engine import detect_pathway
from scripts.core.growth_context import build_growth_context
from scripts.core.known_facts import extract_known_facts
from scripts.core.stage_detector import GrowthStage, detect_stage


def test_law_exam_and_internship_form_weighted_goal_portfolio() -> None:
    message = "法学大三，准备法考，同时想找律所实习，每周 8 小时。"
    facts = extract_known_facts(message)
    pathway = detect_pathway(message, facts)
    portfolio = pathway.goal_portfolio

    assert portfolio is not None
    assert portfolio.primary.goal_type == "professional_qualification"
    assert portfolio.secondary[0].goal_type == "internship"
    assert portfolio.primary.priority == 0.6
    assert portfolio.secondary[0].priority == 0.4
    assert portfolio.primary.allocated_hours == 4.8
    assert portfolio.secondary[0].allocated_hours == 3.2

    context = build_growth_context(identify_academic_profile(message), pathway, stage="EXAM_PREPARATION_STAGE", weekly_capacity=8)
    text = str(context.competencies)
    assert "资格考试" in text and "实习" in text


def test_clear_investment_bank_goal_is_not_career_exploration() -> None:
    stage = detect_stage(extract_known_facts("金融大二，想进投行"))

    assert stage.stage in {GrowthStage.FOUNDATION_STAGE, GrowthStage.SKILL_BUILDING_STAGE, GrowthStage.INTERNSHIP_PREPARATION_STAGE}
    assert stage.stage is not GrowthStage.CAREER_EXPLORATION_STAGE
    assert stage.signals["goal_clarity"] == "clear"
