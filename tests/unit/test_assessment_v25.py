from __future__ import annotations

from scripts.learning.assessment_engine import AssessmentEngine


DCF_CRITERIA = [
    "列出 FCFF 预测及关键假设",
    "使用 WACC 折现显性期现金流",
    "计算终值并完成至少一组敏感性分析",
]


def test_dcf_natural_language_submission_matches_evidence_to_each_criterion() -> None:
    result = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "我预测了 5 年 FCFF，用 WACC 折现，计算了终值，也做了敏感性分析。"},
        criteria=DCF_CRITERIA,
    )

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert {item["status"] for item in result["criteria"]} == {"MET"}
    assert all(item["supporting_evidence"] for item in result["criteria"])
    assert result["confidence"] >= 0.8


def test_partial_fastapi_submission_does_not_become_full_pass() -> None:
    result = AssessmentEngine().evaluate(
        skill="FastAPI",
        submission={"text": "我只实现了 GET /health，访问后返回 200 和 ok。"},
        criteria=["实现健康检查接口", "实现请求参数校验", "为异常响应编写自动化测试"],
    )

    assert result["passed"] is False
    statuses = [item["status"] for item in result["criteria"]]
    assert statuses[0] == "MET"
    assert statuses[1:] == ["MISSING", "MISSING"]
    assert "参数校验" in result["next_action"] or "自动化测试" in result["next_action"]


def test_law_irac_and_two_statutes_can_be_assessed_from_text() -> None:
    result = AssessmentEngine().evaluate(
        skill="案例分析",
        submission={"text": "我用 IRAC 写了争点、规则、适用和结论，并引用《民法典》第五百零九条和第五百七十七条。"},
        criteria=["使用 IRAC 完成案例分析", "引用至少两个法条并说明适用关系"],
    )

    assert result["passed"] is True
    assert all(item["status"] == "MET" for item in result["criteria"])


def test_unclear_claim_is_not_treated_as_observed_evidence() -> None:
    result = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "应该差不多做完了，但细节记不清。"},
        criteria=DCF_CRITERIA,
    )

    assert result["passed"] is False
    assert all(item["status"] in {"UNCLEAR", "MISSING"} for item in result["criteria"])


def test_negated_evidence_is_not_counted_as_completed() -> None:
    result = AssessmentEngine().evaluate(
        skill="DCF",
        submission={"text": "我预测了5年FCFF，用WACC折现，也计算了终值，但是还没做敏感性分析。"},
        criteria=DCF_CRITERIA,
    )

    assert result["passed"] is False
    assert result["criteria"][2]["status"] == "PARTIAL"
    assert "敏感性" not in result["criteria"][2]["supporting_evidence"]
