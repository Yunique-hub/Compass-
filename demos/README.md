# Compass v2.1 演示

推荐先运行四个交互式验收 Demo：

```powershell
python scripts/demo/onboarding_demo.py
python scripts/demo/it_support_student_demo.py
python scripts/demo/six_brain_demo.py
python scripts/demo/full_growth_demo.py
```

它们分别验证渐进 onboarding、真实 IT 支持学生规划、六脑离线回归，以及建档—规划—降载—考试优先—新会话恢复的完整生命周期。每个脚本都有真实断言，失败时返回非零退出码。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\demo_v2.py --output runtime\demo-output-v2
```

脚本会执行 9 个确定性场景：职业方向自动评分、考试复习、统一时间预算、明确同意的记忆写入、跨会话召回、策略反馈、当前交互主动提醒、安全优先路由，以及 Archive v1→v2 迁移/策略写入边界。完整结果写入 `runtime/demo-output-v2/demo-results.json`，该运行时目录不会进入发布包。
