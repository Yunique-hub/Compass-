import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_validator(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN = load_validator("validate_plan")
RESEARCH = load_validator("validate_research")
RESPONSE = load_validator("validate_response")


def test_valid_plan_and_stress_recommendation():
    result = PLAN.validate({
        "weekly_hours": 8,
        "buffer_hours": 3,
        "tasks": [{"id": "recover", "hours": 4, "kind": "core"}],
        "optional_tasks": [],
        "stress": {"consecutive_incomplete_weeks": 2, "fatigue": True},
    })
    assert result["valid"] is True
    assert result["stress_recommendation"]["min_core_hours"] == 4
    assert result["stress_recommendation"]["max_core_hours"] == 5.5


def test_plan_blocks_duplicate_overload_and_optional_hours():
    result = PLAN.validate({
        "weekly_hours": 10,
        "buffer_hours": 2,
        "tasks": [{"id": "exam", "hours": 6}, {"id": "exam", "hours": 3}],
        "optional_tasks": [{"id": "project", "hours": 1}],
    })
    assert result["valid"] is False
    text = "\n".join(result["errors"])
    assert "duplicate task id" in text
    assert "exceeds weekly capacity" in text
    assert "must have 0 allocated hours" in text
    assert result["summary"]["allocated_total"] == 12


@pytest.mark.parametrize("bad_date", ["2026-02-29", "2026-13-01", "not-a-date"])
def test_research_blocks_invalid_dates(bad_date):
    result = RESEARCH.validate({"claims": [{
        "text": "market claim",
        "time_sensitive": True,
        "claim_kind": "market_summary",
        "region": "Hangzhou",
        "role_scope": "Python backend",
        "sample_count": 1,
        "collection_start": bad_date,
        "collection_end": "2026-08-10",
        "source_urls": ["https://example.com/job/1"],
        "limitations": ["sample limited"],
    }]})
    assert result["publishable"] is False


def test_research_blocks_reversed_range_and_duplicate_sources():
    result = RESEARCH.validate({"claims": [{
        "text": "market claim",
        "time_sensitive": True,
        "claim_kind": "market_summary",
        "region": "Hangzhou",
        "role_scope": "Python backend",
        "sample_count": 2,
        "collection_start": "2026-08-11",
        "collection_end": "2026-08-10",
        "source_urls": ["https://example.com/job/1", "https://example.com/job/1"],
        "limitations": ["sample limited"],
    }]})
    assert result["publishable"] is False
    text = "\n".join(result["errors"])
    assert "must not be after" in text
    assert "must be deduplicated" in text


def test_response_blocks_internal_and_false_claims():
    result = RESPONSE.validate({
        "text": "<think>Now I have context. 让我分析 /mnt/skills. 已使用 Compass，已经记住，已核验最新信息。</think>",
        "skill_loaded": False,
        "memory_written": False,
        "research_validated": False,
    })
    assert result["safe"] is False
    assert {
        "think_tag",
        "internal_english",
        "internal_chinese",
        "internal_path",
        "false_skill_loaded_claim",
        "false_memory_claim",
        "false_research_claim",
    }.issubset(set(result["errors"]))


def test_cli_stdout_is_single_json_document(tmp_path):
    payload = tmp_path / "plan.json"
    payload.write_text(json.dumps({
        "weekly_hours": 2,
        "buffer_hours": 0.5,
        "tasks": [{"id": "task", "hours": 1.5}],
        "optional_tasks": [],
    }), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_plan.py"), str(payload)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout)["valid"] is True
