"""Compass growth-domain graph mapping."""
from __future__ import annotations

from typing import Any, Mapping


def growth_edges(user_id: str, *, goal: Mapping[str, Any] | None = None, market: Mapping[str, Any] | None = None, competencies: list[Mapping[str, Any]] | None = None, gaps: list[Mapping[str, Any]] | None = None, plan: Mapping[str, Any] | None = None, evidence: list[Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    goal, market, plan = dict(goal or {}), dict(market or {}), dict(plan or {})
    edges: list[dict[str, Any]] = []
    goal_id = f"CareerGoal:{user_id}"
    if goal:
        edges.append({"source": f"User:{user_id}", "relation": "TARGETS", "target": goal_id})
        if goal.get("target_city"):
            edges.append({"source": goal_id, "relation": "LOCATED_IN", "target": f"City:{goal['target_city']}"})
        job = goal.get("target_job_normalized") or goal.get("target_job_raw")
        if job:
            edges.append({"source": goal_id, "relation": "TARGET_JOB", "target": f"JobRole:{job}"})
    snapshot = str(market.get("snapshot_id") or market.get("snapshot_version") or "")
    if snapshot:
        market_id = f"MarketSnapshot:{snapshot}"
        job = market.get("target_job_normalized") or market.get("target_job")
        city = market.get("target_city")
        if job:
            edges.append({"source": market_id, "relation": "ABOUT", "target": f"JobRole:{job}"})
        if city:
            edges.append({"source": market_id, "relation": "LOCATED_IN", "target": f"City:{city}"})
        for stat in market.get("skill_statistics", []):
            skill = stat.get("skill")
            if skill:
                edges.append({"source": market_id, "relation": "REQUIRES", "target": f"Skill:{skill}", "properties": {"frequency": stat.get("frequency")}})
    for competency in competencies or []:
        skill = competency.get("skill")
        cid = f"Competency:{user_id}:{skill}"
        edges.extend([{"source": f"User:{user_id}", "relation": "HAS_COMPETENCY", "target": cid}, {"source": cid, "relation": "ABOUT", "target": f"Skill:{skill}"}])
    for item in evidence or []:
        skill, eid = item.get("skill"), item.get("evidence_id")
        if skill and eid:
            edges.append({"source": f"Competency:{user_id}:{skill}", "relation": "SUPPORTED_BY", "target": f"Evidence:{eid}"})
    for gap in gaps or []:
        skill = gap.get("skill") or gap.get("competency_name")
        if skill:
            edges.append({"source": f"Gap:{user_id}:{skill}", "relation": "FOR_SKILL", "target": f"Skill:{skill}"})
    plan_id = str(plan.get("plan_id") or "")
    for task in plan.get("weekly_core_tasks", []):
        task_id, skill = task.get("task_id"), task.get("skill") or task.get("title", "")
        if plan_id and task.get("gap_reference"):
            edges.append({"source": f"Plan:{plan_id}", "relation": "ADDRESSES", "target": str(task["gap_reference"])})
        if task_id and skill:
            edges.append({"source": f"Task:{task_id}", "relation": "BUILDS", "target": f"Skill:{skill}"})
    return edges


def persist_growth_graph(memory_engine: Any, user_id: str, **components: Any) -> list[dict[str, Any]]:
    return [memory_engine.add_graph_edge(user_id=user_id, **edge) for edge in growth_edges(user_id, **components)]
