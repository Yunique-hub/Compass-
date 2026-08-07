"""Optional adapter boundary for neo4j-labs/agent-memory.

Compass remains fully functional with SQLite. This adapter deliberately imports
the upstream package lazily so missing Neo4j credentials never break startup.
"""
from __future__ import annotations

from typing import Any


def availability() -> dict[str, Any]:
    try:
        import neo4j_agent_memory  # noqa: F401
    except ImportError as exc:
        return {"available": False, "reason": str(exc), "fallback": "sqlite"}
    return {"available": True, "mode": "optional", "requires": ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"]}


def compass_to_entity(record: dict[str, Any]) -> dict[str, Any]:
    """Map a Compass record to the documented agent-memory entity shape."""
    return {
        "name": str(record.get("record_id") or record.get("candidate_id")),
        "type": str(record.get("memory_type", "event")),
        "properties": {"user_id": record.get("user_id"), "content": record.get("content"), "importance": record.get("importance", 0.5)},
    }
