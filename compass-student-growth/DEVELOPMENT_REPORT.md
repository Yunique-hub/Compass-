# Compass 2.1 Interaction Optimization Report

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
