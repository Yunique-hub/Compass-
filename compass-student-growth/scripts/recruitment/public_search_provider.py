"""Optional public-search provider using an injected search function."""
from __future__ import annotations

from typing import Any, Callable

from .models import JobRecord
from .provider_base import RecruitmentProvider


class PublicSearchProvider(RecruitmentProvider):
    name = "public_search"

    def __init__(self, search: Callable[[str], list[dict[str, Any]]] | None = None) -> None: self.search = search
    def health(self) -> dict[str, Any]: return {"provider": self.name, "available": self.search is not None}

    def collect(self, city: str, job: str, queries: list[str], context: dict[str, Any]) -> list[JobRecord]:
        if not self.search: return []
        records: list[JobRecord] = []
        for query in queries:
            for item in self.search(query):
                if item.get("content"):
                    records.append(JobRecord.from_mapping({"job_id": item.get("job_id") or item.get("url") or f"search-{len(records)+1}", "title_raw": item.get("title") or job, "title_normalized": job, "city": item.get("city") or city, "description": item["content"], "source_name": item.get("source_name", "public-search"), "source_type": "public_search", "source_url": item.get("url", ""), "published_at": item.get("published_at", ""), "relevance_score": item.get("relevance_score", 0.7)}))
        return records
