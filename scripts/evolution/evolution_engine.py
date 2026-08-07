"""Controlled gene/capsule selection, trial and rollback.

This adapts Capability Evolver's selection ideas but never rewrites source.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .strategy_store import StrategyStore


class EvolutionEngine:
    def __init__(self, runtime_dir: str | Path, *, acceptance_improvement_threshold: float = 0.0) -> None:
        self.store = StrategyStore(runtime_dir)
        self.acceptance_improvement_threshold = max(0.0, float(acceptance_improvement_threshold))

    def propose(self, *, gene: str, capsule: dict[str, Any], evidence: list[str]) -> dict[str, Any]:
        if not evidence:
            raise ValueError("策略候选必须包含可观察证据")
        return self.store.add_candidate({"source_pattern": evidence[0], "gene": gene, "capsule": capsule, "evidence": evidence, "auto_apply": False, "allow_self_modify": False})

    def from_promoted_pattern(self, pattern: dict[str, Any]) -> dict[str, Any] | None:
        if not pattern.get("promoted") or not pattern.get("pattern_key"):
            return None
        return self.propose(gene=f"observable_rule:{pattern.get('category', 'general')}", capsule={"change": f"针对 {pattern.get('signal')} 试验更保守策略", "requires_trial": True}, evidence=[str(pattern["pattern_key"])])

    def start_trial(self, strategy_id: str, *, metric: str, baseline: float) -> dict[str, Any]:
        data = self.store.load()
        strategy = next((item for item in data["strategies"] if item["strategy_id"] == strategy_id), None)
        if strategy is None:
            raise KeyError(strategy_id)
        strategy["status"] = "trial"
        strategy["baseline"] = baseline
        trial = {"strategy_id": strategy_id, "metric": metric, "baseline": baseline, "status": "running", "created_at": datetime.now(timezone.utc).isoformat()}
        data["trials"].append(trial)
        self.store.save(data)
        return trial

    def finish_trial(self, strategy_id: str, *, result: float) -> dict[str, Any]:
        data = self.store.load()
        trial = next(item for item in reversed(data["trials"]) if item["strategy_id"] == strategy_id and item["status"] == "running")
        strategy = next(item for item in data["strategies"] if item["strategy_id"] == strategy_id)
        trial["result"] = result
        trial["improvement"] = result - float(trial["baseline"])
        trial["status"] = "accepted" if trial["improvement"] > self.acceptance_improvement_threshold else "rolled_back"
        strategy["status"] = "active" if trial["status"] == "accepted" else "candidate"
        strategy["trial_metric"] = trial["metric"]
        strategy["result"] = result
        if trial["status"] == "accepted": strategy["accepted_at"] = datetime.now(timezone.utc).isoformat()
        else: strategy["rollback_reason"] = "trial_metric_did_not_improve_enough"
        self.store.save(data)
        return trial
