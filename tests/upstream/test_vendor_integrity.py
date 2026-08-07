from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
pytest_plugins: list[str] = []

import pytest

if not (ROOT / "vendor").is_dir():
    pytest.skip("skill package intentionally excludes vendor", allow_module_level=True)


def test_all_locked_upstreams_are_preserved_without_nested_git() -> None:
    lock = json.loads((ROOT / "reference/open_source/upstream-lock.json").read_text(encoding="utf-8"))
    assert len(lock["projects"]) == 6
    for name, expected in lock["projects"].items():
        vendor = ROOT / "vendor" / name
        marker = json.loads((vendor / ".upstream-source.json").read_text(encoding="utf-8"))
        assert marker["repository"] == expected["repository"]
        assert marker["branch"] == expected["branch"]
        assert marker["commit"] == expected["commit"]
        assert len(marker["tree_sha256"]) == 64
        assert not (vendor / ".git").exists()


def test_notices_and_license_or_authorization_are_present() -> None:
    notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for name in ("final-review", "agent-memory", "self-improving-agent", "agent-browser", "capability-evolver", "ProactiveAgent"):
        assert name.casefold() in notice.casefold()
    for directory in (ROOT / "licenses").iterdir():
        assert directory.is_dir()
        assert any(path.is_file() for path in directory.rglob("*"))
