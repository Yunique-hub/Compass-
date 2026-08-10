"""Compose academic background, pathway, competency and evidence needs."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from scripts.academic.major_engine import AcademicProfile, identify_academic_profile, resolve_profile_knowledge
from scripts.academic.pathway_engine import PathwayDecision


PATHWAY_OVERLAYS = {
    "graduate_school": ["研究方法", "文献阅读", "学术写作", "科研经历", "推荐信与申请准备"],
    "phd_research": ["研究问题", "研究方法", "论文与学术表达", "科研协作"],
    "professional_qualification": ["资格考试知识体系", "真题与案例练习", "政策与报名要求验证"],
    "internship": ["专业实践", "实习 Evidence", "简历表达", "目标要求验证"],
    "employment": ["职业能力", "实践 Evidence", "简历与面试", "行业理解"],
    "career_exploration": ["方向探索", "兴趣与约束识别", "低成本试验", "探索 Evidence"],
    "career_transition": ["可迁移能力", "目标能力缺口", "桥接实践", "转型 Evidence"],
    "skill_development": ["知识诊断", "刻意练习", "反馈与复测"],
    "academic_improvement": ["课程基础", "学习方法", "阶段性 Assessment"],
}

ROLE_OVERLAYS = {
    "投行": ["会计基础", "财务分析", "估值", "金融建模", "行业研究", "Networking 与面试"],
    "四大": ["会计与审计基础", "Excel", "商业英语", "案例与实习准备"],
    "UI/UX": ["设计基础", "UI/UX", "交互设计", "用户研究", "设计项目", "作品集"],
    "机器人": ["机械基础", "CAD/CAE", "控制", "机器人", "编程", "原型或工程项目"],
    "数据分析": ["可迁移能力", "统计", "Excel/SQL", "数据可视化", "分析作品集", "目标缺口"],
    "量化": ["数学", "概率统计", "编程", "金融基础", "模型验证"],
    "经济学研究": ["数学", "计量经济学", "研究方法", "文献", "科研 Evidence"],
    "律所": ["法律检索", "案例分析", "法律写作", "律所实习"],
    "后端": ["Python", "数据结构", "数据库", "Web/API", "测试", "技术项目"],
}


@dataclass
class GrowthContext:
    academic_profile: AcademicProfile
    current_stage: str
    primary_goal: str
    secondary_goals: list[str]
    target_pathway: str
    target_role: str
    constraints: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    competencies: list[str] = field(default_factory=list)
    evidence_types: list[str] = field(default_factory=list)
    time_horizon: str = ""
    weekly_capacity: float = 0.0
    knowledge_source: str = "family_fallback"
    transferable_skills: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    goal_portfolio: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _role_overlay(target_role: str) -> list[str]:
    return next((items for key, items in ROLE_OVERLAYS.items() if key.casefold() in target_role.casefold()), [])


def build_growth_context(
    academic: AcademicProfile,
    pathway: PathwayDecision,
    *,
    stage: str,
    weekly_capacity: float = 0.0,
    constraints: Mapping[str, Any] | None = None,
) -> GrowthContext:
    knowledge = resolve_profile_knowledge(academic)
    academic_competencies = [*knowledge.get("foundational_competencies", []), *knowledge.get("core_competencies", [])]
    evidence_types = list(knowledge.get("evidence_types", ["assessment"]))
    for related_major in (academic.secondary_major, academic.minor):
        if not related_major:
            continue
        related = resolve_profile_knowledge(identify_academic_profile(f"我是{related_major}专业"))
        academic_competencies.extend([*related.get("foundational_competencies", [])[:3], *related.get("core_competencies", [])[:2]])
        evidence_types.extend(related.get("evidence_types", []))
    pathway_competencies = list(PATHWAY_OVERLAYS.get(pathway.primary, PATHWAY_OVERLAYS["academic_improvement"]))
    for secondary_pathway in pathway.secondary:
        pathway_competencies.extend(PATHWAY_OVERLAYS.get(secondary_pathway, []))
    pathway_competencies = list(dict.fromkeys(pathway_competencies))
    role_competencies = _role_overlay(pathway.target_role)
    competencies = list(dict.fromkeys([*academic_competencies, *pathway_competencies, *role_competencies]))
    transferable = academic_competencies[:3] if pathway.primary == "career_transition" else []
    gaps = list(dict.fromkeys([*pathway_competencies, *role_competencies])) if pathway.primary == "career_transition" else []
    return GrowthContext(
        academic_profile=academic,
        current_stage=stage,
        primary_goal=pathway.primary_goal,
        secondary_goals=pathway.secondary,
        target_pathway=pathway.primary,
        target_role=pathway.target_role,
        constraints=dict(constraints or {}),
        competencies=competencies,
        evidence_types=list(dict.fromkeys(evidence_types)),
        weekly_capacity=weekly_capacity,
        knowledge_source=str(knowledge.get("knowledge_source", "family_fallback")),
        transferable_skills=transferable,
        gaps=gaps,
        goal_portfolio=asdict(pathway.goal_portfolio) if pathway.goal_portfolio else {},
    )


def pathway_options(context: GrowthContext) -> list[dict[str, str]]:
    knowledge = resolve_profile_knowledge(context.academic_profile)
    primary_options = list(knowledge.get("common_pathways", []))
    options = list(primary_options)
    if context.academic_profile.secondary_major:
        secondary = identify_academic_profile(f"我是{context.academic_profile.secondary_major}专业")
        secondary_options = list(resolve_profile_knowledge(secondary).get("common_pathways", []))
        options = [*primary_options[:2], *secondary_options[:2], *primary_options[2:]]
    if context.target_role:
        options.insert(0, context.target_role)
    options = list(dict.fromkeys(options))[:4]
    return [
        {
            "title": option,
            "why": f"与{context.academic_profile.raw_major or knowledge.get('title', '当前背景')}的能力基础存在连接",
            "required": "从该方向选一个核心任务并完成最小体验",
            "experiment": f"用 1 周完成一次“{option}”低成本体验并记录喜欢、不喜欢和完成证据",
        }
        for option in options
    ]
