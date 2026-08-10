"""Canonical SQLite store for profile, goal, competency and growth state."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

FORBIDDEN_TRACE_KEYS = {"chain_of_thought", "reasoning_trace", "hidden_reasoning", "hidden_reasoning_trace", "private_scratchpad", "cot"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if key.casefold() not in FORBIDDEN_TRACE_KEYS}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


VERSIONED_FIELDS = {
    "profile": {"weekly_available_hours", "graduation_time", "learning_preferences", "learning_preference"},
    "goal": {"target_city", "target_job", "target_job_raw", "target_job_normalized", "career_goal"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteMemoryBackend:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS structured_state (
                    user_id TEXT NOT NULL, category TEXT NOT NULL, data_json TEXT NOT NULL,
                    version INTEGER NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY(user_id, category)
                );
                CREATE TABLE IF NOT EXISTS state_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                    category TEXT NOT NULL, field TEXT NOT NULL, old_json TEXT NOT NULL,
                    new_json TEXT NOT NULL, changed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    memory_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, memory_type TEXT NOT NULL,
                    content_json TEXT NOT NULL, importance REAL NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_semantic_user ON semantic_memory(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS growth_graph (
                    edge_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, source TEXT NOT NULL,
                    relation TEXT NOT NULL, target TEXT NOT NULL, properties_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_graph_user ON growth_graph(user_id, relation);
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _load_category(self, user_id: str, category: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT data_json FROM structured_state WHERE user_id=? AND category=?", (user_id, category)).fetchone()
        return json.loads(row["data_json"]) if row else {}

    def _save_category(self, user_id: str, category: str, updates: Mapping[str, Any]) -> dict[str, Any]:
        if not user_id:
            raise ValueError("user_id 不能为空")
        clean = _sanitize(dict(updates))
        current = self._load_category(user_id, category)
        merged = {**current, **clean}
        history_fields = VERSIONED_FIELDS.get(category, set())
        with self._connect() as db:
            row = db.execute("SELECT version FROM structured_state WHERE user_id=? AND category=?", (user_id, category)).fetchone()
            if row and merged == current:
                return {"category": category, "version": int(row["version"]), "data": current, "unchanged": True}
            version = int(row["version"]) + 1 if row else 1
            for field in history_fields:
                if field in clean and field in current and current[field] != clean[field]:
                    db.execute(
                        "INSERT INTO state_history(user_id,category,field,old_json,new_json,changed_at) VALUES(?,?,?,?,?,?)",
                        (user_id, category, field, json.dumps(current[field], ensure_ascii=False), json.dumps(clean[field], ensure_ascii=False), _now()),
                    )
            db.execute(
                "INSERT INTO structured_state VALUES(?,?,?,?,?) ON CONFLICT(user_id,category) DO UPDATE SET data_json=excluded.data_json,version=excluded.version,updated_at=excluded.updated_at",
                (user_id, category, json.dumps(merged, ensure_ascii=False), version, _now()),
            )
        return {"category": category, "version": version, "data": merged}

    def history(self, user_id: str, *, field: str = "") -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT category,field,old_json,new_json,changed_at FROM state_history WHERE user_id=? AND (?='' OR field=?) ORDER BY history_id",
                (user_id, field, field),
            ).fetchall()
        return [{**dict(row), "old": json.loads(row["old_json"]), "new": json.loads(row["new_json"])} for row in rows]

    def load_user_context(self, user_id: str, *, query: str = "", top_k: int = 5) -> dict[str, Any]:
        categories = {name: self._load_category(user_id, name) for name in ("profile", "goal", "competency", "growth_state")}
        return {**categories, "semantic_memory": self.retrieve_memory(user_id, query, top_k=top_k), "graph": self.graph(user_id)}

    def save_profile(self, user_id: str, profile: Mapping[str, Any]) -> dict[str, Any]:
        return self._save_category(user_id, "profile", profile)

    def save_goal(self, user_id: str, goal: Mapping[str, Any]) -> dict[str, Any]:
        return self._save_category(user_id, "goal", goal)

    def save_competency(self, user_id: str, competency: Mapping[str, Any]) -> dict[str, Any]:
        current = self._load_category(user_id, "competency")
        key = str(competency.get("skill", "")).strip()
        if not key:
            return self._save_category(user_id, "competency", competency)
        return self._save_category(user_id, "competency", {**current, key: dict(competency)})

    def save_growth_state(self, user_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
        return self._save_category(user_id, "growth_state", state)

    def write_memory(self, user_id: str, memory: Mapping[str, Any]) -> dict[str, Any]:
        clean = _sanitize(dict(memory))
        if any(key.casefold() in FORBIDDEN_TRACE_KEYS for key in clean):
            raise ValueError("FORBIDDEN_REASONING_MEMORY")
        canonical = json.dumps(clean.get("content", clean), ensure_ascii=False, sort_keys=True)
        memory_id = str(clean.get("memory_id") or uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}|{clean.get('memory_type', 'semantic')}|{canonical.casefold()}"))
        importance = max(0.0, min(1.0, float(clean.get("importance", 0.7))))
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO semantic_memory VALUES(?,?,?,?,?,?)", (memory_id, user_id, str(clean.get("memory_type", "semantic")), json.dumps(clean.get("content", clean), ensure_ascii=False), importance, _now()))
        return {"memory_id": memory_id, "stored": True, "importance": importance}

    def retrieve_memory(self, user_id: str, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT memory_id,memory_type,content_json,importance,created_at FROM semantic_memory WHERE user_id=? ORDER BY importance DESC,created_at DESC", (user_id,)).fetchall()
        tokens = {item.casefold() for item in str(query).split() if item}
        items = [{**dict(row), "content": json.loads(row["content_json"])} for row in rows]
        if tokens:
            items.sort(key=lambda item: (-sum(token in json.dumps(item["content"], ensure_ascii=False).casefold() for token in tokens), -float(item["importance"])))
        return items[:max(0, top_k)]

    def add_edge(self, user_id: str, source: str, relation: str, target: str, properties: Mapping[str, Any] | None = None) -> dict[str, Any]:
        edge_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{user_id}|{source}|{relation}|{target}"))
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO growth_graph VALUES(?,?,?,?,?,?,?)", (edge_id, user_id, source, relation, target, json.dumps(_sanitize(dict(properties or {})), ensure_ascii=False), _now()))
        return {"edge_id": edge_id, "source": source, "relation": relation, "target": target}

    def graph(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT edge_id,source,relation,target,properties_json,updated_at FROM growth_graph WHERE user_id=?", (user_id,)).fetchall()
        return [{**dict(row), "properties": json.loads(row["properties_json"])} for row in rows]

    def forget(self, user_id: str) -> dict[str, Any]:
        counts: dict[str, int] = {}
        with self._connect() as db:
            for table in ("structured_state", "state_history", "semantic_memory", "growth_graph"):
                counts[table] = int(db.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id=?", (user_id,)).fetchone()[0])
                db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        return {"user_id": user_id, "removed": sum(counts.values()), "details": counts, "hard_deleted": True}

    def health(self) -> dict[str, Any]:
        try:
            with self._connect() as db:
                db.execute("SELECT 1").fetchone()
            return {"available": True, "backend": "sqlite", "path": str(self.path)}
        except sqlite3.Error as exc:
            return {"available": False, "backend": "sqlite", "reason": str(exc)}
