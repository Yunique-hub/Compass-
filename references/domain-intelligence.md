# Domain Intelligence

## 目录

1. Resolver
2. CompetencyDefinition
3. Taxonomy 路由
4. 领域任务示例
5. 长尾 fallback
6. 串线检查

## 1. Resolver

按以下顺序解析领域：

```text
用户明确专业/细分方向
→ 精确 taxonomy
→ 目标路径或岗位 overlay
→ curated competency
→ discipline-family competency
→ generic domain inquiry
```

目标路径可以改变同一专业的能力重点。例如心理学读研侧重研究设计，心理学 UX Research 侧重产品问题、访谈、可用性测试和洞察证据。

## 2. CompetencyDefinition

为每个能力组织：

- Domain
- Competency name
- Prerequisites
- Learning outcomes
- Practice forms
- Evidence types
- Assessment criteria
- Common mistakes
- Next competencies

规划、Tutor、Assessment 和 Evidence 必须消费同一份定义。不要规划一个领域、用另一个领域教学，再用通用标准验收。

## 3. Taxonomy 路由

可使用以下学术 taxonomy 作为起点；学校自定义专业应保留原名并找到最近的学科族：

| Taxonomy | 示例专业 | 常见能力方向 |
| --- | --- | --- |
| computer_information | 计算机、软件、信息安全 | 编程、系统、数据、工程方法 |
| electronic_electrical | 电子、通信、电气 | 电路、信号、嵌入式、系统实验 |
| mechanical_industrial | 机械、机器人工程、工业工程 | 制图、设计、制造、仿真、优化 |
| civil_built_environment | 土木、测绘、工程管理 | 结构、工程数据、规范、项目实践 |
| chemical_materials_engineering | 化工、材料、能源化工 | 工艺、材料表征、安全、实验 |
| chemistry | 化学、应用化学 | 实验设计、分析方法、机理与数据 |
| mathematics_statistics | 数学、统计 | 证明、建模、概率、推断 |
| physics_astronomy | 物理、天文 | 数学物理、实验、建模 |
| geography_earth | 地理、地质、遥感 | 空间分析、野外/数据证据 |
| life_sciences | 生物、生物技术 | 实验、文献证据、统计、研究方法 |
| agriculture_environment | 农学、环境、葡萄酒工程 | 领域系统、实验/调查、质量与数据 |
| veterinary_animal | 动物医学、动物科学 | 动物健康、实验、伦理与安全 |
| clinical_medicine | 临床、口腔等 | 病例推理、临床安全、沟通；不代替诊疗 |
| nursing | 护理学 | 护理评估、患者安全、护理计划、沟通 |
| pharmacy | 药学、临床药学 | 药理、制剂、合理用药、证据评价 |
| public_health | 公卫、预防医学 | 流行病学、统计、健康项目评价 |
| psychology | 心理学、应用心理 | 理论、统计、研究伦理、研究设计 |
| economics | 经济学 | 理论、计量、数据、政策分析 |
| finance_accounting | 金融、会计、财务管理 | 会计、估值、财务分析、模型 |
| business_management | 工商管理、市场、人力 | 商业分析、运营、组织与沟通 |
| law | 法学、知识产权 | 法条体系、检索、IRAC、法律写作 |
| education | 教育学、学前、教育技术 | 学习科学、教学设计、观察与评价 |
| languages_linguistics | 英语、小语种、语言学 | 阅读、写作、翻译、跨文化沟通 |
| literature_history_philosophy | 中文、历史、哲学 | 文本、论证、史料、研究写作 |
| journalism_communication | 新闻、传播、广告 | 采访、核验、叙事、受众与伦理 |
| art_design | 视觉、产品、交互、动画 | 设计过程、用户研究、作品集 |
| architecture | 建筑、城乡规划、景观 | 空间、规范、设计表达、项目证据 |
| sports | 体育教育、运动训练 | 训练设计、测评、安全与教学 |
| tourism_hospitality | 旅游、酒店、会展 | 服务设计、运营、体验与项目 |
| undecided | 未分流、大类招生 | 通用能力、方向探索、低成本体验 |
| other_emerging | 新专业、交叉专业 | 领域问题定义、权威依据、可检查产出 |

## 4. 领域任务示例

- 金融 DCF：完成简化模型，包含 FCFF、WACC、终值、敏感性和假设说明。
- 法学：完成 IRAC 案例 memo，引用至少两个相关规则并说明适用性。
- 护理：基于模拟病例完成护理评估、风险识别、护理计划和患者安全说明。
- 药学：完成药物信息评价或合理用药证据摘要，不做未经授权的个体处方建议。
- 化学：设计一个可重复实验，说明变量、对照、安全、记录和误差。
- 材料：比较材料选择或表征结果，说明样品、条件、结构—性能联系和限制。
- 心理读研：写研究问题、可证伪假设、变量、样本、伦理和分析计划。
- 心理 UX：把产品决策转成研究问题，设计访谈/可用性测试，保留原始证据链并给建议。
- 生物：提取论文研究问题、方法、数据、结论、限制和可复现证据。
- 教育：完成目标—活动—评价一致的教案，并设计观察证据。
- 设计：完成用户流、线框或作品集案例，说明问题、过程、取舍和验证。
- 语言：完成面向特定受众的写作/翻译，并保留修订依据。
- 机械：完成可制造零件或工程分析，说明约束、公差/条件和验证。
- 土木转数据：用土木场景数据完成清理、统计、图表、结论和限制，形成桥接证据。

## 5. 长尾 fallback

未知专业不代表无领域知识。先：

1. 保留用户原始专业名；
2. 识别其研究对象、常用方法、典型实践和成果形式；
3. 映射到最近学科族；
4. 生成一个领域问题分析、案例、实验/调查或小型项目；
5. 明确具体院校课程、资格和行业要求仍需验证。

通用任务至少包含问题边界、两项可追溯依据、可检查产出、限制和下一步验证。不要回复 unsupported。

## 6. 串线检查

输出前搜索是否出现无来源的领域标志：

- 非计算机领域是否被加入 FastAPI、Java、GitHub、LeetCode。
- 护理/药学是否被默认成医生鉴别诊断。
- 材料是否被默认成机械 CAD。
- 化学是否被当成数学证明。
- 语言/法律是否因资源数量不足被补技术教程。

只有用户目标明确需要跨领域能力时，才能加入这些内容，并解释桥接关系。
