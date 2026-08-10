"""Shared competency semantics plus focused domain overlays."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompetencyDefinition:
    competency_id: str
    name: str
    domain: str
    prerequisites: list[str] = field(default_factory=list)
    learning_outcomes: list[str] = field(default_factory=list)
    practice_forms: list[str] = field(default_factory=list)
    evidence_types: list[str] = field(default_factory=list)
    assessment_criteria: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    next_competencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DOMAIN_COMPETENCIES: dict[str, CompetencyDefinition] = {
    "finance_accounting": CompetencyDefinition(
        "finance.valuation.dcf", "DCF 估值", "finance", ["会计与财务基础", "公司金融"],
        ["预测 FCFF", "用 WACC 折现", "计算终值", "解释敏感性"], ["简化估值模型", "估值案例复盘"],
        ["financial_model"], ["FCFF 与假设口径一致", "WACC 与折现时点正确", "终值和敏感性分析完整"],
        ["混淆 FCFE 与 FCFF", "终值口径不一致", "只报估值结果不解释假设"], ["可比公司估值", "行业研究"],
    ),
    "law": CompetencyDefinition(
        "law.case.irac", "案例分析与法律检索", "law", ["法律基础", "法条体系"],
        ["识别争点", "检索权威依据", "用 IRAC 论证"], ["案例 brief", "法律 memo"], ["case_analysis", "legal_memo"],
        ["IRAC 结构完整", "至少引用两个法条或权威来源", "说明规则如何适用于事实"],
        ["只复述案情", "堆砌法条不做适用", "忽略反方论证"], ["法律写作", "模拟法庭"],
    ),
    "psychology": CompetencyDefinition(
        "psychology.research.design", "心理学研究设计", "psychology", ["心理学理论", "统计", "研究伦理"],
        ["提出可检验问题", "完成实验设计", "操作化变量", "控制混淆", "规划分析"], ["研究方案", "预注册草案"],
        ["research_proposal"], ["问题可检验", "变量和样本清晰", "方法与问题匹配", "伦理风险已说明"],
        ["相关等于因果", "样本与结论不匹配", "忽略效度"], ["实验实施", "数据分析"],
    ),
    "life_sciences": CompetencyDefinition(
        "biology.paper.extraction", "生物学论文证据提取", "biology", ["生命科学基础", "实验设计"],
        ["提取问题、方法、结果与限制", "区分数据和作者解释"], ["论文证据表", "图表复现"],
        ["paper", "research_poster"], ["准确提取样本和方法", "用图表数据支持结论", "指出至少一个限制"],
        ["只抄摘要", "忽略对照组", "把相关解释成因果"], ["文献综述", "实验设计"],
    ),
    "engineering": CompetencyDefinition(
        "engineering.cad.design", "工程 CAD 设计", "engineering", ["工程制图", "尺寸与公差"],
        ["建立约束明确的零件模型", "生成可检查工程图"], ["CAD 零件", "装配或仿真"],
        ["cad_model", "design_report"], ["模型约束完整", "关键尺寸与公差明确", "导出工程图并自检"],
        ["草图欠约束", "只建外形不考虑制造", "工程图缺关键尺寸"], ["装配设计", "有限元分析"],
    ),
    "art_design": CompetencyDefinition(
        "design.ux.flow", "用户流程与线框", "design", ["用户问题", "信息架构"],
        ["描述核心场景", "绘制用户流程", "形成可测试线框"], ["用户流", "低保真线框", "可用性测试"],
        ["design_case", "portfolio"], ["流程覆盖关键路径", "线框与任务一致", "记录测试反馈和迭代"],
        ["先画界面后定义问题", "只做视觉稿无流程", "没有真实反馈"], ["交互原型", "作品集叙事"],
    ),
    "education": CompetencyDefinition(
        "education.lesson.design", "教学设计", "education", ["学习目标", "学习者分析"],
        ["写可观察目标", "设计教学活动", "对齐形成性评价"], ["教案", "微格教学"],
        ["lesson_plan", "teaching_demo"], ["目标可观察", "活动与目标对齐", "评价能提供学习证据"],
        ["目标写成教师行为", "活动堆叠无逻辑", "评价与目标脱节"], ["课堂实施", "学习评价"],
    ),
    "medicine_health": CompetencyDefinition(
        "medicine.clinical.reasoning", "临床推理", "medicine", ["基础医学", "病史与体征"],
        ["建立问题表", "生成鉴别诊断", "说明检查和处理理由"], ["结构化病例", "临床推理口述"],
        ["clinical_case"], ["提取关键阳性与阴性信息", "鉴别诊断有依据", "下一步检查或处理说明理由"],
        ["过早闭合", "忽略危险征象", "检查清单缺乏优先级"], ["循证决策", "临床技能"],
    ),
    "computer_information": CompetencyDefinition(
        "software.api.fastapi", "FastAPI 接口实现", "software", ["Python", "HTTP", "数据建模"],
        ["实现接口", "校验输入", "处理错误", "编写测试"], ["API 小项目", "自动化测试"],
        ["code", "technical_project"], ["健康检查接口可运行", "请求参数校验明确", "异常响应有自动化测试"],
        ["只有 happy path", "缺少输入校验", "用手工访问代替测试"], ["数据库集成", "部署与观测"],
    ),
    "economics": CompetencyDefinition(
        "economics.empirical.analysis", "实证经济分析", "economics", ["微观/宏观", "统计"],
        ["提出识别问题", "解释变量与模型", "讨论限制"], ["数据分析报告"], ["econometrics_project"],
        ["问题与模型一致", "结果解释有数据支持", "讨论识别假设和限制"], ["相关当因果", "只报显著性"], ["因果推断"],
    ),
    "journalism_communication": CompetencyDefinition(
        "journalism.interview.story", "采访与事实核验", "journalism", ["新闻写作", "信息核验"],
        ["设计问题", "完成采访", "交叉核验事实"], ["采访稿", "报道"], ["interview", "article"],
        ["问题服务报道主题", "关键事实至少双源核验", "区分事实与观点"], ["诱导式提问", "单一来源"], ["深度报道"],
    ),
    "other_emerging": CompetencyDefinition(
        "generic.domain.inquiry", "领域问题分析", "generic", ["专业基础"],
        ["定义问题", "找到权威依据", "形成可检查产出", "复盘限制"], ["案例分析", "小型调研"],
        ["case_analysis", "assessment"], ["问题边界明确", "依据可追溯", "产出可检查", "限制已说明"],
        ["目标过大", "依据不可追溯", "只有过程没有结果"], ["领域实践"],
    ),
}


TAXONOMY_COMPETENCIES: dict[str, CompetencyDefinition] = {
    "nursing": CompetencyDefinition(
        "nursing.assessment.care-plan", "护理评估与安全照护", "nursing", ["基础医学", "护理学基础", "沟通伦理"],
        ["完成护理评估", "提出护理诊断", "制定护理计划", "识别患者安全风险", "设计患者教育"],
        ["护理病例", "技能清单", "患者教育材料"], ["clinical_case", "skills_checklist"],
        ["护理评估资料完整", "护理诊断与资料一致", "护理措施包含患者安全和教育", "记录沟通与效果评价"],
        ["把医学诊断当护理诊断", "措施缺少优先级", "忽略患者教育与安全"], ["临床护理技能", "护理质量改进"],
    ),
    "pharmacy": CompetencyDefinition(
        "pharmacy.mechanism.rational-use", "药理机制与合理用药", "pharmacy", ["基础化学", "生理学", "药理学"],
        ["连接靶点与作用机制", "解释药代动力学", "识别药物相互作用", "提出合理用药与监测要点"],
        ["药物评价", "用药案例", "药物分析记录"], ["case_analysis", "lab_report"],
        ["药物类别、靶点和机制正确", "治疗作用与不良反应由机制支持", "说明相互作用、剂量或监测依据", "合理用药建议边界清楚"],
        ["只背适应证不讲机制", "忽略药代与相互作用", "把学习分析写成处方建议"], ["药物分析", "制剂与质量", "循证药学"],
    ),
    "chemistry": CompetencyDefinition(
        "chemistry.experiment.quantitative", "化学实验与定量分析", "chemistry", ["无机化学", "有机化学", "物理化学", "实验安全"],
        ["说明反应或分析机理", "设计对照与测量步骤", "完成定量计算", "分析误差和实验限制"],
        ["化学实验方案", "定量分析报告"], ["lab_report", "experiment"],
        ["化学问题和反应机理明确", "实验步骤与安全控制完整", "定量结果可复核", "误差来源和改进有依据"],
        ["只列公式不解释化学机理", "忽略空白与对照", "有效数字和误差处理不一致"], ["仪器分析", "有机合成", "物理化学实验"],
    ),
    "chemical_materials_engineering": CompetencyDefinition(
        "materials.structure.property", "材料结构—性能—表征", "materials", ["材料结构", "热力学与相图", "实验基础"],
        ["连接材料结构与性能", "选择合适表征方法", "解释测试结果", "完成材料选择论证"],
        ["表征数据分析", "材料选择报告", "性能测试"], ["lab_report", "technical_report"],
        ["结构与性能关系有证据", "表征方法与问题匹配", "测试条件和数据可追溯", "材料选择说明约束与权衡"],
        ["把材料任务等同机械制图", "只报性能数值不解释结构", "忽略样品和测试条件"], ["失效分析", "工艺优化", "材料设计"],
    ),
    "mathematics_statistics": CompetencyDefinition(
        "mathematics.proof.problem-solving", "数学证明与问题求解", "mathematics", ["定义", "基本定理"],
        ["准确使用定义", "构造证明", "解决问题", "检验边界与反例"], ["证明题", "问题集", "数学建模"],
        ["proof", "problem_set"], ["定义和定理使用正确", "推理步骤完整", "结论边界明确", "至少检查一个反例或特殊情形"],
        ["跳过关键推理", "把例子当证明", "忽略定理条件"], ["高阶证明", "数学建模"],
    ),
    "languages_linguistics": CompetencyDefinition(
        "language.read-write-communicate", "语言阅读与表达", "languages", ["词汇语法", "文本理解"],
        ["理解文本论证", "完成清晰写作", "进行口语表达", "根据目的翻译或分析语言"], ["批判阅读", "写作", "演讲", "翻译"],
        ["writing", "translation", "presentation"], ["主旨与证据提取准确", "表达结构清晰", "语言选择符合语境", "修订依据可说明"],
        ["只做词句替换", "忽略语境和受众", "写作没有修订证据"], ["学术写作", "语言学分析", "文学研究"],
    ),
}


def get_domain_competency(
    discipline_family: str, *, taxonomy_domain: str = "", normalized_major: str = "",
    specialization: str = "", target_role: str = "",
) -> CompetencyDefinition:
    if "用户研究" in target_role or "UX Research" in target_role:
        return CompetencyDefinition(
            "psychology.ux.research", "用户研究", "psychology_ux", ["研究方法", "访谈", "基础统计"],
            ["定义研究问题", "设计访谈或测试", "综合洞察", "连接产品决策"], ["访谈计划", "可用性测试"],
            ["user_research", "portfolio"], ["问题连接产品决策", "样本与方法合理", "洞察有原始证据", "建议可执行"],
            ["把个人意见当洞察", "问题诱导", "没有证据链"], ["研究运营", "产品分析"],
        )
    del normalized_major, specialization
    return TAXONOMY_COMPETENCIES.get(
        taxonomy_domain,
        DOMAIN_COMPETENCIES.get(discipline_family, DOMAIN_COMPETENCIES["other_emerging"]),
    )
