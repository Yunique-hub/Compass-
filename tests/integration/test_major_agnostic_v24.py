from __future__ import annotations

from pathlib import Path

import pytest

from scripts.academic.major_engine import identify_academic_profile
from scripts.compass_engine import CompassEngine


def _run(tmp_path: Path, message: str, user_id: str = "student") -> dict:
    return CompassEngine(tmp_path).run({"user_id": user_id, "message": message})["data"]


@pytest.mark.parametrize(
    ("message", "family", "required", "forbidden"),
    [
        ("大二计算机，想找 Python 后端实习。", "computer_information", ("Python", "后端"), ("法考", "临床轮转")),
        ("大二金融专业，以后想进投行，但现在什么都没准备。", "finance_accounting", ("财务", "估值", "行业研究"), ("FastAPI", "LeetCode", "React")),
        ("法学大三，准备法考，同时想找律所实习。", "law", ("法考", "法律检索", "案例分析"), ("FastAPI", "GitHub")),
        ("生物大二，想以后申请研究生，现在科研经历为零。", "life_sciences", ("实验", "研究方法", "文献"), ("FastAPI", "LeetCode")),
        ("视觉传达大二，想毕业做 UI/UX。", "art_design", ("UI/UX", "作品集", "用户研究"), ("SQLAlchemy", "法考")),
        ("机械专业大三，想找机器人相关实习。", "engineering", ("机械", "控制", "机器人"), ("法考", "临床轮转")),
        ("心理学大二，想以后申请研究生。", "psychology", ("统计", "研究方法", "实验"), ("FastAPI", "投行")),
    ],
)
def test_domain_aware_golden_scenarios(
    tmp_path: Path,
    message: str,
    family: str,
    required: tuple[str, ...],
    forbidden: tuple[str, ...],
) -> None:
    output = _run(tmp_path / family, message)
    context = output["response"]["details"]["business"]["growth_context"]
    text = output["text"] + str(context)

    assert context["academic_profile"]["discipline_family"] == family
    assert all(term in text for term in required)
    assert not any(term in text for term in forbidden)
    assert output["response"]["do_now"]


def test_english_major_enters_exploration_without_forced_career(tmp_path: Path) -> None:
    output = _run(tmp_path, "英语专业，不知道以后做什么。")
    business = output["response"]["details"]["business"]
    directions = business["pathway_options"]

    assert 3 <= len(directions) <= 5
    assert all(item["title"] not in {"什么", "什么工作", "什么职业"} for item in directions)
    assert "探索" in output["text"]
    assert not any(term in output["text"] for term in ("必须考公", "必须当老师", "FastAPI"))


def test_medicine_learning_problem_uses_domain_tutor_not_career_plan(tmp_path: Path) -> None:
    output = _run(tmp_path, "我是临床医学学生，最近内科学学得很吃力，带我学。")
    tutor = output["response"]["details"]["business"]["tutor"]

    assert "内科学" in str(tutor)
    assert any(term in str(tutor) for term in ("病例", "临床推理", "知识诊断"))
    assert "后端" not in output["text"]


def test_cross_major_transition_builds_bridge_plan(tmp_path: Path) -> None:
    output = _run(tmp_path, "我学土木，但不想做土木，想转数据分析。")
    context = output["response"]["details"]["business"]["growth_context"]
    text = output["text"] + str(context)

    assert context["target_pathway"] == "career_transition"
    assert context["academic_profile"]["raw_major"] == "土木"
    assert all(term in text for term in ("可迁移", "缺口", "数据分析"))
    assert any(term in text for term in ("统计", "SQL", "数据可视化"))


def test_double_major_preserved_and_compared(tmp_path: Path) -> None:
    output = _run(tmp_path, "我是数学和经济双专业，目前不知道走量化还是经济学研究。")
    profile = output["response"]["details"]["business"]["growth_context"]["academic_profile"]

    assert profile["raw_major"] == "数学"
    assert profile["secondary_major"] == "经济"
    assert "比较" in output["text"] or "验证" in output["text"]
    assert "量化" in output["text"] and "经济学研究" in output["text"]


