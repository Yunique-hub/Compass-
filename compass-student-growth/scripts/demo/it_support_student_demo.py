"""Realistic IT-support student conversation with a readable final plan."""
from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.compass_engine import CompassEngine


def main() -> int:
    messages = [
        "你好",
        "叫我小宇。",
        "我现在是一名专科生大二计算机网络技术专业，明年实习，现在该怎么去做？",
        "学过路由交换、网络安全、服务器配置，实习方向是网络运维、IT支持，对Python比较感兴趣，毕业后直接就业。",
        "IT支持方向，每天大概能学习6小时。",
        "互联网公司，喜欢写代码，Python有简单项目经验。",
    ]
    with TemporaryDirectory(prefix="compass-it-support-") as runtime:
        engine = CompassEngine(runtime)
        outputs = []
        for index, message in enumerate(messages, 1):
            output = engine.run({"user_id": "it-support-demo", "message": message})["data"]
            outputs.append(output)
            print(f"\n===== 第 {index} 轮 =====\n用户：{message}\nCompass：\n{output['text']}")

        final = outputs[-1]
        plan = final["response"]["details"]["business"]["goal_plan"]
        capacity = final["archive"]["realistic_capacity"]
        facts = final["archive"]["known_facts"]
        assert facts["career_direction"]["value"] == "IT支持"
        assert facts["direction_status"]["value"] == "confirmed"
        assert facts["python_project_experience"]["value"] is True
        assert 1 <= len(plan["weekly_core_tasks"]) <= 3
        assert capacity["planned_weekly_hours"] <= capacity["stated_weekly_hours"] * 0.7
        assert "目标" in final["text"] and "城市" in outputs[-2]["text"]

    print("\n[PASS] IT 支持 + Python 自动化路线已生成，首周未排满 42 小时。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
