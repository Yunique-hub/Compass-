# Information Sufficiency Rules

充分性回答的问题是“现在是否足够给出有价值的下一步”，不是“档案是否完整”。

## 基础规则

- `major + grade + primary_need` 构成基本定位。
- 技能、稳定时间或明确期限至少提供一类可执行约束。
- 职业/实习计划通常需要专业、年级和技能基础。
- 方向已确认但城市缺失时，允许 `PRELIMINARY_PLAN`。
- 面向特定城市的招聘/JD 正式计划需要方向、城市和时间。
- 考试临近但课程或材料缺失时，允许基础复习策略，同时明确“不是教师真实考点”。

## 输出结构

内部结果包含 `score`、`known_fields`、`missing_blocking`、`missing_non_blocking`、`action_ready`、`confidence`、`next_questions` 和 `planning_mode`。用户回复不得泄露分数或内部字段名。

非阻塞字段永远后置：先给诊断、目标和任务，再自然说明该信息未来如何提高精度。
