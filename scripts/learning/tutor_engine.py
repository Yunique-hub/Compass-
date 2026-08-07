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
    def start(self, task: Mapping[str, Any], *, verified_level: float = 0.0, assessments: list[Mapping[str, Any]] | None = None, job_context: str = "") -> dict[str, Any]:
        skill = str(task.get("skill") or task.get("title") or "当前能力"); level = self.difficulty(verified_level, assessments)
        lesson = self.lessons.build(skill=skill, objective=str(task.get("learning_objective") or task.get("title") or skill), difficulty=level, job_context=job_context)
        exercise = self.exercises.build(skill=skill, difficulty=level, acceptance_criteria=list(task.get("acceptance_criteria", [])))
        return {"action": "START_TUTOR", "status": "lesson_active", "skill": skill, "task_id": task.get("task_id", ""), "lesson": lesson, "exercise": exercise, "next_action": "SUBMIT_EXERCISE"}
    def resume(self, growth_state: Mapping[str, Any]) -> dict[str, Any]:
        lesson = dict(growth_state.get("current_lesson", {})); return {"action": "CONTINUE_TUTOR", "status": "lesson_active" if lesson else "no_active_lesson", "lesson": lesson, "completed_tasks": list(growth_state.get("completed_tasks", [])), "next_task": growth_state.get("next_task", {})}
