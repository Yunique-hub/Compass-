"""基于显式词典的单份/多份 JD 基线提取器。"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .io_utils import error, result, run_cli
except ImportError:
    from io_utils import error, result, run_cli

MODULE = "jd_analyzer"
ROOT = Path(__file__).resolve().parents[1]


def _terms() -> dict[str, list[str]]:
    raw = json.loads((ROOT / "reference" / "job_roles" / "skill_aliases.json").read_text(encoding="utf-8"))
    return {canonical: [canonical, *aliases] for canonical, aliases in raw.items()}


def analyze_jd(text: str, jd_id: str = "jd-1") -> dict[str, Any]:
    if len(text.strip()) < 30:
        return {"jd_id": jd_id, "status": "needs_confirmation", "hard_skills": [], "tools_frameworks": [], "experience": [], "education": [], "major_requirements": [], "project_requirements": [], "soft_skills": [], "bonus_items": [], "evidence": [], "warning": "JD 过短或模糊，请提供完整原文。"}
    found: list[str] = []
    evidence: list[dict[str, Any]] = []
    lowered = text.casefold()
    for canonical, aliases in _terms().items():
        for alias in aliases:
            start = lowered.find(alias.casefold())
            if start >= 0:
                found.append(canonical)
                evidence.append({"field": "hard_skills", "value": canonical, "start": start, "end": start + len(alias), "excerpt": text[max(0, start - 12): start + len(alias) + 12]})
                break
    experience = re.findall(r"(?:至少|具有|具备)?\s*(\d+)[—\-~至]?\d*\s*年(?:以上)?(?:工作|开发)?经验", text)
    education = [item for item in ("大专", "本科", "硕士", "博士") if item in text]
    majors = re.findall(r"([\u4e00-\u9fff]{2,12}(?:专业|类专业))(?:优先|相关|毕业)?", text)
    projects = [sentence.strip() for sentence in re.split(r"[。；;\n]", text) if "项目" in sentence][:5]
    soft = [item for item in ("沟通", "协作", "责任心", "学习能力", "问题分析") if item in text]
    bonus = [sentence.strip() for sentence in re.split(r"[。；;\n]", text) if any(word in sentence for word in ("优先", "加分"))][:5]
    frameworks = [item for item in found if item in {"Spring Boot", "Spring Cloud", "MyBatis", "Redis", "MySQL", "Docker", "Git", "Pytest"}]
    return {"jd_id": jd_id, "status": "parsed", "hard_skills": sorted(set(found)), "tools_frameworks": frameworks, "experience": experience, "education": education, "major_requirements": majors, "project_requirements": projects, "soft_skills": soft, "bonus_items": bonus, "evidence": evidence}


def analyze_multiple(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    analyses = [analyze_jd(str(item.get("text", "")), str(item.get("jd_id", f"jd-{index + 1}"))) for index, item in enumerate(items)]
    traces: dict[str, list[str]] = defaultdict(list)
    valid = [item for item in analyses if item["status"] == "parsed"]
    for item in valid:
        for skill in item["hard_skills"]:
            traces[skill].append(item["jd_id"])
    count = len(valid)
    stats = {skill: {"frequency": round(len(ids) / count, 4), "jd_ids": ids} for skill, ids in sorted(traces.items())} if count else {}
    warnings = [error("JD_NEEDS_CONFIRMATION", item["warning"], jd_id=item["jd_id"]) for item in analyses if item["status"] != "parsed"]
    return result(MODULE, {"input_count": len(items), "valid_count": count, "analyses": analyses, "skill_statistics": stats, "notice": "统计仅基于本次实际输入的 JD。"}, warnings=warnings)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    items = raw.get("jds") or [{"jd_id": raw.get("jd_id", "jd-1"), "text": raw.get("text", "")}]
    return analyze_multiple(items)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
