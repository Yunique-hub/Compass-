# Compass 开发报告

生成日期：2026-08-06（Asia/Shanghai）  
项目：`compass-student-growth`  
版本：1.0.0

## 1. 环境审计

- 初始目录仅有空 Git 仓库，没有用户代码或文件需要覆盖。
- Python：3.11.4，满足 3.10+。
- 初始 Git：`No commits yet on master`。
- 开发核心过程不调用网络、招聘网站、模型或未知平台 API。
- 产品详情来源为 `E:/XIAZAI/Compass大学生智慧成长罗盘_v3.0.docx`：结构化读取到 289 个段落、68 张表，无批注、无修订。内容与开发附件无冲突；本机缺少 LibreOffice/soffice，无法执行 DOCX 页面渲染视觉 QA，因此只作为产品业务详情源，不声明其页面视觉核验通过。

## 2. 创建与修改的文件

当前交付工程包含 59 个项目文件（不计 `.test-deps`、字节码缓存与最终 zip），其中 Python 27 个、自动化测试文件 4 个、JSON 17 个、Markdown 11 个。初始仓库没有项目文件，因此没有覆盖用户已有实现。

- 根文件：`SKILL.md`、`manifest.yaml`、`README.md`、`pyproject.toml`、`.gitignore`、`DEVELOPMENT_REPORT.md`。
- UI 元数据：`agents/openai.yaml`；它不改变兼容性优先的最小 `manifest.yaml`。
- 配置：`config/plan_rules.json`、`config/memory_policy.json`。
- 核心脚本：模型/I/O、画像、方向分析与确认、招聘快照、JD、差距、计划生成与校验、资源、档案导入导出、记忆分类/政策/存储/召回、冲突、安全、演示、包校验和打包。
- reference：5 个方向、1 份醒目标记的杭州 Java 后端合成快照、技能别名/岗位权重、资源元数据、4 个 JSON Schema、规划/记忆/危机说明与 4 个输出示例。
- 测试：3 个单元测试模块、1 个集成测试模块、固定画像 fixture、T01—T19 平台 E2E 手工清单。

## 3. 核心设计决策

1. 三项确认门是硬约束：主方向、目的地、求职时间缺一项就不生成正式目的地数据计划。
2. 竞赛档案模式完全离线；每轮可输出完整 JSON/Markdown 档案。
3. 自动长期记忆明确为 Agent 应用层“条件启用/工程增强”；文件和 SQLite 后端可运行，外部向量库只提供 Protocol，不导入 Chroma/Milvus 或伪造平台接口。
4. 所有招聘比例只由实际输入计算并保留岗位/JD ID。合成 fixture 使用 `synthetic: true`、`source: synthetic-test-fixture` 和“仅用于功能测试，不代表当前市场”。
5. 计划最多 3 个核心任务，总时长不超过每周时间的 85%；每项有时长、产出、验收、依赖、至少 2 个已核验资源和失败备选。
6. 敏感、低可信、冲突与用户意愿规则优先于记忆评分；忘记覆盖结构化、向量、索引、缓存与临时副本，审计不留原文。
7. 安全路由在规划之前：普通压力关怀降载，高风险停止计划并转介；不诊断、不提供药物建议。

## 4. 实际运行命令与结果

### 4.1 编译

原命令 `python -m compileall scripts` 在受管沙箱内因不允许 Python 创建 `__pycache__` 而报 `PermissionError`。获准让同一系统 Python 只为编译命令创建缓存后运行等价命令：

```powershell
E:\programme\pycharm\python\python.exe -m compileall -q scripts
```

实际结果：`COMPILE_OK`，退出码 0。

### 4.2 测试依赖与 pytest

系统 Python 和工作区文档 Python 起初均没有 pytest。经授权仅安装到项目内 `.test-deps`，并将该目录加入 Git/zip 排除；测试不使用网络。最终命令：

```powershell
$env:PYTHONPATH = "$PWD\.test-deps"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -q -p no:cacheprovider
```

实际最终结果：

- 测试总数：48
- 通过：48
- 失败：0
- 跳过：0
- 全量通过运行用时：0.40—0.43 秒；manifest 最终对齐后的最后一次为 0.40 秒

覆盖数据模型/Enum/无效字段、方向评分边界和进入成本、确认门和变更历史、招聘去重/别名/频率/置信度/合成标记、单/多 JD、差距与优先级、计划预算/3 项上限/字段、资源门、档案往返与冲突、记忆评分/分流/敏感/冲突/忘记/用户隔离、文件/SQLite、向量降级、安全和 stdout/stderr，以及 12 个集成闭环。

### 4.3 Skill 与目录校验

