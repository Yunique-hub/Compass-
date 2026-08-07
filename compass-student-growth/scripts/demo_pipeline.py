"""固定“小明”离线演示闭环；所有招聘数据均为醒目标记的合成 fixture。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .archive_export import build_archive
    from .career_direction_analyzer import analyze_directions
    from .competency_gap import build_gaps
    from .direction_confirmation import update_confirmation
    from .io_utils import result, write_json
    from .plan_generator import generate_plan
    from .recruitment_data_processor import process_snapshot
except ImportError:
    from archive_export import build_archive
    from career_direction_analyzer import analyze_directions
    from competency_gap import build_gaps
    from direction_confirmation import update_confirmation
    from io_utils import result, write_json
    from plan_generator import generate_plan
    from recruitment_data_processor import process_snapshot

MODULE = "demo_pipeline"
ROOT = Path(__file__).resolve().parents[1]


def run_demo() -> dict[str, Any]:
    profile = {
        "user_id": "demo-xiaoming", "name": "小明", "major": "计算机科学", "grade": "大二",
        "verified_skills": [
            {"name": "Python", "level": 0.45, "evidence_type": "course", "evidence": "完成 Python 基础课程练习"},
            {"name": "数据结构", "level": 0.30, "evidence_type": "course", "evidence": "完成数据结构入门课程"},
        ],
        "interests": ["后端开发", "数据分析"], "weekly_hours": 10,
        "known_facts": {"direction_confirmed": False}, "pending_confirmations": ["主就业方向"],
    }
    common_evidence = {
        "major_foundation": ["计算机科学专业、大二"], "verified_skills": ["Python 基础和数据结构入门课程证据"],
        "interest_match": ["明确对后端开发和数据分析感兴趣"], "experience_match": [],
        "constraint_match": ["每周可投入 10 小时"],
    }
    directions = analyze_directions({
        "java-backend": {"scores": {"major_foundation": 0.75, "verified_skills": 0.35, "interest_match": 0.85, "experience_match": 0.0, "constraint_match": 0.7}, "evidence": common_evidence},
        "data-analysis": {"scores": {"major_foundation": 0.7, "verified_skills": 0.55, "interest_match": 0.8, "experience_match": 0.0, "constraint_match": 0.75}, "evidence": common_evidence},
        "test-development": {"scores": {"major_foundation": 0.7, "verified_skills": 0.4, "interest_match": 0.5, "experience_match": 0.0, "constraint_match": 0.8}, "evidence": common_evidence},
    }, direction_ids=["java-backend", "data-analysis", "test-development"], limit=3)
    confirmation_result = update_confirmation({}, {"primary_direction": "java-backend", "backup_direction": "data-analysis", "target_city": "杭州", "target_region": "浙江", "job_search_period": "2028 年春招"})
    confirmation = confirmation_result["data"]
    raw_snapshot = json.loads((ROOT / "reference" / "recruitment_snapshots" / "cities" / "hangzhou" / "java-backend-demo-v0.1.json").read_text(encoding="utf-8"))
    recruitment = process_snapshot(raw_snapshot)
    snapshot = recruitment["data"]["snapshot"]
    verified = {item["name"]: {"level": item["level"], "evidence": [item["evidence"]]} for item in profile["verified_skills"]}
    gaps = build_gaps(recruitment["data"]["skill_statistics"], verified, deadline_urgency=0.55)
    plan = generate_plan(confirmation, gaps["data"]["gaps"], weekly_hours=10, snapshot_version=snapshot["snapshot_version"], synthetic=True)
    archive = build_archive({
        "updated_at": "2026-08-06T00:00:00+08:00", "explicit_profile": profile,
        "career_directions": directions["data"]["directions"], "confirmed_goal": confirmation,
        "capability_evidence": profile["verified_skills"],
        "recruitment_snapshot": {key: snapshot[key] for key in ("snapshot_version", "city", "career_direction", "collected_at", "sample_count", "valid_sample_count", "confidence_level", "synthetic", "usage_notice")},
        "skill_graph": gaps["data"]["gaps"], "current_plan": plan["data"].get("plan", {}),
        "important_events": [{"date": "2026-08-06", "event": "用户确认 Java 后端为主方向、杭州为目的地"}],
        "achievements": [],
        "memory_change_summary": {"added": ["confirmed_goal", "destination", "job_search_period"], "updated": ["direction_status"], "deleted": [], "needs_confirmation": []},
        "pending_confirmations": [],
    })
    data = {
        "demo_user": profile, "direction_stage": directions["data"], "confirmation": confirmation,
        "recruitment_analysis": recruitment["data"], "competency_gaps": gaps["data"],
        "formal_plan": plan["data"], "growth_archive": archive.to_dict(),
        "memory_change_summary": archive.memory_change_summary,
        "synthetic_data_notice": "仅用于功能测试，不代表真实招聘市场；不足以得出杭州本地市场结论。",
        "completed_steps": 16,
    }
    warnings = [*recruitment["warnings"], *plan["warnings"]]
    return result(MODULE, data, warnings=warnings)


if __name__ == "__main__":
    write_json(run_demo())