def test_unknown_major_falls_back_without_unsupported(tmp_path: Path) -> None:
    output = _run(tmp_path, "葡萄与葡萄酒工程大二，想知道现在该怎么规划。")
    profile = output["response"]["details"]["business"]["growth_context"]["academic_profile"]

    assert profile["raw_major"] == "葡萄与葡萄酒工程"
    assert profile["discipline_family"]
    assert "不支持" not in output["text"] and "unsupported" not in output["text"].casefold()
    assert output["response"]["do_now"]
    assert any(term in output["text"] for term in ("需要验证", "培养逻辑", "专业基础"))


def test_natural_language_major_variants_and_transition() -> None:
    finance = identify_academic_profile("我学金融，现在大二。")
    mechatronics = identify_academic_profile("我是机械电子工程专业。")
    transition = identify_academic_profile("我本科读生物，现在准备转数据分析。")
    undecided = identify_academic_profile("现在大一，还没分流。")
    minor = identify_academic_profile("我主修计算机，辅修金融，专业方向是人工智能。")

    assert finance.raw_major == "金融"
    assert mechatronics.raw_major == "机械电子工程"
    assert transition.raw_major == "生物" and transition.transition_target == "数据分析"
    assert undecided.discipline_family == "undecided"
    assert minor.raw_major == "计算机" and minor.minor == "金融" and minor.specialization == "人工智能"


def test_same_major_different_goal_produces_different_plan(tmp_path: Path) -> None:
    investment = _run(tmp_path / "investment", "金融大三，目标是投行实习，每周 8 小时。")
    graduate = _run(tmp_path / "graduate", "金融大三，准备申请金融硕士，每周 8 小时。")

    assert "估值" in investment["text"] or "金融模型" in investment["text"]
    assert "研究方法" in graduate["text"] or "推荐信" in graduate["text"]
    assert investment["text"] != graduate["text"]


def test_same_major_goal_different_stage_changes_priority(tmp_path: Path) -> None:
    first_year = _run(tmp_path / "first", "金融大一，以后想进投行。")
    third_year = _run(tmp_path / "third", "金融大三，准备投行实习。")

    assert "方向" in first_year["text"] or "基础" in first_year["text"]
    assert "实习" in third_year["text"] or "面试" in third_year["text"]
    assert first_year["response"]["do_now"] != third_year["response"]["do_now"]


def test_domain_aware_tutor_and_assessment_metadata(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    started = engine.run({"user_id": "finance", "message": "我是金融专业，想学 DCF，现在带我学 DCF。"})["data"]
    tutor = started["response"]["details"]["business"]["tutor"]

    assert all(term in str(tutor) for term in ("FCFF", "WACC", "终值"))
    assert tutor["exercise"]["expected_evidence_type"] == "financial_model"
    criteria = tutor["exercise"]["acceptance_criteria"]
    assessed = engine.run({"user_id": "finance", "message": "提交练习", "submission": {"criteria_met": criteria}})["data"]
    evidence = assessed["response"]["details"]["business"]["assessment"]["evidence"]
    assert evidence["type"] == "financial_model"


def test_major_change_keeps_history_and_uses_current_major(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "switch", "message": "我是材料专业大一。"})
    changed = engine.run({"user_id": "switch", "message": "我从材料转专业到计算机了，现在大二。"})["data"]
    profile = changed["response"]["details"]["business"]["growth_context"]["academic_profile"]

    assert profile["raw_major"] == "计算机"
    assert "材料" in profile["previous_majors"]


def test_pathway_and_role_survive_constraint_only_followup(tmp_path: Path) -> None:
    engine = CompassEngine(tmp_path)
    engine.run({"user_id": "continuity", "message": "我是金融大二，目标是投行实习。"})
    followup = engine.run({"user_id": "continuity", "message": "我每周稳定有 8 小时。"})["data"]
    context = followup["response"]["details"]["business"]["growth_context"]

    assert context["academic_profile"]["raw_major"] == "金融"
    assert context["target_pathway"] == "internship"
    assert "投行" in context["target_role"]
