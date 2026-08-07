"""SQLite-first memory with best-effort Agent Memory graph replication."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from .neo4j_backend import Neo4jMemoryBackend
from .sqlite_backend import SQLiteMemoryBackend


class CompositeMemoryBackend:
    def __init__(self, structured: SQLiteMemoryBackend, graph: Neo4jMemoryBackend | None = None) -> None:
        self.structured, self.graph_backend = structured, graph

    def _write(self, method: str, user_id: str, value: Mapping[str, Any]) -> dict[str, Any]:
        primary = getattr(self.structured, method)(user_id, value)
        replication = {"attempted": False, "ok": False, "fallback": "sqlite"}
        if self.graph_backend and self.graph_backend.health().get("available"):
            replication["attempted"] = True
            try:
                replication.update({"ok": True, "result": getattr(self.graph_backend, method)(user_id, value)})
            except Exception as exc:
                replication["reason"] = f"{type(exc).__name__}: {exc}"
        return {"primary": primary, "graph_replication": replication}

    def load_user_context(self, user_id: str, *, query: str = "", top_k: int = 5) -> dict[str, Any]:
        context = self.structured.load_user_context(user_id, query=query, top_k=top_k)
        if self.graph_backend and self.graph_backend.health().get("available"):
            try:
                context["semantic_memory"] = [*self.graph_backend.retrieve_memory(user_id, query, top_k=top_k), *context["semantic_memory"]][:top_k]
            except Exception as exc:
                context["graph_warning"] = f"{type(exc).__name__}: {exc}"
        return context

    def save_profile(self, user_id: str, profile: Mapping[str, Any]) -> dict[str, Any]: return self._write("save_profile", user_id, profile)
    def save_goal(self, user_id: str, goal: Mapping[str, Any]) -> dict[str, Any]: return self._write("save_goal", user_id, goal)
    def save_competency(self, user_id: str, competency: Mapping[str, Any]) -> dict[str, Any]: return self._write("save_competency", user_id, competency)
    def save_growth_state(self, user_id: str, state: Mapping[str, Any]) -> dict[str, Any]: return self._write("save_growth_state", user_id, state)
    def write_memory(self, user_id: str, memory: Mapping[str, Any]) -> dict[str, Any]: return self._write("write_memory", user_id, memory)
    def retrieve_memory(self, user_id: str, query: str, *, top_k: int = 5) -> list[dict[str, Any]]: return self.load_user_context(user_id, query=query, top_k=top_k)["semantic_memory"]

    def add_edge(self, user_id: str, source: str, relation: str, target: str, properties: Mapping[str, Any] | None = None) -> dict[str, Any]:
        primary = self.structured.add_edge(user_id, source, relation, target, properties)
        if self.graph_backend and self.graph_backend.health().get("available"):
            try:
                return {"primary": primary, "graph": self.graph_backend.add_edge(user_id, source, relation, target, properties)}
            except Exception as exc:
                return {"primary": primary, "graph_warning": f"{type(exc).__name__}: {exc}"}
        return {"primary": primary, "graph": {"available": False}}

    def forget(self, user_id: str) -> dict[str, Any]:
        primary = self.structured.forget(user_id)
        graph = self.graph_backend.forget(user_id) if self.graph_backend and self.graph_backend.health().get("available") else {"available": False}
        return {"primary": primary, "graph": graph}

    def health(self) -> dict[str, Any]:
        return {"structured": self.structured.health(), "neo4j": self.graph_backend.health() if self.graph_backend else {"available": False}, "degraded_ok": True}
