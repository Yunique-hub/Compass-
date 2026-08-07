"""Provider for user-supplied, traceable JD text."""
from __future__ import annotations

import hashlib
from typing import Any

from .models import JobRecord
from .provider_base import RecruitmentProvider


class UserJDProvider(RecruitmentProvider):
    name = "user_jd"

    def collect(self, city: str, job: str, queries: list[str], context: dict[str, Any]) -> list[JobRecord]:
        records: list[JobRecord] = []
        for raw in context.get("jds", []):
            item = {"text": raw} if isinstance(raw, str) else dict(raw)
            text = str(item.get("text") or item.get("description") or "").strip()
            if not text: continue
            job_id = str(item.get("job_id") or f"user-jd-{hashlib.sha256(text.encode()).hexdigest()[:12]}")
            records.append(JobRecord(job_id=job_id, title_raw=str(item.get("title") or job), title_normalized=job, company=str(item.get("company", "")), city=str(item.get("city") or city), description=text, source_name="user-provided-jd", source_type="user_jd", source_url=str(item.get("source_url", "")), relevance_score=1.0, synthetic=bool(item.get("synthetic", False))))
        return records
