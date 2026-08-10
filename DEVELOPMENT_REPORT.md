# Compass Student Growth 2.5.1 Autonomous Engineering Report

## 1. Executive Summary

本轮把 Compass 明确作为一个可安装的 Codex Skill 交付，而不是普通示例项目。审计共确认 19 个独立缺陷或发布风险，19 个均已修复并建立回归门禁；没有遗留 FAIL。主要改善是：专业归属从字符串命中升级为带主体、极性、时间性和角色的语义模型；Assessment 能识别否定、局部完成和不确定；自然语言自述不再直接提高 verified competency；领域任务采用 taxonomy-first；Secondary Goal、压力降载和目标变更真正改变计划与持久状态；简单知识问答不再进入 onboarding 或完整 Growth Pipeline。

正式运行入口仍为 `scripts/compass_engine.py`，正式产品包为 `dist/compass-student-growth-2.5.1-skill.zip`。`dev` 和 `full` 仅用于测试、审计与上游复现。

## 2. Baseline

修复前基线：

```text
passed:   196
failed:   0
skipped:  1
validator: skill/dev/full directory valid
```

唯一 skip 是当前环境未安装可选的 `neo4j_agent_memory`；默认 SQLite backend 已通过。基线虽然全绿，但没有覆盖附件要求的 A—T 语义场景，因此“测试通过”并不代表专业归属、证据可信度和跨领域隔离正确。

## 3. Problems Discovered

共 19 项，按风险分级如下。

### P0（4）

1. Major 归属会把否定、第三方、目标专业和学习主题误当作用户当前专业，并可能跨会话持久化。
2. Assessment 对句后否定、局部完成和不确定表达错误判为 `MET`，DCF 可产生错误通过。
3. 纯自然语言“我做了”可直接提升 verified competency，Evidence 与验证结果混为一体。
4. 护理、药学、化学和材料任务使用过宽学科族 fallback，出现医生鉴别诊断、数学或机械 CAD 串线。

### P1（11）

5. Goal Portfolio 虽保存 Secondary Goal，但只有 Primary Goal 生成周任务。
6. Resource matcher 为凑足 `minimum` 使用任意已核验资源，英语、护理和法律可被补入 Java/Spring。
7. “什么是机会成本”“IRAC 是什么”进入通用成长/onboarding，而非直接回答。
8. “准备以后读研”“之后考虑读研”“毕业后想读研”等时序变体没有统一识别。
9. Renderer 泄漏 `skill_development`、裸 `questions`，并在只有一个任务时声称“3 件事”。
10. 压力回应只在文案中说降载，实际 capacity 和 current plan 未同步缩减。
11. Tutor 主要依赖 skill 字符串模板，没有完整消费结构化 CompetencyDefinition。
12. 只补充学习时间的后续轮次可把稳定实习/就业目标覆盖成“学习提升”。
13. 用户从投行改为商业分析时，旧角色的历史表述可能继续成为当前目标，且缺少目标历史。
14. “算法学得很痛苦”能路由到学习意图，但没有正式计划时 Tutor 缺少 skill，无法直接帮助。
15. `UX Research` 目标没有进入就业规划；修复过程中还发现目标岗位推导必须晚于历史 pathway 恢复，否则会破坏跨轮连续性。

### P2（4）

16. DCF 默认标准把终值和敏感性分析合成一项，无法给出四项独立状态。
17. 未受信任的 `submission.passed=true` 可以绕过逐项证据判断。
18. Evidence ID 与 verified evidence ID 没有清晰区分，重新规划可能被低可信文本触发。
19. 护理/药学 alias 曾并入临床医学 profile，长尾专业与精确 taxonomy 的知识来源标记不够清晰。

## 4. Root Causes

- 专业识别把“字符串出现”当成“用户当前身份声明”，没有同时建模 subject、polarity、temporality 和 role。
- Assessment 用全句关键词存在性代替局部从句状态，没有将标准和否定范围、部分完成、不确定表达绑定。
- Evidence 管道把“有文本支持”和“已验收”压缩成同一个布尔通过，`passed` 也没有来源信任边界。
- Domain resolver 先取宽泛 discipline family，再看具体 taxonomy；Task Factory 因而只能生成家族级模板。
- 多目标、压力、资源 minimum 和 Renderer 都有“数据结构存在但未驱动最终行为”的断层：状态记录了，实际任务/容量/文本没有消费。
- Intent、Known Facts 与 Pathway 各自维护词表，时序变体和英文角色没有共享稳定语义；恢复顺序不正确时，新推导会覆盖历史确认状态。
- Tutor 运行时传递的是 display string，而规划阶段已生成的结构化 competency 没有贯穿 Lesson、Exercise、Hint 和 Assessment。

