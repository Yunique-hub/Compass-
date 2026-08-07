"""Optional, user-isolated adapter for neo4j-labs/agent-memory/Neo4j.

The adapter accepts an injected client for tests and deployments.  It never
becomes a startup requirement: callers must retain SQLite as the canonical
store and treat graph writes as best-effort replication.
"""
from __future__ import annotations

import os
from typing import Any

FORBIDDEN_TRACE_KEYS = {"chain_of_thought", "reasoning_trace", "hidden_reasoning", "hidden_reasoning_trace", "private_scratchpad", "cot"}


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if key.casefold() not in FORBIDDEN_TRACE_KEYS}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


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
        "properties": _sanitize({"user_id": record.get("user_id"), "content": record.get("content"), "importance": record.get("importance", 0.5)}),
    }


class Neo4jMemoryAdapter:
    """Map Compass growth entities and relationships onto an optional client."""

    def __init__(self, client: Any | None = None, *, uri: str = "", username: str = "", password: str = "") -> None:
        self.client = client
        self.uri, self.username = uri, username
        self._reason = "client_not_configured"
        if self.client is None and uri and username and password:
            try:
                from neo4j import GraphDatabase

                self.client = GraphDatabase.driver(uri, auth=(username, password))
                self._reason = ""
            except (ImportError, OSError, ValueError) as exc:
                self._reason = f"{type(exc).__name__}: {exc}"

    @classmethod
    def from_environment(cls) -> "Neo4jMemoryAdapter":
        return cls(uri=os.getenv("NEO4J_URI", ""), username=os.getenv("NEO4J_USERNAME", ""), password=os.getenv("NEO4J_PASSWORD", ""))

    def health(self) -> dict[str, Any]:
        if self.client is None:
            return {"available": False, "backend": "neo4j-agent-memory", "reason": self._reason, "fallback": "sqlite"}
        try:
            if hasattr(self.client, "verify_connectivity"):
                self.client.verify_connectivity()
            return {"available": True, "backend": "neo4j-agent-memory", "mode": "optional"}
        except Exception as exc:
            return {"available": False, "backend": "neo4j-agent-memory", "reason": f"{type(exc).__name__}: {exc}", "fallback": "sqlite"}

    def _execute(self, query: str, **params: Any) -> list[dict[str, Any]]:
        if self.client is None:
            raise RuntimeError("NEO4J_UNAVAILABLE")
        if hasattr(self.client, "execute_query"):
            records, _, _ = self.client.execute_query(query, **params)
            return [dict(item) for item in records]
        with self.client.session() as session:
            return [dict(item) for item in session.run(query, **params)]

    def upsert_entity(self, record: dict[str, Any]) -> dict[str, Any]:
        entity = compass_to_entity(_sanitize(record))
        user_id = str(entity["properties"].get("user_id") or "")
        if not user_id:
            raise ValueError("user_id 不能为空")
        self._execute(
            "MERGE (n:CompassEntity {user_id:$user_id, name:$name}) SET n.type=$type, n.properties_json=$properties_json, n.updated_at=datetime() RETURN n.name AS name",
            user_id=user_id, name=entity["name"], type=entity["type"], properties_json=__import__("json").dumps(entity["properties"], ensure_ascii=False),
        )
        return {"stored": True, "entity": entity}

    def upsert_relation(self, *, user_id: str, source: str, relation: str, target: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        if not relation.replace("_", "").isalnum():
            raise ValueError("INVALID_RELATION")
        safe_relation = relation.upper()
        self._execute(
            f"MERGE (a:CompassEntity {{user_id:$user_id,name:$source}}) MERGE (b:CompassEntity {{user_id:$user_id,name:$target}}) MERGE (a)-[r:{safe_relation}]->(b) SET r.properties_json=$properties_json RETURN type(r) AS relation",
            user_id=user_id, source=source, target=target, properties_json=__import__("json").dumps(_sanitize(properties or {}), ensure_ascii=False),
        )
        return {"stored": True, "source": source, "relation": safe_relation, "target": target}

    def retrieve_context(self, *, user_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        rows = self._execute(
            "MATCH (n:CompassEntity {user_id:$user_id}) WHERE toLower(n.name) CONTAINS toLower($query) OR toLower(n.properties_json) CONTAINS toLower($query) RETURN n.name AS name,n.type AS type,n.properties_json AS properties LIMIT $top_k",
            user_id=user_id, query=query, top_k=max(0, int(top_k)),
        )
        return rows

    def forget_user(self, user_id: str) -> dict[str, Any]:
        rows = self._execute("MATCH (n:CompassEntity {user_id:$user_id}) WITH count(n) AS removed MATCH (m:CompassEntity {user_id:$user_id}) DETACH DELETE m RETURN removed", user_id=user_id)
        return {"user_id": user_id, "removed": int(rows[0].get("removed", 0)) if rows else 0, "hard_deleted": True}
