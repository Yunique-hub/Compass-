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
PROFILE_PERSIST_ALLOWLIST = {
    "preferred_name", "preferred_name_usage", "education_level", "grade", "major",
    "secondary_major", "minor", "primary_need", "claimed_skills", "courses", "interests",
    "daily_learning_hours", "weekly_learning_hours", "weekly_hours", "weekly_available_hours",
    "company_preference", "graduation_time", "learning_preferences", "learning_preference",
    "academic_profile",
}
CONFIRMED_PROFILE_SOURCES = {"user_explicit", "user_confirmed"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if key.casefold() not in FORBIDDEN_TRACE_KEYS}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _safe_profile_updates(updates: dict[str, Any], sources: dict[str, str] | None = None) -> dict[str, Any]:
    """Apply a field allowlist and a separate confirmation gate for academic major."""
    sources = sources or {}
    clean = {key: value for key, value in updates.items() if key in PROFILE_PERSIST_ALLOWLIST}
    academic = clean.get("academic_profile")
    academic_confirmed = isinstance(academic, dict) and academic.get("profile_source") in {"explicit", "user_confirmed"}
    if "major" in clean and sources.get("major") not in CONFIRMED_PROFILE_SOURCES and not academic_confirmed:
        clean.pop("major", None)
    if isinstance(academic, dict):
        if not academic_confirmed:
            clean.pop("academic_profile", None)
        else:
            clean["academic_profile"] = {
                key: value for key, value in academic.items()
                if key not in {"current_topic", "learning_domain"}
            }
    return clean


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
        profile_sources: dict[str, str] | None = None,
        goal_updates: dict[str, Any] | None = None, competency_updates: list[dict[str, Any]] | None = None,
        growth_updates: dict[str, Any] | None = None, semantic_candidates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """WRITE AFTER TURN with structured routing and graph replication."""
        if not self.persistent:
            return {"stored": False, "reason": "structured_backend_unavailable"}
        output: dict[str, Any] = {"profile": None, "goal": None, "competencies": [], "growth_state": None, "semantic": []}
        if profile_updates:
            safe_profile = _safe_profile_updates(_sanitize(profile_updates), profile_sources)
            if safe_profile:
                output["profile"] = self.persistent.save_profile(user_id, safe_profile)
        if goal_updates:
            clean_goal = _sanitize(goal_updates)
            current_goal = self.persistent.load_user_context(user_id, query="", top_k=0).get("goal", {})
            old_target = str(current_goal.get("target_job") or current_goal.get("target_job_normalized") or "")
            new_target = str(clean_goal.get("target_job") or clean_goal.get("target_job_normalized") or "")
            if old_target and new_target and old_target != new_target:
                history = list(current_goal.get("goal_history") or [])
                if old_target not in history:
                    history.append(old_target)
                clean_goal["previous_target_job"] = old_target
                clean_goal["goal_history"] = history
            output["goal"] = self.persistent.save_goal(user_id, clean_goal)
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
