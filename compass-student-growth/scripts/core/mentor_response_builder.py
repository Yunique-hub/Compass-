"""Render action-first mentor responses without internal field names or scores."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _prefix(name: str, usage: bool = True) -> str:
    return f"{name}，" if name and usage else ""


def ask_name_response() -> dict[str, Any]:
    text = "你好，我是 Compass，我会陪你一起梳理大学阶段的学习、实习、就业和成长路线。\n开始前我想先认识你一下——以后我怎么称呼你比较合适？"
    return {"current_judgment": "先建立自然称呼", "why": "称呼会用于后续连续陪伴", "do_now": [], "next_step": "告诉我希望使用的称呼", "mentor_sections": {"onboarding": text}, "text": text}


def quick_profile_response(name: str, *, usage: bool = True) -> dict[str, Any]:
    text = f"好的，{name}。" if name and usage else "好的。"
    text += "为了不让你填一大堆资料，我先了解最关键的：\n你现在是什么专业、几年级？最近最想解决的是学习、考试、实习就业，还是暂时还比较迷茫？"
    return {"current_judgment": "快速定位当前状态", "why": "只收集会直接影响第一步行动的信息", "do_now": [], "next_step": "回答专业、年级和当前最想解决的问题", "mentor_sections": {"quick_profile": text}, "text": text}


def stage_question_response(name: str, stage: Mapping[str, Any], questions: Sequence[Mapping[str, Any]], *, usage: bool = True) -> dict[str, Any]:
    lead = f"{_prefix(name, usage)}你现在已经进入{stage.get('label', '当前成长阶段')}。"
    evidence = "、".join(str(item) for item in stage.get("evidence", []))
    lines = [lead]
    if evidence:
        lines.append(f"这个判断主要来自：{evidence}。")
    lines.append("我只再确认会直接影响第一步计划的关键点：")
    lines.extend(f"{index}. {item['text']}" for index, item in enumerate(questions, 1))
    text = "\n".join(lines)
    return {"current_judgment": lead, "why": evidence or "依据当前已知信息", "do_now": [], "next_step": "回答上面的关键点后立即开始规划", "mentor_sections": {"stage": lead, "questions": [item["text"] for item in questions]}, "text": text}


def action_response(
    name: str, diagnosis: Mapping[str, Any], goal_plan: Mapping[str, Any], capacity: Mapping[str, Any],
    *, directions: Sequence[Mapping[str, Any]] | None = None, later_questions: Sequence[Mapping[str, Any]] | None = None,
    usage: bool = True,
) -> dict[str, Any]:
    stage_text = f"{_prefix(name, usage)}你现在已经进入{diagnosis.get('stage_label', '当前阶段')}。"
    strengths = "、".join(str(item) for item in diagnosis.get("strengths", [])) or "你已经提供的专业和学习基础"
    sections: dict[str, Any] = {
        "我对你当前状态的判断": f"{stage_text}\n你不是从零开始：{strengths}。\n当前最需要解决的是：{diagnosis.get('main_problem', '')}。",
        "当前最重要的目标": goal_plan.get("primary_goal", diagnosis.get("primary_goal", "")),
        "接下来分几个阶段": goal_plan.get("stage_goals", []),
        "这周只做这3件事": goal_plan.get("weekly_core_tasks", [])[:3],
        "为什么先做这些": goal_plan.get("why", ""),
        "下次回来告诉我什么": ["哪些完成了", "实际用了多久", "哪个最卡"],
        "还有哪些信息以后补充": (
            "有一个信息现在不影响你开工，但后面会让我把规划做得更精准："
            + "；".join(str(item.get("text", "")) for item in (later_questions or []))
            + " 你想好后告诉我就行。"
            if later_questions else ""
        ),
    }
    if directions:
        sections["方向判断"] = [
            {
                "direction_name": item.get("direction_name"),
                "status": "confirmed" if item.get("is_confirmed") else "candidate",
                "exploration_task": item.get("exploration_task"),
            }
            for item in directions[:3]
        ]
    lines = [f"【{title}】\n{_render_value(value)}" for title, value in sections.items() if value not in (None, "", [])]
    planned = capacity.get("planned_weekly_hours")
    stated = capacity.get("stated_weekly_hours")
    if planned and stated and planned < stated:
        lines.insert(-2, f"你提供的理论可用时间约为每周 {stated:g} 小时，但第一周只按约 {planned:g} 小时的保守上限规划；两周后再根据真实完成速度调整。")
    text = "\n\n".join(lines)
    tasks = goal_plan.get("weekly_core_tasks", [])[:3]
    return {
        "current_judgment": stage_text,
        "why": diagnosis.get("main_problem", ""),
        "do_now": [task.get("title", "") for task in tasks],
        "next_step": "下次回来告诉我：完成了哪些、实际用了多久、哪个最卡。",
        "mentor_sections": sections,
        "text": text,
    }


def _render_value(value: Any) -> str:
    if isinstance(value, list):
        rendered = []
        for index, item in enumerate(value, 1):
            if isinstance(item, Mapping):
                title = item.get("title") or item.get("period") or item.get("direction_name") or f"第 {index} 项"
                detail = item.get("goal") or item.get("why") or item.get("exploration_task") or ""
                rendered.append(f"{index}. {title}" + (f"：{detail}" if detail else ""))
            else:
                rendered.append(f"{index}. {item}")
        return "\n".join(rendered)
    return str(value)
