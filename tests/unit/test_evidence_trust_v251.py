from __future__ import annotations

from scripts.competency.evidence_engine import EvidenceEngine
from scripts.competency.profile import CompetencyProfile
from scripts.learning.assessment_engine import AssessmentEngine


def test_natural_language_assessment_is_text_supported_not_verified_mastery() -> None:
    assessment = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "我预测了5年FCFF，用WACC折现，计算了终值，也做了敏感性分析。"},
        criteria=["列出 FCFF 预测", "使用 WACC 折现", "计算终值", "完成敏感性分析"],
    )
    evidence = EvidenceEngine().create(
        skill="DCF", evidence_type="financial_model", source="compass-assessment", description=assessment["submission_evidence"], assessment=assessment
    )
    competency = CompetencyProfile.apply_evidence(None, evidence)

    assert assessment["passed"] is True
    assert evidence["verification_level"] == "TEXT_SUPPORTED"
    assert evidence["verification_status"] == "supported"
    assert competency["verified_level"] == 0.0


def test_structured_assessment_remains_compatible_and_auditable() -> None:
    criteria = ["结果可运行", "测试通过"]
    assessment = AssessmentEngine().evaluate(skill="Python", submission={"criteria_met": criteria}, criteria=criteria)
    evidence = EvidenceEngine().create(
        skill="Python", evidence_type="code", source="compass-assessment", description="结构化运行结果", assessment=assessment
    )
    competency = CompetencyProfile.apply_evidence(None, evidence)

    assert evidence["verification_level"] == "ARTIFACT_ASSESSED"
    assert evidence["verification_status"] == "verified"
    assert competency["verified_level"] > 0.0


def test_untrusted_pass_boolean_cannot_force_assessment() -> None:
    assessment = AssessmentEngine().evaluate(
        skill="DCF", submission={"passed": True, "text": "我还没开始。"}, criteria=["完成 WACC 折现"]
    )
    assert assessment["passed"] is False
    assert assessment["criteria"][0]["status"] == "MISSING"