```powershell
$env:PYTHONUTF8 = "1"
python C:\Users\Yonly\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python scripts/validate_package.py
```

实际结果：官方 Skill 校验 `Skill is valid!`；项目校验 `ok=true, valid=true`，检查 31 个必需文件、16 个运行配置/reference JSON 和 1 个快照。唯一警告为 `pending-spring-guide` 待团队核验；该资源被正式推荐门排除。

官方校验首次运行因其在中文 Windows 上用默认 GBK 读取 UTF-8 文件而失败；使用 Python 的 UTF-8 模式后通过，未修改外部脚本。

## 5. 测试失败与修复记录

第一次实际 pytest：47 通过、1 失败。失败用例错误地期望“低可信记忆直接忽略”，但需求规定可信度检查优先，应进入 `needs_confirmation`。修正测试预期，并增加“可信但总评分低→ignore”断言；业务实现不需修改。之后两次全量运行均为 48/48。

演示复查发现部分任务只有 1 个强匹配资源；虽然满足“任务有资源”，但产品详情要求每次推荐 2—4 个，因此改为强匹配优先并补已核验共享资源。复验后 3 个任务资源数均为 2，测试仍 48/48。

## 6. 固定演示实际结果

命令：`python scripts/demo_pipeline.py`

- `ok=true`，完成 16 个规定步骤。
- 比较数据分析、Java 后端、测试开发 3 个方向；全部标记为探索候选，未冒充确认目标。
- 模拟用户确认 Java 后端主方向、数据分析备选、杭州目的地、2028 年春招。
- 加载原始 7 条合成岗位，按 `source_key` 去重 1 条，得到 6 条有效样本；置信度 `low_confidence`。
- 技能统计均可追溯到 `syn-hz-java-*`；输出“仅用于功能测试，不代表当前市场；不足以得出杭州本地市场结论”。
- 生成差距矩阵、本月里程碑和 3 个核心任务；任务资源数为 2/2/2，总时长 8.0 小时，容量 8.5 小时。
- 导出 1.0.0 成长档案与新增/更新/删除/待确认记忆摘要。

## 7. 包校验

命令：

```powershell
python scripts/pack_skill.py --output dist/compass-student-growth-1.0.0.zip
python scripts/validate_package.py --zip dist/compass-student-growth-1.0.0.zip
```

受管沙箱拒绝普通 Python 在 `dist/` 新建 zip；获准只提升这条明确打包命令后成功。实际打包结果：`ok=true`，目录校验 `valid=true`，zip 校验 `valid=true`。随后重建并独立复验：包含 59 个条目，根目录 `SKILL.md=true`、`manifest.yaml=true`、禁止内容 0；Git、`__pycache__`、pytest 缓存、`.test-deps`、虚拟环境、临时数据库和旧 zip 均被排除。报告不记录会因报告内容变化而变化的压缩字节数。

## 8. 当前限制与团队待补充项

- 没有经过授权的真实招聘数据；现有杭州 Java 后端数据全部是合成测试 fixture，不能代表当前市场。
- 外部学习资源 `pending-spring-guide` 仍需团队核验 URL、版权、活跃度和最后检查时间；正式演示只使用本地已核验资源。
- 本地 JD 提取是确定性规则基线；模型语义补充必须由平台侧接入且仍需原文证据。
- 本地关键词召回不是正式 Embedding/Reranker 的等价替代。
- 未实现实时爬虫、未知平台 SDK、消息推送、真实向量数据库、视觉简历/截图、ASR/TTS、日历和校园系统联动。
- 当前真实数据范围不足以覆盖产品文档建议的北京、上海、深圳、杭州、广州、成都及全岗位组合。
- Word 产品详情因本机缺少 LibreOffice/soffice，未完成页面渲染视觉 QA；已完成结构化内容读取。

## 9. 平台上传后需人工验证

1. zip 能否上传，manifest 的 4 个字段是否被接受，是否从 description 正确触发。
2. 平台是否以 Skill 根目录执行脚本，是否能访问 `reference/`，Python 版本是否为 3.10+。
3. JSON/附件/stdin 输入和 stdout/stderr 分离是否被平台正确转发。
4. 方向未确认、目的地缺失和求职时间缺失三道门在真实对话中是否稳定。
5. 合成标识、样本数、区间、来源、版本和局限是否完整展示。
6. 成长档案是否可下载、重新上传并保留显式字段。
7. 安全路由和 T01—T19 手工 E2E，特别是跨用户隔离与完整删除。
8. 如平台提供持久化、Embedding/Reranker 或向量接口，先实现适配器并通过隔离/删除/故障降级测试，再将自动记忆标为启用。
