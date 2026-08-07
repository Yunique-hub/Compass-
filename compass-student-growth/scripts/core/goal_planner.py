"""Build long-term, stage and immediate goals with executable weekly tasks."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping

from .known_facts import fact_value

ROOT = Path(__file__).resolve().parents[2]


def _direction_text(facts: Mapping[str, Any]) -> str:
    value = fact_value(facts, "career_direction", "当前探索方向")
    return " / ".join(value) if isinstance(value, list) else str(value)


def _template_key(facts: Mapping[str, Any]) -> str:
    direction = _direction_text(facts).casefold()
    coding = bool(fact_value(facts, "coding_interest")) or "python" in " ".join(fact_value(facts, "skills", [])).casefold()
    if "it支持" in direction or "技术支持" in direction:
        return "it_support_automation" if coding else "network_operations"
    if "网络运维" in direction:
        return "network_operations"
    return "generic_growth"


def build_goal_plan(facts: Mapping[str, Any], stage: Mapping[str, Any], capacity: Mapping[str, Any], *, planning_mode: str = "PRELIMINARY_PLAN") -> dict[str, Any]:
    templates = json.loads((ROOT / "reference" / "interaction" / "task_templates.json").read_text(encoding="utf-8"))
    direction = _direction_text(facts)
    coding = bool(fact_value(facts, "coding_interest")) or "Python" in fact_value(facts, "skills", [])
    automation = "，并形成至少 2 个可展示的自动化项目" if coding else "，并形成至少 2 份可展示的实践证据"
    horizon = "未来 12 个月" if fact_value(facts, "deadline_time") == "明年" else "未来 6—12 个月"
    primary_goal = f"{horizon}达到{direction}相关实习/就业岗位的基础胜任要求{automation}"
    stage_goals = [
        {"period": "0—3 个月", "goal": "补齐基础并完成第一个可验收作品", "evidence": "实验清单、故障记录或最小项目"},
        {"period": "4—6 个月", "goal": "形成项目能力并稳定输出过程记录", "evidence": "至少一个完整项目和复盘"},
        {"period": "7—9 个月", "goal": "用目标岗位 JD 校准技能和项目表达", "evidence": "JD 对齐表和改进后的项目"},
        {"period": "10—12 个月", "goal": "完成简历、面试练习和分批投递准备", "evidence": "简历、项目说明和面试记录"},
    ]
    tasks = templates[_template_key(facts)][:3]
    available = float(capacity.get("planned_weekly_hours", 0) or 0)
    total = sum(float(task["estimated_time"]) for task in tasks)
    if available and total > available:
        selected: list[dict[str, Any]] = []
        used = 0.0
        for task in tasks:
            hours = float(task["estimated_time"])
            if selected and used + hours > available:
                continue
            selected.append(task)
            used += hours
        tasks = selected or [tasks[0]]
    return {
        "plan_type": planning_mode,
        "primary_goal": primary_goal,
        "goal_horizon": horizon,
        "stage_goals": stage_goals,
        "current_stage_goal": stage_goals[0]["goal"],
        "week_goal": "完成第一批可运行、可解释、可复盘的能力证据",
        "weekly_core_tasks": tasks[:3],
        "optional_tasks": [],
        "why": "先把已有基础转成岗位和项目证据，再根据真实完成率逐步增加负荷",
        "success_evidence": [item for task in tasks for item in task["output"]],
        "review_date": (date.today() + timedelta(days=7)).isoformat(),
    }
