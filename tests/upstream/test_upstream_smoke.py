from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "vendor").is_dir():
    pytest.skip("skill package intentionally excludes vendor", allow_module_level=True)
def test_final_review_rule_source_is_present() -> None:
    skill = (ROOT / "vendor/final-review/SKILL.md").read_text(encoding="utf-8")
    assert "Past exams" in skill or "past exam" in skill.casefold() or "真题" in skill


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_self_improving_upstream_hook_suite() -> None:
    path = ROOT / "vendor/self-improving-agent/self-improving-agent/hooks/openclaw/handler.test.js"
    completed = subprocess.run([shutil.which("node") or "node", "--test", str(path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "13" in completed.stdout


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_capability_evolver_selector_suite() -> None:
    path = ROOT / "vendor/capability-evolver/test/selector.test.js"
    completed = subprocess.run([shutil.which("node") or "node", "--test", str(path)], cwd=ROOT / "vendor/capability-evolver", capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "8" in completed.stdout


def test_agent_memory_package_imports_when_optional_dependency_installed() -> None:
    module = pytest.importorskip("neo4j_agent_memory")
    assert module is not None


def test_proactive_agent_datamodel_imports_without_desktop_runtime() -> None:
    vendor = str(ROOT / "vendor/proactive-agent")
    sys.path.insert(0, vendor)
    try:
        module = importlib.import_module("agent.datamodel")
        assert module is not None
    finally:
        sys.path.remove(vendor)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_agent_browser_cli_version() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    cli = ROOT / "node_modules/agent-browser/bin/agent-browser.js"
    if not cli.is_file():
        pytest.skip("agent-browser dependencies not installed")
    completed = subprocess.run([shutil.which("node") or "node", str(cli), "--version"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert package["dependencies"]["agent-browser"] in completed.stdout