## 5. Fixes

### 5.1 Major 与学术状态

```text
Before: 只要句中出现 alias 就可能确认当前专业。
After:  MajorMention 带 subject/polarity/temporality/role；current、previous、target、topic 分离，只有明确当前声明可持久化。
Files:  scripts/academic/major_engine.py, scripts/core/known_facts.py, reference/academic_profiles.json
Tests:  negation、third-party、target、past、completed transition、cross-session gate
```

### 5.2 Assessment 与 Evidence Trust

```text
Before: 全句词命中与 passed 布尔可直接通过并提升能力。
After:  按局部从句解析 MET/PARTIAL/MISSING/UNCLEAR；passed 仅接受 trusted_structured；证据分级并只让已验收层提高 verified_level。
Files:  scripts/learning/assessment_engine.py, scripts/competency/evidence_engine.py, scripts/competency/profile.py, scripts/growth_orchestrator.py
Tests:  DCF 否定、部分、不确定、untrusted passed、text-supported persistence
```

### 5.3 Taxonomy-first 与领域任务

```text
Before: family fallback 先于精确专业，护理/药学/化学/材料产生邻域任务。
After:  taxonomy → curated competency → family/generic fallback；为护理、药学、化学、材料、数理、语言等补结构化 competency 与任务 blueprint。
Files:  scripts/competency/domain_intelligence.py, scripts/learning/domain_task_factory.py, reference/academic_profiles.json
Tests:  34-domain Golden Matrix、护理/药学/化学/材料隔离、长尾 fallback
```

### 5.4 Goal、Pathway 与压力

```text
Before: Secondary Goal、压力和目标变更只影响描述或部分状态。
After:  每个 active goal 生成独立 goal-tagged task 并受总预算约束；压力直接缩减 capacity/current plan；新目标成为 current，旧目标进入 history。
Files:  scripts/core/goal_planner.py, scripts/academic/pathway_engine.py, scripts/compass_engine.py, scripts/memory/memory_engine.py
Tests:  法考+律所、10h→压力减半、投行→商业分析、constraint-only follow-up
```

### 5.5 Intent、Direct QA、Tutor 与 Resource

```text
Before: 简单 QA 被 onboarding；无计划的学习困难无法开课；Tutor 依赖字符串；Resource 用跨领域 filler 补数量。
After:  DirectAnswerHandler 支持可注入 LLM adapter 与安全离线概念答案；当前 topic 可启动 ad-hoc Tutor；Tutor 消费 CompetencyDefinition；资源不足明确返回不足而不串线。
Files:  scripts/core/direct_answer.py, scripts/core/intent_router.py, scripts/learning/{lesson,exercise,tutor}_engine.py, scripts/resource_matcher.py
Tests:  opportunity cost/IRAC/p-value/WACC、算法困难、competency-driven tutor、英语/护理/法律资源隔离
```

## 6. Major / Academic Model

`current` 只来自用户明确的当前专业声明或明确完成的转专业；`previous` 保存“以前学过”和已完成转专业的来源专业；`target` 保存“想转/计划转”的目标，不覆盖 current；`topic` 表示当前学习对象，只在当前轮使用，不作为长期 Major。否定句和第三方主体均被 persistence gate 拒绝。双专业保留 `raw_major + secondary_major`，长尾专业保留原始名称并标注 `knowledge_source=family_fallback`。

## 7. Evidence Trust

实际等级为：

```text
SELF_REPORTED
TEXT_SUPPORTED
ARTIFACT_SUBMITTED
ARTIFACT_ASSESSED
EXECUTION_VERIFIED
EXTERNAL_VERIFIED
```

自然语言练习结果默认是 `TEXT_SUPPORTED`，可保留 evidence ID 和支持状态，但 `verified_level` 保持不变。结构化标准逐项验收可形成 `ARTIFACT_ASSESSED`；执行或可靠外部结果使用更高等级。Profile 分别保存 evidence IDs 与 verified evidence IDs，Growth Orchestrator 只在 verified level 实际变化时重新规划。

## 8. Assessment

