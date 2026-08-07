# Compass 2.2.0 Development Report

## Architecture Summary

Compass 2.1.0 已具备行动优先交互、阶段判断、初步计划、SQLite 记录记忆、考试 Review、自改进/演化/主动建议雏形，以及六份本地锁定上游快照。2.2.0 没有重建项目或删除成熟模块，而是在现有 `scripts/compass_engine.py` 上完成核心架构升级：

- 记忆从通用记录召回升级为 Profile、Career Goal、Competency、Growth State、Semantic Memory 五类永久状态；SQLite 是 canonical store，Neo4j Agent Memory 是可选图谱/语义复制层。
- 城市和岗位从有限识别升级为开放文本 Target Resolver + Job Normalizer + Query Expansion；Alias 是可成长缓存，不是白名单。
- 招聘从单一快照/JD 脚本升级为 Public Search、Agent Browser、User JD、Versioned Snapshot 的 Provider 架构；没有真实数据时返回 `insufficient`，不造市场百分比。
- 学习从“生成计划”升级为 Market → Gap → Plan → Tutor → Assessment → Evidence → Competency → Replan 的证据闭环。
- Self Improving、Capability Evolver、Proactive 不再是孤立模块：重复的去标识化 Pattern 可产生策略 Candidate/Trial，主动建议反馈可继续进入改进链；运行时禁止修改源码和后台假推送。
- Review Brain 作为 2.1 的成熟考试/材料业务模块继续保留；2.2 的“五脑”专指 Agent Memory、Agent Browser、Self Improving Agent、Capability Evolver、Proactive Agent 五个基础能力层。

统一运行顺序：

```text
SAFETY → PERSISTENT MEMORY RESTORE → SEMANTIC/GRAPH RETRIEVAL
→ INTENT/FACT/STAGE/SUFFICIENCY/ACTION → CAREER TARGET
→ RECRUITMENT → MARKET → GAP → PLAN/TUTOR/ASSESSMENT
→ EVIDENCE → COMPETENCY → REPLAN → PROACTIVE
→ SELF IMPROVEMENT → EVOLUTION → MEMORY PERSIST → RESPONSE
```

## Five-Brain Integration

### Agent Memory

- 上游能力：`neo4j-labs/agent-memory` 的实体、关系、上下文检索与长期语义记忆思想；锁定提交见 `reference/open_source/upstream-lock.json`。
- Compass Adapter：`scripts/integrations/neo4j_memory_adapter.py` 的 `Neo4jMemoryAdapter`；拒绝 hidden reasoning 字段并按 `user_id` 隔离实体。
- 实际入口：`MemoryEngine.load_user_context()` 在每轮意图识别前执行；`persist_turn()` 在响应前写 Profile/Goal/Competency/Growth/Semantic，`persist_growth_graph()` 写成长关系。
- Fallback：`CompositeMemoryBackend` 始终先写 `SQLiteMemoryBackend`；Neo4j 缺包、缺凭据或连接失败时返回健康状态并继续运行。
- 测试：`tests/unit/test_memory_v22.py` 覆盖跨实例恢复、目标版本历史、隐藏推理过滤和 Neo4j 可选降级；五脑合同测试用 Fake Neo4j 验证实体写入。

### Agent Browser

- 上游能力：`vercel-labs/agent-browser` 公共网页打开、快照和文本读取。
- Compass Adapter：`AgentBrowserAdapter` 仅允许公开 HTTPS read/get text；`AgentBrowserProvider` 转换为带 URL/采集时间的 `JobRecord`。
- 实际入口：`RecruitmentEngine → ProviderRouter → AgentBrowserProvider → AgentBrowserAdapter.read_public_page()`。
- Fallback：Reader/CLI 不可用或页面失败时报告 Provider 状态，继续 User JD 或 Versioned Snapshot；不投递、不上传、不填表、不绕过验证码。
- 测试：`tests/unit/test_recruitment_v22.py` 验证实际输入输出并拒绝 fill/upload/submit；`five_brain_demo.py` 用五个明确标记为 synthetic 的公共页面夹具验证 Provider 链，不把它们计作真实市场。

### Self Improving Agent

