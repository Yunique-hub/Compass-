from __future__ import annotations

import pytest

from scripts.academic.major_engine import identify_academic_profile
from scripts.learning.domain_task_factory import build_domain_task


@pytest.mark.parametrize(
    ("major", "taxonomy"),
    [
        ("计算机科学与技术", "computer_information"),
        ("电子信息工程", "electronic_electrical_engineering"),
        ("机械工程", "mechanical_industrial_engineering"),
        ("土木工程", "civil_built_environment"),
        ("材料科学与工程", "chemical_materials_engineering"),
        ("数学与应用数学", "mathematics_statistics"),
        ("物理学", "physics"),
        ("化学", "chemistry"),
        ("地理科学", "earth_geography"),
        ("生物科学", "life_sciences"),
        ("农学", "agriculture_environment"),
        ("动物医学", "veterinary_animal_science"),
        ("临床医学", "medicine"),
        ("护理学", "nursing"),
        ("药学", "pharmacy"),
        ("公共卫生", "public_health"),
        ("心理学", "psychology"),
        ("经济学", "economics"),
        ("金融学", "finance"),
        ("会计学", "accounting"),
        ("工商管理", "business_management"),
        ("公共管理", "public_administration"),
        ("法学", "law"),
        ("国际关系", "international_relations"),
        ("教育学", "education"),
        ("英语语言文学", "languages_linguistics"),
        ("汉语言文学", "literature"),
        ("历史学", "history_philosophy"),
        ("新闻学", "journalism_communication"),
        ("视觉传达设计", "visual_design"),
        ("音乐表演", "performing_arts"),
        ("建筑学", "architecture"),
        ("体育教育", "sports_physical_education"),
        ("旅游管理", "hospitality_tourism"),
    ],
)
def test_domain_golden_matrix_keeps_major_and_produces_assessable_task(major: str, taxonomy: str) -> None:
    profile = identify_academic_profile(f"我的专业是{major}")
    task = build_domain_task(profile.discipline_family)

    assert profile.raw_major == major
    assert profile.taxonomy_domain == taxonomy
    assert profile.major_status == "confirmed"
    assert 1 <= task["estimated_time"] <= 3
    assert task["specific_action"] and task["output"] and task["acceptance_criteria"]
    assert "最小验证" not in str(task)
    if taxonomy != "computer_information":
        assert "FastAPI" not in str(task)
