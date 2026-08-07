"""In-session proactive recommendations with cooldown and explicit feedback."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class ProactiveEngine:
    def __init__(self, *, cooldown_hours: int = 24) -> None:
        self.cooldown = timedelta(hours=cooldown_hours)

    def check(self, *, signals: dict[str, Any], last_prompt_at: str = "") -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        if last_prompt_at:
            last = datetime.fromisoformat(last_prompt_at)
            if now - last < self.cooldown:
                return {"should_prompt": False, "reason": "cooldown", "available_after": (last + self.cooldown).isoformat()}
        missed = int(signals.get("missed_tasks", 0))
        exam_days = signals.get("exam_days")
        stress = float(signals.get("stress", 0))
        if stress >= 0.8:
            message, reason = "这周任务先减半。你愿意保留最小的一项行动吗？", "high_stress"
        elif isinstance(exam_days, int) and exam_days <= 5:
            message, reason = "考试已进入 5 天窗口，要把本周时间优先切到复习吗？", "exam_window"
        elif missed >= 2:
            message, reason = "连续任务未完成，要把下一项拆成 30 分钟可验收步骤吗？", "repeated_miss"
        else:
            return {"should_prompt": False, "reason": "no_trigger"}
        return {"should_prompt": True, "reason": reason, "message": message, "prompted_at": now.isoformat(), "delivery": "current_interaction_only", "background_push": False}

    @staticmethod
    def feedback(prompt: dict[str, Any], response: str) -> dict[str, Any]:
        allowed = {"accepted", "rejected", "ignored"}
        if response not in allowed:
            raise ValueError(f"response 必须是 {sorted(allowed)} 之一")
        return {"reason": prompt.get("reason"), "response": response, "recorded_at": datetime.now(timezone.utc).isoformat()}
