"""Five-Brain integration debug view using observable, offline evidence."""
from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in {None, ""}: sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.evolution.evolution_engine import EvolutionEngine
from scripts.improvement.improvement_engine import ImprovementEngine
from scripts.integrations.agent_browser_adapter import AgentBrowserAdapter
from scripts.memory.memory_engine import MemoryEngine
from scripts.proactive.proactive_engine import ProactiveEngine
from scripts.recruitment.agent_browser_provider import AgentBrowserProvider
from scripts.recruitment.recruitment_engine import RecruitmentEngine


def main() -> int:
    with TemporaryDirectory(prefix="compass-five-brain-") as runtime:
        root = Path(runtime); memory = MemoryEngine(root / "memory.sqlite3")
        memory.persist_turn(user_id="u", profile_updates={"preferred_name": "小宇"}, goal_updates={"target_city": "杭州", "target_job_normalized": "IT支持"})
        restored = memory.load_user_context(user_id="u")
        browser = AgentBrowserAdapter(reader=lambda command: {"content": "IT支持岗位要求 Active Directory、Windows Server、PowerShell、网络排障和用户沟通，需要实验项目。"})
        market = RecruitmentEngine(providers=[AgentBrowserProvider(browser)], minimum_samples=5).analyze({"target_city": "杭州", "target_job": "IT支持", "public_urls": [f"https://example.com/jobs/{i}" for i in range(5)], "synthetic": True})
        improvement = ImprovementEngine(root / "improvement")
        pattern = None
        for index in range(3): pattern = improvement.observe(user_id="u", task_id=f"t{index}", category="weekly_capacity", signal="任务太多")["pattern"]
        evolver = EvolutionEngine(root / "evolution"); candidate = evolver.from_promoted_pattern(pattern or {})
        trial = evolver.start_trial(candidate["strategy_id"], metric="completion_rate", baseline=0.4); outcome = evolver.finish_trial(candidate["strategy_id"], result=0.7)
        proactive = ProactiveEngine().check(signals={"completion_rate": 0.3})
        print(f"Agent Memory → Context Restored: {restored['profile']['preferred_name']}")
        print(f"Agent Browser → {market['valid_sample_count']} Synthetic Public-Page Fixtures / market={market['market_data_status']}")
        print(f"Self Improving → Pattern Recorded / recurrence={pattern['recurrence_count']}")
        print(f"Capability Evolver → Strategy Candidate / Trial / {outcome['status']}")
        print(f"Proactive Agent → Context-Aware Suggestion / {proactive['reason']}")
        assert market["market_data_status"] == "insufficient" and market["synthetic"] and pattern["promoted"] and outcome["status"] == "accepted" and proactive["should_prompt"]
    print("[PASS] 五脑实际调用链通过；无后台推送、无源码自修改。")
    return 0


if __name__ == "__main__": raise SystemExit(main())
