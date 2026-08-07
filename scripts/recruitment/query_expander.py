"""Query expansion from local, historical and optional LLM aliases."""
from __future__ import annotations

import re
from typing import Callable, Iterable

from scripts.career.job_normalizer import JobNormalizer


class QueryExpander:
    def __init__(self, *, historical_aliases: dict[str, list[str]] | None = None, llm_expander: Callable[[str, str], Iterable[str]] | None = None, maximum: int = 8) -> None:
        self.normalizer = JobNormalizer(historical_aliases)
        self.historical_aliases = historical_aliases or {}
        self.llm_expander, self.maximum = llm_expander, maximum

    def expand(self, city: str, job: str) -> list[str]:
        normalized = self.normalizer.normalize(job)
        aliases = [job, normalized["normalized"], *normalized["aliases"], *self.historical_aliases.get(normalized["normalized"], [])]
        aliases.extend(item for item in re.split(r"[/、|]", job) if item.strip())
        if self.llm_expander:
            try: aliases.extend(str(item) for item in self.llm_expander(city, job))
            except Exception: pass
        unique = list(dict.fromkeys(" ".join(item.strip().split()) for item in aliases if item and item.strip()))
        return [f"{city} {alias} 招聘" for alias in unique[: self.maximum]]


def expand_queries(city: str, job: str) -> list[str]: return QueryExpander().expand(city, job)
