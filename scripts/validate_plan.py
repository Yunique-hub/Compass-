#!/usr/bin/env python3
"""Validate Compass weekly plan ledgers using only the Python standard library."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def load_input(argument: str | None) -> dict[str, Any]:
    raw = Path(argument).read_text(encoding="utf-8") if argument and argument != "-" else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def number(value: Any, field: str, errors: list[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        errors.append(f"{field} must be a finite number")
        return 0.0
    result = float(value)
    if result < 0:
        errors.append(f"{field} must be non-negative")
        return 0.0
    return result


def half_floor(value: float) -> float:
    return math.floor(value * 2 + 1e-9) / 2


def validate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    weekly = number(data.get("weekly_hours"), "weekly_hours", errors)
    buffer_hours = number(data.get("buffer_hours", 0), "buffer_hours", errors)
    tasks = data.get("tasks", [])
    optional = data.get("optional_tasks", [])
    if not isinstance(tasks, list):
        errors.append("tasks must be a list")
        tasks = []
    if not isinstance(optional, list):
        errors.append("optional_tasks must be a list")
        optional = []

    seen: set[str] = set()
    task_hours = 0.0
    optional_hours = 0.0
    core_count = 0
    for group_name, items in (("tasks", tasks), ("optional_tasks", optional)):
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{group_name}[{index}] must be an object")
                continue
            task_id = str(item.get("id", "")).strip()
            if not task_id:
                errors.append(f"{group_name}[{index}].id is required")
            elif task_id in seen:
                errors.append(f"duplicate task id: {task_id}")
            else:
                seen.add(task_id)
            hours = number(item.get("hours"), f"{group_name}[{index}].hours", errors)
            if group_name == "optional_tasks":
                optional_hours += hours
                if hours != 0:
                    errors.append(f"optional task {task_id or index} must have 0 allocated hours")
            else:
                task_hours += hours
                if item.get("kind", "core") == "core":
                    core_count += 1

    if core_count < 1 or core_count > 3:
        errors.append("core task count must be between 1 and 3")
    total = task_hours + optional_hours + buffer_hours
    if total > weekly + 1e-9:
        errors.append(f"allocated total {total:g} exceeds weekly capacity {weekly:g}")

    stress = data.get("stress") if isinstance(data.get("stress"), dict) else {}
    consecutive = stress.get("consecutive_incomplete_weeks", 0)
    fatigue = stress.get("fatigue", False) is True
    stressed = fatigue or (isinstance(consecutive, int) and not isinstance(consecutive, bool) and consecutive >= 2)
    recommendation = None
    if stressed and weekly > 0:
        recommendation = {
            "min_core_hours": round(weekly * 0.5, 2),
            "max_core_hours": half_floor(weekly * 0.7),
            "max_core_tasks": 1,
            "reason": "fatigue_or_repeated_incompletion",
        }

    return {
        "valid": not errors,
        "errors": errors,
        "summary": {
            "weekly_hours": weekly,
            "task_hours": round(task_hours, 4),
            "buffer_hours": round(buffer_hours, 4),
            "optional_hours": round(optional_hours, 4),
            "allocated_total": round(total, 4),
            "remaining_hours": round(weekly - total, 4),
            "core_task_count": core_count,
        },
        "stress_recommendation": recommendation,
    }


def main() -> int:
    try:
        result = validate(load_input(sys.argv[1] if len(sys.argv) > 1 else None))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
