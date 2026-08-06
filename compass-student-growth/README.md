# Compass 大学生智慧成长罗盘

`compass-student-growth` v1.0.0 是一个中文、离线优先、可上传到 AI 龙虾/ezAgent 类平台的教育 Skill。它先帮助大学生比较就业方向，把最终决定交给用户；只有主方向、就业目的地和求职时间均确认后，才用可追溯招聘快照或用户真实 JD 生成胜任力差距和学习计划。

## 定位、目标用户与首批范围

Compass 是朋友式成长导师，不是一次性职业测评、万能课程推荐器或心理诊断工具。竞赛版采用“窄范围高质量”：优先服务计算机科学、软件工程、数据科学等信息类专业；方向知识库首批覆盖 Java 后端、Python 后端、数据分析、测试开发、产品助理。当前仅附杭州 × Java 后端的合成演示快照；北京、上海、深圳、广州、成都等城市需要团队补充真实、授权、可追溯数据后才可宣称覆盖。

## 确认式业务闭环

用户画像 → 2—4 个方向比较 → 用户确认主/备选方向 → 确认目的地和求职时间 → 读取匹配快照/真实 JD → 岗位需求与差距 → 学期/季度、月、周三级计划 → 执行复盘 → 更新成长档案与条件启用的应用层长期记忆。

三道硬门：

1. 方向未确认：只能比较方向并给 1—2 周探索任务。
2. 方向已确认、目的地缺失：只给通用基础，明确“不是基于目的地招聘市场的数据规划”。
3. 主方向、目的地和求职时间全确认：才能用匹配快照或真实 JD 生成正式计划。

方向或目的地改变后，旧招聘快照、能力差距与正式计划失效，必须重新确认和计算。

## 两种模式

| 模式 | 状态 | 能力与边界 |
|---|---|---|
| 竞赛保底档案模式 | 已实现，默认 | 无网络；版本化 reference 快照；真实 JD；每轮完整 JSON/Markdown 成长档案；独立演示闭环。 |
| 自动长期记忆模式 | 条件启用/工程增强 | 文件与 SQLite 结构化后端已实现；可选向量适配器协议、分流、召回、冲突、遗忘已实现；真实 Embedding/Reranker/向量库需部署方接入并测试。 |

大模型本身不拥有这里描述的永久记忆。自动记忆是 Agent 应用层能力，不是未知平台的原生已实现能力。

## 安装与运行

核心运行仅需 Python 3.10+ 标准库。测试开发需要环境已有 `pytest`；项目不在运行时自动安装依赖。

```powershell
cd compass-student-growth
python scripts/demo_pipeline.py
python scripts/validate_package.py
```

统一业务 CLI 从 `--input input.json` 或 stdin 接收 JSON，stdout 只输出最终 JSON，错误诊断写 stderr。例如：

```powershell
'{"text":"本科，熟悉 Java 和 Spring Boot，参与过 Web 项目并负责接口开发。"}' | python scripts/jd_analyzer.py
```

## 测试、演示与打包

```powershell
python -m compileall scripts
python -m pytest -q
python scripts/validate_package.py
python scripts/demo_pipeline.py
python scripts/pack_skill.py --output dist/compass-student-growth-1.0.0.zip
```

若环境禁止在源码目录写 `__pycache__`，可设置任务专用 `PYTHONPYCACHEPREFIX` 指向项目内可写缓存目录后执行等价 `compileall`。固定演示使用小明档案和醒目标记的合成快照，不联网，不把合成数据描述为杭州真实市场。

## 招聘快照与真实数据替换

快照位于 `reference/recruitment_snapshots/cities/<city>/<direction>-<version>.json`，清单位于 `snapshot_manifest.json`。至少保留：来源/来源类型、岗位发布日期、采集时间、样本量/有效样本量、采集区间、版本、城市、方向、局限、版权/使用说明。每条岗位至少有稳定的 `job_id` 或 `source_key`。

接入真实公开数据时：

1. 取得合法使用授权并由团队离线整理；不要把爬虫放入 Skill。
2. 保留原始来源标识，填 `synthetic: false`，不得伪造缺失薪资或数量。
3. 用 `recruitment_data_processor.py` 校验、归一化、去重和统计。
4. 人工抽检岗位名、同义词、必备/高频/加分分层。
5. 更新 `snapshot_manifest.json`，执行测试与包校验。

