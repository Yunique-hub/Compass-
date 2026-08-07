"""Stable import boundary for in-session proactive recommendations."""
from scripts.proactive.proactive_engine import ProactiveEngine


class ProactiveAgentAdapter:
    def __init__(self, *, cooldown_hours: int = 24) -> None: self.engine = ProactiveEngine(cooldown_hours=cooldown_hours)
    def check(self, signals: dict, *, last_prompt_at: str = "", feedback_history: list[dict] | None = None) -> dict:
        return self.engine.check(signals=signals, last_prompt_at=last_prompt_at, feedback_history=feedback_history)
    def feedback(self, prompt: dict, response: str) -> dict:
        return self.engine.feedback(prompt, response)


__all__ = ["ProactiveAgentAdapter", "ProactiveEngine"]
