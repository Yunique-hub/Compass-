"""Build long-term, stage and immediate goals with executable weekly tasks."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping

from .growth_context import GrowthContext
from .known_facts import fact_value
from scripts.learning.domain_task_factory import PATHWAY_LABELS, build_domain_tasks

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


def _task(title: str, why: str, evidence_type: str, hours: float) -> dict[str, Any]:
    return {
        "title": title,
        "why": why,
        "estimated_time": hours,
        "specific_action": [f"明确{title}的完成边界", "完成一个最小版本", "按标准自检并记录卡点"],
        "output": [f"{title}成果"],
        "acceptance_criteria": ["成果可查看且包含过程说明", "能说明依据、结论与下一步改进"],
        "evidence": f"{title}成果",
        "evidence_type": evidence_type,
        "fallback": "时间不足时只完成最小版本和一条复盘",
    }


def _fit_capacity(tasks: list[dict[str, Any]], capacity: Mapping[str, Any]) -> list[dict[str, Any]]:
    available = float(capacity.get("planned_weekly_hours", 0) or 0)
    if not available or sum(float(task["estimated_time"]) for task in tasks) <= available:
        return tasks[:3]
    selected: list[dict[str, Any]] = []
    used = 0.0
    for task in tasks:
        hours = float(task["estimated_time"])
        if selected and used + hours > available:
            continue
        selected.append(task)
        used += hours
    return selected or [tasks[0]]


def _domain_plan(context: GrowthContext, stage: Mapping[str, Any], capacity: Mapping[str, Any], planning_mode: str) -> dict[str, Any]:
    competencies = context.competencies
    academic = context.academic_profile
    stage_code = str(stage.get("stage", ""))
    early = academic.academic_year == "大一" or "EXPLORATION" in stage_code
    core_start = min(3, max(0, len(competencies) - 1))
    chosen = list(dict.fromkeys([competencies[0] if competencies else "专业基础", *competencies[core_start:core_start + 2]]))
    if context.target_role and not early:
        role_priority = {
            "投行": ["估值", "金融建模", "市场与行业研究"],
            "UI/UX": ["UI/UX", "用户研究", "作品集"],
            "机器人": ["机械基础", "控制", "机器人"],
            "数据分析": ["统计", "Excel/SQL", "数据可视化"],
            "律所": ["案例分析", "法律检索", "法律写作"],
            "后端": ["Python", "数据库", "Web/API"],
        }
        prioritized = next((items for key, items in role_priority.items() if key.casefold() in context.target_role.casefold()), [])
        role_specific = [item for item in prioritized if any(item in competency or competency in item for competency in competencies)]
        chosen = list(dict.fromkeys([*role_specific, *chosen]))[:3]
    evidence_types = context.evidence_types or ["assessment"]
    tasks = _fit_capacity(
        build_domain_tasks(
            academic.discipline_family,
            taxonomy_domain=academic.taxonomy_domain,
            normalized_major=academic.normalized_major,
            specialization=academic.specialization,
            target_role=context.target_role,
            maximum=3,
            foundation=early,
            goal_portfolio=context.goal_portfolio,
        ),
        capacity,
    )
    if early:
        priority = "先打牢专业基础并用低成本体验验证方向"
    elif context.target_pathway in {"internship", "employment"}:
        priority = "优先形成实习要求、实践证据和面试表达"
    elif context.target_pathway == "graduate_school":
        priority = "优先补研究方法、文献阅读和科研经历"
    elif context.target_pathway == "professional_qualification":
        priority = "优先建立资格考试知识体系、案例练习和真题反馈"
    elif context.target_pathway == "career_transition":
        priority = "保留可迁移能力，并用桥接任务补齐目标缺口"
    else:
        priority = "先完成专业基础与可验证成果的双轴闭环"
    target = context.target_role or context.primary_goal
    caveat = " 当前路线基于一般培养逻辑，具体院校、行业或资格要求需要验证。" if context.knowledge_source == "family_fallback" else ""
    primary_goal = f"未来 6—12 个月围绕{academic.raw_major or '当前学科背景'}与{target}，形成专业能力、路径里程碑和领域证据。{caveat}".strip()
    stage_goals = [
        {"period": "0—3 个月", "goal": priority, "evidence": tasks[0]["evidence"] if tasks else "阶段成果"},
        {"period": "4—6 个月", "goal": f"组合{PATHWAY_LABELS.get(context.target_pathway, '目标路径')}所需核心能力", "evidence": "能力组合与反馈记录"},
        {"period": "7—9 个月", "goal": "用真实要求校准差距", "evidence": "要求对照与修订成果"},
        {"period": "10—12 个月", "goal": "完成下一阶段申请、实践或发展准备", "evidence": "里程碑材料与复盘"},
    ]
    return {
        "plan_type": planning_mode,
        "primary_goal": primary_goal,
        "goal_horizon": "未来 6—12 个月",
        "stage_goals": stage_goals,
        "current_stage_goal": priority,
        "week_goal": f"完成{chosen[0] if chosen else '专业基础'}与一项{evidence_types[0]}证据",
        "weekly_core_tasks": tasks,
        "optional_tasks": [],
        "why": f"计划由学术背景、{stage.get('label', stage_code)}、目标路径、现实容量和证据缺口共同决定。{caveat}".strip(),
        "success_evidence": [item for task in tasks for item in task["output"]],
        "review_date": (date.today() + timedelta(days=7)).isoformat(),
        "academic_axis": competencies[:3],
        "outcome_axis": {"pathway": context.target_pathway, "pathway_label": PATHWAY_LABELS.get(context.target_pathway, "目标路径"), "role": context.target_role, "evidence_types": evidence_types},
    }


def build_goal_plan(facts: Mapping[str, Any], stage: Mapping[str, Any], capacity: Mapping[str, Any], *, planning_mode: str = "PRELIMINARY_PLAN", growth_context: GrowthContext | None = None) -> dict[str, Any]:
    if growth_context is not None:
        return _domain_plan(growth_context, stage, capacity, planning_mode)
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
    tasks = _fit_capacity(tasks, capacity)
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
