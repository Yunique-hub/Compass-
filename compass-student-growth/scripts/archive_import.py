"""成长档案导入、版本升级和显式冲突报告。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

try:
    from .archive_export import build_archive
    from .io_utils import error, result, run_cli
except ImportError:
    from archive_export import build_archive
    from io_utils import error, result, run_cli

MODULE = "archive_import"


def parse_content(content: str, fmt: str | None = None) -> dict[str, Any]:
    detected = fmt or ("json" if content.lstrip().startswith("{") else "markdown")
    if detected == "json":
        value = json.loads(content)
    else:
        match = re.search(r"```json\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
        if not match:
            raise ValueError("Markdown 档案缺少机器可读 JSON 区块，未覆盖原文件。")
        value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("档案根节点必须是 JSON 对象")
    return value


def merge_archives(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    merged = dict(existing)
    conflicts: list[dict[str, Any]] = []
    for key, value in incoming.items():
        if key in merged and merged[key] not in (None, "", [], {}) and value not in (None, "", [], {}) and merged[key] != value:
            conflicts.append({"field": key, "existing": merged[key], "incoming": value, "action": "needs_confirmation"})
            continue
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged, conflicts


def import_archive(raw: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("path"):
        content = Path(str(raw["path"])).read_text(encoding="utf-8")
    else:
        content = str(raw.get("content", ""))
    incoming = parse_content(content, raw.get("format"))
    merged, conflicts = merge_archives(raw.get("existing", {}), incoming)
    archive = build_archive(merged)
    warnings = [error("ARCHIVE_CONFLICT", "冲突字段未静默覆盖，需要用户确认。", conflicts=conflicts)] if conflicts else []
    return result(MODULE, {"archive": archive.to_dict(), "summary": {"added_or_preserved": sorted(merged), "updated": [], "deleted": [], "needs_confirmation": conflicts}, "upgraded_to": "1.0.0"}, warnings=warnings)


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return import_archive(raw)


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
