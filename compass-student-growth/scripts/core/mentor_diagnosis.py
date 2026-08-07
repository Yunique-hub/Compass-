"""Turn known facts into a concise, evidence-backed mentor diagnosis."""
from __future__ import annotations

from typing import Any, Mapping

from .known_facts import fact_value


def build_mentor_diagnosis(facts: Mapping[str, Any], stage: Mapping[str, Any], *, planning_confidence: str) -> dict[str, Any]:
    skills = list(fact_value(facts, "skills", []))
    direction = fact_value(facts, "career_direction", "当前方向")
    if isinstance(direction, list):
        direction_text = " / ".join(direction)
    else:
        direction_text = str(direction)
    strengths = skills[:5]
    if fact_value(facts, "python_project_experience"):
        strengths.append("Python 简单项目经验")
    if not strengths and fact_value(facts, "major"):
        strengths.append(f"{fact_value(facts, 'major')}专业基础")

    stage_code = str(stage.get("stage", ""))
    coding = bool(fact_value(facts, "coding_interest")) or "Python" in skills
    if "INTERNSHIP_PREPARATION" in stage_code:
        main_problem = "还缺少围绕具体实习方向形成的技能组合、排障记录和项目证据"
        primary_goal = f"在接下来的实习准备期达到{direction_text}岗位的基础胜任要求，并形成可展示证据"
    elif "EXAM_SPRINT" in stage_code:
        main_problem = "时间窗口很短，需要先从全面学习切换为高优先级复习和练习"
        primary_goal = "在考试前完成重点覆盖、练习反馈和错题重做"
    elif "JOB_SEARCH" in stage_code:
        main_problem = "需要把已有能力快速对齐岗位、简历和面试证据"
        primary_goal = f"完成{direction_text}方向的岗位对齐、简历证据和投递准备"
    else:
        main_problem = "已有信息还没有被组织成一条可执行、可验证的成长路线"
        primary_goal = f"用小任务验证{direction_text}并积累第一批能力证据"
    opportunity = f"{direction_text} + Python 自动化" if coding and "IT" in direction_text.upper() else (f"{direction_text}的项目化实践" if direction_text != "当前方向" else "通过最小项目验证方向")
    return {
        "current_stage": stage_code,
        "stage_label": stage.get("label", "当前阶段"),
        "strengths": list(dict.fromkeys(strengths)),
        "main_problem": main_problem,
        "opportunity": opportunity,
        "primary_goal": primary_goal,
        "planning_confidence": planning_confidence,
    }
