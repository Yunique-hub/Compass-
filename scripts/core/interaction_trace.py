"""Development-only interaction trace; never included in the user response."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def write_interaction_trace(runtime_dir: str | Path, payload: Mapping[str, Any]) -> Path:
    path = Path(runtime_dir) / "debug" / "interaction_trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {
        "time": datetime.now(timezone.utc).isoformat(),
        "state": payload.get("state"),
        "known_facts": payload.get("known_facts", {}),
        "missing_fields": payload.get("missing_fields", []),
        "sufficiency": payload.get("sufficiency", {}),
        "action_selected": payload.get("action_selected"),
        "questions_asked": payload.get("questions_asked", []),
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(safe, ensure_ascii=False) + "\n")
    return path
