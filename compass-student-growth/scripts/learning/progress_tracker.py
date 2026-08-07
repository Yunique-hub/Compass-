"""Learning progress calculations used by memory and proactive signals."""
from __future__ import annotations

from typing import Any, Mapping


def update_progress(state: Mapping[str, Any], *, task_id: str, passed: bool, actual_hours: float = 0.0) -> dict[str, Any]:
    value = dict(state); completed = list(value.get("completed_tasks", [])); failed = list(value.get("failed_tasks", []))
    (completed if passed else failed).append(task_id); value["completed_tasks"] = list(dict.fromkeys(completed)); value["failed_tasks"] = list(dict.fromkeys(failed)); value["actual_hours"] = float(value.get("actual_hours", 0.0)) + max(0.0, actual_hours)
    attempts = len(value["completed_tasks"]) + len(value["failed_tasks"]); value["completion_rate"] = round(len(value["completed_tasks"]) / attempts, 4) if attempts else 0.0; return value
