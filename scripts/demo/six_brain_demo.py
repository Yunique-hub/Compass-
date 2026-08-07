"""Offline smoke demonstration for all six Compass brains."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.evolution.evolution_engine import EvolutionEngine
from scripts.improvement.improvement_engine import ImprovementEngine
from scripts.memory.memory_engine import MemoryEngine
from scripts.proactive.proactive_engine import ProactiveEngine
from scripts.research.browser_policy import validate_command, validate_public_url
from scripts.review.review_engine import ReviewEngine


def _memory_candidate() -> dict:
    return {
        "candidate_id": "demo-direction", "record_id": "demo-direction", "user_id": "six-brain-demo",
        "memory_type": "confirmed_goal", "content": {"direction": "IT支持"},
        "importance": 1, "stability": 1, "future_relevance": 1, "user_explicitness": 1,
        "recurrence": 1, "confidence": 1, "task_value": 1, "user_intent": "remember",
    }


def main() -> int:
    with TemporaryDirectory(prefix="compass-six-brain-") as runtime:
        root = Path(runtime)
        material = root / "操作系统真题.txt"
        material.write_text("进程与线程\n死锁四个必要条件\n", encoding="utf-8")
        review = ReviewEngine().build(course="操作系统", material_paths=[material])

        memory_engine = MemoryEngine(root / "memory.sqlite3")
        memory_write = memory_engine.write(user_id="six-brain-demo", candidate=_memory_candidate())
        memory_load = memory_engine.load(user_id="six-brain-demo", query="IT支持")["data"]

        improvement_engine = ImprovementEngine(root / "improvement")
        improvement_engine.observe(user_id="u", task_id="t1", category="plan", signal="任务太大")
        improvement_engine.observe(user_id="u", task_id="t1", category="plan", signal="任务太大")
        improvement = improvement_engine.observe(user_id="u", task_id="t2", category="plan", signal="任务太大")

        evolution_engine = EvolutionEngine(root / "evolution")
        strategy = evolution_engine.propose(gene="smaller_tasks", capsule={"max_minutes": 30}, evidence=["任务太大"])
        evolution_engine.start_trial(strategy["strategy_id"], metric="completion", baseline=0.5)
        evolution = evolution_engine.finish_trial(strategy["strategy_id"], result=0.7)

        research = {
            "host": validate_public_url("https://example.com/course", {"example.com"}),
            "command": validate_command("get text body"),
        }
        proactive = ProactiveEngine().check(signals={"exam_days": 3})

        summary = {
            "Review Brain": bool(review["questions"] and review["answers"]),
            "Memory Brain": bool(memory_write["stored"] and memory_load["count"] == 1),
            "Improvement Brain": bool(improvement["suggestion"]),
            "Evolution Brain": evolution["status"] == "accepted",
            "Research Brain": research["host"] == "example.com",
            "Proactive Brain": proactive["should_prompt"] and not proactive["background_push"],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        assert all(summary.values())
    print("[PASS] 六脑离线回归全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
