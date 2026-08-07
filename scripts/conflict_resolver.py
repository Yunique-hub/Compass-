"""检测目标、偏好和证据冲突，显式返回待确认操作。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

try:
    from .io_utils import result, run_cli
except ImportError:
    from io_utils import result, run_cli

MODULE = "conflict_resolver"
TARGET_FIELDS = {"primary_direction", "target_city", "target_region", "job_search_period", "graduation_date"}
CONFLICT_FIELDS = TARGET_FIELDS | {"learning_preferences", "verified_skills"}


def resolve_conflicts(existing: Mapping[str, Any], incoming: Mapping[str, Any], *, user_explicit: bool = False) -> dict[str, Any]:
    merged = dict(existing)
    conflicts: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = list(existing.get("history", []))
    for field, new_value in incoming.items():
        old_value = existing.get(field)
        if field == "learning_preferences" and isinstance(old_value, list) and isinstance(new_value, list):
            merged[field] = list(dict.fromkeys([*old_value, *new_value]))
            continue
        if field in CONFLICT_FIELDS and old_value not in (None, "", [], {}) and new_value != old_value:
            requires_confirmation = field in TARGET_FIELDS
            conflicts.append({"field": field, "existing": old_value, "incoming": new_value, "requires_confirmation": requires_confirmation, "recommended": "incoming" if user_explicit else "confirm"})
            history.append({"field": field, "old": old_value, "proposed": new_value, "time": datetime.now(timezone.utc).isoformat(), "source": "user_explicit" if user_explicit else "unconfirmed"})
            if user_explicit and not requires_confirmation:
                merged[field] = new_value
            continue
        merged[field] = new_value
    merged["history"] = history
    return result(MODULE, {"merged": merged, "conflicts": conflicts, "needs_confirmation": [item for item in conflicts if item["requires_confirmation"] or not user_explicit], "invalidated": ["recruitment_snapshot", "competency_gap", "current_plan"] if any(item["field"] in TARGET_FIELDS for item in conflicts) else []})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return resolve_conflicts(raw.get("existing", {}), raw.get("incoming", {}), user_explicit=bool(raw.get("user_explicit", False)))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
