"""Read-only public-page provider backed by Agent Browser."""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.integrations.agent_browser_adapter import AgentBrowserAdapter
from .models import JobRecord
from .provider_base import RecruitmentProvider


class AgentBrowserProvider(RecruitmentProvider):
    name = "agent_browser"
    def __init__(self, adapter: AgentBrowserAdapter | None = None) -> None: self.adapter = adapter or AgentBrowserAdapter()

    def collect(self, city: str, job: str, queries: list[str], context: dict[str, Any]) -> list[JobRecord]:
        records: list[JobRecord] = []
        for url in context.get("public_urls", []):
            page = self.adapter.read_public_page(str(url))
            if page.get("ok") and page.get("content"):
                records.append(JobRecord(job_id=f"browser-{hashlib.sha256(str(url).encode()).hexdigest()[:12]}", title_raw=job, title_normalized=job, city=city, description=str(page["content"]), source_name="public-page", source_type="agent_browser", source_url=str(page.get("source_url") or url), collected_at=str(page.get("collected_at", "")), relevance_score=0.8, synthetic=bool(context.get("synthetic", False))))
        return records

    def health(self) -> dict[str, Any]: return self.adapter.health()
