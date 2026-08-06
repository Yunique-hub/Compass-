"""用户确认门与目标变更历史。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

try:
    from .io_utils import error, result, run_cli
    from .models import DirectionConfirmation, DirectionStatus
except ImportError:
    from io_utils import error, result, run_cli
    from models import DirectionConfirmation, DirectionStatus

MODULE = "direction_confirmation"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_status(value: DirectionConfirmation) -> DirectionStatus:
    if value.primary_direction and value.target_city and (value.job_search_period or value.graduation_date):
        return DirectionStatus.CONFIRMED
    if value.primary_direction:
        return DirectionStatus.PARTIALLY_CONFIRMED
    return DirectionStatus.UNCONFIRMED


def update_confirmation(current: Mapping[str, Any] | None, updates: Mapping[str, Any]) -> dict[str, Any]:
    value = DirectionConfirmation.from_dict(current or {})
    changed: list[str] = []
    invalidated: list[str] = []
    target_fields = {"primary_direction", "target_city", "target_region", "job_search_period", "graduation_date"}
    for key, new_value in updates.items():
        if key not in DirectionConfirmation.__dataclass_fields__ or key in {"status", "history"}:
            continue
        old_value = getattr(value, key)
        if old_value and new_value != old_value:
            changed.append(key)
            if key in target_fields:
                invalidated.extend(["recruitment_snapshot", "competency_gap", "current_plan"])
            value.history.append({"field": key, "old": old_value, "new": new_value, "changed_at": now_iso(), "requires_confirmation": key in target_fields})
        setattr(value, key, new_value)
    value.confirmed_at = now_iso()
    computed = derive_status(value)
    value.status = DirectionStatus.CHANGED if changed else computed
    missing = []
    if not value.primary_direction:
        missing.append("primary_direction")
    if value.primary_direction and not value.target_city:
        missing.append("target_city")
    if value.primary_direction and not (value.job_search_period or value.graduation_date):
        missing.append("job_search_period")
    warnings = []
    if changed:
        warnings.append(error("GOAL_CHANGED", "目标发生变化，旧招聘数据、差距和正式计划必须失效并重新确认。", fields=changed))
    data = value.to_dict()
    data.update({"computed_status": computed.value, "missing_for_formal_plan": missing[:3], "invalidated": sorted(set(invalidated))})
    return result(MODULE, data, warnings=warnings)


def formal_plan_gate(confirmation: Mapping[str, Any]) -> dict[str, Any]:
    value = DirectionConfirmation.from_dict(confirmation)
    missing = []
    if not value.primary_direction:
        missing.append("primary_direction")
    if not value.target_city:
        missing.append("target_city")
    if not (value.job_search_period or value.graduation_date):
        missing.append("job_search_period")
    if missing or derive_status(value) != DirectionStatus.CONFIRMED:
        code = "DIRECTION_NOT_CONFIRMED" if "primary_direction" in missing else "DESTINATION_OR_DEADLINE_MISSING"
        return result(MODULE, ok=False, errors=[error(code, "主方向、就业目的地和求职时间均确认后才能生成正式计划。", missing=missing)], fallback={"action": "request_missing_confirmation", "fields": missing[:3]})
    return result(MODULE, {"allowed": True, "confirmation": value.to_dict()})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return update_confirmation(raw.get("current"), raw.get("updates", raw))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
