from __future__ import annotations

from pathlib import Path

import pytest

from scripts.evolution.evolution_engine import EvolutionEngine
from scripts.improvement.improvement_engine import ImprovementEngine
from scripts.memory.memory_engine import MemoryEngine
from scripts.proactive.proactive_engine import ProactiveEngine
from scripts.research.browser_policy import validate_command, validate_public_url
from scripts.review.review_engine import ReviewEngine


def test_review_brain_prioritizes_exam_and_separates_answers(tmp_path: Path) -> None:
    exam = tmp_path / "历年真题.txt"
    notes = tmp_path / "课堂笔记.txt"
    exam.write_text("进程与线程\n死锁的四个条件\n", encoding="utf-8")
    notes.write_text("进程与线程\n虚拟内存\n", encoding="utf-8")
    output = ReviewEngine().build(course="操作系统", material_paths=[notes, exam])
    assert output["materials"][0]["source_type"] == "past_exam"
    assert output["questions"] and output["answers"]
    assert "must_include" not in output["questions"][0]
    assert output["answers"][0]["question_id"] == output["questions"][0]["question_id"]


def _candidate(user_id: str, candidate_id: str, content: object) -> dict:
    return {
        "candidate_id": candidate_id,
        "record_id": candidate_id,
        "user_id": user_id,
        "memory_type": "confirmed_goal",
        "content": content,
        "importance": 1,
        "stability": 1,
        "future_relevance": 1,
        "user_explicitness": 1,
        "recurrence": 1,
        "confidence": 1,
        "task_value": 1,
        "user_intent": "remember",
    }


def test_memory_isolates_users_sanitizes_trace_and_forgets(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / "memory.db")
    content = {"goal": "Python 后端", "chain_of_thought": "不得保存"}
    written = engine.write(user_id="u1", candidate=_candidate("u1", "m1", content))
    assert written["stored"] is True
    assert "chain_of_thought" not in written["record"]["content"]
    assert engine.load(user_id="u2", query="Python")["data"]["count"] == 0
    with pytest.raises(PermissionError):
        engine.write(user_id="u2", candidate=_candidate("u1", "m2", "wrong user"))
    assert engine.forget(user_id="u1")["removed"] == 1


def test_improvement_requires_recurrence_across_tasks(tmp_path: Path) -> None:
    engine = ImprovementEngine(tmp_path)
    assert engine.observe(user_id="u", task_id="t1", category="plan", signal="任务太大")["suggestion"] is None
    assert engine.observe(user_id="u", task_id="t1", category="plan", signal="任务太大")["suggestion"] is None
    output = engine.observe(user_id="u", task_id="t2", category="plan", signal="任务太大")
    assert output["pattern"]["promoted"] is True
    assert output["suggestion"]["auto_apply"] is False


def test_evolution_trials_and_runtime_boundary(tmp_path: Path) -> None:
    engine = EvolutionEngine(tmp_path / "runtime-strategies")
    strategy = engine.propose(gene="smaller_tasks", capsule={"max_minutes": 30}, evidence=["pattern-1"])
    engine.start_trial(strategy["strategy_id"], metric="completion", baseline=0.5)
    assert engine.finish_trial(strategy["strategy_id"], result=0.4)["status"] == "rolled_back"
    with pytest.raises(PermissionError):
        engine.store.assert_runtime_path(tmp_path / "SKILL.md")


def test_research_policy_is_public_https_and_read_only() -> None:
    assert validate_public_url("https://example.com/course", {"example.com"}) == "example.com"
    validate_command("get text body")
    with pytest.raises(PermissionError):
        validate_public_url("http://localhost/private")
    with pytest.raises(PermissionError):
        validate_command("click button")


def test_proactive_is_in_session_and_has_cooldown() -> None:
    engine = ProactiveEngine(cooldown_hours=24)
    prompt = engine.check(signals={"exam_days": 3})
    assert prompt["should_prompt"] is True
    assert prompt["background_push"] is False
    assert engine.check(signals={"exam_days": 3}, last_prompt_at=prompt["prompted_at"])["reason"] == "cooldown"
    assert engine.feedback(prompt, "accepted")["response"] == "accepted"