- Negation：按与标准最近的局部从句识别“没做/没有/未完成”，支持句后共享否定。
- Partial：识别“只做一半/部分完成”等表达，输出 `PARTIAL`。
- Uncertainty：识别“不确定方法对不对”等表达，输出 `PARTIAL/UNCLEAR` 并降低置信度。
- Criterion matching：DCF 的 FCFF、WACC、Terminal、Sensitivity 是四个独立标准；只有全部关键标准 `MET` 才通过。
- Structured trust：外部 `passed` 只有在 `trusted_structured=true` 时才可作为受信结构输入，仍保留 verification basis。

## 9. Domain Intelligence

Resolver 顺序为 `taxonomy_domain → curated competency → discipline_family → generic fallback`。护理使用护理评估、患者安全；药学使用药理、合理用药；应用化学使用实验设计与化学证据；材料使用材料选择/表征，不默认机械 CAD。心理学读研与 UX Research 分别生成研究设计和产品问题导向用户研究。未知专业不返回 unsupported，而是保留原专业名，使用学科族/通用任务并明确具体要求需验证。

## 10. Resource

跨领域 filler 已删除。`minimum` 是期望数量，不再是必须凑满的数量；相关且已核验资源不足时返回 `INSUFFICIENT_RELEVANT_RESOURCES`，不会从任意领域 registry 补 Java/Spring。测试确认英语写作、护理评估和法律检索均保持领域隔离。

## 11. Intent / Router

高置信 deterministic route 仍是主入口，Understanding 提取 current topic、difficulty、goal、target role、primary/secondary intent 后参与 action decision。新增稳定概念问句直达 `KNOWLEDGE_QA`，学习困难直达 Tutor，读研时序变体共享 `has_graduate_school_signal`，`UX Research/用户研究` 可形成就业规划。Pathway 先恢复已确认 `primary_need`，确无历史路径时才从目标岗位推导，避免后续容量消息覆盖既有目标。

## 12. Goal Portfolio

Primary 和每个 active Secondary Goal 都进入 `build_domain_tasks`。任务携带 `goal_type`，按 portfolio allocated hours 缩放，并受 weekly capacity 总预算约束。法考 + 律所实习场景同时生成资格考试与实习任务，总时长不超过用户给出的 8 小时。

## 13. Tutor

Tutor 已改为 competency-driven。Goal Planner 生成的 `CompetencyDefinition` 贯穿 Lesson、Exercise 和 Tutor：prerequisites 用于诊断，learning outcomes 用于教学，practice forms/evidence types 用于练习，assessment criteria 用于验收，common mistakes 用于反馈与 Hint，next competencies 用于后续学习。字符串 fallback 只保留给无正式任务的兼容场景；“算法学得很痛苦”会用当前 topic 直接开启 ad-hoc Tutor。

## 14. Memory

- Persistence gate：Major 只接受明确用户主体、肯定、当前/已完成转换的事实；目标、第三方、否定和 topic 不进入 current major。
- Lifetime：confirmed profile、稳定 goal、verified/text-supported evidence 按结构化状态跨会话保留；current topic 与临时压力不永久保留。
- Cross-session：重新创建 Engine 后确认专业可恢复，错误 candidate major 不恢复，topic 清空，新目标为 current 且旧目标留在 history，text-supported evidence 保留但 verified level 不提高。
- Dedup：语义记录继续使用 deterministic record key/upsert，等价信息不会无界追加。

## 15. Tests

最终完整结果：

```text
passed:   239
failed:   0
skipped:  1
```

- New tests：3 个文件，43 个 collected cases；覆盖自主语义审计、Evidence Trust 与 A—T 验收。
- Modified tests：更新资源隔离契约与 archive version 断言；旧行为测试未被批量改写。
- Semantic regression tests：Major attribution、Assessment scope、Evidence levels、domain isolation、goal continuity、cross-session、direct QA 和 stress load 均有行为级断言。
- Golden：34/34；完整专业对话：14/14；A—T：20/20。
- Skip：仅可选 `neo4j_agent_memory` 未安装；不是核心失败。

## 16. Manual Scenario Results

| Scenario | Result | 结果摘要 |
| --- | --- | --- |
| A | PASS | 算法困难不识别法学、不写 Major、直接 Tutor |
| B | PASS | 否定法学不保存当前专业 |
| C | PASS | 第三方专业不修改用户专业 |
| D | PASS | 法学是 target，current 不覆盖 |
| E | PASS | Nursing task，无医生/Java 串线 |
| F | PASS | Pharmacy 药理与合理用药 |
| G | PASS | Chemistry 实验任务，不当数学 |
| H | PASS | Materials 不默认机械 CAD |
| I | PASS | Psychology graduate 含统计/方法/文献/证据 |
| J | PASS | Psychology UX 生成产品/访谈用户研究任务 |
| K | PASS | 两个 Goal 均有任务且不超 8h |
| L | PASS | DCF 状态为 MET/MISSING/MISSING/MISSING |
| M | PASS | WACC 不确定不是高置信 MET |
| N | PASS | 机会成本直接回答 |
| O | PASS | IRAC 直接回答 |
| P | PASS | 英语写作无 Java/Spring |
| Q | PASS | 土木保留并生成数据桥接计划 |
| R | PASS | 数学+经济双专业路径比较 |
| S | PASS | 葡萄酒工程诚实 fallback |
| T | PASS | 实际 capacity 减半且任务 ≤1 |

