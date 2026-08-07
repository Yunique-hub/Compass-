"""结构化优先、可选向量、关键词降级的 user_id 隔离召回。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .io_utils import error, result, run_cli
    from .memory_store import FileMemoryStore, UnavailableVectorStore, VectorStoreAdapter
except ImportError:
    from io_utils import error, result, run_cli
    from memory_store import FileMemoryStore, UnavailableVectorStore, VectorStoreAdapter

MODULE = "memory_retriever"


def keyword_similarity(query: str, content: Any) -> float:
    q = {token for token in re.findall(r"[\w\u4e00-\u9fff]+", query.casefold()) if token}
    text = str(content).casefold()
    if not q:
        return 0.0
    matched = sum(1 for token in q if token in text)
    return matched / len(q)


def retrieve(
    store: Any, user_id: str, query: str, *, top_k: int = 5,
    memory_types: Sequence[str] | None = None, vector_store: VectorStoreAdapter | None = None,
    minimum_score: float = 0.20,
) -> dict[str, Any]:
    records = store.list(user_id, status="active")
    if memory_types:
        allowed = set(memory_types)
        records = [item for item in records if item.get("memory_type") in allowed]
    structured_types = {"confirmed_goal", "profile_fact", "weekly_hours", "destination", "deadline"}
    exact = [item for item in records if item.get("memory_type") in structured_types]
    vector_warning = None
    external: list[Mapping[str, Any]] = []
    if vector_store is not None:
        try:
            external = list(vector_store.search(user_id, query, top_k))
        except RuntimeError:
            vector_warning = error("VECTOR_STORE_UNAVAILABLE", "向量存储不可用，已降级为结构化字段 + 本地关键词检索。")
    candidates: dict[str, dict[str, Any]] = {str(item.get("record_id")): dict(item) for item in [*records, *external] if item.get("record_id")}
    ranked: list[dict[str, Any]] = []
    for item in candidates.values():
        semantic = keyword_similarity(query, item.get("content"))
        importance = float(item.get("importance", 0.5))
        usage = min(1.0, float(item.get("usage_count", 0)) / 10.0)
        recency = 0.5
        updated = item.get("updated_at")
        if updated:
            try:
                days = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(str(updated))).days)
                recency = max(0.0, 1.0 - days / 365.0)
            except ValueError:
                pass
        score = 0.55 * semantic + 0.20 * importance + 0.15 * recency + 0.10 * usage
        if score >= minimum_score:
            ranked.append({"record": item, "retrieval_score": round(score, 4), "reason": "结构化精确字段" if item in exact else "本地关键词降级匹配"})
    ranked.sort(key=lambda item: (-item["retrieval_score"], item["record"]["record_id"]))
    warnings = [vector_warning] if vector_warning else []
    return result(MODULE, {"exact_fields": exact, "results": ranked[:top_k], "count": min(len(ranked), top_k), "fallback_notice": "本地关键词检索仅为可测试降级，不等价于正式 Embedding/Reranker 语义模型。"}, warnings=warnings)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    store = FileMemoryStore(Path(str(raw["store_path"])))
    vector = UnavailableVectorStore() if raw.get("simulate_vector_unavailable") else None
    return retrieve(store, str(raw.get("user_id", "")), str(raw.get("query", "")), top_k=int(raw.get("top_k", 5)), memory_types=raw.get("memory_types"), vector_store=vector)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
