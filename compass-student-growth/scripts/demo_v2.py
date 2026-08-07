"""Run nine deterministic Compass v2 scenarios and write an evidence report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.archive_v2 import migrate_archive
from scripts.compass_engine import CompassEngine
from scripts.evolution.evolution_engine import EvolutionEngine
from scripts.research.browser_policy import validate_public_url

ROOT = Path(__file__).resolve().parents[1]


def memory_candidate(user_id: str) -> dict[str, Any]:
    return {
        "candidate_id": "demo-goal-1",
        "record_id": "demo-goal-1",
        "user_id": user_id,
        "memory_type": "confirmed_goal",
        "content": {"primary_direction": "Python 后端", "target_city": "杭州"},
        "importance": 1, "stability": 1, "future_relevance": 1,
        "user_explicitness": 1, "recurrence": 1, "confidence": 1,
        "task_value": 1, "user_intent": "remember",
    }


def run_all(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = output_dir / "runtime"
    engine = CompassEngine(runtime)
    material = output_dir / "操作系统历年真题.txt"
    material.write_text("进程与线程\n死锁的四个必要条件\n虚拟内存页面置换\n", encoding="utf-8")
    cases: list[dict[str, Any]] = []

    def add(case_id: str, title: str, payload: dict[str, Any]) -> None:
        cases.append({"case_id": case_id, "title": title, "result": payload})

    add("01", "职业方向自动评分", engine.run({"user_id": "demo-career", "message": "计算机大二，学过 Python 和数据库，不知道毕业适合什么工作"}))
    add("02", "考试资料与题目答案分离", engine.run({"user_id": "demo-exam", "message": "帮我根据真题复习考试并出题", "course": "操作系统", "attachments": [{"name": material.name, "path": str(material)}], "exam_days": 4}))
    add("03", "统一每周容量", engine.run({"user_id": "demo-plan", "message": "给我本周计划", "weekly_hours": 10, "exam_days": 4}))
    add("04", "明确同意的记忆写入", engine.run({"user_id": "demo-memory", "message": "请记住我的目标", "memory_candidate": memory_candidate("demo-memory")}))
    add("05", "跨会话隔离召回", engine.run({"user_id": "demo-memory", "message": "你记住了什么，继续上次进度"}))
    engine.run({"user_id": "demo-feedback", "message": "计划不现实，任务太多", "task_id": "t1", "signal": "任务太大"})
    engine.run({"user_id": "demo-feedback", "message": "计划不现实，任务太多", "task_id": "t2", "signal": "任务太大"})
    add("06", "重复反馈形成策略候选", engine.run({"user_id": "demo-feedback", "message": "计划不现实，任务太多", "task_id": "t3", "signal": "任务太大"}))
    add("07", "仅当前交互的主动提醒", engine.run({"user_id": "demo-proactive", "message": "给我本周计划", "weekly_hours": 8, "exam_days": 3, "missed_tasks": 2}))
    add("08", "高风险安全优先路由", engine.run({"user_id": "demo-safety", "message": "我不想活了"}))
    migrated = migrate_archive({"archive_version": "1.0.0", "explicit_profile": {"major": "软件工程"}, "custom": {"keep": True}}, user_id="demo-migrate")
    add("09", "Archive v1 到 v2 与策略边界", {"ok": True, "data": {"archive": migrated, "public_url": validate_public_url("https://example.com", {"example.com"}), "evolution_mode": "runtime-only", "source_rewrite": False}})

    report = {"version": "2.0.0", "scenario_count": len(cases), "all_ok": all(case["result"].get("ok") for case in cases), "cases": cases}
    (output_dir / "demo-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "runtime" / "demo-output-v2")
    args = parser.parse_args()
    value = run_all(args.output)
    print(json.dumps({"version": value["version"], "scenario_count": value["scenario_count"], "all_ok": value["all_ok"], "output": str(args.output)}, ensure_ascii=False))
    raise SystemExit(0 if value["all_ok"] and value["scenario_count"] == 9 else 2)
