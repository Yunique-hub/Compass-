# Compass 大学生智慧成长罗盘 v2.2.0

Compass 是一个以目标就业城市公开招聘需求为依据，为大学生动态规划学习路径、直接陪伴学习，并通过知识图谱永久保存成长状态的就业导向成长智能体。架构支持任意自由文本城市和岗位；实际市场覆盖度取决于可公开访问的数据，拿不到真实样本时会明确返回 `market_data_status=insufficient`，不会用内置知识或合成夹具冒充市场结论。

默认配置不需要网络、外部 LLM 或 Neo4j：SQLite 保存关键用户画像、目标、Competency、Evidence 和成长状态，用户提供的 JD 与版本化快照可在离线模式运行。Neo4j Agent Memory 提供可选知识图谱/语义增强，Agent Browser 提供公共网页只读执行；任一可选能力不可用都不会阻断核心流程。

## 核心架构

统一入口是 `scripts/compass_engine.py`，每轮按固定顺序执行：

```text
SAFETY → PERSISTENT MEMORY RESTORE → SEMANTIC/GRAPH RETRIEVAL
       → INTENT → FACT/STAGE/SUFFICIENCY → ACTION → CAREER TARGET
       → RECRUITMENT → MARKET → GAP → PLAN/TUTOR/ASSESSMENT
       → EVIDENCE → COMPETENCY → REPLAN → PROACTIVE
       → SELF IMPROVEMENT → EVOLUTION → MEMORY PERSIST → RESPONSE
```

五个基础脑区（Review 继续作为成熟业务模块保留，但不计入五脑）：

- Agent Memory：SQLite 结构化永久状态 + 可选 Neo4j 成长知识图谱和语义召回。
- Agent Browser：公共招聘页面只读打开/读取/文本证据；拒绝 fill、upload、submit。
- Self Improving Agent：去标识化记录错误、纠正、最佳实践和重复 Pattern。
- Capability Evolver：由已提升 Pattern 产生可审计策略候选、Trial、Accept/Rollback；禁止修改源码。
- Proactive Agent：综合 Memory、Market、Progress 信号，在当前交互内给出带 cooldown 和反馈的建议。

核心业务闭环是 `Target → Query → Provider/Browser → JD → Skill → Market → Gap → Plan → Tutor → Assessment → Evidence → Competency → Replan`。用户自述技能只写入 `claimed_level`；只有通过 Assessment 或其他可验证 Evidence 才能提高 `verified_level`。

职业方向主路径从 `StudentFeatureProfile` 自动评分，不接受外部手写维度分数。原 v1 脚本保留为兼容包装和独立工具。

## Interaction Design v2.2

2.2 保留 2.1 的渐进式、行动优先交互，并把永久记忆、招聘市场和陪学闭环接到每轮统一运行链：

- Preferred name onboarding：新用户第一轮只询问希望使用的称呼；高风险安全信号例外。
- Minimum information principle：判断是否足够“现在开始”，不等待完整画像。
- Action-first policy：先给阶段判断、目标和最多三个本周任务，再补充非阻塞信息。
- Stage awareness：识别适应、基础、探索、实习准备、求职、考试冲刺等阶段。
- Question budget：单轮最多三个问题，连续纯信息收集不超过两轮。
- Duplicate question prevention：按字段记录已知事实和提问历史，阻止语义重复追问。
- Preliminary planning：方向已确认但城市缺失时仍生成初步计划，城市在行动后自然询问。
- Returning-user resume：新会话恢复称呼、阶段和上次计划，不重复 onboarding。

例如，用户给出“专科大二、明年实习、学过网络和服务器、想做 IT 支持、每天 6 小时”后，Compass 会直接判断为实习准备期，生成长期目标、四段路线和首周最多三个任务。理论可用时间虽然是 42 小时，冷启动计划默认只使用约 60%，两周后再根据真实完成速度校准。

## 环境要求

- Python 3.10 或更高；本项目已在 Python 3.11.4 验证。
- Node.js 24 或更高、pnpm 11 或更高，仅在使用 agent-browser 或运行对应上游烟测时需要。
- Docker 仅用于可选 Neo4j 服务，不是核心运行条件。

建议使用项目内虚拟环境：

```powershell
python scripts/bootstrap_dev.py --install
.\dev.ps1
```

Linux/macOS：

