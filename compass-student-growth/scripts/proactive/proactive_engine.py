"""In-session proactive recommendations with cooldown and explicit feedback."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class ProactiveEngine:
    def __init__(self, *, cooldown_hours: int = 24) -> None:
        self.cooldown = timedelta(hours=cooldown_hours)

    def check(self, *, signals: dict[str, Any], last_prompt_at: str = "", feedback_history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        if last_prompt_at:
            last = datetime.fromisoformat(last_prompt_at)
            if now - last < self.cooldown:
                return {"should_prompt": False, "reason": "cooldown", "available_after": (last + self.cooldown).isoformat()}
        missed = int(signals.get("missed_tasks", 0))
        exam_days = signals.get("exam_days")
        stress = float(signals.get("stress", 0))
        completion = signals.get("completion_rate")
        actual_ratio = signals.get("actual_hours_ratio")
        rejected = sum(1 for item in feedback_history or [] if item.get("response") == "rejected")
        if rejected >= 3:
            return {"should_prompt": False, "reason": "rejection_suppression", "delivery": "current_interaction_only", "background_push": False}
        if stress >= 0.8:
            message, reason, priority, confidence = "这周任务先减半。你愿意保留最小的一项行动吗？", "high_stress", "high", 0.9
        elif isinstance(exam_days, int) and exam_days <= 5:
            message, reason, priority, confidence = "考试已进入 5 天窗口，要把本周时间优先切到复习吗？", "exam_window", "high", 0.9
        elif signals.get("market_snapshot_stale"):
            message, reason, priority, confidence = "当前招聘市场快照已过期，需要重新分析后再校准学习优先级吗？", "market_snapshot_stale", "medium", 0.85
        elif signals.get("target_changed"):
            message, reason, priority, confidence = "你的目标城市或岗位已改变，旧市场快照和计划需要重新校准。", "career_target_changed", "high", 0.95
        elif isinstance(signals.get("job_search_days"), int) and signals["job_search_days"] <= 60:
            message, reason, priority, confidence = "求职窗口已临近，建议把本周压缩到最能形成岗位证据的一项任务。", "job_search_window", "high", 0.85
        elif signals.get("gap_stalled_weeks", 0) >= 2:
            message, reason, priority, confidence = "这个能力 Gap 连续两周没有下降，建议改用更小的练习和验收标准。", "gap_stalled", "medium", 0.8
        elif signals.get("weeks_without_evidence", 0) >= 2:
            message, reason, priority, confidence = "最近没有形成新的能力证据，建议本周只保留一个可验收产出。", "evidence_drought", "medium", 0.8
        elif isinstance(completion, (int, float)) and completion < 0.5:
            message, reason, priority, confidence = "最近两周计划完成率持续下降。建议把这一周压缩到一个最关键的能力证据任务。", "completion_decline", "medium", 0.85
        elif isinstance(actual_ratio, (int, float)) and actual_ratio < 0.5:
            message, reason, priority, confidence = "实际学习时间持续低于计划，建议先降低任务量再恢复节奏。", "actual_time_shortfall", "medium", 0.75
        elif missed >= 2:
            message, reason, priority, confidence = "连续任务未完成，要把下一项拆成 30 分钟可验收步骤吗？", "repeated_miss", "medium", 0.8
        else:
            return {"should_prompt": False, "reason": "no_trigger", "delivery": "current_interaction_only", "background_push": False}
        return {"should_prompt": True, "reason": reason, "priority": priority, "confidence": confidence, "cooldown_hours": self.cooldown.total_seconds() / 3600, "message": message, "prompted_at": now.isoformat(), "delivery": "current_interaction_only", "background_push": False}

    @staticmethod
    def feedback(prompt: dict[str, Any], response: str) -> dict[str, Any]:
        allowed = {"accepted", "rejected", "ignored"}
        if response not in allowed:
            raise ValueError(f"response 必须是 {sorted(allowed)} 之一")
        return {"reason": prompt.get("reason"), "response": response, "recorded_at": datetime.now(timezone.utc).isoformat()}
