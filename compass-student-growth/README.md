# Compass 大学生智慧成长罗盘 v2.0.0

Compass 是一个离线优先、可上传到智能体平台的大学生成长 Skill。它把职业探索、招聘/JD 分析、课程学习、考试复习、长期记忆、策略改进、公开只读研究和当前交互主动关怀统一到一个 Growth Engine 中。

默认配置不需要网络和 Neo4j：职业知识、招聘演示快照、课程资料处理、SQLite 记忆、复盘和档案都可以在本地运行。Neo4j agent-memory 与 agent-browser 是可选增强，失败时不会阻断核心流程。

## 核心架构

统一入口是 `scripts/compass_engine.py`，每轮按固定顺序执行：

```text
SAFETY → MEMORY LOAD → INTENT → STATE → CONTEXT → BUSINESS
       → REVIEW → RESEARCH → IMPROVEMENT → EVOLUTION
       → PROACTIVE → MEMORY WRITE → ARCHIVE → RESPONSE
```

六个适配模块：

- Review Brain：材料转换、来源优先级、知识点、题目/答案分离、错题。
- Memory Brain：SQLite/JSON、用户隔离、召回、去重、遗忘、可选 Neo4j。
- Improvement Brain：按可观察反馈识别跨任务重复模式。
- Evolution Brain：运行时策略候选、试验、指标和回滚，禁止修改源码。
- Research Brain：明确授权的 HTTPS 公共网页只读访问与离线快照降级。
- Proactive Brain：当前交互内提醒、24 小时冷却和 accepted/rejected/ignored 反馈。

职业方向主路径从 `StudentFeatureProfile` 自动评分，不接受外部手写维度分数。原 v1 脚本保留为兼容包装和独立工具。

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
.\.venv\Scripts\python.exe -B scripts\demo_v2.py --output runtime\demo-output-v2
.\.venv\Scripts\python.exe -B scripts\validate_package.py
```

9 个演示场景的说明见 `demos/README.md`。运行结果写入忽略的 `runtime/demo-output-v2/`。

## 上游源码和合规

六个上游仓库的固定仓库地址、分支和 commit 位于 `reference/open_source/upstream-lock.json`。完整未带嵌套 `.git` 的源快照保留在 `vendor/`，许可证或单独授权说明保留在 `licenses/`，集成边界见 `THIRD_PARTY_NOTICES.md`。

同步或验证上游快照：

```powershell
.\.venv\Scripts\python.exe scripts\vendor_sync.py --offline
```

脚本会核对快照指纹；发现本地修改时拒绝覆盖。需要联网重新同步时去掉 `--offline`，仍会检出 lock 文件中的准确 commit。

## 发布包

竞赛/平台 Skill 包不含完整 `vendor/` 源码，但包含运行代码、测试、文档、许可证和第三方通知：

```powershell
.\.venv\Scripts\python.exe scripts\pack_skill.py --mode skill
```

完整开发包包含六个固定上游源快照：

```powershell
.\.venv\Scripts\python.exe scripts\pack_skill.py --mode full
```

输出：

- `dist/compass-student-growth-2.0.0-skill.zip`
- `dist/compass-student-growth-2.0.0-full.zip`

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