- 上游能力：`LEARNINGS/ERRORS/FEATURE_REQUESTS`、Pattern Key、Recurrence Count、Promotion。
- Compass Adapter：`SelfImprovingAdapter` 和 `ImprovementEngine.observe_event()`；只保留去标识化摘要、reason code 和允许的运行上下文。
- 实际入口：用户反馈、浏览器/解析错误和主动建议反馈进入 Pattern Store；同 Pattern 在 30 天窗口跨任务重复后提升。
- Fallback：单次观察只记录 pending，不自动应用策略；不保存身份证、密钥、完整对话或私有推理。
- 测试：既有跨任务复现测试继续通过；`test_five_brain_v22.py` 验证 recurrence=3、promoted=true。

### Capability Evolver

- 上游能力：Gene、Capsule、Evolution Event、候选选择和受控实验思想。
- Compass Adapter：`from_promoted_pattern()`、`start_trial()`、`finish_trial()`；保存 source pattern、baseline、metric、result、accepted_at/rollback_reason。
- 实际入口：Self Improving 提升后的 Pattern 产生 Candidate；完成率等可观察指标决定 Accept/Rollback。
- Fallback：证据为空不建 Candidate；`auto_apply=false`、`allow_self_modify=false`，写入限制在 runtime strategy store。
- 测试：无证据拒绝、trial 接受/回滚、保护路径拒写和五脑 E2E 均通过。

### Proactive Agent

- 上游能力：基于上下文信号的主动时机判断。
- Compass Adapter：`ProactiveEngine.check()` 支持 missed tasks、完成率、实际时长、考试/求职窗口、目标变化、市场过期、Gap 停滞和 Evidence drought。
- 实际入口：`CompassEngine` 在当前交互末尾收集 Memory/Market/Progress 信号，返回 should_prompt/reason/priority/confidence/cooldown。
- Fallback：无信号返回 no_trigger；冷却期不重复；连续 reject 抑制同类提示；`delivery=current_interaction_only`、`background_push=false`。
- 测试：触发、冷却、accepted/rejected/ignored 和拒绝抑制合同均有覆盖。

## Recruitment Pipeline

```text
Target: scripts/career/job_target_resolver.py + job_normalizer.py
→ Query: scripts/recruitment/query_expander.py
→ Browser/Provider: provider_router.py + public_search/agent_browser/user_jd/snapshot_provider.py
→ JD Normalize/Relevance/Deduplicate: recruitment_engine.py + models.py
→ Skill/Requirement: skill_extractor.py
→ Market: recruitment_engine.py + market_cache.py
```

任何城市和岗位都允许进入动态研究。User JD 和公共页面保留 source；synthetic 始终标记且不能形成真实市场状态。动态未知技能写入 runtime registry，不修改固定源码词典。

## Learning Pipeline

`Market → Gap → Plan → Tutor → Assessment → Evidence → Competency → Replan`

- `gap_engine.py` 只用岗位要求减已验证能力；claimed 无 Evidence 时按 0 处理。
- `adaptive_planner.py` 对真实充足市场生成 Formal Plan，否则生成声明清楚的 Preliminary Plan；周任务最多三项并保留 Task → Gap → JD 证据链。
- `tutor_engine.py` 进入微课和练习，不生成第二份计划；`assessment_engine.py` 使用显式验收项。
- `evidence_engine.py` 只把 passed Assessment 变成 verified Evidence；Competency 更新后重算 Gap 并 Replan。

## Memory Pipeline

`SQLite Structured Store (canonical) + Neo4j Agent Memory (optional graph/semantic) + SQLite Semantic Retrieval fallback`

READ BEFORE TURN 恢复 Profile/Goal/Competency/Growth/Semantic/Graph；WRITE AFTER TURN 分别写结构化更新、重要语义候选和领域关系。`state_history` 对目标、时间和偏好字段保留旧值。知识图谱覆盖 User→Goal、Goal→City/Job、Market→Skill、User→Competency→Evidence、Gap→Skill、Plan/Task→Gap/Skill。

## Improvement and Proactive Pipelines

```text
Error/Correction → Sanitized Pattern → Promotion → Candidate → Trial → Accept/Rollback
Memory + Market + Progress → Decision → Suggestion → Feedback → Policy Learning
```

系统改进知识与用户 Memory 分库存储；Pattern 使用用户哈希且只保留受控上下文字段。演化不修改源码、安全策略、许可证或 vendor。主动检查只发生在当前交互。

## File Changes

Added：

