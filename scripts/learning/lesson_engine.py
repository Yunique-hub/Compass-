"""Employment-context micro lesson builder."""
from __future__ import annotations

from typing import Any, Mapping


class LessonEngine:
    def build(
        self, *, skill: str, objective: str, difficulty: str, job_context: str = "",
        domain_context: Mapping[str, Any] | None = None, competency: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        domain_context = domain_context or {}
        competency = competency or {}
        if competency:
            prerequisites = "、".join(str(item) for item in competency.get("prerequisites", [])[:3]) or "必要基础"
            outcomes = "、".join(str(item) for item in competency.get("learning_outcomes", [])[:3]) or objective
            mistakes = "、".join(str(item) for item in competency.get("common_mistakes", [])[:2]) or "缺少可检查证据"
            explanation = f"先用{prerequisites}定位起点，再围绕{outcomes}建立概念—示范—练习链；重点避免{mistakes}。"
            example = f"示例：选择一个小场景，依次说明{outcomes}，并按验收标准留下可检查结果。"
        elif skill.casefold() == "dcf":
            explanation = "先用 FCFF 表示企业可分配现金流，再用 WACC 折现显性预测期与终值；重点检查口径、增长率和折现时点。"
            example = "示例：预测 5 年 FCFF，以 WACC 折现，并用永续增长法计算终值，最后做 WACC/增长率敏感性分析。"
        elif "内科学" in skill:
            explanation = "先做知识诊断：从主诉、病史、体征和检查结果建立问题表，再进行鉴别诊断与临床推理。"
            example = "示例：面对呼吸困难病例，先列危险征象，再按常见病、重症和可逆原因组织鉴别诊断。"
        elif "药理学" in skill:
            explanation = "不要把药名、用途和不良反应分开死记；按‘药物类别→靶点/受体→细胞或器官效应→治疗作用→同机制不良反应’建立一条可推导机制链。"
            example = "示例：先说明药物激动或阻断哪个靶点，再分别推导预期治疗作用、常见不良反应和需要观察的风险信号。"
        elif any(term in skill for term in ("法律", "案例")):
            explanation = f"先把 {skill} 拆成事实、争点、规则、适用与结论，再核对法条或权威来源。"
            example = "示例：用 IRAC 结构完成一段案例分析，并记录法律检索路径。"
        else:
            family = str(domain_context.get("academic_profile", {}).get("discipline_family", "当前领域"))
            explanation = f"先诊断 {skill} 的已会与不会，再理解它在{family}中的核心概念，最后完成一个可检查的小步骤。"
            example = f"示例：围绕 {skill} 写明问题、依据、过程、结果与复盘。"
        return {"lesson_id": f"lesson:{skill}:{difficulty}", "skill": skill, "objective": objective, "difficulty": difficulty, "job_context": job_context, "explanation": explanation, "example": example, "maximum_minutes": 30}
