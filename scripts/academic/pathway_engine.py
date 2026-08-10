"""Goal and pathway detection independent from academic major."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from scripts.core.intent_router import has_graduate_school_signal


@dataclass
class GoalItem:
    goal_type: str
    description: str
    priority: float
    deadline: str | None = None
    status: str = "active"
    allocated_hours: float = 0.0


@dataclass
class GoalPortfolio:
    primary: GoalItem
    secondary: list[GoalItem] = field(default_factory=list)
    weekly_capacity: float = 0.0


@dataclass
class PathwayDecision:
    primary: str
    secondary: list[str] = field(default_factory=list)
    target_role: str = ""
    primary_goal: str = ""
    confidence: float = 0.7
    evidence: list[str] = field(default_factory=list)
    goal_portfolio: GoalPortfolio | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_pathway(message: str, facts: Mapping[str, Any] | None = None, *, transition_target: str = "") -> PathwayDecision:
    text = str(message or "")
    facts = facts or {}
    evidence: list[str] = []
    pathways: list[str] = []
    signals = (
        ("career_transition", ("转行", "不想做", "转数据", "转专业")),
        ("graduate_school", ("申请研究生", "申请硕士", "准备读研", "考研", "研究生", "硕士")),
        ("phd_research", ("博士", "科研道路", "学术研究")),
        ("professional_qualification", ("法考", "教资", "资格考试", "执业资格", "证书")),
        ("study_abroad", ("留学", "出国", "海外申请")),
        ("civil_service", ("考公", "公务员", "选调")),
        ("internship", ("实习", "律所实习", "轮转")),
        ("employment", ("找工作", "就业", "投行", "四大", "毕业做", "求职")),
        ("skill_development", ("带我学", "学得很吃力", "不会", "想学")),
        ("career_exploration", ("不知道以后", "不知道走", "迷茫", "没想好", "不知道做什么")),
    )
    for pathway, terms in signals:
        matched = next((term for term in terms if term in text), "")
        if matched:
            pathways.append(pathway)
            evidence.append(matched)
    if has_graduate_school_signal(text) and "graduate_school" not in pathways:
        pathways.append("graduate_school")
        evidence.append("读研或研究生目标")
    if "申请" in text and "硕士" in text and "graduate_school" not in pathways:
        pathways.append("graduate_school")
        evidence.append("申请硕士")
    if transition_target and "career_transition" not in pathways:
        pathways.insert(0, "career_transition")
        evidence.append(f"目标转向 {transition_target}")
    primary = pathways[0] if pathways else "academic_improvement"
    def fact_value(key: str) -> Any:
        value = facts.get(key, "")
        return value.get("value", "") if isinstance(value, Mapping) else value

    target_role = transition_target or str(fact_value("target_job") or "")
    role_terms = ("Python 后端", "后端", "投行", "UI/UX", "UX Research", "用户研究", "机器人", "数据分析", "量化", "经济学研究", "商业分析", "律所")
    if not target_role:
        candidates = [term for term in role_terms if term.casefold() in text.casefold() and not any(negation in text for negation in (f"不喜欢{term}", f"不想做{term}", f"不考虑{term}", f"放弃{term}"))]
        if candidates:
            target_role = max(candidates, key=lambda term: text.casefold().rfind(term.casefold()))

    if not pathways:
        need_pathways = {
            "跨专业转型": "career_transition",
            "学术深造": "graduate_school",
            "资格考试": "professional_qualification",
            "实习准备": "internship",
            "就业准备": "employment",
            "学习诊断": "skill_development",
            "学习提升": "skill_development",
            "成长方向": "career_exploration",
        }
        inherited = need_pathways.get(str(fact_value("primary_need")), "")
        if inherited:
            pathways.append(inherited)
            primary = inherited
            evidence.append("已知成长目标")
    if target_role and not pathways:
        pathways.append("employment")
        primary = "employment"
        evidence.append(f"目标岗位 {target_role}")
    if not target_role:
        target_role = str(fact_value("target_job") or fact_value("career_direction") or "")
    goal_parts = [evidence[0]] if evidence else []
    if target_role and target_role not in goal_parts:
        goal_parts.append(target_role)
    goal = " + ".join(goal_parts) or "改善当前成长状态"
    unique_pathways = list(dict.fromkeys(pathways)) or [primary]
    weekly = float(fact_value("weekly_learning_hours") or 0.0)
    weights = [1.0] if len(unique_pathways) == 1 else ([0.6, 0.4] if len(unique_pathways) == 2 else [0.5, 0.3, 0.2])
    items = [
        GoalItem(
            goal_type=pathway,
            description=(target_role if index == 0 and target_role else pathway),
            priority=weights[index] if index < len(weights) else 0.0,
            deadline=str(fact_value("deadline_time") or "") or None,
            allocated_hours=round(weekly * (weights[index] if index < len(weights) else 0.0), 2),
        )
        for index, pathway in enumerate(unique_pathways[:3])
    ]
    portfolio = GoalPortfolio(primary=items[0], secondary=items[1:], weekly_capacity=weekly)
    return PathwayDecision(primary=primary, secondary=unique_pathways[1:], target_role=target_role, primary_goal=goal, confidence=0.9 if evidence else 0.6, evidence=evidence, goal_portfolio=portfolio)
