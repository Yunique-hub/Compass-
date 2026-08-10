# Compass Student Growth 2.5.1

Compass 是一个面向大学生的长期成长型 AI 导师。它把学业、考试、职业探索、实习求职、招聘市场、学习陪伴、成果验收和跨会话状态组织成同一条可验证成长闭环：理解当前状态，选择最重要目标，执行小行动，收集证据，再根据结果调整。

2.5.1 在 2.5 全专业运行基础上完成语义正确性与证据可信度修正：Major Mention Classification 区分当前/历史/目标/话题，Assessment 识别否定、局部完成与不确定性，Evidence 使用分级可信度，领域解析采用 taxonomy-first，Secondary Goal 真正进入计划。专业只是一项输入，不等于职业；学习主题也不等于专业。

核心规划公式：

```text
Academic Background + Current Stage + Goal/Pathway + Constraints + Evidence/Gaps = Growth Plan
```

系统支持双专业、辅修、未分流、转专业和跨专业转型。常见专业使用一份结构化 profile 作为加速层；未命中时按学科族与通用成长逻辑生成可执行路线，并明确具体培养方案、资格要求或行业要求需要验证。金融、法学、医学、生物、心理、设计、机械、语言、教育等领域分别使用匹配的 competency、Tutor、Assessment 与 Evidence，不默认套用 Python、GitHub 或工程师路线。

## 核心能力

- Career / Recruitment / JD / Gap：职业探索、目标岗位解析、招聘样本分析和能力差距。
- Planning / Tutor / Assessment / Review：阶段计划、AI 陪学、练习验收、考试复习和错题闭环。
- Evidence / Competency：区分 `SELF_REPORTED / TEXT_SUPPORTED / ARTIFACT_SUBMITTED / ARTIFACT_ASSESSED / EXECUTION_VERIFIED / EXTERNAL_VERIFIED`；只有经过标准验收的可观察结果才能提高 verified competency。
- Memory / Archive：SQLite 保存长期画像、目标、能力和成长状态；Growth Archive 保留兼容迁移。
- Research / Resource：只读、显式授权的公共来源；记录来源和日期，失败时安全降级。
- Improvement / Evolution / Proactive：根据重复反馈低频调整策略；不修改核心安全规则，不虚构后台推送。

统一入口为 `scripts/compass_engine.py`。每轮使用一套正式流程：

```text
SAFETY → RESTORE → UNDERSTAND → DECIDE → EXECUTE → LEARN → PERSIST → RESPOND
```

`CompassEngine.run()` 只编排各阶段。`TurnContext` 统一承载单轮状态；intent router 只做路由；Career、Planning、Tutor、Assessment、Recruitment、Review 和 Resource/Research 处理业务；Memory、Evidence、Proactive、Archive 和 response normalization 在统一后处理阶段完成。详细边界见 `docs/architecture.md`。

## 环境与运行

要求 Python 3.10 或更高。默认核心流程不需要网络、外部 LLM 或 Neo4j。Node.js、agent-browser 和 Neo4j 只用于可选增强。

推荐使用 `uv`：

```powershell
uv sync --frozen --extra dev
```

也可以使用现有 bootstrap 脚本：

```powershell
python scripts/bootstrap_dev.py --install
```

通过 stdin 发送 JSON：

```powershell
'{"user_id":"student-1","message":"我是计算机大二，学过 Python，明年找后端实习，现在怎么准备？"}' |
  .\.venv\Scripts\python.exe -B scripts\compass_engine.py
```

Python API：

```python
from scripts.compass_engine import CompassEngine

engine = CompassEngine("runtime")
output = engine.run({
    "user_id": "student-1",
    "message": "继续上次计划。",
})
```

响应统一包含 `current_judgment`、`current_goal`、`do_now`、`why`、`next_step` 和最多一个 `questions`。简单知识问题会压缩为直接答案，不强制输出完整成长模板。

## 测试与校验

```powershell
.\.venv\Scripts\python.exe -B -m compileall -q scripts
.\.venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B scripts\validate_package.py --mode skill
.\.venv\Scripts\python.exe -B scripts\validate_package.py --mode dev
.\.venv\Scripts\python.exe -B scripts\validate_package.py --mode full
```

