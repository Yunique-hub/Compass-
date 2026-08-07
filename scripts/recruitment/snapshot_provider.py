"""Versioned local snapshot provider; synthetic fixtures remain labelled."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import JobRecord
from .provider_base import RecruitmentProvider


class SnapshotProvider(RecruitmentProvider):
    name = "snapshot"

    def __init__(self, root: str | Path | None = None) -> None: self.root = Path(root or Path(__file__).resolve().parents[2] / "reference" / "recruitment_snapshots")

    def collect(self, city: str, job: str, queries: list[str], context: dict[str, Any]) -> list[JobRecord]:
        records: list[JobRecord] = []
        for path in self.root.rglob("*.json") if self.root.exists() else []:
            try: raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): continue
            if str(raw.get("city", "")).casefold() != city.casefold(): continue
            direction = str(raw.get("career_direction", ""))
            compact_job, compact_direction = job.casefold().replace(" ", ""), direction.casefold().replace(" ", "")
            if compact_job not in compact_direction and compact_direction not in compact_job: continue
            for item in raw.get("jobs", []):
                prepared = dict(item)
                prepared.update({"source_type": "snapshot", "synthetic": bool(raw.get("synthetic", False)), "source_name": prepared.get("source", "versioned-snapshot")})
                records.append(JobRecord.from_mapping(prepared))
        return records
