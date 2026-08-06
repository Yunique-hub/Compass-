from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.archive_export import build_archive, to_markdown
from scripts.archive_import import import_archive, merge_archives, parse_content
from scripts.conflict_resolver import resolve_conflicts
from scripts.memory_classifier import validate_candidates
from scripts.memory_policy import calculate_memory_score, route_memory
from scripts.memory_retriever import retrieve
from scripts.memory_store import FileMemoryStore, SQLiteMemoryStore, UnavailableVectorStore, forget_everywhere
from scripts.models import MemoryCandidate
from scripts.safety_router import route_safety

ROOT = Path(__file__).resolve().parents[2]


def candidate(**overrides):
    data = {"candidate_id": "m1", "user_id": "u1", "memory_type": "learning_preference", "content": "喜欢项目学习", "importance": 0.8, "stability": 0.8, "future_relevance": 0.8, "user_explicitness": 0.8, "recurrence": 0.8, "confidence": 0.8, "task_value": 0.8}
    data.update(overrides)
    return data


def test_archive_json_markdown_roundtrip_and_unknown_extension() -> None:
    archive = build_archive({"updated_at": "2026-08-06T00:00:00+00:00", "explicit_profile": {"user_id": "u", "name": "小明"}, "confirmed_goal": {"primary_direction": "java-backend"}, "custom_future": 7})
    markdown = to_markdown(archive)
    restored = parse_content(markdown)
    assert restored["explicit_profile"]["name"] == "小明"
    assert restored["extensions"]["custom_future"] == 7


def test_archive_import_preserves_explicit_fields() -> None:
    raw = build_archive({"updated_at": "2026-08-06", "explicit_profile": {"user_id": "u", "major": "计算机"}, "confirmed_goal": {"target_city": "杭州"}}).to_dict()
    output = import_archive({"content": json.dumps(raw, ensure_ascii=False)})
    assert output["data"]["archive"]["explicit_profile"] == raw["explicit_profile"]
    assert output["data"]["archive"]["confirmed_goal"] == raw["confirmed_goal"]


def test_archive_conflict_not_silently_overwritten() -> None:
    merged, conflicts = merge_archives({"confirmed_goal": {"target_city": "杭州"}}, {"confirmed_goal": {"target_city": "上海"}})
    assert merged["confirmed_goal"]["target_city"] == "杭州"
    assert conflicts[0]["action"] == "needs_confirmation"


def test_memory_score_and_routing_thresholds() -> None:
    c = MemoryCandidate.from_dict(candidate())
    score, parts = calculate_memory_score(c, {"future_relevance": 0.5, "stability": 0.5})
    assert score == pytest.approx(0.8) and parts["stability"] == 0.8
    assert route_memory(candidate())["data"]["action"] == "long_term_vector"
    low_confidence = candidate(future_relevance=0.1, stability=0.1, user_explicitness=0.1, recurrence=0.1, confidence=0.1, task_value=0.1)
    assert route_memory(low_confidence)["data"]["action"] == "needs_confirmation"
    low_score = candidate(future_relevance=0.1, stability=0.1, user_explicitness=0.1, recurrence=0.1, confidence=0.8, task_value=0.1)
    assert route_memory(low_score)["data"]["action"] == "ignore"


def test_memory_intent_and_sensitive_rules_override_score() -> None:
    assert route_memory(candidate(user_intent="不要记住"))["data"]["action"] == "ignore"
    assert route_memory(candidate(user_intent="忘记"))["data"]["action"] == "delete"
    assert route_memory(candidate(sensitivity="health"))["data"]["action"] == "needs_confirmation"
    assert route_memory(candidate(memory_type="candidate_direction"))["data"]["action"] == "temp"


def test_classifier_allows_zero_and_marks_sensitive() -> None:
    assert validate_candidates([], "u")["data"]["count"] == 0
    output = validate_candidates([candidate(content="我的精确住址", user_id="wrong")], "u")
    item = output["data"]["candidates"][0]
    assert item["user_id"] == "u" and item["sensitivity"] == "high" and item["requires_confirmation"] is True


@pytest.mark.parametrize("store_type", ["file", "sqlite"])
def test_memory_backends_crud_isolation_and_forget(tmp_path: Path, store_type: str) -> None:
    store = FileMemoryStore(tmp_path / "memory.json") if store_type == "file" else SQLiteMemoryStore(tmp_path / "memory.sqlite3")
    store.upsert("u1", candidate())
    store.upsert("u2", candidate(candidate_id="m2", user_id="u2", content="另一个用户"))
    assert len(store.list("u1")) == 1 and len(store.list("u2")) == 1
    assert store.get("u2", "m1") is None
    cache = {"u1:q": 1, "u2:q": 2}
    summary = forget_everywhere("u1", store, vector_store=UnavailableVectorStore(), cache=cache)
    assert summary["structured_records"] == 1
    assert store.list("u1") == [] and len(store.list("u2")) == 1
    assert "u1:q" not in cache and "u2:q" in cache
    assert all("content" not in event for event in store.audit("u1"))


def test_cross_user_upsert_rejected(tmp_path: Path) -> None:
    store = FileMemoryStore(tmp_path / "m.json")
    with pytest.raises(PermissionError):
        store.upsert("u1", candidate(user_id="u2"))


def test_vector_unavailable_falls_back_without_cross_user(tmp_path: Path) -> None:
    store = FileMemoryStore(tmp_path / "m.json")
    store.upsert("u1", candidate(content="喜欢 Java 项目"))
    store.upsert("u2", candidate(candidate_id="m2", user_id="u2", content="Java 私密历史"))
    output = retrieve(store, "u1", "Java", vector_store=UnavailableVectorStore())
    assert output["warnings"][0]["code"] == "VECTOR_STORE_UNAVAILABLE"
    assert all(item["record"]["user_id"] == "u1" for item in output["data"]["results"])


def test_conflict_requires_confirmation_and_merges_preferences() -> None:
    output = resolve_conflicts({"target_city": "杭州", "learning_preferences": ["项目"]}, {"target_city": "上海", "learning_preferences": ["项目", "视频"]}, user_explicit=True)
    assert output["data"]["merged"]["target_city"] == "杭州"
    assert output["data"]["needs_confirmation"][0]["field"] == "target_city"
    assert output["data"]["merged"]["learning_preferences"] == ["项目", "视频"]
    assert "current_plan" in output["data"]["invalidated"]


def test_safety_routes() -> None:
    assert route_safety("今天状态正常")["data"]["type"] == "normal"
    stress = route_safety("最近压力大，完全学不动")
    assert stress["data"]["type"] == "stress" and stress["data"]["task_load_factor"] == 0.5
    risk = route_safety("我不想活了")
    assert risk["data"]["type"] == "high_risk" and risk["data"]["stop_learning_plan"] is True
    assert route_safety("请诊断我并开药")["data"]["type"] == "out_of_scope"


def test_cli_stdout_stderr_contract() -> None:
    ok = subprocess.run([sys.executable, "scripts/jd_analyzer.py"], input=json.dumps({"text": "短"}), text=True, capture_output=True, cwd=ROOT)
    assert json.loads(ok.stdout)["meta"]["module"] == "jd_analyzer"
    assert ok.stderr == ""
    bad = subprocess.run([sys.executable, "scripts/jd_analyzer.py"], input="not-json", text=True, capture_output=True, cwd=ROOT)
    assert json.loads(bad.stdout)["ok"] is False
    assert "jd_analyzer" in bad.stderr
