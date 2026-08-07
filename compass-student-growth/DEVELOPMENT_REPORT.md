# Compass v2.0.0 开发与验收报告

## 1. 交付结论

Compass 已从 v1.0.0 的职业规划 Skill 升级为 v2.0.0 统一 Growth Engine。v1 的 48 项基线测试在改造前全部通过；v2 最终自有、集成和上游烟测合计 67 项全部通过。9 个演示场景真实执行，结果为 `scenario_count=9`、`all_ok=true`。

本次改造没有把六个上游项目简单拼接成一组脚本，而是保留固定源快照，在 `scripts/integrations/` 后建立稳定边界。默认核心功能离线可用；浏览器和 Neo4j 都是可选增强。

## 2. 环境基线

实际验证环境：

| 项目 | 结果 |
|---|---|
| 系统 | Windows 10.0.26200 x64，PowerShell 5.1 |
| Python | 3.11.4 |
| Node.js | 24.19.0 |
| npm | 11.17.0 |
| pnpm | 11.16.0 |
| Git | 2.55.0.windows.3 |
| uv | 项目本地 0.12.2 |
| Chrome | 系统 Chrome 151；agent-browser 另安装 Chrome for Testing 151.0.7922.77 |
| Docker / Neo4j | 当前主机未安装或未启动；因此只验证 SQLite 默认路径和 Neo4j 可选导入边界 |

项目本地 `.venv` 安装了 pytest 9.1.1、pytest-cov 7.1.0、jsonschema 4.26、PyYAML 6.0.3、MarkItDown 0.1.7 及文档格式依赖。详细原始基线见 `ENVIRONMENT_BASELINE.md`。

## 3. 上游锁定与保留

| 组件 | 固定分支 | 固定 commit | Compass 集成方式 |
|---|---|---|---|
| lucianwhy/final-review | master | `622df4d7334508ed844b5312b8f0ad648b725ccd` | Review 的来源优先级、材料→知识点→题目规则 |
| neo4j-labs/agent-memory | main | `ac86a8ff01354e6b9c4d1b17089fba89d42dcf2b` | 可选 Neo4j 适配；默认 SQLite/JSON |
| pskoett/self-improving-agent | master | `b889ef0724c27b7181111b8dd1ac3a108d0b5160` | 可观察反馈、Pattern-Key、复现晋升阈值 |
| vercel-labs/agent-browser | main | `acbc22bdc5d4f6c5a88d97d4a4745d3c5eb0591f` | 公共 HTTPS 只读研究和离线降级 |
| NMTZ-z/capability-evolver | main | `56bad38c48ed31f97c49aef99fa34edb7b92b03c` | gene/capsule、受控试验和回滚概念 |
| thunlp/ProactiveAgent | main | `3fcf9beebe256b86871659fbb12541c41c9381b9` | 当前交互信号→建议→反馈，不启用桌面监控 |

`scripts/vendor_sync.py` 根据 lock 文件同步精确 commit，将 Git 工作副本放在忽略的 `runtime/cache/upstream/`，把无嵌套 `.git` 的完整快照放入 `vendor/`。每个快照都有 `.upstream-source.json` 和树指纹；脏快照不会被静默覆盖。

agent-memory、agent-browser、capability-evolver、ProactiveAgent 的许可证原文已复制到 `licenses/`。final-review 与 self-improving-agent 的上游快照没有许可证文件，因此项目没有擅自给它们指定开源许可证，而是保留单独授权说明。完整通知见 `THIRD_PARTY_NOTICES.md`。

## 4. 上游真实烟测

- self-improving-agent：`node --test` 上游 hook 套件，13/13 通过。
- capability-evolver：`node --test` selector 套件，8/8 通过。
- agent-browser：0.33.2 CLI 版本/帮助通过；真实打开 `https://example.com`、读取标题、生成快照并关闭浏览器通过。
- agent-memory：Python 包可导入；异步 MockMemoryClient 的 message、preference、context 路径通过。
- ProactiveAgent：`agent.datamodel` 可在不启动桌面 ActivityWatcher、训练和模型服务的情况下导入。
- final-review：上游为规则型 Skill，没有可执行测试；已验证规则源和固定快照存在。

## 5. 统一引擎和业务模块

`scripts/compass_engine.py` 实现固定 14 步顺序：安全、记忆读取、意图、状态、上下文、业务、质检、研究、改进、进化、主动检查、记忆写入、档案、响应。高风险安全结果会在第一步终止普通业务。

职业主路径：

- `profile_engine.py` 从结构化画像和当前消息生成 `StudentFeatureProfile`。
- `direction_engine.py` 自动计算专业、已验证技能、兴趣、经历和约束分项。
- 主入口没有 `scores` 参数；外部手写分数不能进入 v2 职业评分。
- v1 分析脚本仍保留，便于旧调用方迁移，但不由统一引擎调用。

学业主路径：