- `config/`：recruitment、memory v2.2、improvement、evolution、proactive、planning、learning policy。
- `scripts/memory/backends/` 与 `knowledge_graph.py`。
- `scripts/career/job_target_resolver.py`、`job_normalizer.py`。
- `scripts/recruitment/` Provider、模型、查询扩展、技能提取、Cache、统一 Engine。
- `scripts/competency/` Profile、Evidence、Gap、Dependency Graph。
- `scripts/learning/` Planner、Tutor、Lesson、Exercise、Assessment、Progress。
- `scripts/growth_orchestrator.py`、三个 2.2 Demo、四个新测试文件。

Modified：

- `scripts/compass_engine.py` 接入 READ BEFORE TURN、动态招聘/学习闭环、Tutor/Assessment 和 WRITE AFTER TURN。
- 五个 Integration/Engine、Intent/Action/Facts、Archive/Models、Validator/Packer、版本元数据、README/SKILL 和 upstream skill-mode 跳过规则。

Removed：无。既有 Review、职业探索、考试、计划、Memory API、测试和 vendor 均保留。

## Tests and Packaging

修改前真实基线：compile 通过；`81 passed`；2.1 validator 不认识 `--mode skill`（退出码 2），该缺口已修复。

2.2 源目录验证（2026-08-07）：

- compile：通过。
- pytest：`90 passed`。
- skill validation：`valid=true`，102 个必需文件、29 个 JSON、1 个快照。
- full validation：`valid=true`，同时核对 vendor marker/commit。
- onboarding、full growth、market driven、persistent memory、five brain 五个规定 Demo：全部通过。
- skill/full pack：成功。
- skill ZIP 解压复验：compile=0；`82 passed, 2 skipped`（skill 按设计无 vendor，两个 upstream 模块级跳过）；skill validation=true。
- skill/full ZIP 内容验证：均 valid=true。

唯一验证警告是既有资源 `pending-spring-guide` 仍标记待人工复核；未将它误报为已验证资源。

## Final Package

- `dist/compass-student-growth-2.2.0-skill.zip`：已真实生成并通过解压自验证。
- `dist/compass-student-growth-2.2.0-full.zip`：已真实生成，包含 vendor 和完整 attribution，并通过 full/ZIP validation。

## Remaining Limitations

- 公开招聘覆盖取决于可公开访问来源；网站条款、robots、登录、验证码、反自动化和页面变化会限制采集。
- Public Search Provider 需要宿主注入搜索能力；Agent Browser 需要 CLI/Reader 和网络；失败时使用 User JD 或 Snapshot。
- Neo4j 需要单独部署和凭据；未部署时无远端图检索，但 SQLite 状态、关系和语义 fallback 正常。
- LLM 标准化、Query Expansion 和结构化抽取均为 optional；离线时采用确定性规则与动态 Registry。
- 市场快照随时间失效；Cache 标记 expires_at/stale，不能把旧快照表述为实时市场。
- Proactive 默认没有 scheduler、notification 或后台 push，只在当前交互检查。
- Demo 中硬编码用户 JD 和注入式网页内容全部标记 `synthetic=true`；它们只证明处理闭环，market status 为 insufficient，不代表公共市场覆盖。

---

# Compass 2.1 Interaction Optimization Report (historical baseline)

## 1 Baseline

Compass 2.0.0 的统一 Growth Engine、六脑适配、Growth Archive、安全路由和发布工具均保留为本次升级基线。改造前实际执行：

```text
python -m pytest tests -q
67 passed in 4.15s
```

本次只改动交互优化直接涉及的入口、状态、画像充分性、问题策略、目标与容量规划、档案字段、文档、测试和 Demo；没有重构无关业务模块或修改 `vendor/` 上游快照。

## 2 Problem Reproduction

2.0 的入口能完成职业、课程、考试、记忆等单轮业务，但缺少 preferred name、跨轮 known facts、阶段检测、充分性判定和字段级提问历史。新用户即使已逐步提供专业、年级、技能、方向和时间，后续轮次仍可能把本轮视为孤立请求，表现为：

- 第一轮直接进入业务字段收集，没有自然的关系建立。
- 把“资料完整”误当成“足够开始”，城市、公司等非阻塞字段可能延迟初步计划。
- “每天能学习多久”和“每天能投入多长时间”无法按同一字段去重。
- 用户已经说“IT 支持方向”后，仍可能再次要求确认方向。
- 声明每天 6 小时时，缺少冷启动负荷保护。

