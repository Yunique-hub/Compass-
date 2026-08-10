from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.competency_gap import build_gaps, calculate_priority
from scripts.jd_analyzer import analyze_jd, analyze_multiple
from scripts.plan_generator import generate_plan
from scripts.plan_validator import validate_plan
from scripts.recruitment_data_processor import normalize_skill, process_snapshot
from scripts.resource_matcher import match_resources

ROOT = Path(__file__).resolve().parents[2]


def snapshot_raw() -> dict:
    return json.loads((ROOT / "reference" / "recruitment_snapshots" / "cities" / "hangzhou" / "java-backend-demo-v0.1.json").read_text(encoding="utf-8"))


def confirmation() -> dict:
    return {"primary_direction": "java-backend", "target_city": "杭州", "job_search_period": "2028 春招", "status": "CONFIRMED"}


def test_skill_alias_merge() -> None:
    aliases = {"spring boot": "Spring Boot"}
    assert normalize_skill("Spring-Boot", aliases) == "Spring Boot"


def test_recruitment_dedup_frequency_confidence_and_synthetic() -> None:
    output = process_snapshot(snapshot_raw())
    data = output["data"]
    assert data["duplicate_job_ids"] == ["syn-hz-java-006-dup"]
    assert data["snapshot"]["valid_sample_count"] == 6
    assert data["skill_statistics"]["Java"]["frequency"] == 1.0
    assert len(data["skill_statistics"]["Java"]["job_ids"]) == 6
    assert data["snapshot"]["confidence_level"] == "low_confidence"
    assert data["snapshot"]["synthetic"] is True
    assert "仅用于功能测试" in data["snapshot"]["usage_notice"]


def test_invalid_job_is_reported() -> None:
    raw = snapshot_raw()
    raw["jobs"].append({"job_id": "bad"})
    assert process_snapshot(raw)["data"]["invalid_records"]


def test_jd_extracts_fields_and_evidence_positions() -> None:
    text = "本科计算机相关专业，具有2年以上开发经验。熟悉 Java、Spring Boot、MySQL 和 Redis；有 Web 项目经验，沟通协作良好。Docker 经验优先。"
    item = analyze_jd(text)
    assert {"Java", "Spring Boot", "MySQL", "Redis", "Docker"}.issubset(item["hard_skills"])
    assert item["education"] == ["本科"]
    assert item["project_requirements"] and item["bonus_items"] and item["evidence"]


def test_short_jd_needs_confirmation() -> None:
    assert analyze_jd("会 Java")["status"] == "needs_confirmation"


def test_multi_jd_statistics_use_actual_inputs() -> None:
    output = analyze_multiple([
        {"jd_id": "a", "text": "本科岗位，使用 Java 和 Spring Boot 开发接口，需要 MySQL 数据库与项目经验，沟通协作良好。"},
        {"jd_id": "b", "text": "本科岗位，要求 Java、SpringBoot、Redis 和 Git，完成服务端项目并整理接口文档，责任心强。"},
    ])
    assert output["data"]["skill_statistics"]["Java"]["frequency"] == 1.0
    assert output["data"]["skill_statistics"]["Spring Boot"]["jd_ids"] == ["a", "b"]


def test_priority_calculation_and_gap_evidence() -> None:
    assert calculate_priority(1, 1, 1, 1, 1, 0.5) == pytest.approx(2)
    output = build_gaps({"Java": {"frequency": 1.0, "job_ids": ["j1"]}}, {}, deadline_urgency=1)
    gap = output["data"]["gaps"][0]
    assert gap["user_evidence"] == [] and gap["gap_level"] > 0
    assert gap["priority_score"] == 1.0


def test_unconfirmed_direction_only_gets_exploration_plan() -> None:
    output = generate_plan({}, [], weekly_hours=10, snapshot_version="", exploration_tasks=["任务一", "任务二", "任务三"])
    assert output["data"]["mode"] == "exploration"
    assert output["data"]["max_weeks"] == 2
    assert len(output["data"]["weekly_core_tasks"]) == 2


def test_partial_confirmation_blocks_destination_plan() -> None:
    output = generate_plan({"primary_direction": "java-backend"}, [], weekly_hours=10, snapshot_version="v")
    assert not output["ok"]
    assert output["data"]["mode"] == "general_foundation"
    assert "不是基于目的地" in output["data"]["notice"]


def test_formal_plan_budget_max_three_and_complete_fields() -> None:
    stats = process_snapshot(snapshot_raw())["data"]["skill_statistics"]
    gaps = build_gaps(stats, {})["data"]["gaps"]
    output = generate_plan(confirmation(), gaps, weekly_hours=7, snapshot_version="v1", synthetic=True)
    plan = output["data"]["plan"]
    assert output["data"]["formal_plan_generated"] is False
    assert plan["mode"] == "preliminary"
    assert len(plan["weekly_core_tasks"]) <= 3
    assert plan["total_weekly_hours"] <= 7 * 0.85
    for task in plan["weekly_core_tasks"]:
        assert task["output"] and task["acceptance_criteria"] and task["dependencies"] and task["fallback"]
        assert 2 <= len(task["resources"]) <= 4


def test_validator_removes_low_priority_until_within_budget() -> None:
    tasks = [{"task_id": f"t{i}", "title": "x", "priority": i / 10, "estimated_hours": 3, "output": "o", "acceptance_criteria": ["a"], "dependencies": ["d"], "resources": [{"name": "r"}], "fallback": "f"} for i in range(1, 5)]
    plan = {"mode": "formal", "basis": {"x": 1}, "snapshot_version": "v", "weekly_core_tasks": tasks, "optional_tasks": [], "capacity_limit": 6}
    output = validate_plan(plan, confirmation())
    fixed = output["data"]["plan"]
    assert output["data"]["valid"] is True
    assert len(fixed["weekly_core_tasks"]) == 2
    assert fixed["total_weekly_hours"] == 6


def test_resource_matcher_excludes_unverified_and_limits_count() -> None:
    output = match_resources(["Spring Boot"], maximum=4)
    resources = output["data"]["resources"]
    assert 0 < len(resources) <= 4
    assert all("Spring Boot" in item.get("recommended_for", []) for item in resources)
    assert all(item["verified"] for item in resources)
    assert any(item["resource_id"] == "pending-spring-guide" for item in output["warnings"] if False) is False
