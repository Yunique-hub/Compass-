from pathlib import Path

from scripts.compass_engine import CompassEngine
from scripts.integrations.agent_browser_adapter import AgentBrowserAdapter
from scripts.integrations.capability_evolver_adapter import CapabilityEvolverAdapter
from scripts.integrations.neo4j_memory_adapter import Neo4jMemoryAdapter
from scripts.integrations.proactive_agent_adapter import ProactiveAgentAdapter
from scripts.integrations.self_improving_adapter import SelfImprovingAdapter


class FakeNeo4j:
    def verify_connectivity(self) -> None: pass
    def execute_query(self, query: str, **params: object): return ([], None, None)


def test_five_adapter_contracts_have_real_inputs_and_outputs(tmp_path: Path) -> None:
    neo = Neo4jMemoryAdapter(FakeNeo4j())
    assert neo.health()["available"] and neo.upsert_entity({"record_id": "g", "user_id": "u", "memory_type": "goal", "content": {"target_city": "杭州"}})["stored"]
    assert AgentBrowserAdapter(reader=lambda command: "public jd").read_public_page("https://example.com/job")["content"] == "public jd"
    improvement = SelfImprovingAdapter(str(tmp_path / "improvement"))
    for task in ("t1", "t2"):
        improvement.record({"event_type": "correction", "pattern_key": "plan.overload", "summary": "任务太多", "area": "plan", "user_id": "u", "task_id": task})
    promoted = improvement.record({"event_type": "correction", "pattern_key": "plan.overload", "summary": "任务太多", "area": "plan", "user_id": "u", "task_id": "t3"})["pattern"]
    evolver = CapabilityEvolverAdapter(str(tmp_path / "evolution"))
    candidate = evolver.propose_from_pattern(promoted)
    assert candidate and candidate["allow_self_modify"] is False
    evolver.start_trial(candidate["strategy_id"], metric="completion_rate", baseline=0.4)
    assert evolver.finish_trial(candidate["strategy_id"], result=0.7)["status"] == "accepted"
    proactive = ProactiveAgentAdapter()
    prompt = proactive.check({"completion_rate": 0.3})
    assert prompt["should_prompt"] and prompt["background_push"] is False
    assert proactive.feedback(prompt, "rejected")["response"] == "rejected"


def test_engine_cross_session_market_tutor_assessment_and_memory(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"; user_id = "xiaoyu"; engine = CompassEngine(runtime)
    engine.run({"user_id": user_id, "message": "你好"})
    engine.run({"user_id": user_id, "message": "叫我小宇"})
    jds = [{"job_id": f"j{i}", "title": "IT支持", "city": "杭州", "text": f"本科岗位，要求 Active Directory、Windows Server、PowerShell、网络排障与用户支持，完成实验项目并记录故障。样本{i}", "synthetic": True} for i in range(5)]
    market_turn = engine.run({"user_id": user_id, "message": "我是计算机网络技术专业大二，明年实习，目标城市杭州，想做IT支持工作，每周学习10小时。", "jds": jds})["data"]
    cycle = market_turn["archive"]["extensions"]["growth_cycle"]
    assert cycle["market"]["market_data_status"] == "insufficient" and cycle["market"]["synthetic"]
    assert cycle["plan"]["weekly_core_tasks"] and not cycle["plan"]["formal_plan_generated"]
    started = engine.run({"user_id": user_id, "message": "现在开始学习 Active Directory。"})["data"]
    assert started["response"]["details"]["business"]["tutor"]["action"] == "START_TUTOR"
    criteria = started["response"]["details"]["business"]["tutor"]["exercise"]["acceptance_criteria"]
    assessed = engine.run({"user_id": user_id, "message": "提交练习", "submission": {"criteria_met": criteria}, "actual_hours": 2})["data"]
    assert assessed["response"]["details"]["business"]["assessment"]["replanned"] is True
    reopened = CompassEngine(runtime)
    resumed = reopened.run({"user_id": user_id, "message": "继续学习"})["data"]
    restored = reopened.growth.compact_context(__import__("scripts.memory.memory_engine", fromlist=["MemoryEngine"]).MemoryEngine(reopened._paths(user_id)[1]).load_user_context(user_id=user_id))
    assert resumed["response"]["details"]["business"]["tutor"]["action"] == "CONTINUE_TUTOR"
    assert restored["profile"]["preferred_name"] == "小宇" and restored["competency"]
    prompted = reopened.run({"user_id": user_id, "message": "继续上次", "completion_rate": 0.3})["data"]
    assert prompted["response"]["details"]["proactive"]["should_prompt"] and "主动建议" in prompted["text"]
    rejected = reopened.run({"user_id": user_id, "message": "先不用", "proactive_feedback": "rejected"})["data"]
    assert rejected["response"]["details"]["business"]["proactive_feedback"]["response"] == "rejected"
    assert rejected["response"]["details"]["business"]["proactive_improvement"]["event"]["event_type"] == "correction"
