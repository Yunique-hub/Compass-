"""确认门驱动的探索计划或正式三级计划生成器。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .direction_confirmation import formal_plan_gate
    from .io_utils import error, result, run_cli
    from .models import LearningPlan, LearningTask
    from .plan_validator import validate_plan
    from .resource_matcher import match_resources
except ImportError:
    from direction_confirmation import formal_plan_gate
    from io_utils import error, result, run_cli
    from models import LearningPlan, LearningTask
    from plan_validator import validate_plan
    from resource_matcher import match_resources

MODULE = "plan_generator"
ROOT = Path(__file__).resolve().parents[1]


def exploration_plan(tasks: Sequence[str], weekly_hours: float) -> dict[str, Any]:
    capacity = max(0.0, weekly_hours * 0.85)
    selected = list(tasks)[:2] or ["完成一次 1 小时岗位工作内容核对，并记录喜欢、排斥和待验证点。"]
    per_task = min(3.0, capacity / len(selected)) if selected and capacity else 0.0
    items = [LearningTask(task_id=f"explore-{index}", title=title, priority=1.0 - index * 0.1, category="direction_exploration", estimated_hours=round(per_task, 2), output="代码、分析页或访谈记录等可检查产出", acceptance_criteria=["产出可打开或运行", "写出 3 条体验结论和 1 个下一步问题"], dependencies=["用户选择要验证的候选方向"], resources=[{"resource_id": "local-exploration", "name": "方向探索记录模板"}], fallback="若任务过大，缩小到 60 分钟最小体验并记录卡点。") for index, title in enumerate(selected, 1)]
    return result(MODULE, {"mode": "exploration", "stage": "当前为探索阶段", "max_weeks": 2, "weekly_core_tasks": [item.to_dict() for item in items], "total_weekly_hours": sum(item.estimated_hours for item in items), "capacity_limit": capacity, "formal_plan_generated": False})


def generate_plan(
    confirmation: Mapping[str, Any], gaps: Sequence[Mapping[str, Any]], *, weekly_hours: float,
    snapshot_version: str, synthetic: bool = False, exploration_tasks: Sequence[str] | None = None,
) -> dict[str, Any]:
    gate = formal_plan_gate(confirmation)
    if not gate["ok"]:
        if not confirmation.get("primary_direction"):
            return exploration_plan(exploration_tasks or [], weekly_hours)
        message = "方向已确认，但目的地或求职时间缺失；以下只能作为通用基础建议，不是基于目的地招聘市场的数据规划。"
        return result(MODULE, {"mode": "general_foundation", "formal_plan_generated": False, "notice": message, "missing": gate.get("fallback", {}).get("fields", [])}, ok=False, warnings=[error("FORMAL_PLAN_BLOCKED", message)], errors=gate["errors"], fallback={"action": "request_destination_or_deadline"})
    if not snapshot_version:
        return result(MODULE, ok=False, errors=[error("SNAPSHOT_MISSING", "没有匹配快照；请上传真实 JD、选择已有城市数据或使用通用框架。")], fallback={"action": "request_jd_or_snapshot"})
    rules = json.loads((ROOT / "config" / "plan_rules.json").read_text(encoding="utf-8"))
    capacity = round(max(0.0, weekly_hours) * float(rules["weekly_capacity_ratio"]), 2)
    sorted_gaps = sorted(gaps, key=lambda item: (-float(item.get("priority_score", 0)), item.get("competency_name", "")))
    competencies = [str(item.get("competency_name", "")) for item in sorted_gaps]
    resources = match_resources(competencies, max_hours=capacity)["data"]["resources"]
    tasks: list[LearningTask] = []
    standard_hours = [3.0, 3.0, 2.0]
    for index, gap in enumerate(sorted_gaps[: int(rules["max_core_tasks_per_week"])], 1):
        skill = str(gap.get("competency_name", f"能力 {index}"))
        related = [item for item in resources if skill in item.get("recommended_for", [])]
        for shared in resources:
            if shared not in related and len(related) < 2:
                related.append(shared)
        tasks.append(LearningTask(
            task_id=f"week-{index}", title=f"完成 {skill} 最小可验证练习", priority=float(gap.get("priority_score", 0)), category=str(gap.get("category", "high_frequency")), estimated_hours=standard_hours[index - 1],
            output=f"一份可运行或可检查的 {skill} 练习产出和复盘说明", acceptance_criteria=["产出可运行或可打开", "覆盖至少 3 个关键场景", "记录问题、修复与验证结果"], dependencies=["确认任务范围", "准备本地开发或记录环境"], resources=related[:4], fallback="若完整练习受阻，提交最小复现、问题记录和下一步验证清单。",
        ))
    plan = LearningPlan(
        basis={"primary_direction": confirmation.get("primary_direction"), "city": confirmation.get("target_city"), "job_search_period": confirmation.get("job_search_period") or confirmation.get("graduation_date"), "evidence": "实际招聘快照或用户真实 JD + 用户可验证能力证据", "data_notice": "仅用于功能测试，不代表当前市场" if synthetic else "结论只适用于所列数据范围"},
        snapshot_version=snapshot_version,
        quarter_or_semester_milestones=[{"period": "本季度/学期", "milestone": "形成目标岗位核心基础与一个可演示项目证据"}],
        monthly_milestones=[{"period": "本月", "milestone": f"完成 {', '.join(competencies[:3]) or '核心基础'} 的最小闭环并保留证据"}],
        weekly_core_tasks=tasks, optional_tasks=[], total_weekly_hours=sum(item.estimated_hours for item in tasks), capacity_limit=capacity,
        risks=["招聘快照为低样本时只能作为流程演示或弱证据", "任务难度需根据本周复盘调整"], adjustment_notes=["超预算时删除低优先级核心任务，不把所有任务压缩为不现实的时长。"],
    ).to_dict()
    plan["mode"] = "formal"
    validated = validate_plan(plan, confirmation, synthetic=synthetic, auto_fix=True)
    validated_plan = validated["data"]["plan"]
    warnings = list(validated.get("warnings", []))
    if synthetic:
        warnings.append(error("SYNTHETIC_DATA", "仅用于功能测试，不代表当前市场"))
    return result(MODULE, {"plan": validated_plan, "validation": {key: validated["data"][key] for key in ("valid", "auto_fix", "remaining_issues")}, "formal_plan_generated": validated["data"]["valid"]}, ok=validated["data"]["valid"], warnings=warnings, errors=validated.get("errors", []))


def _handler(raw: Mapping[str, Any]) -> dict[str, Any]:
    return generate_plan(raw.get("confirmation", {}), raw.get("gaps", []), weekly_hours=float(raw.get("weekly_hours", 0)), snapshot_version=str(raw.get("snapshot_version", "")), synthetic=bool(raw.get("synthetic", False)), exploration_tasks=raw.get("exploration_tasks", []))


if __name__ == "__main__":
    raise SystemExit(run_cli(MODULE, _handler))
