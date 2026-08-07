"""Small user-isolated relationship graph persisted as regular memory records."""
from __future__ import annotations

import hashlib
from typing import Any


def edge_id(user_id: str, source: str, relation: str, target: str) -> str:
    digest = hashlib.sha256(f"{user_id}\0{source}\0{relation}\0{target}".encode()).hexdigest()[:20]
    return f"edge-{digest}"


def add_edge(store: Any, *, user_id: str, source: str, relation: str, target: str, evidence: str = "") -> dict[str, Any]:
    if not all((user_id, source, relation, target)):
        raise ValueError("关系边必须包含 user_id/source/relation/target")
    record_id = edge_id(user_id, source, relation, target)
    return store.upsert(user_id, {
        "record_id": record_id,
        "candidate_id": record_id,
        "user_id": user_id,
        "memory_type": "relationship",
        "content": {"source": source, "relation": relation, "target": target, "evidence": evidence},
        "importance": 0.7,
        "confidence": 1.0 if evidence else 0.6,
    }, source="memory_graph", reason="relationship_upsert")
