"""Target -> query -> provider -> JD -> skill -> market intelligence."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from scripts.career.job_target_resolver import JobTargetResolver
from .agent_browser_provider import AgentBrowserProvider
from .models import JobRecord
from .provider_router import ProviderRouter
from .public_search_provider import PublicSearchProvider
from .query_expander import QueryExpander
from .skill_extractor import SkillExtractor
from .snapshot_provider import SnapshotProvider
from .user_jd_provider import UserJDProvider


class RecruitmentEngine:
    def __init__(self, *, providers: Iterable[Any] | None = None, resolver: JobTargetResolver | None = None, expander: QueryExpander | None = None, extractor: SkillExtractor | None = None, minimum_samples: int | None = None) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "config" / "recruitment_policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8")) if policy_path.exists() else {"minimum_valid_samples": 5}
        self.resolver, self.expander, self.extractor, self.minimum_samples = resolver or JobTargetResolver(), expander or QueryExpander(), extractor or SkillExtractor(), int(minimum_samples if minimum_samples is not None else policy["minimum_valid_samples"])
        self.router = ProviderRouter(providers or [PublicSearchProvider(), AgentBrowserProvider(), UserJDProvider(), SnapshotProvider()])

    @staticmethod
    def _dedupe(records: list[JobRecord]) -> list[JobRecord]:
        seen: set[str] = set(); output: list[JobRecord] = []
        for item in records:
            key = item.source_url or hashlib.sha256(f"{item.title_raw}|{item.company}|{item.city}|{item.description}".encode()).hexdigest()
            if key not in seen: seen.add(key); output.append(item)
        return output

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = self.resolver.resolve(str(payload.get("message", "")), payload.get("context", {}), city=str(payload.get("target_city", "")), job=str(payload.get("target_job", "")))
        if target["confirmation_state"] != "confirmed":
            return {"status": "target_incomplete", **target, "queries": [], "sources": [], "raw_sample_count": 0, "valid_sample_count": 0, "skill_statistics": [], "market_profile": {}, "confidence": "none", "market_data_status": "insufficient", "limitations": [f"缺少：{', '.join(target['missing'])}"]}
        queries = self.expander.expand(target["target_city"], target["target_job_normalized"])
        records, reports = self.router.collect(target["target_city"], target["target_job_normalized"], queries, payload)
        raw_count = len(records); valid: list[JobRecord] = []; traces: dict[str, list[str]] = defaultdict(list); dynamic: list[str] = []
        for record in self._dedupe(records):
            normalized_title = (record.title_normalized or record.title_raw).casefold().replace(" ", "")
            title_match = target["target_job_normalized"].casefold().replace(" ", "") in normalized_title
            record.relevance_score = max(record.relevance_score, 0.7 if title_match else 0.4)
            if not record.description.strip() or record.relevance_score < 0.35: record.valid = False; continue
            extracted = self.extractor.extract(record.description)
            record.hard_skills = list(dict.fromkeys([*record.hard_skills, *extracted["hard_skills"]])); record.soft_skills = list(dict.fromkeys([*record.soft_skills, *extracted["soft_skills"]]))
            record.education = record.education or extracted["education"]; record.experience = record.experience or extracted["experience"]
            record.project_requirements = list(dict.fromkeys([*record.project_requirements, *extracted["project_requirements"]])); dynamic.extend(extracted["dynamic_skills"]); valid.append(record)
            for skill in record.hard_skills: traces[skill].append(record.job_id)
        self.extractor.persist_dynamic(dynamic)
        synthetic_only = bool(valid) and all(item.synthetic for item in valid); denominator = len(valid)
        statistics = [{"skill": skill, "count": len(ids), "frequency": round(len(ids) / denominator, 4) if denominator else 0.0, "job_ids": ids} for skill, ids in sorted(traces.items(), key=lambda pair: (-len(pair[1]), pair[0].casefold()))]
        sufficient = denominator >= self.minimum_samples and not synthetic_only; limitations: list[str] = []
        if denominator < self.minimum_samples: limitations.append(f"有效样本 {denominator} 少于最低阈值 {self.minimum_samples}")
        if synthetic_only: limitations.append("样本均为 synthetic fixture，仅用于功能测试，不代表真实招聘市场")
        if not records: limitations.append("当前 Provider 未取得可追溯公开招聘样本；未使用内置知识冒充市场数据")
        snapshot_id = hashlib.sha256(json.dumps([item.to_dict() for item in valid], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        return {"status": "analyzed" if valid else "no_data", **target, "queries": queries, "sources": reports, "raw_sample_count": raw_count, "valid_sample_count": denominator, "records": [item.to_dict() for item in valid], "skill_statistics": statistics, "market_profile": {"snapshot_id": snapshot_id, "top_skills": statistics[:10], "synthetic": synthetic_only}, "snapshot_id": snapshot_id, "confidence": "high" if denominator >= 30 and not synthetic_only else ("medium" if sufficient else "low"), "market_data_status": "sufficient" if sufficient else "insufficient", "synthetic": synthetic_only, "usage_notice": "仅用于功能测试，不代表真实招聘市场" if synthetic_only else "统计仅基于本次可追溯来源与时间范围。", "limitations": limitations}