validator 检查必要结构、版本一致性、JSON/schema、关键 import、首轮行动、统一 pipeline、简单问题响应和发布包边界。它不依赖固定章节标题、Brain 名或示例字符串来证明系统正确。

## 打包

```powershell
.\.venv\Scripts\python.exe -B scripts\pack_skill.py --mode skill
.\.venv\Scripts\python.exe -B scripts\pack_skill.py --mode dev
.\.venv\Scripts\python.exe -B scripts\pack_skill.py --mode full
```

产物写入 `dist/`：

| 包 | 用途 | 包含 | 不包含 |
|---|---|---|---|
| `skill` | 运行/发布 | Skill 指令、运行代码、配置、schema、运行资源、许可证和 upstream lock | tests、开发报告、demo、构建脚本、vendor 源码、运行数据 |
| `dev` | 开发与 CI | runtime 内容、tests、scripts、开发文档、fixtures、打包配置 | vendor 源码、缓存、运行数据 |
| `full` | 审计与上游复现 | dev 内容、vendor snapshots、上游许可证和审计资源 | 缓存、虚拟环境、运行数据 |

所有 ZIP 根目录直接包含项目文件，不额外嵌套目录。skill/dev 包禁止携带 `vendor/`；只有 full 包包含完整 upstream snapshots。

正式产品交付物是 `dist/compass-student-growth-2.5.1-skill.zip`。解压到 Codex Skills 目录后，目录根必须直接包含 `SKILL.md`、`agents/openai.yaml`、`scripts/` 与 `reference/`；`dev` 和 `full` 包仅用于测试、审计和上游复现，不是日常安装包。

## 数据位置与清理

默认数据位于：

```text
runtime/users/<sha256(user_id)[:24]>/
├── archive.json
├── memory.sqlite3
└── strategies/
```

SQLite 是 profile、goal、competency、evidence-derived state 和 growth state 的 canonical store。Neo4j 是可选副本/图增强，不可用时不会阻断 SQLite。

用户说“忘记我的所有记忆”时，统一入口会删除该用户的应用层长期记忆并重置成长档案。测试使用 `tmp_path`，正常测试不会写入仓库 `runtime/`。如需清理本地手工演示数据，请先确认目标是当前仓库内的 `runtime/`，再删除其中对应用户目录；不要删除其他环境的数据目录。

## Vendor 与上游

`reference/open_source/upstream-lock.json` 锁定上游仓库、分支和 commit；`THIRD_PARTY_NOTICES.md` 与 `licenses/` 保留许可证或授权信息。`vendor/` 只用于 full 审计包，不进入 runtime skill。运行时代码如果没有实际 import/read 某个 vendor snapshot，就不得把它加入 skill 包。

## 安全与隐私边界

- 高风险医疗、法律、金融、自伤和危险行为优先转介；系统不做专业诊断或结果保证。
- Memory 按 `user_id` 隔离；高敏感标识符默认不保存；用户可以查询、纠正、拒绝保存和彻底遗忘。
- 不记录 chain-of-thought、隐藏推理或私有草稿。
- Research 仅访问明确授权的公共 HTTPS 只读来源，不登录、不提交、不绕过访问控制。
- 招聘、政策、价格和行业事实必须带来源/日期或声明“最新情况需验证”。
- Proactive 只在当前交互中给出可拒绝建议，不声称后台监控或推送。

## 已知限制

- 本地招聘快照仍主要覆盖信息技术方向；资源与技能归一化已覆盖金融、法律、研究、设计、工程、教育和医学，但真实市场结论仍必须来自用户 JD 或可追溯来源。合成快照仅供测试，不能代表真实市场。
- 公共网页覆盖受网站条款、登录、验证码、robots 和页面结构限制。
- SQLite 关键词召回不是正式语义向量模型；Neo4j、agent-browser 和 MarkItDown 都是可选增强。
- 2.5.1 保持 2.x Archive 和 SQLite 表结构可读，无破坏性数据迁移；旧档案加载后会在保存时升级 `archive_version`。`profile_state` 与 `business_state` 明确分离，同时保留旧顶层字段作为兼容包装。

项目采用 [MIT License](LICENSE)。