```sh
python scripts/bootstrap_dev.py --install
./dev.sh
```

如果只想执行现有环境验证：

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_dev.py
```

可选 Neo4j：复制 `.env.example`，修改密码后执行：

```powershell
docker compose --profile neo4j up -d
```

## 调用统一引擎

通过 stdin 传 JSON：

```powershell
'{"user_id":"student-1","message":"计算机大二，学过 Python，不知道毕业适合什么工作"}' |
  .\.venv\Scripts\python.exe scripts\compass_engine.py
```

生成考试复习时，附件项提供本地路径：

```json
{
  "user_id": "student-1",
  "message": "根据真题帮我复习并出题",
  "course": "操作系统",
  "exam_days": 4,
  "attachments": [
    {"name": "操作系统历年真题.pdf", "path": "E:/materials/操作系统历年真题.pdf"}
  ]
}
```

输出包含 `intent`、`state`、四段式 `response`、不含内部推理的执行 `trace`、安全结果、记忆变化和 Growth Archive v2。

## 测试和演示

```powershell
.\.venv\Scripts\python.exe -B -m compileall -q scripts
.\.venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
.\.venv\Scripts\python.exe -B scripts\demo\onboarding_demo.py
.\.venv\Scripts\python.exe -B scripts\demo\it_support_student_demo.py
.\.venv\Scripts\python.exe -B scripts\demo\six_brain_demo.py
.\.venv\Scripts\python.exe -B scripts\demo\market_driven_learning_demo.py
.\.venv\Scripts\python.exe -B scripts\demo\persistent_memory_demo.py
.\.venv\Scripts\python.exe -B scripts\demo\five_brain_demo.py
.\.venv\Scripts\python.exe -B scripts\demo\full_growth_demo.py
.\.venv\Scripts\python.exe -B scripts\demo_v2.py --output runtime\demo-output-v2
.\.venv\Scripts\python.exe -B scripts\validate_package.py
```

9 个演示场景的说明见 `demos/README.md`。运行结果写入忽略的 `runtime/demo-output-v2/`。

## 已知限制

- 公共招聘来源覆盖受网站公开可访问性、robots/条款、登录、验证码和页面结构影响；系统不绕过访问控制。
- Public Search 与 Agent Browser Provider 是可选能力；不可用时只能使用用户 JD 或版本化快照。
- Neo4j 需要单独部署与凭据；SQLite 始终是核心状态的 canonical store。
- LLM 扩展/抽取是可选增强；没有 LLM 时使用 Alias、Pattern 和动态技能注册表。
- 市场结论只适用于记录的来源与采集时间；过期快照会标为 stale。
- Proactive 默认仅在当前交互检查，不假装存在后台监控、通知或推送。

ZIP 根目录直接包含 `SKILL.md` 和 `manifest.yaml`，没有额外套层；`.git`、虚拟环境、依赖缓存、运行时数据库和 Python 缓存不会进入发布包。

## 安全与隐私

- 高风险状态优先于学习和职业规划；系统不进行心理诊断。
- 记忆按 `user_id` 隔离，高敏感标识符默认不存，用户可查询、纠正和彻底遗忘。
- 日志、记忆和档案不保存 chain-of-thought 或隐藏推理。
- Research Brain 仅允许公共 HTTPS 只读命令，不登录、不点击、不填表、不上传。
- Evolution Brain 只能写入 `runtime/`，不得修改源码、Skill、manifest、安全规则或许可证。
- Proactive Brain 只在当前交互内给建议，不虚构后台推送能力。

## 已知限制

- 当前职业和资源知识库主要面向信息技术相关方向，扩展其他专业需要增加本地参考数据。
- 仓库内招聘快照为合成演示数据，醒目标注为功能测试用途，不能代表当前市场。
- 默认召回使用结构化字段和关键词降级，不等价于正式语义向量模型。
- agent-browser、Neo4j、MarkItDown 对特定格式的增强取决于本机可选依赖；失败时输出警告并降级。
- 本项目不会自行在后台运行。宿主平台若需要定时提醒，必须另外配置平台调度能力。

更完整的环境、测试、上游缺陷和工程决策见 `ENVIRONMENT_BASELINE.md` 与 `DEVELOPMENT_REPORT.md`。

## 执照

本项目采用 [MIT 执照](LICENSE)。
