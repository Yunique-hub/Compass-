"""Evidence-producing exercise builder."""
from __future__ import annotations

from typing import Any, Mapping


class ExerciseEngine:
    def build(
        self, *, skill: str, difficulty: str, acceptance_criteria: list[str] | None = None,
        evidence_type: str = "", domain_context: Mapping[str, Any] | None = None,
        competency: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        domain_context = domain_context or {}
        competency = competency or {}
        if competency:
            criteria = acceptance_criteria or list(competency.get("assessment_criteria") or ["产出可查看", "依据可说明"])
            outcomes = "、".join(str(item) for item in competency.get("learning_outcomes", [])[:3]) or skill
            practices = "、".join(str(item) for item in competency.get("practice_forms", [])[:2]) or "领域练习"
            evidence_types = list(competency.get("evidence_types") or [])
            expected = evidence_type or (evidence_types[0] if evidence_types else "assessment")
            prompt = f"完成一次{practices}：围绕{outcomes}产出可检查结果，并逐项对照验收标准。"
        elif skill.casefold() == "dcf":
            criteria = acceptance_criteria or ["列出 FCFF 预测及关键假设", "使用 WACC 折现显性期现金流", "计算终值", "完成至少一组敏感性分析"]
            prompt, expected = "完成一个简化 DCF 模型：预测 FCFF、应用 WACC、计算终值并解释关键假设。", "financial_model"
        elif "内科学" in skill:
            criteria = acceptance_criteria or ["提取病例关键阳性与阴性信息", "给出有依据的鉴别诊断", "说明下一步检查或处理及理由"]
            prompt, expected = "完成一个内科学病例的结构化临床推理，并标出最不确定的判断。", "clinical_case"
        elif "药理学" in skill:
            criteria = acceptance_criteria or ["正确说明药物类别、靶点以及激动或阻断方向", "从机制推导至少一个治疗作用", "从同一机制解释至少两个不良反应或观察项"]
            prompt, expected = "选本节一个代表药物，写出‘类别→靶点→效应→治疗作用→不良反应/观察’机制链。", "course_assessment"
        elif any(term in skill for term in ("法律", "案例")):
            criteria = acceptance_criteria or ["使用 IRAC 完成案例分析", "引用至少两个法条或权威来源并说明适用关系", "写出一个反方论证或不确定点"]
            prompt, expected = "完成一份 IRAC 案例分析：提炼争点、检索权威依据、适用到事实并给出结论。", "case_analysis"
        else:
            criteria = acceptance_criteria or ["产出可查看", "说明关键依据与步骤", "记录验证结果和一项改进"]
            candidates = list(domain_context.get("evidence_types") or [])
            expected = evidence_type or (candidates[0] if candidates else "assessment")
            prompt = f"完成一个 {skill} 的领域练习，并保留问题、依据、过程、结果与复盘。"
        return {"exercise_id": f"exercise:{skill}:{difficulty}", "skill": skill, "difficulty": difficulty, "prompt": prompt, "acceptance_criteria": criteria, "expected_evidence_type": expected}
