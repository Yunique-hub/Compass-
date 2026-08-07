"""Stable import boundary for controlled runtime strategy evolution."""
from scripts.evolution.evolution_engine import EvolutionEngine


class CapabilityEvolverAdapter:
    def __init__(self, runtime_dir: str, *, acceptance_threshold: float = 0.0) -> None:
        self.engine = EvolutionEngine(runtime_dir, acceptance_improvement_threshold=acceptance_threshold)
    def propose_from_pattern(self, pattern: dict) -> dict | None:
        return self.engine.from_promoted_pattern(pattern)
    def start_trial(self, strategy_id: str, *, metric: str, baseline: float) -> dict:
        return self.engine.start_trial(strategy_id, metric=metric, baseline=baseline)
    def finish_trial(self, strategy_id: str, *, result: float) -> dict:
        return self.engine.finish_trial(strategy_id, result=result)


__all__ = ["CapabilityEvolverAdapter", "EvolutionEngine"]
