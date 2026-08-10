from __future__ import annotations

import pytest

from scripts.academic.major_engine import identify_academic_profile
from scripts.academic.taxonomy import ACADEMIC_TAXONOMY
from scripts.competency.domain_intelligence import get_domain_competency
from scripts.learning.domain_task_factory import build_domain_task


def test_taxonomy_covers_all_required_academic_domains() -> None:
    assert len(ACADEMIC_TAXONOMY) >= 37
    assert len(ACADEMIC_TAXONOMY) == len(set(ACADEMIC_TAXONOMY))
    for required in ("nursing", "pharmacy", "public_health", "veterinary_animal_science", "performing_arts", "hospitality_tourism"):
        assert required in ACADEMIC_TAXONOMY


@pytest.mark.parametrize(
    ("message", "taxonomy"),
    [
        ("我是护理学专业", "nursing"),
        ("我是药学专业", "pharmacy"),
        ("我是机械工程专业", "mechanical_industrial_engineering"),
        ("我是材料科学与工程专业", "chemical_materials_engineering"),
        ("我是视觉传达设计专业", "visual_design"),
        ("我是葡萄与葡萄酒工程专业", "agriculture_environment"),
    ],
)
def test_exact_major_is_not_swallowed_by_shared_family(message: str, taxonomy: str) -> None:
    profile = identify_academic_profile(message)
    assert profile.raw_major
    assert profile.taxonomy_domain == taxonomy


@pytest.mark.parametrize(
    ("family", "required"),
    [
        ("finance_accounting", ("FCFF", "WACC", "敏感性")),
        ("law", ("IRAC", "法条", "案例")),
        ("psychology", ("研究", "变量", "伦理")),
        ("life_sciences", ("论文", "图表", "限制")),
        ("engineering", ("CAD", "公差", "工程图")),
        ("art_design", ("用户流", "线框", "走查")),
        ("education", ("教案", "学习目标", "评价")),
    ],
)
def test_domain_task_is_concrete_and_assessable(family: str, required: tuple[str, ...]) -> None:
    task = build_domain_task(family)
    text = str(task)

    assert 1.0 <= task["estimated_time"] <= 3.0
    assert all(term in text for term in required)
    assert task["output"] and task["acceptance_criteria"]
    assert "最小验证" not in text
    definition = task["competency_definition"]
    assert all(definition[key] for key in ("learning_outcomes", "practice_forms", "evidence_types", "assessment_criteria", "common_mistakes", "next_competencies"))


def test_psychology_research_and_ux_use_different_competency_models() -> None:
    research = get_domain_competency("psychology")
    ux = get_domain_competency("psychology", target_role="UX Research 用户研究")

    assert research.competency_id != ux.competency_id
    assert "实验设计" in str(research.to_dict())
    assert "产品决策" in str(ux.to_dict())
