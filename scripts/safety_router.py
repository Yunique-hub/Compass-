"""职业规划前置的状态关怀和安全路由基线。"""
from __future__ import annotations

from typing import Any, Mapping

try:
    from .io_utils import result, run_cli
    from .models import SafetyType
except ImportError:
    from io_utils import result, run_cli
    from models import SafetyType

MODULE = "safety_router"
HIGH_RISK = ("不想活", "想死", "自杀", "伤害自己", "结束生命", "活不下去")
STRESS = ("压力大", "焦虑", "撑不住", "很累", "崩溃", "学不动", "失眠")
OUT_OF_SCOPE = ("诊断我", "开什么药", "替我打官司", "提供法律意见", "保证胜诉", "保证就业", "保证薪资")


def route_safety(text: str) -> dict[str, Any]:
    lowered = text.casefold()
    if any(term in lowered for term in HIGH_RISK):
        route = SafetyType.HIGH_RISK
        response = "我很在意你现在的安全。先暂停学习计划，请尽快联系所在地经过核验的紧急服务、学校心理中心、辅导员或身边可信任的人，并尽量不要独处。"
        stop_plan, load_factor, memory = True, 0.0, "危机细节默认不写入长期记忆"
    elif any(term in lowered for term in OUT_OF_SCOPE):
        route = SafetyType.OUT_OF_SCOPE
        response = "这个请求超出 Compass 的教育与职业规划边界；我不能诊断、提供药物建议或保证就业/薪资结果。"
        stop_plan, load_factor, memory = True, 0.0, "不保存越界敏感内容"
    elif any(term in lowered for term in STRESS):
        route = SafetyType.STRESS
        response = "听起来你这段时间承受了不少压力。我们先把本周任务降到最小可行量，也可以先休息并联系可信任的人；你愿意说说最卡的一件事吗？"
        stop_plan, load_factor, memory = False, 0.5, "仅保存与计划相关的短期状态并设置 TTL"
    else:
        route = SafetyType.NORMAL
        response = "未检测到需要优先安全转介的信号；继续当前职业规划步骤。"
        stop_plan, load_factor, memory = False, 1.0, "按记忆政策处理"
    return result(MODULE, {"type": route.value, "response": response, "stop_learning_plan": stop_plan, "task_load_factor": load_factor, "memory_handling": memory, "caution": "关键词规则只作辅助，实际 Agent 必须结合上下文谨慎判断，不进行心理诊断。"})


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return route_safety(str(raw.get("text", "")))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
