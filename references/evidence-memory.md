# Evidence and Memory

## 目录

1. Evidence Trust
2. Competency 更新
3. 事实生命周期
4. 记忆后端协议
5. 跨会话与冲突
6. 遗忘

## 1. Evidence Trust

使用以下层级：

```text
SELF_REPORTED
TEXT_SUPPORTED
ARTIFACT_SUBMITTED
ARTIFACT_ASSESSED
EXECUTION_VERIFIED
EXTERNAL_VERIFIED
```

- `SELF_REPORTED`：用户只声称“会/掌握/做过”。
- `TEXT_SUPPORTED`：文本描述覆盖部分标准，但没有检查真实 artifact。
- `ARTIFACT_SUBMITTED`：用户提供作品、文件、链接或结果，尚未完整验收。
- `ARTIFACT_ASSESSED`：可观察 artifact 已按标准逐项检查。
- `EXECUTION_VERIFIED`：代码、模型、计算、实验流程等已在可信环境执行或复核。
- `EXTERNAL_VERIFIED`：可靠第三方成绩、证书、评审或正式结果。

同一证据记录来源、时间、对应能力、支持的标准、信任等级、置信度和限制。不要把 Evidence ID 与 verified Evidence ID 混为一谈。

## 2. Competency 更新

能力状态至少区分 claimed、supported 和 verified。规则：

- 自述可以影响诊断起点，但不能提高 verified level。
- 文本支持可以减少重复教学，但仍需要验证任务。
- 作品只有通过相应标准后才能提高 verified level。
- 局部通过只更新相应子能力。
- 新证据与旧证据冲突时，说明冲突并优先安排验证，不静默覆盖。
- 只有 verified level 或目标真正改变时才重新计算 Gap 与计划。

## 3. 事实生命周期

| 信息 | 默认生命周期 |
| --- | --- |
| 确认专业、年级、长期目标 | 长期，允许用户修正 |
| 稳定时间约束、学习偏好 | 长期或定期复核 |
| 目标历史、重要决定 | 有界历史 |
| 进行中任务和 checkpoint | 持续到完成、取消或失效 |
| Evidence 与 Assessment | 长期，但保留来源和状态 |
| 当前学习 topic | 当前会话/短期 |
| 普通压力与临时情绪 | 当前会话，不默认长期保存 |
| 第三方信息、否定候选 | 不保存为用户事实 |
| 模型推断与建议 | 不保存为 Known |

相同或等价信息应更新/合并，召回和历史保持有界。

## 4. 记忆后端协议

本 Skill 不要求 SQLite、Neo4j 或任何固定数据库。文件读写可用时，把 [persistent-memory.md](persistent-memory.md) 定义的个人目录作为跨会话事实来源；宿主记忆只用于保存个人档案标识、目录定位器或少量高价值摘要。无论使用哪种后端：

1. 读取当前用户、当前任务直接相关的少量状态；
2. 使用宿主定义的用户隔离边界；
3. 写入前应用事实与信任门禁；
4. 不保存身份证号、银行卡、密码、精确住址等高敏感信息；
5. 不保存 chain-of-thought、隐藏推理或私有草稿；
6. 写入后回读关键字段，失败时继续当前任务并明确记忆未持久化。

没有可写文件目录且没有宿主记忆时，在回复末尾给一个可复制的“继续摘要”，包含目标、当前任务、完成证据和下次起点。不要声称下次会自动记得。

## 5. 跨会话与冲突

跨会话恢复应满足：

- confirmed major 可以恢复；错误 candidate major 不恢复。
- current topic 不永久占据专业或目标。
- changed goal 使用新目标，旧目标只作为有界历史。
- evidence trust 原样恢复，不把低可信证据升级。
- self-report 不使 verified competency 过度提高。
- 只恢复当前请求需要的内容，不把全部历史倾倒给用户。

用户新陈述与记忆冲突时，明确指出关键冲突。用户明确修正具有最高优先级；含糊修正先确认。

## 6. 遗忘

用户要求忘记时，优先调用宿主提供的删除/遗忘能力，删除该用户在本 Skill 范围内的结构化状态、语义记忆、索引和临时缓存。无法验证完整删除时，明确说明宿主限制和用户可采取的设置操作。遗忘后不要继续利用已删除内容。
