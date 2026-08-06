"""按 user_id 隔离的文件/SQLite 记忆后端与可选向量适配器。"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

try:
    from .models import MemoryRecord
except ImportError:
    from models import MemoryRecord


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(raw: Mapping[str, Any]) -> MemoryRecord:
    value = dict(raw)
    value.setdefault("record_id", value.get("candidate_id") or str(uuid.uuid4()))
    value.setdefault("candidate_id", value["record_id"])
    value.setdefault("created_at", now_iso())
    value["updated_at"] = now_iso()
    return MemoryRecord.from_dict(value)


class VectorStoreAdapter(Protocol):
    def upsert(self, user_id: str, record: Mapping[str, Any]) -> None: ...
    def search(self, user_id: str, query: str, top_k: int) -> Sequence[Mapping[str, Any]]: ...
    def delete_user(self, user_id: str) -> int: ...


class UnavailableVectorStore:
    def upsert(self, user_id: str, record: Mapping[str, Any]) -> None:
        raise RuntimeError("VECTOR_STORE_UNAVAILABLE")
    def search(self, user_id: str, query: str, top_k: int) -> Sequence[Mapping[str, Any]]:
        raise RuntimeError("VECTOR_STORE_UNAVAILABLE")
    def delete_user(self, user_id: str) -> int:
        return 0


class MemoryStore(ABC):
    @abstractmethod
    def upsert(self, user_id: str, raw: Mapping[str, Any], *, source: str = "user", reason: str = "upsert") -> dict[str, Any]: ...
    @abstractmethod
    def get(self, user_id: str, record_id: str) -> dict[str, Any] | None: ...
    @abstractmethod
    def list(self, user_id: str, *, status: str = "active") -> list[dict[str, Any]]: ...
    @abstractmethod
    def delete_user(self, user_id: str, *, reason: str = "user_forget_request") -> int: ...


class FileMemoryStore(MemoryStore):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.exists():
            self._save({"records": {}, "audit": []})

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"记忆文件损坏或不可读，未覆盖原文件：{exc}") from exc
        return value

    def _save(self, value: Mapping[str, Any]) -> None:
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.path)

    def upsert(self, user_id: str, raw: Mapping[str, Any], *, source: str = "user", reason: str = "upsert") -> dict[str, Any]:
        if not user_id or raw.get("user_id", user_id) != user_id:
            raise PermissionError("USER_ISOLATION_VIOLATION")
        record = _record({**raw, "user_id": user_id})
        with self._lock:
            value = self._load()
            user_records = value["records"].setdefault(user_id, {})
            action = "update" if record.record_id in user_records else "create"
            if action == "update":
                record.version = int(user_records[record.record_id].get("version", 1)) + 1
            user_records[record.record_id] = record.to_dict()
            value["audit"].append({"user_id": user_id, "record_id": record.record_id, "time": now_iso(), "source": source, "action": action, "reason": reason, "version": record.version})
            self._save(value)
        return record.to_dict()

    def get(self, user_id: str, record_id: str) -> dict[str, Any] | None:
        return self._load()["records"].get(user_id, {}).get(record_id)

    def list(self, user_id: str, *, status: str = "active") -> list[dict[str, Any]]:
        return [item for item in self._load()["records"].get(user_id, {}).values() if not status or item.get("status") == status]

    def delete_user(self, user_id: str, *, reason: str = "user_forget_request") -> int:
        with self._lock:
            value = self._load()
            removed = len(value["records"].pop(user_id, {}))
            value["audit"].append({"user_id": user_id, "time": now_iso(), "source": "user", "action": "hard_delete_user", "reason": reason, "version": 1, "removed_count": removed})
            self._save(value)
        return removed

    def audit(self, user_id: str) -> list[dict[str, Any]]:
        return [item for item in self._load()["audit"] if item["user_id"] == user_id]


class SQLiteMemoryStore(MemoryStore):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    user_id TEXT NOT NULL, record_id TEXT NOT NULL, memory_type TEXT NOT NULL,
                    content_json TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, record_id)
                );
                CREATE INDEX IF NOT EXISTS idx_memories_user_status ON memories(user_id, status);
                CREATE TABLE IF NOT EXISTS memory_audit (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                    record_id TEXT, happened_at TEXT NOT NULL, source TEXT NOT NULL,
                    action TEXT NOT NULL, reason TEXT NOT NULL, version INTEGER NOT NULL
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def upsert(self, user_id: str, raw: Mapping[str, Any], *, source: str = "user", reason: str = "upsert") -> dict[str, Any]:
        if not user_id or raw.get("user_id", user_id) != user_id:
            raise PermissionError("USER_ISOLATION_VIOLATION")
        record = _record({**raw, "user_id": user_id})
        with self._connect() as db:
            old = db.execute("SELECT version FROM memories WHERE user_id=? AND record_id=?", (user_id, record.record_id)).fetchone()
            record.version = int(old["version"]) + 1 if old else 1
            data = record.to_dict()
            db.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id, record_id) DO UPDATE SET memory_type=excluded.memory_type, content_json=excluded.content_json, status=excluded.status, version=excluded.version, updated_at=excluded.updated_at", (user_id, record.record_id, record.memory_type, json.dumps(data, ensure_ascii=False), record.status, record.version, record.created_at, record.updated_at))
            db.execute("INSERT INTO memory_audit(user_id, record_id, happened_at, source, action, reason, version) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, record.record_id, now_iso(), source, "update" if old else "create", reason, record.version))
        return data

    def get(self, user_id: str, record_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT content_json FROM memories WHERE user_id=? AND record_id=?", (user_id, record_id)).fetchone()
        return json.loads(row["content_json"]) if row else None

    def list(self, user_id: str, *, status: str = "active") -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT content_json FROM memories WHERE user_id=? AND (?='' OR status=?) ORDER BY updated_at DESC", (user_id, status, status)).fetchall()
        return [json.loads(row["content_json"]) for row in rows]

    def soft_invalidate(self, user_id: str, record_id: str, *, reason: str = "superseded") -> bool:
        with self._connect() as db:
            row = db.execute("SELECT version FROM memories WHERE user_id=? AND record_id=?", (user_id, record_id)).fetchone()
            if not row:
                return False
            version = int(row["version"]) + 1
            db.execute("UPDATE memories SET status='invalid', version=?, updated_at=? WHERE user_id=? AND record_id=?", (version, now_iso(), user_id, record_id))
            db.execute("INSERT INTO memory_audit(user_id, record_id, happened_at, source, action, reason, version) VALUES (?, ?, ?, 'system', 'soft_invalidate', ?, ?)", (user_id, record_id, now_iso(), reason, version))
        return True

    def delete_user(self, user_id: str, *, reason: str = "user_forget_request") -> int:
        with self._connect() as db:
            count = int(db.execute("SELECT COUNT(*) FROM memories WHERE user_id=?", (user_id,)).fetchone()[0])
            db.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
            db.execute("INSERT INTO memory_audit(user_id, record_id, happened_at, source, action, reason, version) VALUES (?, NULL, ?, 'user', 'hard_delete_user', ?, 1)", (user_id, now_iso(), reason))
        return count

    def audit(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT user_id, record_id, happened_at, source, action, reason, version FROM memory_audit WHERE user_id=? ORDER BY audit_id", (user_id,)).fetchall()
        return [dict(row) for row in rows]


def forget_everywhere(user_id: str, store: MemoryStore, *, vector_store: VectorStoreAdapter | None = None, cache: dict[str, Any] | None = None) -> dict[str, int]:
    structured = store.delete_user(user_id)
    vectors = vector_store.delete_user(user_id) if vector_store else 0
    cache_removed = 0
    if cache is not None:
        for key in [key for key in cache if key == user_id or key.startswith(user_id + ":")]:
            del cache[key]
            cache_removed += 1
    return {"structured_records": structured, "vector_records": vectors, "cache_entries": cache_removed, "temporary_copies": 0, "indexes": vectors}
