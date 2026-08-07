"""将结构化输入整理为显式画像；不把自称技能升级为已验证证据。"""
from __future__ import annotations

from typing import Any, Mapping

try:
    from .io_utils import error, result, run_cli
    from .models import ConversationState, UserProfile
except ImportError:
    from io_utils import error, result, run_cli
    from models import ConversationState, UserProfile

MODULE = "profile_parser"
PROFILE_FIELDS = {name for name in UserProfile.__dataclass_fields__ if name != "required_fields"}
EVIDENCE_TYPES = {"course", "repository", "project", "internship", "competition", "certificate", "task_output"}


def required_for_state(state: ConversationState | str) -> list[str]:
    state = ConversationState(state)
    return {
        ConversationState.PROFILE_INCOMPLETE: ["user_id", "major", "grade"],
        ConversationState.DIRECTION_ANALYSIS: ["major", "interests", "weekly_hours"],
        ConversationState.AWAITING_DESTINATION: ["target_deadline"],
    }.get(state, [])


def parse_profile(raw: Mapping[str, Any], state: ConversationState | str = ConversationState.PROFILE_INCOMPLETE) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError("用户画像必须是 JSON 对象")
    warnings: list[dict[str, Any]] = []
    unknown = sorted(set(raw) - PROFILE_FIELDS - {"claimed_skills", "state"})
    if unknown:
        warnings.append(error("UNKNOWN_FIELDS", "未知字段已忽略。", fields=unknown))
    data = {key: value for key, value in raw.items() if key in PROFILE_FIELDS}
    data.setdefault("user_id", "")
    data.setdefault("pending_confirmations", [])
    for skill in raw.get("claimed_skills", []):
        data["pending_confirmations"].append(f"技能自述待验证：{skill}")
    verified: list[dict[str, Any]] = []
    for item in data.get("verified_skills", []):
        if not isinstance(item, Mapping) or item.get("evidence_type") not in EVIDENCE_TYPES or not item.get("evidence"):
            warnings.append(error("UNVERIFIED_SKILL", "缺少可验证证据的技能未计入 verified_skills。", item=item))
            if isinstance(item, Mapping) and item.get("name"):
                data["pending_confirmations"].append(f"技能证据待补充：{item['name']}")
            continue
        verified.append(dict(item))
    data["verified_skills"] = verified
    profile = UserProfile.from_dict(data)
    missing = [field for field in required_for_state(state) if getattr(profile, field, None) in (None, "", [], 0)]
    payload = profile.to_dict()
    payload["missing_required_fields"] = missing[:3]
    payload["next_state"] = (ConversationState.PROFILE_INCOMPLETE if missing else ConversationState.DIRECTION_ANALYSIS).value
    return result(MODULE, payload, warnings=warnings)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return parse_profile(raw, raw.get("state", ConversationState.PROFILE_INCOMPLETE.value))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
