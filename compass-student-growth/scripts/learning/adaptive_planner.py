"""Market-evidence gated stage/month/week planning."""
from __future__ import annotations

import uuid
from typing import Any, Mapping


class AdaptivePlanner:
    def __init__(self, *, maximum_weekly_tasks: int = 3, capacity_ratio: float = 0.85) -> None:
        self.maximum_weekly_tasks, self.capacity_ratio = maximum_weekly_tasks, capacity_ratio

    def build(self, *, goal: Mapping[str, Any], market: Mapping[str, Any], gaps: list[Mapping[str, Any]], weekly_hours: float) -> dict[str, Any]:
        confirmed = bool(goal.get("target_city") and (goal.get("target_job_normalized") or goal.get("target_job_raw")) and (goal.get("job_search_time") or goal.get("job_search_period") or goal.get("graduation_time")))
        formal = confirmed and market.get("market_data_status") == "sufficient" and not market.get("synthetic", False)
        mode = "formal" if formal else "preliminary"; capacity = max(0.0, float(weekly_hours)) * self.capacity_ratio
        tasks: list[dict[str, Any]] = []
        remaining = capacity
        for index, gap in enumerate(sorted(gaps, key=lambda item: -float(item.get("priority_score", 0.0)))[: self.maximum_weekly_tasks], 1):
            if remaining <= 0: break
            skill = str(gap.get("skill") or gap.get("competency_name") or f"能力 {index}"); hours = min(3.0, remaining); remaining -= hours
            city, job = goal.get("target_city", "目标城市"), goal.get("target_job_normalized") or goal.get("target_job_raw") or "目标岗位"
            evidence = list(gap.get("job_evidence", []))
            why = (f"因为你的目标是{city} {job}，本次可追溯招聘样本显示 {skill} 的需求频率为 {float(gap.get('market_frequency', 0)):.0%}，而你的已验证能力为 {float(gap.get('verified_level', 0)):.0%}，当前 Gap 为 {float(gap.get('gap_level', 0)):.0%}。" if formal else f"当前先补 {skill} 的最小基础；该任务尚未经过目标城市充足公开招聘样本校准。")
            tasks.append({"task_id": f"task-{index}-{uuid.uuid4().hex[:8]}", "skill": skill, "title": f"完成 {skill} 最小岗位场景实验", "why": why, "market_evidence": evidence, "gap_reference": gap.get("gap_id", f"Gap:{skill}"), "learning_objective": f"能在目标岗位场景中独立完成一项 {skill} 操作并验证结果", "estimated_hours": round(hours, 2), "specific_action": ["学习一个微课", "完成场景练习", "提交可检查产出"], "output": f"{skill} 实验产出与验证记录", "acceptance_criteria": ["产出可打开或可运行", "说明关键操作", "记录验证结果与一个故障排查"], "evidence_requirements": ["assessment passed", "实验产出"], "resources": [], "fallback": "缩小为 30 分钟最小步骤并记录卡点", "status": "pending"})
        notice = "已使用本次可追溯招聘样本校准。" if formal else "当前路线尚未经过目标城市充足公开招聘数据校准，属于 Preliminary Plan。" + (" Synthetic fixture 仅用于功能测试，不代表真实招聘市场。" if market.get("synthetic") else "")
        return {"plan_id": str(uuid.uuid4()), "mode": mode, "formal_plan_generated": formal, "notice": notice, "basis": {"goal": dict(goal), "snapshot_id": market.get("snapshot_id", ""), "market_data_status": market.get("market_data_status", "insufficient")}, "stage_plan": [{"stage": "当前", "goal": "优先缩小最高价值能力差距"}], "monthly_plan": [{"month": "当前月", "goal": "形成至少一项可验证岗位能力证据"}], "weekly_core_tasks": tasks, "total_weekly_hours": round(sum(item["estimated_hours"] for item in tasks), 2), "capacity_limit": round(capacity, 2), "status": "active"}

    def replan(self, *, previous: Mapping[str, Any], goal: Mapping[str, Any], market: Mapping[str, Any], gaps: list[Mapping[str, Any]], weekly_hours: float, reason: str) -> dict[str, Any]:
        plan = self.build(goal=goal, market=market, gaps=gaps, weekly_hours=weekly_hours); plan["supersedes"] = previous.get("plan_id", ""); plan["replan_reason"] = reason; return plan
