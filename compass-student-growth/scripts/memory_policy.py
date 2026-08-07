"""用户意愿和敏感规则优先的长期记忆评分与分流。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:
    from .io_utils import error, result, run_cli
    from .models import MemoryAction, MemoryCandidate, clamp
except ImportError:
    from io_utils import error, result, run_cli
    from models import MemoryAction, MemoryCandidate, clamp

MODULE = "memory_policy"
ROOT = Path(__file__).resolve().parents[1]
STRUCTURED_TYPES = {"explicit_profile", "preferred_name", "confirmed_goal", "profile_fact", "weekly_hours", "destination", "deadline"}
VECTOR_TYPES = {"learning_preference", "event", "achievement", "recurring_difficulty"}


def calculate_memory_score(candidate: MemoryCandidate, weights: Mapping[str, float]) -> tuple[float, dict[str, float]]:
    breakdown = {key: clamp(float(getattr(candidate, key))) for key in weights}
    return clamp(sum(breakdown[key] * float(weight) for key, weight in weights.items())), breakdown


def route_memory(raw: Mapping[str, Any]) -> dict[str, Any]:
    candidate = MemoryCandidate.from_dict(raw)
    config = json.loads((ROOT / "config" / "memory_policy.json").read_text(encoding="utf-8"))
    score, breakdown = calculate_memory_score(candidate, config["memory_weights"])
    intent = candidate.user_intent.casefold()
    sensitivity = candidate.sensitivity.casefold()
    if intent in {"forget", "忘记", "delete"}:
        action, reason = MemoryAction.DELETE, "用户明确要求忘记，删除优先于所有评分。"
    elif intent in {"do_not_remember", "不要记住", "不保存"}:
        action, reason = MemoryAction.IGNORE, "用户明确拒绝保存。"
    elif sensitivity not in {"", "none", "low"}:
        action, reason = MemoryAction.NEEDS_CONFIRMATION, "敏感信息默认不自动长期保存。"
    elif candidate.requires_confirmation or candidate.confidence < 0.5:
        action, reason = MemoryAction.NEEDS_CONFIRMATION, "候选尚未确认或可信度不足。"
    elif candidate.memory_type in {"candidate_direction", "inferred_fact"}:
        action, reason = MemoryAction.TEMP, "候选方向或模型推断在确认前仅进入临时记忆。"
    elif intent in {"remember", "请记住"} and candidate.memory_type in STRUCTURED_TYPES:
        action, reason = MemoryAction.LONG_TERM_STRUCTURED, "用户明确要求保存且内容适合精确结构化读取。"
    elif intent in {"remember", "请记住"}:
        action, reason = MemoryAction.LONG_TERM_VECTOR, "用户明确要求保存且内容更适合语义/事件记忆。"
    elif score < float(config["temporary_threshold"]):
        action, reason = MemoryAction.IGNORE, "评分低于临时记忆阈值。"
    elif score < float(config["long_term_threshold"]):
        action, reason = MemoryAction.TEMP, "进入带 TTL 的临时记忆。"
    elif candidate.memory_type in STRUCTURED_TYPES:
        action, reason = MemoryAction.LONG_TERM_STRUCTURED, "高价值且需精确读取。"
    elif candidate.memory_type in VECTOR_TYPES:
        action, reason = MemoryAction.LONG_TERM_VECTOR, "高价值语义或事件记忆候选。"
    else:
        action, reason = MemoryAction.NEEDS_CONFIRMATION, "存储类型不明确，需要用户确认。"
    return result(MODULE, {"candidate_id": candidate.candidate_id, "score": round(score, 4), "score_breakdown": breakdown, "action": action.value, "reason": reason, "application_layer_notice": "自动长期记忆是 Agent 应用层条件启用能力，不是大模型自身的永久记忆。"})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return route_memory(raw)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
