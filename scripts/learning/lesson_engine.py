"""Employment-context micro lesson builder."""
from __future__ import annotations

from typing import Any


class LessonEngine:
    def build(self, *, skill: str, objective: str, difficulty: str, job_context: str = "") -> dict[str, Any]:
        return {"lesson_id": f"lesson:{skill}:{difficulty}", "skill": skill, "objective": objective, "difficulty": difficulty, "job_context": job_context, "explanation": f"先理解 {skill} 在 {job_context or '目标岗位'}中的真实使用场景，再完成一个可检查的小步骤。", "example": f"示例：把 {skill} 用在一个最小岗位任务中，记录输入、操作、输出和故障处理。", "maximum_minutes": 30}
