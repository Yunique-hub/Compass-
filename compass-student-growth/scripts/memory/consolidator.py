"""Deterministic duplicate detection without exposing or persisting reasoning traces."""
from __future__ import annotations

import json
from typing import Any


def _key(record: dict[str, Any]) -> tuple[str, str]:
    content = json.dumps(record.get("content"), ensure_ascii=False, sort_keys=True).strip().casefold()
    return str(record.get("memory_type", "")), " ".join(content.split())


def find_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[str]] = {}
    for record in records:
        groups.setdefault(_key(record), []).append(str(record.get("record_id", "")))
    return [{"keep": ids[0], "duplicates": ids[1:]} for ids in groups.values() if len(ids) > 1]


def consolidate(store: Any, user_id: str) -> dict[str, Any]:
    records = store.list(user_id, status="active")
    groups = find_duplicates(records)
    invalidated = 0
    if hasattr(store, "soft_invalidate"):
        for group in groups:
            for record_id in group["duplicates"]:
                invalidated += int(store.soft_invalidate(user_id, record_id, reason=f"duplicate_of:{group['keep']}"))
    return {"groups": groups, "invalidated": invalidated, "original_count": len(records)}
