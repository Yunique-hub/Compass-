# Persistent Memory and Evidence

仅在用户要求记住、恢复、继续长期任务，或需要保存已验证经验时读取。

## 1. 能力与写入边界

把可回读的文件或宿主记忆作为跨会话状态来源，不把模型上下文本身称为永久记忆。只有同时满足以下条件才声称“已保存”：

1. 用户授权保存该类信息；
2. 路径或宿主记忆位于允许的写入范围；
3. 写入成功；
4. 回读 profile、更新时间和下一动作一致。

文件不可写或宿主没有记忆能力时，输出可复制的继续摘要，不声称后续会话会自动记得。

## 2. 状态位置

用户没有限定目录且明确授权个人持久化时，默认使用：

```text
~/.compass/users/<profile-id>/
```

- 兼容旧 `~/.compass-student-growth/users/<profile-id>/`；新目录不存在而旧目录存在时，先恢复旧档案，不同时创建两份。
- 用户只授权当前项目时，使用项目内 `.compass/`。
- 用户只授权课程资料目录时，使用 `.compass-review/`。
- 不把记忆写入 Skill 安装目录、ZIP、Git 历史或公共共享目录。
- 共享设备每次只使用一个确认的 profile；归属冲突时暂停写入，不合并不同用户数据。

## 3. 最小文件结构

按需创建，不预建空数据库：

```text
<profile-root>/
├── MEMORY.md
├── profile.md
├── goals.md
├── evidence.md
├── lessons.md
├── patterns.md
├── workspaces.md
└── checkpoints/
    ├── latest.md
    └── previous.md
```

- `MEMORY.md`：短启动快照，保留当前身份、活动目标、约束、工作区和下一动作。
- `profile.md` / `goals.md`：已确认背景、current/previous/target 和有界目标历史。
- `evidence.md`：来源、时间、标准、信任等级和限制。
- `lessons.md`：已复现、修复并复测的经验。
- `patterns.md`：observed / confirmed / rejected 的工作偏好。
- `workspaces.md`：项目或课程定位器，不复制资料全文。
- `latest.md` / `previous.md`：当前恢复点与最近有效回退。

每个文件记录 `schema_version`、`profile_id` 和带时区的 `updated_at`。

## 4. 恢复

1. 确认当前 profile 和写入边界。
2. 读取 `MEMORY.md` 与 `checkpoints/latest.md`；损坏时使用 `previous.md`。
3. 按当前任务只读一个必要文件，例如职业问题读 goals/evidence，课程复习读 workspace state。
4. 把信息分为 confirmed、pending、stale 和 conflict；过期或冲突内容不静默沿用。
5. 用一句自然语言说明恢复点并继续任务，不倾倒完整档案。

优先级：

```text
用户当前明确修正 > 新验证证据 > latest checkpoint
> canonical files > previous checkpoint > 模型推断
```

## 5. 提交

1. 重新读取待修改文件的 `updated_at`，避免覆盖外部更新。
2. 只保存稳定事实、活动目标、工作区、证据、已验证经验和下一入口。
3. 合并等价项，不重复追加；把旧 `latest.md` 保存为 `previous.md`。
4. 写入新的 canonical 文件、`latest.md` 和短 `MEMORY.md`。
5. 回读 profile、更新时间、变更内容和下一动作；失败时重试一次，仍失败则报告未持久化。

不要保存完整聊天、原始项目/课程全文、长工具输出或临时情绪。

## 6. 证据信任

使用以下等级，不自动升级：

```text
SELF_REPORTED
TEXT_SUPPORTED
ARTIFACT_SUBMITTED
ARTIFACT_ASSESSED
EXECUTION_VERIFIED
EXTERNAL_VERIFIED
```

- 自述可影响教学起点，但不能提高 verified competency。
- 文本覆盖标准时最多标为文本支持；真实 artifact 仍需检查。
- 作品按标准逐项验收后，只更新通过的子能力。
- 代码、模型或计算只有在可信环境运行或复核后才能标记执行验证。
- 冲突证据并列记录并安排验证，不静默覆盖。

成长证据链为：

```text
Goal → Competency → Task → Output → Evidence → Criteria → Verified Competency
```

## 7. 经验与偏好

只把经过验证的修复写入 `lessons.md`，包含问题、触发条件、根因或假设、有效修复、验证证据、适用/不适用范围和预防检查。没有复测的原因保留为 hypothesis。

单次行为只写为 `observed`；用户明确确认或多个场景重复后才能成为 `confirmed`。当前指令和项目规则始终高于历史偏好，记忆不能弱化安全、事实核验、质量或授权标准。

## 8. 隐私与用户控制

- 不保存密码、令牌、身份证号、银行卡、精确住址、无必要健康隐私、第三方隐私或隐藏推理。
- 用户可以查看、纠正、导出、暂停或删除记忆。
- 用户说“不要记住”时不写；要求忘记具体内容时删除对应状态并检查索引和 checkpoint。
- 删除整个档案前展示精确绝对路径、提供导出选项并再次确认。
- 无法验证完整删除时，明确宿主限制和用户可以执行的设置操作。
