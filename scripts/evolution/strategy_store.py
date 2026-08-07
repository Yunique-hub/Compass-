"""Runtime-only strategy storage with immutable project boundaries."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTECTED_NAMES = {"skill.md", "manifest.yaml", "manifest.yml", "manifest.json", "third_party_notices.md", "license", "licenses", "scripts", "config", "vendor", ".git"}


class StrategyStore:
    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "strategies.json"
        if not self.path.exists():
            self.path.write_text('{"strategies":[],"trials":[]}\n', encoding="utf-8")

    def assert_runtime_path(self, target: str | Path) -> Path:
        resolved = Path(target).resolve()
        if self.root != resolved and self.root not in resolved.parents:
            raise PermissionError("EVOLUTION_WRITE_OUTSIDE_RUNTIME")
        if any(part.casefold() in PROTECTED_NAMES for part in resolved.parts):
            raise PermissionError("EVOLUTION_PROTECTED_PATH")
        return resolved

    def load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self.assert_runtime_path(self.path)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def add_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        item = {"strategy_id": str(uuid.uuid4()), "status": "candidate", "created_at": datetime.now(timezone.utc).isoformat(), **candidate}
        data["strategies"].append(item)
        self.save(data)
        return item
