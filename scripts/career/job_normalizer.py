"""Open-vocabulary job normalization; aliases are a cache, never a whitelist."""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable


DEFAULT_ALIASES = {
    "IT支持": ["it支持", "it support", "helpdesk", "help desk", "桌面支持", "技术支持"],
    "网络安全工程师": ["网络安全", "安全工程师", "信息安全工程师", "soc工程师", "安全运维"],
    "AI产品经理": ["ai产品经理", "人工智能产品经理", "aigc产品经理"],
    "跨境电商运营": ["跨境运营", "跨境电商", "海外电商运营"],
}


def clean_job_title(value: str) -> str:
    text = re.sub(r"(?:岗位|职位|方向)$", "", " ".join(str(value).strip().split()), flags=re.I)
    return text.strip("，。；;、：: ")


class JobNormalizer:
    def __init__(self, historical_aliases: dict[str, list[str]] | None = None, llm_normalizer: Callable[[str], str] | None = None) -> None:
        self.aliases = {key: list(values) for key, values in DEFAULT_ALIASES.items()}
        for key, values in (historical_aliases or {}).items():
            self.aliases.setdefault(key, []).extend(values)
        self.llm_normalizer = llm_normalizer

    def normalize(self, raw: str) -> dict[str, Any]:
        cleaned = clean_job_title(raw)
        folded = re.sub(r"\s+", "", cleaned).casefold()
        for canonical, aliases in self.aliases.items():
            if folded in {re.sub(r"\s+", "", item).casefold() for item in [canonical, *aliases]}:
                return {"raw": raw, "normalized": canonical, "aliases": list(dict.fromkeys([canonical, *aliases])), "source": "alias_registry", "dynamic": False}
        if self.llm_normalizer:
            candidate = clean_job_title(self.llm_normalizer(cleaned))
            if candidate:
                return {"raw": raw, "normalized": candidate, "aliases": [cleaned, candidate], "source": "optional_llm", "dynamic": True}
        return {"raw": raw, "normalized": cleaned, "aliases": [cleaned], "source": "open_vocabulary", "dynamic": True}
