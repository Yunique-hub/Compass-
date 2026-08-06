from __future__ import annotations

import json
from pathlib import Path

from scripts.archive_export import build_archive, to_markdown
from scripts.archive_import import parse_content
from scripts.career_direction_analyzer import analyze_directions
from scripts.competency_gap import build_gaps
from scripts.conflict_resolver import resolve_conflicts
from scripts.demo_pipeline import run_demo
from scripts.direction_confirmation import update_confirmation
from scripts.jd_analyzer import analyze_multiple
from scripts.memory_retriever import retrieve
from scripts.memory_store import FileMemoryStore, UnavailableVectorStore, forget_everywhere
from scripts.plan_generator import generate_plan
from scripts.plan_validator import validate_plan
from scripts.recruitment_data_processor import process_snapshot
from scripts.safety_router import route_safety

ROOT = Path(__file__).resolve().parents[2]


def snapshot() -> dict:
    return json.loads((ROOT / "reference" / "recruitment_snapshots" / "cities" / "hangzhou" / "java-backend-demo-v0.1.json").read_text(encoding="utf-8"))


def confirmed() -> dict:
    return update_confirmation({}, {"primary_direction": "java-backend", "target_city": "杭州", "job_search_period": "2028 春招"})["data"]


def test_new_user_direction_analysis_does_not_formal_plan() -> None:
    directions = analyze_directions({}, limit=3)
    plan = generate_plan({}, [], weekly_hours=8, snapshot_version="", exploration_tasks=[item["exploration_task"] for item in directions["data"]["directions"]])
    assert plan["data"]["formal_plan_generated"] is False and plan["data"]["mode"] == "exploration"


def test_confirmed_direction_without_destination_requests_it() -> None:
    plan = generate_plan({"primary_direction": "java-backend"}, [], weekly_hours=8, snapshot_version="v")
    assert not plan["ok"] and plan["fallback"]["action"] == "request_destination_or_deadline"


def test_confirmed_goal_snapshot_gap_and_formal_plan() -> None:
    recruitment = process_snapshot(snapshot())
    gaps = build_gaps(recruitment["data"]["skill_statistics"], {})
    plan = generate_plan(confirmed(), gaps["data"]["gaps"], weekly_hours=10, snapshot_version=recruitment["data"]["snapshot"]["snapshot_version"], synthetic=True)
    assert plan["ok"] and plan["data"]["formal_plan_generated"] is True


def test_multiple_jds_build_real_input_skill_graph() -> None:
    output = analyze_multiple([
        {"jd_id": "1", "text": "本科岗位，要求 Java、Spring Boot 和 MySQL，完成 Web 项目并提交接口文档，沟通协作良好。"},
        {"jd_id": "2", "text": "本科岗位，使用 Java、SpringBoot、Redis 与 Git 开发服务，需要项目经验和责任心。"},
    ])
    assert output["data"]["valid_count"] == 2 and output["data"]["skill_statistics"]["Spring Boot"]["frequency"] == 1.0


def test_overbudget_plan_auto_recovers() -> None:
    tasks = [{"task_id": f"t{i}", "title": "任务", "priority": i / 10, "estimated_hours": 3, "output": "产出", "acceptance_criteria": ["通过"], "dependencies": ["准备"], "resources": [{"name": "本地"}], "fallback": "缩小范围"} for i in range(5)]
    plan = {"mode": "formal", "basis": {"direction": "java"}, "snapshot_version": "v", "weekly_core_tasks": tasks, "optional_tasks": [], "capacity_limit": 6}
    fixed = validate_plan(plan, confirmed())["data"]["plan"]
    assert len(fixed["weekly_core_tasks"]) == 2 and fixed["total_weekly_hours"] <= 6


def test_archive_export_reimport_preserves_explicit_fields() -> None:
    original = build_archive({"updated_at": "2026-08-06", "explicit_profile": {"user_id": "u", "major": "计算机"}, "confirmed_goal": confirmed(), "recruitment_snapshot": {"snapshot_version": "v"}})
    restored = parse_content(to_markdown(original))
    assert restored["explicit_profile"] == original.explicit_profile
    assert restored["confirmed_goal"] == original.confirmed_goal


def test_direction_change_invalidates_old_plan() -> None:
    output = resolve_conflicts({"primary_direction": "data-analysis"}, {"primary_direction": "java-backend"}, user_explicit=True)
    assert output["data"]["merged"]["primary_direction"] == "data-analysis"
    assert "current_plan" in output["data"]["invalidated"]


def test_destination_change_invalidates_city_snapshot() -> None:
    output = resolve_conflicts({"target_city": "杭州"}, {"target_city": "上海"}, user_explicit=True)
    assert "recruitment_snapshot" in output["data"]["invalidated"]


def test_vector_failure_archive_mode_continues(tmp_path: Path) -> None:
    store = FileMemoryStore(tmp_path / "memory.json")
    store.upsert("u", {"candidate_id": "m", "user_id": "u", "memory_type": "profile_fact", "content": "计算机专业"})
    output = retrieve(store, "u", "专业", vector_store=UnavailableVectorStore())
    assert output["ok"] and output["warnings"][0]["code"] == "VECTOR_STORE_UNAVAILABLE"


def test_stress_reduces_load_and_high_risk_stops() -> None:
    stress = route_safety("我压力大，学不动")
    risk = route_safety("我想伤害自己")
    assert stress["data"]["task_load_factor"] < 1 and not stress["data"]["stop_learning_plan"]
    assert risk["data"]["stop_learning_plan"] and risk["data"]["type"] == "high_risk"


def test_forget_removes_store_and_cache(tmp_path: Path) -> None:
    store = FileMemoryStore(tmp_path / "memory.json")
    store.upsert("u", {"candidate_id": "m", "user_id": "u", "memory_type": "event", "content": "待删除"})
    cache = {"u:query": "cached"}
    summary = forget_everywhere("u", store, cache=cache)
    assert summary["structured_records"] == 1 and not cache and store.list("u") == []


def test_fixed_demo_closes_all_steps_and_marks_synthetic() -> None:
    output = run_demo()
    assert output["ok"] and output["data"]["completed_steps"] == 16
    assert "仅用于功能测试" in output["data"]["synthetic_data_notice"]
    assert output["data"]["formal_plan"]["formal_plan_generated"] is True
