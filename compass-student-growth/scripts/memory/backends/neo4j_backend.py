"""Optional graph/semantic backend backed by the Agent Memory adapter."""
from __future__ import annotations

from typing import Any, Mapping

from scripts.integrations.neo4j_memory_adapter import Neo4jMemoryAdapter


class Neo4jMemoryBackend:
    def __init__(self, adapter: Neo4jMemoryAdapter | None = None) -> None:
        self.adapter = adapter or Neo4jMemoryAdapter.from_environment()

    def load_user_context(self, user_id: str, *, query: str = "", top_k: int = 5) -> dict[str, Any]:
        return {"profile": {}, "goal": {}, "competency": {}, "growth_state": {}, "semantic_memory": self.retrieve_memory(user_id, query, top_k=top_k), "graph": []}

    def _entity(self, user_id: str, category: str, value: Mapping[str, Any]) -> dict[str, Any]:
        return self.adapter.upsert_entity({"record_id": f"{category}:{user_id}", "user_id": user_id, "memory_type": category, "content": dict(value)})

    def save_profile(self, user_id: str, profile: Mapping[str, Any]) -> dict[str, Any]: return self._entity(user_id, "profile", profile)
    def save_goal(self, user_id: str, goal: Mapping[str, Any]) -> dict[str, Any]: return self._entity(user_id, "goal", goal)
    def save_competency(self, user_id: str, competency: Mapping[str, Any]) -> dict[str, Any]: return self._entity(user_id, "competency", competency)
    def save_growth_state(self, user_id: str, state: Mapping[str, Any]) -> dict[str, Any]: return self._entity(user_id, "growth_state", state)
    def write_memory(self, user_id: str, memory: Mapping[str, Any]) -> dict[str, Any]: return self._entity(user_id, "semantic", memory)
    def retrieve_memory(self, user_id: str, query: str, *, top_k: int = 5) -> list[dict[str, Any]]: return self.adapter.retrieve_context(user_id=user_id, query=query, top_k=top_k)
    def forget(self, user_id: str) -> dict[str, Any]: return self.adapter.forget_user(user_id)
    def health(self) -> dict[str, Any]: return self.adapter.health()
    def add_edge(self, user_id: str, source: str, relation: str, target: str, properties: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self.adapter.upsert_relation(user_id=user_id, source=source, relation=relation, target=target, properties=dict(properties or {}))
