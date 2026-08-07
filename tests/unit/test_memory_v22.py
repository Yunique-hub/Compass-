from pathlib import Path

from scripts.memory.memory_engine import MemoryEngine


def test_structured_memory_restores_across_engine_instances_and_versions_goal(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite3"
    first = MemoryEngine(path)
    first.persist_turn(
        user_id="u",
        profile_updates={"preferred_name": "小宇", "major": "计算机网络技术", "weekly_available_hours": 12},
        goal_updates={"target_city": "杭州", "target_job_raw": "IT支持", "target_job_normalized": "IT支持"},
        growth_updates={"current_skill": "Active Directory", "completed_tasks": ["Domain Creation"], "next_task": "User / Group / GPO"},
    )
    second = MemoryEngine(path)
    restored = second.load_user_context(user_id="u", query="继续")
    assert restored["profile"]["preferred_name"] == "小宇"
    assert restored["goal"]["target_city"] == "杭州"
    assert restored["growth_state"]["completed_tasks"] == ["Domain Creation"]
    second.persist_turn(user_id="u", goal_updates={"target_city": "上海"})
    assert second.load_user_context(user_id="u")["goal"]["target_city"] == "上海"
    history = second.persistent.structured.history("u", field="target_city")
    assert history[-1]["old"] == "杭州" and history[-1]["new"] == "上海"


def test_structured_memory_never_persists_hidden_reasoning_and_neo4j_is_optional(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path / "memory.sqlite3")
    engine.persist_turn(user_id="u", semantic_candidates=[{"memory_type": "decision", "importance": 0.9, "content": {"outcome": "use snapshot", "chain_of_thought": "private"}}])
    restored = engine.load_user_context(user_id="u", query="snapshot")
    assert "chain_of_thought" not in str(restored["semantic_memory"])
    health = engine.health()
    assert health["structured"]["available"] is True
    assert health["degraded_ok"] is True
