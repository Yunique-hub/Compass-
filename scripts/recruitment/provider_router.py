"""Provider ordering, isolation and observable fallback reporting."""
from __future__ import annotations

from typing import Any, Iterable

from .models import JobRecord
from .provider_base import RecruitmentProvider


class ProviderRouter:
    def __init__(self, providers: Iterable[RecruitmentProvider]) -> None: self.providers = list(providers)

    def collect(self, city: str, job: str, queries: list[str], context: dict[str, Any]) -> tuple[list[JobRecord], list[dict[str, Any]]]:
        records: list[JobRecord] = []; reports: list[dict[str, Any]] = []
        for provider in self.providers:
            health = provider.health()
            if not health.get("available", True):
                reports.append({"provider": provider.name, "status": "unavailable", "health": health}); continue
            try:
                items = provider.collect(city, job, queries, context); records.extend(items)
                reports.append({"provider": provider.name, "status": "ok", "count": len(items)})
            except Exception as exc:
                reports.append({"provider": provider.name, "status": "error", "error": f"{type(exc).__name__}: {exc}"})
        return records, reports