首次 A—T 运行的两个失败来自测试断言误用公开结构/固定文案，修正验收代码后 20/20；产品场景没有残留 FAIL。

## 17. Package Validation

```text
skill: PASS — 可安装运行包，skill-creator 与 Compass ZIP validator 通过
dev:   PASS — 测试/开发/报告包，ZIP validator 通过
full:  PASS — dev + vendor/upstream 审计快照，ZIP validator 通过
```

三个包均为 2.5.1，ZIP 根目录直接包含项目文件；skill/dev 不含 vendor，skill 不含 tests、开发报告、缓存、数据库或运行数据。正式安装只使用 `skill` 包。

## 18. Compatibility

- SQLite：保持现有表和 upsert 接口，不要求破坏性迁移；新增字段存储在兼容 JSON payload 中。
- Memory：现有 profile/goal/competency/growth_state API 保留；新增 evidence trust 和 goal history 为向后兼容字段。
- Archive：旧 2.x archive 可读，保存时升级为 2.5.1；顶层兼容 wrapper 与 `profile_state/business_state` 仍保留。
- Evidence：旧结构化 `criteria_met` 路径保留并标记为 `ARTIFACT_ASSESSED`；旧自然语言结果不会被错误当成 verified mastery。

## 19. Files Changed

主要文件：

- Skill 与发布：`SKILL.md`、`agents/openai.yaml`、`manifest.yaml`、`pyproject.toml`、`scripts/pack_skill.py`、`scripts/validate_package.py`。
- 专业与路径：`scripts/academic/major_engine.py`、`scripts/academic/pathway_engine.py`、`reference/academic_profiles.json`。
- Understanding/Intent/Plan：`scripts/core/intent_router.py`、`scripts/core/known_facts.py`、`scripts/core/direct_answer.py`、`scripts/core/goal_planner.py`、`scripts/compass_engine.py`。
- Domain/Tutor/Assessment：`scripts/competency/domain_intelligence.py`、`scripts/learning/domain_task_factory.py`、`scripts/learning/assessment_engine.py`、`scripts/learning/lesson_engine.py`、`scripts/learning/exercise_engine.py`、`scripts/learning/tutor_engine.py`。
- Evidence/Memory/Resource：`scripts/competency/evidence_engine.py`、`scripts/competency/profile.py`、`scripts/growth_orchestrator.py`、`scripts/memory/memory_engine.py`、`scripts/resource_matcher.py`。
- 验收与文档：`tests/integration/test_autonomous_audit_v251.py`、`tests/unit/test_evidence_trust_v251.py`、`tests/e2e/test_manual_scenarios_v251.py`、`tests/e2e/manual_cases.md`、`README.md`、`ENVIRONMENT_BASELINE.md`。

## 20. Remaining Risks

1. Deterministic 中文语义解析已覆盖本轮关键变体，但更复杂的反讽、长距离指代和多主体嵌套仍可能需要可注入 LLM/NLU 适配器或更多语料评估。
2. 长尾专业能安全 fallback，但院校课程、资格政策、申请 deadline 和实时行业要求必须依赖可追溯外部来源；本地 taxonomy 不能冒充最新事实。
3. `TEXT_SUPPORTED` 能防止低质量自述提升能力，但复杂附件、模型文件、临床/实验操作和完整作品集仍需要专用解析器、执行沙箱或人工验收才能升到更高信任等级。

## 21. Recommended Next Steps

1. 在干净 Codex 环境安装 `compass-student-growth-2.5.1-skill.zip`，执行一次真实触发、跨会话恢复和卸载/遗忘 smoke test。
2. 用匿名真实对话建立 major attribution、criterion scope 和 domain leakage 的离线评测集，持续测 precision/recall，而不是只增加示例词表。
3. 为高价值领域逐步接入可追溯资料与 artifact assessor；每次扩展都维持 Evidence Trust 门禁和 taxonomy-first 隔离测试。
