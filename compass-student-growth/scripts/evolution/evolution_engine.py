"""Controlled gene/capsule selection, trial and rollback.

This adapts Capability Evolver's selection ideas but never rewrites source.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .strategy_store import StrategyStore


class EvolutionEngine:
    def __init__(self, runtime_dir: str | Path) -> None:
        self.store = StrategyStore(runtime_dir)

    def propose(self, *, gene: str, capsule: dict[str, Any], evidence: list[str]) -> dict[str, Any]:
        if not evidence:
            raise ValueError("策略候选必须包含可观察证据")
        return self.store.add_candidate({"gene": gene, "capsule": capsule, "evidence": evidence, "auto_apply": False})

    def start_trial(self, strategy_id: str, *, metric: str, baseline: float) -> dict[str, Any]:
        data = self.store.load()
        strategy = next((item for item in data["strategies"] if item["strategy_id"] == strategy_id), None)
        if strategy is None:
            raise KeyError(strategy_id)
        strategy["status"] = "trial"
        trial = {"strategy_id": strategy_id, "metric": metric, "baseline": baseline, "status": "running"}
        data["trials"].append(trial)
        self.store.save(data)
        return trial

    def finish_trial(self, strategy_id: str, *, result: float) -> dict[str, Any]:
        data = self.store.load()
        trial = next(item for item in reversed(data["trials"]) if item["strategy_id"] == strategy_id and item["status"] == "running")
        strategy = next(item for item in data["strategies"] if item["strategy_id"] == strategy_id)
        trial["result"] = result
        trial["status"] = "accepted" if result > trial["baseline"] else "rolled_back"
        strategy["status"] = "active" if trial["status"] == "accepted" else "candidate"
        self.store.save(data)
        return trial
