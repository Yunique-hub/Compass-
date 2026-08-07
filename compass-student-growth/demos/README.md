# Compass v2 演示

运行：

```powershell
.\.venv\Scripts\python.exe scripts\demo_v2.py --output runtime\demo-output-v2
```

脚本会执行 9 个确定性场景：职业方向自动评分、考试复习、统一时间预算、明确同意的记忆写入、跨会话召回、策略反馈、当前交互主动提醒、安全优先路由，以及 Archive v1→v2 迁移/策略写入边界。完整结果写入 `runtime/demo-output-v2/demo-results.json`，该运行时目录不会进入发布包。
