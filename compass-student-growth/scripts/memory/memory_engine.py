"""Memory Brain orchestration with explicit consent, isolation and deletion."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.memory_policy import route_memory
from scripts.memory_retriever import retrieve
from scripts.memory_store import FileMemoryStore, SQLiteMemoryStore

from .consolidator import consolidate

FORBIDDEN_TRACE_KEYS = {"chain_of_thought", "reasoning_trace", "hidden_reasoning", "cot"}
SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{17}[0-9Xx]\b"),
    re.compile(r"\b(?:\d[ -]*?){16,19}\b"),
)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if key.casefold() not in FORBIDDEN_TRACE_KEYS}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


class MemoryEngine:
    def __init__(self, path: str | Path, *, backend: str = "sqlite") -> None:
        self.path = Path(path)
        self.store = SQLiteMemoryStore(self.path) if backend == "sqlite" else FileMemoryStore(self.path)

    def load(self, *, user_id: str, query: str, top_k: int = 5) -> dict[str, Any]:
        if not user_id:
            raise ValueError("user_id 不能为空")
        return retrieve(self.store, user_id, query, top_k=top_k)

    def write(self, *, user_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
        if not user_id or candidate.get("user_id", user_id) != user_id:
            raise PermissionError("USER_ISOLATION_VIOLATION")
        sanitized = _sanitize({**candidate, "user_id": user_id})
        text = str(sanitized.get("content", ""))
        if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
            return {"action": "needs_confirmation", "stored": False, "reason": "检测到高敏感标识符，默认不保存"}
        decision = route_memory(sanitized)
        action = decision["data"]["action"]
        if action not in {"long_term_structured", "long_term_vector", "temp"}:
            return {"action": action, "stored": False, "decision": decision["data"]}
        record = self.store.upsert(user_id, sanitized, source="growth_engine", reason=decision["data"]["reason"])
        return {"action": action, "stored": True, "record": record, "decision": decision["data"]}

    def forget(self, *, user_id: str) -> dict[str, Any]:
        return {"user_id": user_id, "removed": self.store.delete_user(user_id), "hard_deleted": True}

    def consolidate(self, *, user_id: str) -> dict[str, Any]:
        return consolidate(self.store, user_id)
