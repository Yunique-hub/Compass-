"""Growth Archive migration and atomic persistence."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

VERSION = "2.5.1"


def empty_archive(user_id: str = "") -> dict[str, Any]:
    return {
        "archive_version": VERSION,
        "user_id": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "preferred_name": "",
        "preferred_name_usage": True,
        "onboarding_complete": False,
        "current_growth_stage": "",
        "profile_sufficiency": {},
        "realistic_capacity": {},
        "question_history": {"asked_fields": [], "question_only_streak": 0},
        "planning_confidence": "low",
        "last_action": "",
        "next_expected_update": [],
        "known_facts": {},
        "profile": {},
        "profile_state": {},
        "business_state": {},
        "career": {"directions": [], "confirmed_goal": {}, "capability_evidence": [], "recruitment_snapshot": {}, "skill_graph": []},
        "academic": {"courses": {}, "capacity": {}, "current_plan": {}},
        "exam": {"knowledge_points": [], "mistakes": [], "review_history": []},
        "learning_strategy": {"patterns": [], "strategies": [], "trials": []},
        "important_events": [],
        "achievements": [],
        "pending_confirmations": [],
        "memory_change_summary": {},
        "extensions": {},
    }


def migrate_archive(raw: Mapping[str, Any] | None, *, user_id: str = "") -> dict[str, Any]:
    if not raw:
        return empty_archive(user_id)
    source = copy.deepcopy(dict(raw))
    if str(source.get("archive_version", "1.0.0")).startswith("2."):
        archive = empty_archive(str(source.get("user_id") or user_id))
        for key, value in source.items():
            if key in archive:
                archive[key] = value
            else:
                archive["extensions"][key] = value
        archive["archive_version"] = VERSION
        return archive
    archive = empty_archive(user_id or str(source.get("user_id", "")))
    archive["profile"] = source.get("explicit_profile", source.get("profile", {}))
    archive["career"] = {
        "directions": source.get("career_directions", []),
        "confirmed_goal": source.get("confirmed_goal", {}),
        "capability_evidence": source.get("capability_evidence", []),
        "recruitment_snapshot": source.get("recruitment_snapshot", {}),
        "skill_graph": source.get("skill_graph", []),
    }
    archive["academic"]["current_plan"] = source.get("current_plan", {})
    archive["important_events"] = source.get("important_events", [])
    archive["achievements"] = source.get("achievements", [])
    archive["pending_confirmations"] = source.get("pending_confirmations", [])
    archive["memory_change_summary"] = source.get("memory_change_summary", {})
    archive["extensions"] = source.get("extensions", {})
    known_v1 = {
        "archive_version", "user_id", "updated_at", "explicit_profile", "profile",
        "career_directions", "confirmed_goal", "capability_evidence",
        "recruitment_snapshot", "skill_graph", "current_plan",
        "important_events", "achievements", "pending_confirmations",
        "memory_change_summary", "extensions",
    }
    for key, value in source.items():
        if key not in known_v1:
            archive["extensions"][key] = value
    archive["extensions"]["migrated_from"] = str(source.get("archive_version", "1.0.0"))
    return archive


def load_archive(path: str | Path, *, user_id: str = "") -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return empty_archive(user_id)
    try:
        return migrate_archive(json.loads(source.read_text(encoding="utf-8")), user_id=user_id)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"成长档案损坏或不可读，原文件未被覆盖：{exc}") from exc


def synchronize_archive_states(archive: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(archive))
    value["profile_state"] = {
        "profile": copy.deepcopy(value.get("profile", {})),
        "known_facts": copy.deepcopy(value.get("known_facts", {})),
        "preferred_name": value.get("preferred_name", ""),
        "preferred_name_usage": value.get("preferred_name_usage", True),
    }
    value["business_state"] = {
        "career": copy.deepcopy(value.get("career", {})),
        "academic": copy.deepcopy(value.get("academic", {})),
        "exam": copy.deepcopy(value.get("exam", {})),
        "learning_strategy": copy.deepcopy(value.get("learning_strategy", {})),
        "current_growth_stage": value.get("current_growth_stage", ""),
    }
    return value


def save_archive(path: str | Path, archive: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    value = migrate_archive(archive, user_id=str(archive.get("user_id", "")))
    value = synchronize_archive_states(value)
    value["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
