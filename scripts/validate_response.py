#!/usr/bin/env python3
"""Detect internal reasoning and unsupported capability claims in final responses."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PATTERNS = {
    "think_tag": re.compile(r"</?think(?:ing)?>", re.IGNORECASE),
    "internal_english": re.compile(
        r"\b(?:I need to|Now I have|Let me (?:think|analyze)|The user (?:is asking|wants|needs)|The skill isn't available)\b",
        re.IGNORECASE,
    ),
    "internal_chinese": re.compile(r"(?:让我(?:先)?(?:分析|思考)|我需要先(?:分析|判断))"),
    "internal_path": re.compile(r"(?:/mnt/skills|/app/backend/\.easyclaw|/mnt/user-data)(?:/|\b)", re.IGNORECASE),
}


def load_input(argument: str | None) -> dict[str, Any]:
    raw = Path(argument).read_text(encoding="utf-8") if argument and argument != "-" else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def validate(data: dict[str, Any]) -> dict[str, Any]:
    text = data.get("text")
    if not isinstance(text, str):
        return {"safe": False, "errors": ["text must be a string"], "matches": []}
    matches: list[dict[str, str]] = []
    for rule, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append({"rule": rule, "text": match.group(0)[:120]})
    lowered = text.lower()
    if data.get("skill_loaded") is not True and ("已加载" in text or "已使用 compass" in lowered):
        matches.append({"rule": "false_skill_loaded_claim", "text": "skill_loaded=false"})
    if data.get("memory_written") is not True and ("永久记住" in text or "已经记住" in text):
        matches.append({"rule": "false_memory_claim", "text": "memory_written=false"})
    if data.get("research_validated") is not True and ("已核验最新" in text or "已经核验最新" in text):
        matches.append({"rule": "false_research_claim", "text": "research_validated=false"})
    return {"safe": not matches, "errors": sorted({item["rule"] for item in matches}), "matches": matches}


def main() -> int:
    try:
        result = validate(load_input(sys.argv[1] if len(sys.argv) > 1 else None))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"safe": False, "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["safe"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
