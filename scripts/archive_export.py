"""成长档案 JSON/Markdown 导出。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from .io_utils import result, run_cli
    from .models import GrowthArchive
except ImportError:
    from io_utils import result, run_cli
    from models import GrowthArchive

MODULE = "archive_export"


def build_archive(data: Mapping[str, Any]) -> GrowthArchive:
    prepared = dict(data)
    prepared.setdefault("archive_version", "1.0.0")
    prepared.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
    known = {name for name in GrowthArchive.__dataclass_fields__ if name != "required_fields"}
    extensions = dict(prepared.get("extensions", {}))
    for key in list(prepared):
        if key not in known:
            extensions[key] = prepared.pop(key)
    prepared["extensions"] = extensions
    return GrowthArchive.from_dict(prepared)


def to_markdown(archive: GrowthArchive) -> str:
    payload = archive.to_dict()
    profile, goal, plan = payload["explicit_profile"], payload["confirmed_goal"], payload["current_plan"]
    return "\n".join([
        "# Compass 成长档案", f"版本：{payload['archive_version']}", f"更新时间：{payload['updated_at']}", "",
        "## 1. 用户明确档案", f"- 称呼：{profile.get('name', '')}", f"- 专业 / 年级：{profile.get('major', '')} / {profile.get('grade', '')}", f"- 每周可投入时间：{profile.get('weekly_hours', '')}",
        "", "## 2. 已确认目标", f"- 主方向 / 备选方向：{goal.get('primary_direction', '')} / {goal.get('backup_direction', '')}", f"- 就业目的地：{goal.get('target_city', '')}", f"- 求职时间：{goal.get('job_search_period', '') or goal.get('graduation_date', '')}",
        "", "## 3. 招聘数据与能力证据", f"- 快照版本：{payload['recruitment_snapshot'].get('snapshot_version', '')}", f"- 能力证据数量：{len(payload['capability_evidence'])}",
        "", "## 4. 当前计划", f"- 本周核心任务数：{len(plan.get('weekly_core_tasks', []))}",
        "", "## 5. 重要事件与成就", f"- 事件数 / 成就数：{len(payload['important_events'])} / {len(payload['achievements'])}",
        "", "## 6. 本轮变更摘要", f"- 新增/更新/删除/待确认：{json.dumps(payload['memory_change_summary'], ensure_ascii=False)}", "",
        "## 机器可读 JSON", "```json", json.dumps(payload, ensure_ascii=False, indent=2), "```", "",
    ])


def export_archive(raw: Mapping[str, Any], *, output: Path | None = None, fmt: str = "json") -> dict[str, Any]:
    archive = build_archive(raw)
    content = json.dumps(archive.to_dict(), ensure_ascii=False, indent=2) + "\n" if fmt == "json" else to_markdown(archive)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    return result(MODULE, {"archive": archive.to_dict(), "format": fmt, "output_path": str(output) if output else "", "content": "" if output else content})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    output = Path(raw["output"]) if raw.get("output") else None
    return export_archive(raw.get("archive", raw), output=output, fmt=str(raw.get("format", "json")))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