复现结论不是业务能力缺失，而是多轮交互协调层缺失。

## 3 Preferred Name Onboarding

新增 `ConversationState` 与 `onboarding_engine.py`。安全路由保持第一优先级；普通新用户第一轮只询问希望使用的称呼。`preferred_name` 和 `preferred_name_usage` 作为用户明确事实写入结构化记忆与 Archive。用户可以更新称呼或禁用称呼。

第二轮只询问专业、年级和当前最想解决的问题。已有 Archive 的新会话不重复询问称呼，`继续上次` 会恢复称呼、阶段和当前计划。

## 4 Minimal Information Policy

2.1 的目标不是一次性填满画像，而是收集当前行动所需的最少事实。目标城市、公司类型和具体公司默认后置；技能证据、项目细节也可在执行过程中逐步完善。

硬性策略已写入 `SKILL.md`：当现有信息已经足够生成有价值的下一步行动时，禁止为了完成档案而继续追问；非阻塞信息必须在当前行动之后询问。

## 5 Profile Sufficiency

`profile_sufficiency.py` 输出：`score`、`known_fields`、`missing_blocking`、`missing_non_blocking`、`action_ready`、`confidence`、`next_questions` 和 `planning_mode`。

规则按场景区分：

- 专业、年级、目标、技能和时间足够时立即行动。
- 只有专业时继续询问关键缺口。
- 职业方向已确认但城市缺失时生成 `PRELIMINARY_PLAN`。
- 特定城市的正式市场规划仍要求方向、城市和期限。
- 考试临近但材料不足时允许给基础复习策略，并明确不是教师真实考点。

内部充分性分数不出现在用户回复中。

## 6 Stage Detection

`stage_detector.py` 支持大学适应、基础能力建设、职业探索、实习准备、实习实践、求职准备、求职行动、考试冲刺、项目冲刺和毕业过渡阶段。

关键测试均通过：

- 专科大二 + 明年实习 → `INTERNSHIP_PREPARATION_STAGE`。
- 大四 + 秋招 → `JOB_SEARCH_STAGE`。
- 考试还有 5 天 → `EXAM_SPRINT_STAGE`。

阶段判断附可观察证据并允许后续更新。

## 7 Question Budget

`question_policy.py` 读取 `config/mentor_policy.json`：单轮问题硬上限为 3，推荐 1—2；连续纯信息收集不超过 2 轮。第三轮仍缺字段时，回复也必须包含阶段判断或最小行动，不能继续输出问卷。

真实 E2E 中：第一轮 1 个称呼问题，第二轮自然快速画像，第三轮显示实习准备期并询问技能、方向和时间，共 3 项；第四轮只保留真正影响下一步的方向确认。

## 8 Duplicate Question Guard

`known_facts.py` 以 `{value, confidence, source, updated_at}` 保存字段事实；`duplicate_question_guard.py` 与 `question_history.asked_fields` 以语义字段去重，不依赖问题文本。

已验证：

- 用户回答 IT 支持后，不再问“IT 支持还是运维”。
- 用户回答每天 6 小时后，不再问时间投入。
- 用户给出 Python 简单项目后，不再问 Python 水平。
- 用户明确改为“不想做 IT 支持”时，方向状态变为 `changed`，旧计划与正式目标标记 `invalidated`，重新进入探索。

## 9 Action-First Mentor

`action_selector.py` 在每轮选择询问、阶段诊断、职业探索、初步计划、正式分析、复习或进度复盘。`mentor_diagnosis.py` 主动形成当前阶段、已有优势、主要问题、机会和主目标；不会要求用户自己设计前三个月学什么。

用户侧响应依次呈现判断、目标、阶段、最多三个本周任务、选择理由、下次反馈和后置信息。候选职业使用“值得重点探索”，用户明确确认后使用“已经明确选择”，推测不会写成 confirmed。

## 10 Goal Planning

`goal_planner.py` 输出三层目标：6—12 个月主目标、四个阶段目标、当前周目标。IT 支持且对代码感兴趣时，计划会强化 Python 自动化，但该路线来自用户事实和方向模板，不会硬编码给所有用户。

目标城市缺失不阻止初步计划；只有城市、方向、时间和可靠市场数据齐全时，才形成正式市场驱动计划。规划不承诺就业、薪资或考试结果。

