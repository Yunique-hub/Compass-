"""Resolve arbitrary free-text city and job targets without allowlists."""
from __future__ import annotations

import re
from typing import Any, Mapping

from .job_normalizer import JobNormalizer, clean_job_title


CITY_PATTERN = re.compile(r"(?:目标(?:城市)?(?:是|为)?|准备去|毕业(?:后)?(?:准备|想)?去|想去|希望去|去)\s*([\u4e00-\u9fff]{2,12}?)(?:市)?(?=做|从事|当|找|的|\s|，|。|$)|在\s*([\u4e00-\u9fff]{2,12}市)(?=做|从事|当|找)")
JOB_PATTERN = re.compile(r"(?:目标(?:岗位|职位|工作)?(?:是|为)?|想做|做|从事|当|找(?:一份)?)([A-Za-z0-9+#.\-\u4e00-\u9fff /]{2,40}?)(?=岗位|职位|工作|方向|[，。；;！!？?]|$)", re.I)


class JobTargetResolver:
    def __init__(self, normalizer: JobNormalizer | None = None) -> None:
        self.normalizer = normalizer or JobNormalizer()

    def resolve(self, text: str = "", context: Mapping[str, Any] | None = None, *, city: str = "", job: str = "") -> dict[str, Any]:
        context = context or {}
        goal = context.get("goal", context) if isinstance(context, Mapping) else {}
        city_match = CITY_PATTERN.search(text)
        resolved_city = str(city or (((city_match.group(1) or city_match.group(2)).removesuffix("市")) if city_match else "") or goal.get("target_city", "")).strip()
        job_match = JOB_PATTERN.search(text)
        resolved_job = clean_job_title(str(job or (job_match.group(1) if job_match else "") or goal.get("target_job_raw", "") or goal.get("target_job_normalized", "")))
        normalized = self.normalizer.normalize(resolved_job) if resolved_job else {"raw": "", "normalized": "", "aliases": [], "source": "missing", "dynamic": True}
        complete = bool(resolved_city and normalized["normalized"])
        return {
            "target_city": resolved_city,
            "target_job_raw": resolved_job,
            "target_job_normalized": normalized["normalized"],
            "search_aliases": normalized["aliases"],
            "normalization_source": normalized["source"],
            "confirmation_state": "confirmed" if complete else "needs_confirmation",
            "research_mode": "DYNAMIC_JOB_RESEARCH" if complete else "TARGET_INCOMPLETE",
            "missing": [name for name, value in (("target_city", resolved_city), ("target_job", resolved_job)) if not value],
        }
