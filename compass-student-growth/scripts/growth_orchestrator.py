"""Compass 2.2 market-driven learning and evidence orchestration."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from scripts.competency.evidence_engine import EvidenceEngine
from scripts.competency.gap_engine import GapEngine
from scripts.learning.adaptive_planner import AdaptivePlanner
from scripts.learning.assessment_engine import AssessmentEngine
from scripts.learning.progress_tracker import update_progress
from scripts.learning.tutor_engine import TutorEngine
from scripts.memory.knowledge_graph import persist_growth_graph
from scripts.memory.memory_engine import MemoryEngine
from scripts.recruitment.recruitment_engine import RecruitmentEngine


class GrowthOrchestrator:
    def __init__(self, *, runtime_dir: str | Path) -> None:
        self.runtime = Path(runtime_dir)
        self.recruitment = RecruitmentEngine(extractor=__import__("scripts.recruitment.skill_extractor", fromlist=["SkillExtractor"]).SkillExtractor(self.runtime / "dynamic_skill_registry.json"))
        self.gaps, self.planner, self.tutor = GapEngine(), AdaptivePlanner(), TutorEngine()
        self.assessment, self.evidence = AssessmentEngine(), EvidenceEngine()

    @staticmethod
    def _skill_from_message(message: str) -> str:
        match = re.search(r"(?:开始|继续|现在)?(?:学习|学)\s*([A-Za-z0-9+#.\- ]+|[\u4e00-\u9fff]{2,20})", message, re.I)
        return match.group(1).strip("，。；;：: ") if match else ""

    def market_learning_cycle(self, *, user_id: str, request: Mapping[str, Any], archive: dict[str, Any], memory: MemoryEngine, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = {**dict(request), "context": context}
        market = self.recruitment.analyze(payload)
        goal = {"target_city": market.get("target_city", ""), "target_job_raw": market.get("target_job_raw", ""), "target_job_normalized": market.get("target_job_normalized", ""), "job_search_time": request.get("job_search_time", ""), "target_status": market.get("confirmation_state", "needs_confirmation")}
        competencies = dict(context.get("competency", {})); gaps = self.gaps.calculate(market.get("skill_statistics", []), competencies, deadline_urgency=float(request.get("deadline_urgency", 0.7)))
        weekly_hours = float(request.get("weekly_hours") or archive.get("profile", {}).get("weekly_hours") or context.get("profile", {}).get("weekly_available_hours") or 7.0)
        previous = archive.get("academic", {}).get("current_plan", {})
        plan = self.planner.replan(previous=previous, goal=goal, market=market, gaps=gaps, weekly_hours=weekly_hours, reason="market_or_competency_changed") if previous else self.planner.build(goal=goal, market=market, gaps=gaps, weekly_hours=weekly_hours)
        archive.setdefault("career", {})["confirmed_goal"] = goal
        archive["career"]["recruitment_snapshot"] = market
        archive["career"]["current_gaps"] = gaps
        archive.setdefault("academic", {})["current_plan"] = plan
        memory.persist_turn(user_id=user_id, goal_updates=goal, growth_updates={"current_plan": plan, "current_stage": archive.get("current_growth_stage", ""), "active_tasks": plan.get("weekly_core_tasks", [])})
        graph = persist_growth_graph(memory, user_id, goal=goal, market=market, competencies=list(competencies.values()), gaps=gaps, plan=plan)
        return {"target": goal, "market": market, "gaps": gaps, "plan": plan, "graph_updates": len(graph), "pipeline": ["Target", "Query", "Provider", "JD", "Skill", "Market", "Gap", "Plan"]}

    def start_tutor(self, *, message: str, request: Mapping[str, Any], archive: dict[str, Any], context: Mapping[str, Any], memory: MemoryEngine, user_id: str, resume: bool = False) -> dict[str, Any]:
        growth = dict(context.get("growth_state", {}))
        if resume and growth.get("current_lesson"):
            return self.tutor.resume(growth)
        plan = archive.get("academic", {}).get("current_plan", {}) or growth.get("current_plan", {})
        tasks = list(plan.get("weekly_core_tasks", [])); requested_skill = str(request.get("skill") or self._skill_from_message(message))
        task = next((item for item in tasks if requested_skill and requested_skill.casefold() in str(item.get("skill") or item.get("title", "")).casefold()), tasks[0] if tasks else None)
        if task is None:
            if not requested_skill:
                return {"action": "START_TUTOR", "status": "no_task", "message": "当前还没有可开始的学习任务；请先确认一个能力目标。"}
            task = {"task_id": f"ad-hoc:{requested_skill}", "skill": requested_skill, "title": f"学习 {requested_skill}", "learning_objective": f"完成 {requested_skill} 最小场景练习", "acceptance_criteria": ["产出可打开或可运行", "说明关键操作", "记录验证结果与一个故障排查"]}
        competency = context.get("competency", {}).get(str(task.get("skill", "")), {})
        target = archive.get("career", {}).get("confirmed_goal", {}); job_context = " ".join(str(target.get(key, "")) for key in ("target_city", "target_job_normalized")).strip()
        tutor = self.tutor.start(task, verified_level=float(competency.get("verified_level", 0.0)), job_context=job_context)
        archive.setdefault("extensions", {})["current_tutor"] = tutor
        memory.persist_turn(user_id=user_id, growth_updates={"current_plan": plan, "current_lesson": tutor["lesson"], "current_skill": tutor["skill"], "next_task": tutor["exercise"]})
        return tutor

    def assess(self, *, request: Mapping[str, Any], archive: dict[str, Any], context: Mapping[str, Any], memory: MemoryEngine, user_id: str) -> dict[str, Any]:
        tutor = archive.get("extensions", {}).get("current_tutor", {}); exercise = tutor.get("exercise", {}); skill = str(request.get("skill") or tutor.get("skill") or "")
        if not skill or not exercise:
            return {"action": "ASSESS_LEARNING", "status": "no_active_exercise", "passed": False}
        submission = dict(request.get("submission") or {}); assessment = self.assessment.evaluate(skill=skill, submission=submission, criteria=exercise.get("acceptance_criteria", []))
        evidence = self.evidence.create(skill=skill, evidence_type=str(request.get("evidence_type", "assessment")), source=str(request.get("source", "compass-assessment")), description=str(request.get("description", "系统内练习验收")), assessment=assessment)
        current = context.get("competency", {}).get(skill, {}); competency = self.evidence.update_competency(current, evidence)
        growth = update_progress(context.get("growth_state", {}), task_id=str(tutor.get("task_id", "current-task")), passed=assessment["passed"], actual_hours=float(request.get("actual_hours", 0.0)))
        output: dict[str, Any] = {"action": "ASSESS_LEARNING", "assessment": assessment, "evidence": evidence, "competency": competency, "growth_state": growth, "replanned": False}
        memory.persist_turn(user_id=user_id, competency_updates=[competency] if assessment["passed"] else [], growth_updates=growth)
        if assessment["passed"]:
            market = archive.get("career", {}).get("recruitment_snapshot", {}); competencies = {**context.get("competency", {}), skill: competency}; gaps = self.gaps.calculate(market.get("skill_statistics", []), competencies)
            goal = archive.get("career", {}).get("confirmed_goal", {}); previous = archive.get("academic", {}).get("current_plan", {}); plan = self.planner.replan(previous=previous, goal=goal, market=market, gaps=gaps, weekly_hours=float(previous.get("capacity_limit", 7.0)), reason="verified_competency_changed")
            archive["career"]["current_gaps"] = gaps; archive["academic"]["current_plan"] = plan; output.update({"gaps": gaps, "plan": plan, "replanned": True})
            memory.persist_turn(user_id=user_id, growth_updates={**growth, "current_plan": plan, "completed_tasks": growth.get("completed_tasks", [])})
            persist_growth_graph(memory, user_id, goal=goal, market=market, competencies=list(competencies.values()), gaps=gaps, plan=plan, evidence=[evidence])
        return output

    @staticmethod
    def compact_context(context: Mapping[str, Any]) -> dict[str, Any]:
        return {"profile": context.get("profile", {}), "goal": context.get("goal", {}), "competency": context.get("competency", {}), "growth_state": context.get("growth_state", {}), "semantic_memory": list(context.get("semantic_memory", []))[:5]}
