"""Normalized recruitment evidence models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class JobRecord:
    job_id: str
    title_raw: str
    title_normalized: str = ""
    company: str = ""
    city: str = ""
    district: str = ""
    description: str = ""
    responsibilities: list[str] = field(default_factory=list)
    education: str = ""
    experience: str = ""
    major_requirement: list[str] = field(default_factory=list)
    hard_skills: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    project_requirements: list[str] = field(default_factory=list)
    bonus_items: list[str] = field(default_factory=list)
    source_name: str = ""
    source_type: str = ""
    source_url: str = ""
    published_at: str = ""
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    relevance_score: float = 0.0
    valid: bool = True
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "JobRecord":
        aliases = {"job_title_raw": "title_raw", "job_title_normalized": "title_normalized", "region": "district", "major_requirements": "major_requirement", "source": "source_name", "validity_flag": "valid"}
        prepared = {aliases.get(key, key): item for key, item in value.items()}
        if isinstance(prepared.get("valid"), str): prepared["valid"] = prepared["valid"] == "valid"
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: item for key, item in prepared.items() if key in allowed})
