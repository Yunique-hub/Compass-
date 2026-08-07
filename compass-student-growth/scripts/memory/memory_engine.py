"""Memory Brain orchestration with explicit consent, isolation and deletion."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.memory_policy import route_memory
from scripts.memory_retriever import retrieve
from scripts.memory_store import FileMemoryStore, SQLiteMemoryStore

from .consolidator import consolidate
from .backends.composite_backend import CompositeMemoryBackend
from .backends.neo4j_backend import Neo4jMemoryBackend
from .backends.sqlite_backend import SQLiteMemoryBackend

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
        self.persistent = CompositeMemoryBackend(SQLiteMemoryBackend(self.path), Neo4jMemoryBackend()) if backend == "sqlite" else None

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
        legacy_removed = self.store.delete_user(user_id)
        structured = self.persistent.forget(user_id) if self.persistent else {"primary": {"removed": 0}}
        return {"user_id": user_id, "removed": legacy_removed + int(structured.get("primary", {}).get("removed", 0)), "hard_deleted": True, "backends": structured}

    def consolidate(self, *, user_id: str) -> dict[str, Any]:
        return consolidate(self.store, user_id)

    def load_user_context(self, *, user_id: str, query: str = "", top_k: int = 5) -> dict[str, Any]:
        """READ BEFORE TURN: restore all canonical categories and relevant memory."""
        if not self.persistent:
            return {"profile": {}, "goal": {}, "competency": {}, "growth_state": {}, "semantic_memory": []}
        return self.persistent.load_user_context(user_id, query=query, top_k=top_k)

    def persist_turn(
        self, *, user_id: str, profile_updates: dict[str, Any] | None = None,
        goal_updates: dict[str, Any] | None = None, competency_updates: list[dict[str, Any]] | None = None,
        growth_updates: dict[str, Any] | None = None, semantic_candidates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """WRITE AFTER TURN with structured routing and graph replication."""
        if not self.persistent:
            return {"stored": False, "reason": "structured_backend_unavailable"}
        output: dict[str, Any] = {"profile": None, "goal": None, "competencies": [], "growth_state": None, "semantic": []}
        if profile_updates:
            output["profile"] = self.persistent.save_profile(user_id, _sanitize(profile_updates))
        if goal_updates:
            output["goal"] = self.persistent.save_goal(user_id, _sanitize(goal_updates))
        for item in competency_updates or []:
            output["competencies"].append(self.persistent.save_competency(user_id, _sanitize(item)))
        if growth_updates:
            output["growth_state"] = self.persistent.save_growth_state(user_id, _sanitize(growth_updates))
        for item in semantic_candidates or []:
            clean = _sanitize(item)
            if float(clean.get("importance", 0.0)) >= 0.7:
                output["semantic"].append(self.persistent.write_memory(user_id, clean))
        output["stored"] = any(value for key, value in output.items() if key != "stored")
        return output

    def add_graph_edge(self, *, user_id: str, source: str, relation: str, target: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.persistent:
            return {"stored": False}
        return self.persistent.add_edge(user_id, source, relation, target, properties)

    def health(self) -> dict[str, Any]:
        return self.persistent.health() if self.persistent else {"structured": {"available": False}, "degraded_ok": True}