- `capacity_engine.py` 使用一个周总预算，保留 10%—15% 缓冲；考试五天内启用明确优先级。
- `ReviewEngine` 支持 MarkItDown、纯文本降级、固定来源优先级、知识点证据、题目/答案分离和错题摘要。
- 主观题答案包含 must-include、分项计分和常见失分；资料不足时不冒充教师标准答案。

## 6. Memory、Improvement、Evolution、Research、Proactive

Memory：SQLite 与 JSON 后端可用，所有操作带 `user_id`，提供召回、精确结构化优先、关键词降级、重复软失效、用户彻底删除和审计。写入前移除隐藏推理键；身份证/银行卡类高敏感标识符默认不存。Neo4j 只在明确配置后通过适配层使用。

Improvement：一次反馈只影响当前任务。相同模式在 30 天内出现至少三次并跨至少两个任务后，才生成 `auto_apply=false` 的策略候选。

Evolution：策略只写到用户 `runtime/`，必须有证据、指标、基线和试验。结果不优于基线即回滚。代码通过路径检查拒绝写出运行时目录以及受保护路径。

Research：策略只允许 HTTPS 公共域名和 open/get/snapshot/find/close，禁止点击、输入、上传、拖拽、eval、localhost 和私有文件。CLI 错误或超时返回离线快照降级，不阻塞主业务。

Proactive：只在当前交互检查考试窗口、连续失败和压力；同类提醒有 24 小时冷却，反馈限制为 accepted/rejected/ignored，结果明确标记 `background_push=false`。

## 7. Growth Archive v2

`scripts/archive_v2.py` 提供 v2 空档案、v1 迁移、读取和原子保存。档案分为 profile、career、academic、exam、learning_strategy、事件、成就、待确认和 extensions。v1 未识别字段原样进入 extensions，并记录 `migrated_from`。损坏 JSON 报错且不覆盖原文件。

## 8. 测试结果

最终命令：

```text
.venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
67 passed in 2.32s
```

覆盖：

- v1 数据模型、方向、招聘、计划、记忆、安全和归档回归测试。
- v2 意图/状态、自动职业评分、统一容量、Review、Memory、Improvement、Evolution、Research、Proactive 单元测试。
- 统一 14 步流程、安全短路、档案迁移和跨用户隔离集成测试。
- 六个上游的快照/许可证完整性和可执行烟测。

9 个演示命令：

```text
.venv\Scripts\python.exe -B scripts\demo_v2.py --output runtime\demo-output-v2
{"version":"2.0.0","scenario_count":9,"all_ok":true,...}
```

包目录校验：`valid=true`，检查 52 个必要文件、17 个 JSON、1 个招聘快照。唯一警告是资源 `pending-spring-guide` 尚待团队核验；它不会进入正式资源推荐。

## 9. 已发现的上游限制

这些问题没有直接修改 `vendor/`，由适配层规避：

- agent-memory 的 MockLongTermMemory 在处理字符串型 Enum 的 entity type 时存在类型/小写转换冲突；Compass 烟测使用 message、preference 和 context，生产 Neo4j 路径需要服务后另做集成验证。
- capability-evolver 固定快照中的 `assets/gep/genes.json` 在第 107 行附近不是有效 JSON。Compass 不读取该文件，而使用自己的受控运行时策略结构。
- final-review 和 self-improving-agent 固定快照没有许可证文件；发布包通过授权说明和第三方通知如实标注。
- ProactiveAgent 上游依赖桌面活动、模型和训练设施；Compass 不安装或运行该监控链，只适配数据模型和交互内反馈思想。
- MarkItDown 在缺少 ffmpeg 时会对音视频转换给出警告；Compass 当前目标文档格式不依赖 ffmpeg。

## 10. 仍然存在的产品限制

- 当前方向知识库覆盖五个信息技术相关方向，不是全专业职业百科。
- 招聘快照为合成功能数据，不能声称代表 2026 年实时市场。
- 默认关键词召回是离线降级，不是语义搜索。
- 当前主机没有 Docker/Neo4j，故未执行真实 Neo4j 服务端写入、并发和故障恢复测试。
- agent-browser 公共网页烟测通过，但目标网站的条款、结构和可用性会变化；任何生产研究仍需域名白名单和人工复核。
- 智能体平台的定时推送能力不在该 Skill 内，不能把交互内 Proactive 检查描述成后台服务。

## 11. 发布验收标准

发布前必须全部满足：Python compileall 通过、67 项及后续新增测试全部通过、9 场景 `all_ok=true`、目录 validator 通过、两个 ZIP validator 通过、ZIP 无 `.git`/虚拟环境/缓存/运行时数据库、根目录有 `SKILL.md`/manifest、两包均包含许可证和 `THIRD_PARTY_NOTICES.md`。完整包必须包含六个 vendor 快照；Skill 包必须不包含 vendor 源码。