当前 `java-backend-demo-v0.1.json` 全部记录都使用 `synthetic: true` 和 `source: synthetic-test-fixture`，只验证流程。样本少于 20，因此为低置信度；项目的 20/30 条规则不是行业统一标准。

## JD、档案和资源

用户可向 `jd_analyzer.py` 提交单份 `text` 或多份 `jds`；多份统计只以实际输入为分母并保留 JD ID。档案导出支持 JSON/Markdown：调用 `archive_export.py` 时传 `archive`、`format` 和可选 `output`；导入时向 `archive_import.py` 传 `path` 或 `content`。Markdown 档案包含机器可读 JSON 区块，确保显式字段、确认状态、快照版本和计划状态可往返。冲突字段进入待确认，不静默覆盖；未知字段保存在 `extensions`。

学习资源位于 `reference/resources/cs_resources.json`。每个资源含阶段、时长、练习、类型、活跃度、最后检查、理由和替代。`verified: false` 的候选资源只产生警告，不进入正式演示推荐。

## 文件与 SQLite 记忆后端

```python
from scripts.memory_store import FileMemoryStore, SQLiteMemoryStore

file_store = FileMemoryStore("runtime/memory.json")
sqlite_store = SQLiteMemoryStore("runtime/memory.sqlite3")
```

所有 `upsert/get/list/delete_user` 必须显式传 `user_id`。SQLite 使用事务、复合主键和用户/状态索引；文件后端用临时文件原子替换。两者都记录新增、更新、失效和删除审计，删除审计不包含原始内容。

## 扩展向量存储适配器

在部署层实现 `memory_store.VectorStoreAdapter` 的 `upsert(user_id, record)`、`search(user_id, query, top_k)` 和 `delete_user(user_id)`。每个查询必须强制 user_id/租户过滤。可接入 Chroma、Milvus、Qdrant、FAISS 或平台服务，但本包不安装、不导入、不伪造任何一个具体 SDK。Embedding 与 Reranker 也由部署适配器提供。失败时 `memory_retriever.py` 降级为结构化字段 + 本地关键词；关键词检索不等价于正式语义模型。

## 已实现、条件启用、未实现

已实现：F1–F9、F11–F12；即建档、方向分析、确认门、离线招聘快照、JD 规则基线、差距、三级计划、资源、档案、复盘规则和安全路由；文件/SQLite 存储、记忆分类/政策/冲突/遗忘与本地检索也有可测试实现。

条件启用：F10 的真实自动长期记忆服务、向量检索和重排序。代码接口与降级已实现；只有部署方提供持久化、Embedding、Reranker 和向量服务并通过隔离/删除测试后，才可标为启用。

未实现：未经授权实时爬虫；具体 AI 龙虾 SDK/API；平台原生永久记忆；自动消息推送；简历/截图视觉解析；ASR/TTS；日历、校园系统联动；全专业、全城市、全岗位覆盖；真实招聘数据与实时薪资趋势。

## 隐私与安全

只保存规划必要数据；用户可查看、纠正、导出、删除和关闭长期记忆。敏感健康、危机、身份、精确位置和金融信息默认不长期保存。忘记请求删除结构化、向量、索引、缓存和临时副本。安全路由高于规划：普通压力先关怀并降载；危机信号立即停止学习任务，建议联系当地经过核验的紧急服务、学校心理中心、辅导员或身边可信任的人。Compass 不诊断、不提供药物建议、不替代专业治疗。

## 上传平台

上传 `dist/compass-student-growth-1.0.0.zip`。zip 根目录直接含 `SKILL.md` 与 `manifest.yaml`。平台接口未知，因此上传后必须人工确认：manifest 是否接受；触发语义；附件/JSON 输入；Python 脚本调用、工作目录、stdout/stderr；reference 访问；文件写入权限；档案下载/再上传；安全路由；会话隔离；是否有获批的持久化/Embedding/Reranker 接口。未实际验证前不要在演示或文档中写“平台已原生实现”。
