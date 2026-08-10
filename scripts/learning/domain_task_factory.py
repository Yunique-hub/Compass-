"""Create small, domain-authentic tasks from competency semantics."""
from __future__ import annotations

import copy
from typing import Any

from scripts.competency.domain_intelligence import CompetencyDefinition, get_domain_competency


TASK_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "finance_accounting": {"title": "完成一版简化 DCF 估值模型", "actions": ["预测 5 年 FCFF 并写出关键假设", "用 WACC 折现并计算终值", "制作 WACC × 永续增长率敏感性表"], "output": "DCF 模型与一页假设说明", "hours": 3.0},
    "law": {"title": "完成一份 IRAC 案例分析", "actions": ["从案情提炼争点与关键事实", "检索并引用至少两个法条或权威来源", "写出规则适用、反方观点和结论"], "output": "800–1200 字案例 memo 与检索记录", "hours": 2.5},
    "psychology": {"title": "设计一项可检验的心理学研究", "actions": ["提出研究问题和可证伪假设", "操作化自变量、因变量和混淆变量", "写出样本、流程、伦理与分析计划"], "output": "两页研究设计草案", "hours": 3.0},
    "life_sciences": {"title": "提取一篇论文的证据链", "actions": ["记录研究问题、样本、对照和方法", "从一张核心图表提取结果", "区分作者结论、数据支持和研究限制"], "output": "论文证据提取表", "hours": 2.0},
    "engineering": {"title": "建立一个可制造零件的 CAD 模型", "actions": ["定义功能、关键尺寸和约束", "完成全约束草图与三维模型", "导出含公差的工程图并做干涉/制造自检"], "output": "CAD 文件、工程图与自检记录", "hours": 3.0},
    "art_design": {"title": "完成核心场景的用户流与线框", "actions": ["写出用户、任务和成功条件", "画出主路径与两个异常分支", "制作 5–8 个低保真线框并请一人走查"], "output": "用户流、线框和走查记录", "hours": 3.0},
    "education": {"title": "完成一节课的目标—活动—评价教案", "actions": ["写出 2–3 个可观察学习目标", "设计导入、练习与反馈活动", "制作与目标对齐的退出卡或评分量规"], "output": "一页教案与形成性评价材料", "hours": 2.5},
    "medicine_health": {"title": "完成一个病例的结构化临床推理", "actions": ["提取关键阳性、阴性信息和危险征象", "按可能性与危险性排序鉴别诊断", "说明下一步检查或处理及理由"], "output": "病例问题表与鉴别诊断记录", "hours": 2.0},
    "computer_information": {"title": "实现并测试一个 FastAPI 小接口", "actions": ["实现 GET /health 和一个带参数的业务接口", "用 Pydantic 校验输入并定义异常响应", "用 TestClient 编写正常与异常自动化测试"], "output": "可运行代码、测试与 README", "hours": 3.0},
    "economics": {"title": "完成一页实证分析备忘录", "actions": ["定义问题、样本和关键变量", "运行一个描述或回归分析并解释结果", "说明识别假设、替代解释和限制"], "output": "分析表、图和一页 memo", "hours": 3.0},
    "journalism_communication": {"title": "完成一次小型采访与事实核验", "actions": ["围绕报道主题设计 8 个开放问题", "完成并整理一次 20 分钟采访", "对两个关键事实做独立来源核验"], "output": "采访稿、核验表与 500 字报道", "hours": 3.0},
    "other_emerging": {"title": "完成一个领域案例的证据分析", "actions": ["把问题缩小为一个可回答问题", "找到两项权威依据并记录出处", "形成结论、限制和下一步验证"], "output": "两页案例分析", "hours": 2.0},
}

TAXONOMY_TASK_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "nursing": {"title": "完成一份护理评估与安全照护计划", "actions": ["按主观、客观资料完成护理评估并识别患者安全风险", "根据资料提出有依据的护理诊断和优先级", "制定护理措施、患者教育和效果评价方法"], "output": "护理评估表、护理计划与患者教育卡", "hours": 2.5},
    "pharmacy": {"title": "完成一份药理机制与合理用药分析", "actions": ["选择一个药物类别，连接靶点、作用机制与治疗作用", "从机制和药代解释不良反应、相互作用与监测项", "用教育性语言写出合理用药边界，不给个体处方"], "output": "药物机制链、相互作用表与用药教育卡", "hours": 2.5},
    "chemistry": {"title": "完成一次化学定量实验设计与结果分析", "actions": ["明确化学问题、反应或分析机理和实验安全要求", "设计样品、对照、测量步骤与定量计算", "分析误差来源并提出一次可验证改进"], "output": "化学实验方案、计算表与误差分析", "hours": 2.5},
    "chemical_materials_engineering": {"title": "完成一份材料结构—性能—表征分析", "actions": ["选定材料与使用约束，提出结构—性能假设", "选择一种表征和一种性能测试并说明依据", "用数据比较候选材料，记录测试条件、限制和选择权衡"], "output": "材料表征与性能分析报告", "hours": 2.5},
    "mathematics_statistics": {"title": "完成一道定理证明与变式检验", "actions": ["重写定义、定理条件和目标", "逐步完成证明或问题求解", "检查一个边界情形、反例或变式"], "output": "证明稿、条件清单与变式复盘", "hours": 2.0},
    "languages_linguistics": {"title": "完成一次阅读—写作—修订闭环", "actions": ["提取文本主旨、论证和语言证据", "面向明确受众完成一篇短文或翻译", "根据结构、语境和语言准确性完成一次修订"], "output": "标注文本、初稿、修订稿与修订说明", "hours": 2.0},
}

