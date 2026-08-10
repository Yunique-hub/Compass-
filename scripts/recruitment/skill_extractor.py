"""Hybrid open-vocabulary skill and requirement extraction."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
TECH_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9+#.\-]*(?:\s+[A-Za-z][A-Za-z0-9+#.\-]*){0,2})(?![A-Za-z0-9])")
DOMAIN_PATTERN = re.compile(r"(?:熟悉|掌握|了解|具备|使用|负责|要求)([\u4e00-\u9fff]{2,12})(?:能力|经验|技术|工具|平台|系统|流程)?")
STOPWORDS = {"and", "or", "the", "with", "using", "years", "year", "full", "job", "good", "strong"}


class SkillExtractor:
    def __init__(self, registry_path: str | Path | None = None, llm_extractor: Callable[[str], list[str]] | None = None) -> None:
        self.registry_path = Path(registry_path or ROOT / "runtime" / "dynamic_skill_registry.json")
        self.llm_extractor = llm_extractor
        raw = json.loads((ROOT / "reference" / "job_roles" / "skill_aliases.json").read_text(encoding="utf-8"))
        self.aliases = {alias.casefold().replace("-", " "): canonical for canonical, values in raw.items() for alias in [canonical, *values]}

    def normalize(self, skill: str) -> str:
        cleaned = " ".join(skill.strip("，。；;、：:()（） ").split())
        return self.aliases.get(cleaned.casefold().replace("-", " "), cleaned)

    def extract(self, text: str) -> dict[str, Any]:
        candidates: list[str] = []; folded = text.casefold().replace("-", " ")
        for alias, canonical in self.aliases.items():
            contains_cjk = bool(re.search(r"[\u4e00-\u9fff]", alias))
            if (alias in folded if contains_cjk else re.search(rf"(?<![\w]){re.escape(alias)}(?![\w])", folded, re.I)):
                candidates.append(canonical)
        for match in TECH_PATTERN.findall(text):
            if match.casefold() not in STOPWORDS and len(match) <= 30: candidates.append(match)
        candidates.extend(DOMAIN_PATTERN.findall(text))
        if self.llm_extractor:
            try: candidates.extend(self.llm_extractor(text))
            except Exception: pass
        skills = list(dict.fromkeys(self.normalize(item) for item in candidates if self.normalize(item)))
        known = set(self.aliases.values())
        dynamic = [item for item in skills if item not in known]
        experience_match = re.search(r"(\d+(?:-\d+)?)\s*年(?:以上)?经验", text)
        return {"hard_skills": skills, "dynamic_skills": dynamic, "education": next((item for item in ("博士", "硕士", "本科", "大专") if item in text), ""), "experience": experience_match.group(1) if experience_match else "", "soft_skills": [item for item in ("沟通", "协作", "责任心", "学习能力", "问题分析") if item in text], "project_requirements": [item.strip() for item in re.split(r"[。；;\n]", text) if "项目" in item][:5]}

    def persist_dynamic(self, skills: list[str]) -> None:
        if not skills: return
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[str] = []
        if self.registry_path.exists():
            try: existing = json.loads(self.registry_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): existing = []
        value = sorted(set(existing) | set(skills), key=str.casefold)
        temporary = self.registry_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); temporary.replace(self.registry_path)
