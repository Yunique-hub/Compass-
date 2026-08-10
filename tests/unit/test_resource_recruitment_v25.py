from __future__ import annotations

from scripts.recruitment.skill_extractor import SkillExtractor
from scripts.resource_matcher import load_resources, match_resources


def test_resource_registry_is_domain_aware_and_locally_verified() -> None:
    resources = load_resources()
    names = " ".join(item["name"] for item in resources)

    assert all(term in names for term in ("DCF", "IRAC", "研究设计", "CAD", "教案"))
    result = match_resources(["法律检索"], minimum=1, maximum=2)["data"]
    assert result["resources"][0]["resource_id"] == "local-law-irac"
    assert all(item["verified"] for item in result["resources"])


def test_recruitment_normalizes_nontechnical_domain_skills(tmp_path) -> None:
    extractor = SkillExtractor(tmp_path / "dynamic.json")
    result = extractor.extract("要求具备法律检索、法律写作和跨部门沟通能力，有案例分析经验。")

    assert all(skill in result["hard_skills"] for skill in ("Legal Research", "Legal Writing", "IRAC", "Stakeholder Communication"))


def test_recruitment_keeps_open_vocabulary_for_unknown_domain_terms(tmp_path) -> None:
    extractor = SkillExtractor(tmp_path / "dynamic.json")
    result = extractor.extract("要求掌握葡萄酒感官评价能力，具备酒窖流程经验。")

    assert any("葡萄酒感官评价" in skill for skill in result["hard_skills"])
    assert result["dynamic_skills"]