PATHWAY_LABELS = {
    "professional_qualification": "资格考试",
    "internship": "实习准备",
    "graduate_school": "研究生路径",
    "employment": "就业准备",
    "career_transition": "跨领域转型",
    "skill_development": "专业能力提升",
    "academic_improvement": "学业提升",
}


def build_domain_task(
    discipline_family: str, *, taxonomy_domain: str = "", normalized_major: str = "",
    specialization: str = "", target_role: str = "", competency: CompetencyDefinition | None = None,
    foundation: bool = False,
) -> dict[str, Any]:
    definition = competency or get_domain_competency(
        discipline_family, taxonomy_domain=taxonomy_domain, normalized_major=normalized_major,
        specialization=specialization, target_role=target_role,
    )
    if foundation and discipline_family == "finance_accounting":
        definition = CompetencyDefinition(
            "finance.accounting.statements", "财务报表基础", "finance", ["基础会计"],
            ["连接三张报表", "解释现金流与利润差异"], ["报表勾稽练习"], ["excel_model"],
            ["三张报表核心项目识别正确", "至少解释两条报表勾稽关系", "用三个比率解释公司变化"],
            ["只看利润不看现金流", "混淆存量与流量"], ["财务分析", "DCF 估值"],
        )
    if "数据分析" in target_role and discipline_family != "computer_information":
        definition = CompetencyDefinition(
            "transition.data.analysis", "数据分析桥接实践", "data", ["领域知识", "基础统计"],
            ["定义分析问题", "清理数据", "制作图表", "解释限制"], ["小型数据项目"], ["data_analysis"],
            ["问题与原专业场景相关", "数据清理过程可复现", "至少两张图表支持结论", "说明限制和下一步"],
            ["只学工具不定义问题", "图表没有结论", "忽略数据质量"], ["SQL", "统计建模"],
        )
    blueprint = TAXONOMY_TASK_BLUEPRINTS.get(taxonomy_domain, TASK_BLUEPRINTS.get(discipline_family, TASK_BLUEPRINTS["other_emerging"]))
    if foundation and discipline_family == "finance_accounting":
        blueprint = {"title": "完成三张财务报表勾稽练习", "actions": ["选一家公司列出利润表、资产负债表和现金流量表核心项目", "解释净利润如何连接经营现金流与留存收益", "标出三个关键比率并解释变化原因"], "output": "三表勾稽表与一页分析", "hours": 2.5}
    if definition.competency_id == "psychology.ux.research":
        blueprint = {"title": "完成一次产品问题导向的用户研究", "actions": ["把产品决策转成研究问题", "设计 5 人访谈或可用性测试", "用原始证据综合洞察并提出三项建议"], "output": "研究计划、证据表和洞察报告", "hours": 3.0}
    elif definition.competency_id == "transition.data.analysis":
        blueprint = {"title": "用原专业数据完成一个分析小项目", "actions": ["从原专业选一个可回答问题和小型数据集", "完成清理、描述统计和两张解释性图表", "写出结论、限制与目标岗位能力映射"], "output": "可复现分析文件与两页报告", "hours": 3.0}
    return {
        "task_id": f"domain:{definition.competency_id}",
        "skill": definition.name,
        "title": blueprint["title"],
        "why": f"该任务直接验证{definition.name}，并产生领域可识别的证据。",
        "estimated_time": blueprint["hours"],
        "specific_action": list(blueprint["actions"]),
        "output": [blueprint["output"]],
        "acceptance_criteria": list(definition.assessment_criteria),
        "evidence": blueprint["output"],
        "evidence_type": definition.evidence_types[0],
        "fallback": f"时间不足时先完成第一步，并提交一个可检查的半成品与具体卡点。",
        "competency_definition": definition.to_dict(),
    }


def build_domain_tasks(
    discipline_family: str, *, taxonomy_domain: str = "", normalized_major: str = "",
    specialization: str = "", target_role: str = "", maximum: int = 3, foundation: bool = False,
    goal_portfolio: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    primary = build_domain_task(
        discipline_family, taxonomy_domain=taxonomy_domain, normalized_major=normalized_major,
        specialization=specialization, target_role=target_role, foundation=foundation,
    )
    portfolio = goal_portfolio or {}
    primary_goal = dict(portfolio.get("primary") or {})
    primary["goal_type"] = str(primary_goal.get("goal_type") or "academic_improvement")
    primary["allocated_hours"] = float(primary_goal.get("allocated_hours") or primary["estimated_time"])
    tasks = [primary]
    for item in list(portfolio.get("secondary") or []):
        if len(tasks) >= max(1, maximum):
            break
        goal_type = str(item.get("goal_type") or "secondary")
        label = PATHWAY_LABELS.get(goal_type, str(item.get("description") or "次要目标"))
        secondary = copy.deepcopy(primary)
        secondary["task_id"] = f"{primary['task_id']}:{goal_type}"
        secondary["goal_type"] = goal_type
        secondary["title"] = f"面向{label}完成一份{primary['skill']}实践证据"
        secondary["why"] = f"让{label}不只停留在目标列表中，而是产生独立行动和可检查证据。"
        secondary["specific_action"] = [f"选择一个与{label}真实要求相关的小场景", *primary["specific_action"][:2]]
        secondary["output"] = [f"{label}版{primary['output'][0]}"]
        secondary["evidence"] = secondary["output"][0]
        allocated = float(item.get("allocated_hours") or 2.0)
        secondary["allocated_hours"] = allocated
        secondary["estimated_time"] = min(2.0, max(1.0, allocated))
        tasks.append(secondary)
    return tasks[:max(1, maximum)]
