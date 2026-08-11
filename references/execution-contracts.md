# Execution Contracts

仅在需要校验时间预算、Research 证据或最终回复安全时读取。脚本不可用时手工应用相同字段与规则，不要求用户安装依赖。

## 1. PlanLedger

输入至少包含：

```json
{
  "weekly_hours": 10,
  "buffer_hours": 1.5,
  "tasks": [
    {"id": "exam", "hours": 4, "kind": "core"}
  ],
  "optional_tasks": [
    {"id": "project", "hours": 0}
  ],
  "stress": {
    "previous_planned_hours": 14,
    "consecutive_incomplete_weeks": 2,
    "fatigue": true
  }
}
```

规则：任务 ID 不重复；核心任务 1—3 个；所有时长非负；可选区为 0；核心任务与缓冲总和不超容量。连续两次未完成或明确疲惫时，建议核心负荷为容量的 50%—70%，并通常只保留一个核心任务。

运行：

```text
python scripts/validate_plan.py plan.json
```

退出码 `0` 表示有效，`2` 表示契约不满足，`1` 表示输入不可解析。

## 2. ResearchClaim

每条实时结论包含：

```json
{
  "text": "待发布结论",
  "time_sensitive": true,
  "claim_kind": "market_summary",
  "region": "杭州",
  "role_scope": "Python 后端",
  "sample_count": 96,
  "collection_start": "2026-08-01",
  "collection_end": "2026-08-10",
  "source_urls": ["https://example.com/job/1"],
  "limitations": ["仅统计公开可访问且去重后的岗位"]
}
```

实时结论需要可访问 HTTPS 来源和日期。市场汇总还需要地区、岗位范围、正样本数、采集区间和限制。单份 JD 使用 `claim_kind: single_jd`，只代表该 JD，不得外推市场。

运行：

```text
python scripts/validate_research.py claims.json
```

## 3. FinalResponseContext

输入：

```json
{
  "text": "最终用户回复",
  "skill_loaded": true,
  "memory_written": false,
  "research_validated": false
}
```

校验器检查 think 标记、常见内部分析短语、内部容器路径，以及在能力未完成时声称“已加载”“已永久记住”“已核验最新信息”。它是最终防线，不替代平台 SSE 过滤。

运行：

```text
python scripts/validate_response.py response.json
```

## 4. 降级状态

内部使用以下状态，面向用户只说明必要影响：

```text
READY
SKILL_LOAD_FAILED
TOOL_UNAVAILABLE
VALIDATION_FAILED
RESEARCH_UNVERIFIED
MEMORY_NOT_PERSISTED
```

任何失败都保留可安全完成的部分；不得把绑定、调用记录、模型记忆或搜索摘要冒充为已加载、已持久化或已核验。
