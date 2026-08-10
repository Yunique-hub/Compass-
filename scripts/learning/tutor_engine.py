"""Stateful Tutor loop entry; starting learning never regenerates a plan."""
from __future__ import annotations

from typing import Any, Mapping

from .exercise_engine import ExerciseEngine
from .lesson_engine import LessonEngine


class TutorEngine:
    def __init__(self) -> None: self.lessons, self.exercises = LessonEngine(), ExerciseEngine()
    @staticmethod
    def difficulty(verified_level: float, assessments: list[Mapping[str, Any]] | None = None) -> str:
        recent = [float(item.get("score", 0.0)) for item in (assessments or [])[-3:]]; effective = max(float(verified_level), sum(recent) / len(recent) if recent else 0.0)
        return "advanced" if effective >= 0.75 else ("intermediate" if effective >= 0.3 else "beginner")
    def start(self, task: Mapping[str, Any], *, verified_level: float = 0.0, assessments: list[Mapping[str, Any]] | None = None, job_context: str = "", domain_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        skill = str(task.get("skill") or task.get("title") or "当前能力"); level = self.difficulty(verified_level, assessments)
        domain_context = domain_context or {}
        competency = dict(task.get("competency_definition") or {})
        lesson = self.lessons.build(skill=skill, objective=str(task.get("learning_objective") or task.get("title") or skill), difficulty=level, job_context=job_context, domain_context=domain_context, competency=competency)
        exercise = self.exercises.build(skill=skill, difficulty=level, acceptance_criteria=list(task.get("acceptance_criteria", [])), evidence_type=str(task.get("evidence_type", "")), domain_context=domain_context, competency=competency)
        if competency:
            prerequisites = list(competency.get("prerequisites") or [])
            outcomes = list(competency.get("learning_outcomes") or [])
            mistakes = list(competency.get("common_mistakes") or [])
            criteria = list(competency.get("assessment_criteria") or task.get("acceptance_criteria") or [])
            questions = [
                f"在{'、'.join(str(item) for item in prerequisites[:2]) or '必要基础'}中，你能独立解释哪一部分？",
                f"完成{'、'.join(str(item) for item in outcomes[:2]) or skill}时，目前最先卡在哪一步？",
            ]
            hints = [
                f"先回到一个前置点：{prerequisites[0] if prerequisites else '写清问题和已知条件'}。",
                f"按学习结果拆成步骤：{'；'.join(str(item) for item in outcomes[:3]) or '输入；过程；结果'}。",
                f"对照标准逐项补齐：{'；'.join(str(item) for item in criteria[:3]) or '产出；依据；验证'}；并检查常见错误：{mistakes[0] if mistakes else '结论缺少证据'}。",
            ]
        elif skill.casefold() == "dcf":
            questions = ["FCFF 与净利润有什么区别？", "WACC 为什么能用于企业自由现金流折现？"]
            hints = ["先只列出显性预测期需要的现金流。", "用 EBIT(1-T)+D&A-Capex-ΔNWC 检查 FCFF 口径。", "再把显性期、终值和敏感性表逐项核对。"]
        elif any(term in skill for term in ("法律", "案例")):
            questions = ["这个案例的核心争点是什么？", "你会从哪类权威来源开始检索？"]
            hints = ["先圈出决定法律关系的事实。", "按争点检索法条，并记录来源与版本。", "用 IRAC 写规则适用，同时加入一个反方论证。"]
        elif "内科学" in skill:
            questions = ["哪些信息属于危险征象？", "目前最需要排除的诊断是什么？"]
            hints = ["先列主诉、关键阳性与阴性信息。", "按常见、危险、可逆三组组织鉴别诊断。", "为每个检查写清它会改变哪项判断。"]
        else:
            questions = [f"你能用自己的话解释 {skill} 的目标吗？", "目前最先卡住的是概念、步骤还是验证？"]
            hints = ["先缩小到一个可检查的问题。", "回到示例，标出输入、过程和结果。", "对照验收标准逐项补齐，并记录仍不确定的地方。"]
        return {
            "action": "START_TUTOR", "status": "lesson_active", "skill": skill, "task_id": task.get("task_id", ""),
            "teaching_loop": ["DIAGNOSE", "TEACH", "DEMONSTRATE", "PRACTICE", "HINT", "ASSESS", "FEEDBACK", "UPDATE_MASTERY", "NEXT"],
            "diagnosis": {"questions": questions, "assumed_level": level, "status": "awaiting_observable_response"},
            "lesson": lesson, "demonstration": lesson.get("example", ""), "exercise": exercise,
            "hint_ladder": [{"level": index, "hint": hint, "release": "on_request_or_stall"} for index, hint in enumerate(hints, 1)],
            "feedback": {"status": "pending_submission", "basis": "acceptance_criteria"},
            "mastery": {"before": round(float(verified_level), 4), "after": None, "status": "not_updated_until_assessed"},
            "next_action": "SUBMIT_EXERCISE",
        }
    def resume(self, growth_state: Mapping[str, Any]) -> dict[str, Any]:
        lesson = dict(growth_state.get("current_lesson", {})); return {"action": "CONTINUE_TUTOR", "status": "lesson_active" if lesson else "no_active_lesson", "lesson": lesson, "completed_tasks": list(growth_state.get("completed_tasks", [])), "next_task": growth_state.get("next_task", {})}