## 11 Weekly Task Planning

首周最多 3 个核心任务。每项任务包含预计时间、具体动作、产出、验收标准、证据和失败备选。真实 IT 支持场景生成：Linux 实验环境、Python 批量 Ping 工具、GitHub 证据仓库。

`calculate_realistic_capacity` 将每天 6 小时换算为理论每周 42 小时，但冷启动只按 60%，即 25.2 小时规划，满足不超过 70% 的约束。任务过多反馈会立即降载并进入 Improvement Log；考试 5 天内，复习时间高于职业时间。

## 12 Memory Integration

Growth Archive 版本升级为 2.1.0，新增：`preferred_name`、`onboarding_complete`、`current_growth_stage`、`profile_sufficiency`、`realistic_capacity`、`question_history`、`planning_confidence`、`last_action`、`next_expected_update` 和 `known_facts`。

结构化显式画像进入 Memory Brain，用户隔离、查询、纠正和彻底遗忘保持有效。SQLite 连接改为事务结束后显式关闭，避免 Windows 端到端测试清理时文件锁定。调试模式可写 `runtime/debug/interaction_trace.jsonl`，正式回复不暴露内部轨迹。

## 13 Six Brain Regression

`scripts/demo/six_brain_demo.py` 已真实运行并断言：

- Review Brain：题目与答案分离。
- Memory Brain：结构化写入与隔离召回。
- Improvement Brain：跨任务重复反馈形成候选。
- Evolution Brain：运行时试验接受/回滚边界。
- Research Brain：公共 HTTPS、只读命令。
- Proactive Brain：当前交互提醒，无虚构后台推送。

Safety 仍在任何 onboarding、记忆和业务步骤之前；Archive、统一周容量和旧兼容脚本均由回归测试覆盖。

## 14 Real Conversation Test

旧版典型体验：

```text
用户逐轮提供专业、年级、实习期限、技能、方向和时间
→ 每轮按孤立输入判断
→ 继续请求补充资料或重新确认
→ 用户感觉必须先想清楚很多东西，系统才开始帮助
```

2.1 真实 IT 支持 E2E：

```text
你好
→ 只问称呼
叫我小宇
→ 问专业、年级、当前问题
专科大二计算机网络技术，明年实习
→ 判断“实习准备期”，最多问技能、方向、时间
路由交换、网络安全、服务器，网络运维/IT 支持，喜欢 Python
→ 给候选分析，只问仍会改变计划的关键点
IT 支持，每天 6 小时
→ 立即生成 12 个月目标、四阶段路线、首周三个任务和 25.2 小时保守容量
互联网公司，Python 有简单项目
→ 更新并优化为 IT 支持 + Python 自动化，不重新问卷
新会话“继续上次”
→ 使用“小宇”并恢复当前计划
```

城市缺失时计划已经存在；城市问题位于行动之后。

## 15 Automated Tests

最终发布前执行：

```text
python -m compileall -q scripts
python -m pytest tests -q
81 passed in 3.13s
```

统计：total 81，passed 81，failed 0，skipped 0。新增真实 E2E 覆盖七轮 IT 支持场景、称呼跨会话恢复、问题预算、语义去重、过载反馈、考试优先和用户改方向。

## 16 Demo

以下脚本均已真实运行并以断言通过：

- `scripts/demo/onboarding_demo.py`
- `scripts/demo/it_support_student_demo.py`
- `scripts/demo/six_brain_demo.py`
- `scripts/demo/full_growth_demo.py`

完整生命周期 Demo 覆盖称呼、最小画像、阶段判断、计划、用户偏好优化、任务降载、考试优先和新会话恢复。

## 17 Package

目录校验通过：`valid=true`，检查 69 个必需文件、22 个 JSON 文件和 1 个招聘快照。唯一警告是既有资源 `pending-spring-guide` 标记为待复核，它不会进入正式资源推荐，不阻塞发布。

最终上传包：

```text
dist/compass-student-growth-2.1.0-skill.zip
```

ZIP 根目录直接包含 `SKILL.md` 和 `manifest.yaml`，排除 `.git`、虚拟环境、缓存、运行时数据库和 `vendor/` 完整上游源码；许可证与第三方通知保留。

最终打包与 ZIP 二次校验均返回 `ok=true`；首次最终产物实测大小为 273,625 字节，报告写入后的重打包大小以交付文件为准。
