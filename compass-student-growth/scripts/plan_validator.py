"""学习计划二次校验和一次保守自动修复。"""
from __future__ import annotations

from typing import Any, Mapping

try:
    from .io_utils import result, run_cli
except ImportError:
    from io_utils import result, run_cli

MODULE = "plan_validator"
TASK_FIELDS = {"task_id", "title", "estimated_hours", "output", "acceptance_criteria", "dependencies", "resources", "fallback"}


def _issues(plan: Mapping[str, Any], confirmation: Mapping[str, Any], *, synthetic: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    formal = plan.get("mode") == "formal"
    if formal:
        missing = []
        if not confirmation.get("primary_direction"):
            missing.append("primary_direction")
        if not confirmation.get("target_city"):
            missing.append("target_city")
        if not (confirmation.get("job_search_period") or confirmation.get("graduation_date")):
            missing.append("job_search_period")
        if missing:
            errors.append({"code": "CONFIRMATION_GATE_FAILED", "message": "正式计划缺少确认字段。", "fields": missing})
        if not plan.get("snapshot_version"):
            errors.append({"code": "SNAPSHOT_VERSION_MISSING", "message": "正式计划缺少招聘数据快照版本。"})
        if not plan.get("basis"):
            errors.append({"code": "PLAN_BASIS_MISSING", "message": "正式计划缺少规划依据。"})
    tasks = list(plan.get("weekly_core_tasks", []))
    if len(tasks) > 3:
        errors.append({"code": "TOO_MANY_CORE_TASKS", "message": "每周最多 3 个核心任务。"})
    for index, task in enumerate(tasks):
        missing_fields = [field for field in TASK_FIELDS if task.get(field) in (None, "", [])]
        if missing_fields:
            errors.append({"code": "TASK_FIELDS_MISSING", "message": f"任务 {index + 1} 字段不完整。", "fields": missing_fields})
    total = sum(float(task.get("estimated_hours", 0)) for task in tasks)
    capacity = float(plan.get("capacity_limit", 0))
    if total > capacity + 1e-9:
        errors.append({"code": "TIME_BUDGET_EXCEEDED", "message": "核心任务总时长超过预算。", "total": total, "capacity": capacity})
    text = str(plan)
    if synthetic and any(phrase in text for phrase in ("当前杭州真实市场", "当前企业普遍要求", "真实平均薪资", "最新岗位趋势")):
        errors.append({"code": "SYNTHETIC_MARKET_CLAIM", "message": "合成数据被错误描述为真实市场。"})
    if synthetic and "仅用于功能测试，不代表真实招聘市场" not in text:
        warnings.append({"code": "SYNTHETIC_NOTICE_MISSING", "message": "建议在正式输出中醒目标注合成数据用途。"})
    return errors, warnings


def validate_plan(plan: Mapping[str, Any], confirmation: Mapping[str, Any], *, synthetic: bool = False, auto_fix: bool = True) -> dict[str, Any]:
    fixed = {**plan, "weekly_core_tasks": [dict(item) for item in plan.get("weekly_core_tasks", [])], "optional_tasks": [dict(item) for item in plan.get("optional_tasks", [])]}
    initial_errors, warnings = _issues(fixed, confirmation, synthetic=synthetic)
    fixes: list[dict[str, Any]] = []
    if auto_fix:
        tasks = sorted(fixed["weekly_core_tasks"], key=lambda item: (-float(item.get("priority", 0)), item.get("task_id", "")))
        if len(tasks) > 3:
            moved = tasks[3:]
            fixed["optional_tasks"].extend(moved)
            tasks = tasks[:3]
            fixes.append({"action": "move_to_optional", "task_ids": [item.get("task_id") for item in moved]})
        capacity = float(fixed.get("capacity_limit", 0))
        while tasks and sum(float(item.get("estimated_hours", 0)) for item in tasks) > capacity + 1e-9:
            removed = tasks.pop()
            fixed["optional_tasks"].append(removed)
            fixes.append({"action": "remove_low_priority_from_core", "task_id": removed.get("task_id")})
        fixed["weekly_core_tasks"] = tasks
        fixed["total_weekly_hours"] = sum(float(item.get("estimated_hours", 0)) for item in tasks)
    remaining, final_warnings = _issues(fixed, confirmation, synthetic=synthetic)
    return result(MODULE, {"valid": not remaining, "errors": initial_errors, "warnings": warnings + final_warnings, "auto_fix": fixes, "remaining_issues": remaining, "plan": fixed}, ok=not remaining, warnings=warnings + final_warnings, errors=remaining)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return validate_plan(raw.get("plan", {}), raw.get("confirmation", {}), synthetic=bool(raw.get("synthetic", False)), auto_fix=bool(raw.get("auto_fix", True)))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
