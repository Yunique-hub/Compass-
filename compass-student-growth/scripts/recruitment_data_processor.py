"""离线招聘快照校验、归一化、去重与可追溯统计。"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .io_utils import error, result, run_cli
    from .models import JobRecord, RecruitmentSnapshot
except ImportError:
    from io_utils import error, result, run_cli
    from models import JobRecord, RecruitmentSnapshot

MODULE = "recruitment_data_processor"
ROOT = Path(__file__).resolve().parents[1]


def load_aliases() -> dict[str, str]:
    raw = json.loads((ROOT / "reference" / "job_roles" / "skill_aliases.json").read_text(encoding="utf-8"))
    return {alias.casefold().replace("-", " "): canonical for canonical, aliases in raw.items() for alias in [canonical, *aliases]}


def normalize_skill(value: str, aliases: Mapping[str, str]) -> str:
    key = " ".join(value.strip().casefold().replace("-", " ").split())
    return aliases.get(key, value.strip())


def normalize_title(value: str) -> str:
    lowered = " ".join(value.strip().split())
    replacements = {"java开发工程师": "Java 后端工程师", "java后端": "Java 后端工程师", "后端开发(java)": "Java 后端工程师"}
    return replacements.get(lowered.casefold(), lowered)


def deduplicate_jobs(jobs: Iterable[JobRecord]) -> tuple[list[JobRecord], list[str]]:
    seen: set[str] = set()
    kept: list[JobRecord] = []
    removed: list[str] = []
    for job in jobs:
        key = job.source_key.strip() or "|".join([job.job_title_normalized.casefold(), job.company.casefold(), job.city.casefold(), job.published_at])
        if key in seen:
            removed.append(job.job_id)
            continue
        seen.add(key)
        kept.append(job)
    return kept, removed


def process_snapshot(raw: Mapping[str, Any]) -> dict[str, Any]:
    aliases = load_aliases()
    invalid: list[dict[str, Any]] = []
    jobs: list[JobRecord] = []
    for index, item in enumerate(raw.get("jobs", [])):
        try:
            prepared = dict(item)
            prepared["job_title_normalized"] = normalize_title(prepared.get("job_title_normalized") or prepared.get("job_title_raw", ""))
            prepared["hard_skills"] = sorted({normalize_skill(skill, aliases) for skill in prepared.get("hard_skills", [])})
            jobs.append(JobRecord.from_dict(prepared))
        except (TypeError, ValueError) as exc:
            invalid.append({"index": index, "reason": str(exc)})
    deduped, duplicates = deduplicate_jobs(jobs)
    valid = [job for job in deduped if job.validity_flag == "valid"]
    traces: dict[str, list[str]] = defaultdict(list)
    for job in valid:
        for skill in job.hard_skills:
            traces[skill].append(job.job_id)
    denominator = len(valid)
    frequencies = {skill: {"frequency": round(len(ids) / denominator, 4) if denominator else 0.0, "job_ids": ids, "count": len(ids)} for skill, ids in sorted(traces.items())}
    threshold = 20
    confidence = "low_confidence" if denominator < threshold else ("recommended_sample" if denominator >= 30 else "medium_confidence")
    synthetic = bool(raw.get("synthetic", False))
    notice = "仅用于功能测试，不代表当前市场" if synthetic else "结论仅适用于所列来源、时间范围和样本。"
    snapshot = RecruitmentSnapshot(
        snapshot_version=str(raw.get("snapshot_version", "")), city=str(raw.get("city", "")),
        career_direction=str(raw.get("career_direction", "")), collected_at=str(raw.get("collected_at", "")),
        date_range=dict(raw.get("date_range", {})), source_types=list(raw.get("source_types", [])),
        source_count=len(set(job.source for job in valid)), sample_count=len(raw.get("jobs", [])),
        valid_sample_count=denominator, confidence_level=confidence, synthetic=synthetic,
        limitations=list(raw.get("limitations", [])), jobs=deduped, usage_notice=notice,
    )
    warnings = []
    if confidence == "low_confidence":
        warnings.append(error("LOW_CONFIDENCE", "有效样本少于 20；这是项目初始质量控制规则，不是行业统一标准。"))
    if synthetic:
        warnings.append(error("SYNTHETIC_DATA", notice))
    return result(MODULE, {"snapshot": snapshot.to_dict(), "skill_statistics": frequencies, "duplicate_job_ids": duplicates, "invalid_records": invalid, "traceability": {"snapshot_version": snapshot.snapshot_version, "date_range": snapshot.date_range, "source_types": snapshot.source_types}}, warnings=warnings)


def load_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in ("hard_skills", "major_requirements", "project_requirements", "soft_skills"):
            row[field] = [item.strip() for item in row.get(field, "").split("|") if item.strip()]
    return {"jobs": rows}


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return process_snapshot(raw)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
