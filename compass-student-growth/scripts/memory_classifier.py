"""记忆候选分类模板和确定性响应校验；不调用云端模型。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

try:
    from .io_utils import error, result, run_cli
    from .models import MemoryCandidate, clamp
except ImportError:
    from io_utils import error, result, run_cli
    from models import MemoryCandidate, clamp

MODULE = "memory_classifier"
PROMPT_TEMPLATE = """从本轮摘要中提取 0 到少量高价值记忆候选，仅输出 JSON 数组。不要复制整段对话。区分已确认目标、临时状态、偏好、事件、成就；标记敏感性。模型推断必须 requires_confirmation=true。用户明确拒绝记忆时输出空数组或 delete 候选。"""
ALLOWED_FIELDS = {name for name in MemoryCandidate.__dataclass_fields__ if name != "required_fields"}
SENSITIVE_HINTS = ("身份证", "银行卡", "精确住址", "诊断", "药物", "自杀", "宗教", "民族")


def validate_candidates(raw: Any, user_id: str) -> dict[str, Any]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        return result(MODULE, ok=False, errors=[error("INVALID_CLASSIFIER_RESPONSE", "候选响应必须是 JSON 数组。")], fallback={"action": "return_zero_candidates"})
    candidates: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            warnings.append(error("INVALID_CANDIDATE", "非对象候选已忽略。", index=index))
            continue
        cleaned = {key: value for key, value in item.items() if key in ALLOWED_FIELDS}
        cleaned["candidate_id"] = str(cleaned.get("candidate_id") or f"candidate-{index + 1}")
        cleaned["user_id"] = user_id
        cleaned["memory_type"] = str(cleaned.get("memory_type") or "event")
        cleaned["created_at"] = str(cleaned.get("created_at") or now)
        cleaned["updated_at"] = str(cleaned.get("updated_at") or now)
        for field in ("importance", "stability", "future_relevance", "user_explicitness", "recurrence", "confidence", "task_value"):
            cleaned[field] = clamp(float(cleaned.get(field, 0.0)))
        content_text = str(cleaned.get("content", ""))
        if any(hint in content_text for hint in SENSITIVE_HINTS):
            cleaned["sensitivity"] = "high"
            cleaned["requires_confirmation"] = True
        try:
            candidates.append(MemoryCandidate.from_dict(cleaned).to_dict())
        except (TypeError, ValueError) as exc:
            warnings.append(error("INVALID_CANDIDATE", str(exc), index=index))
    return result(MODULE, {"candidates": candidates, "count": len(candidates), "prompt_template": PROMPT_TEMPLATE}, warnings=warnings)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return validate_candidates(raw.get("candidates", []), str(raw.get("user_id", "")))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
