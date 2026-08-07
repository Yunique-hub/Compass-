"""Full lifecycle: onboarding, plan, feedback, exam priority and resume."""
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
        "我是专科大二计算机网络技术专业，明年实习。",
        "学过路由交换、网络安全、服务器配置，想做IT支持，会点Python，每天6小时。",
        "互联网公司，喜欢写代码，Python有简单项目经验。",
        "这个星期任务太多了。",
        "考试还有5天。",
    ]
    with TemporaryDirectory(prefix="compass-full-growth-") as runtime:
        engine = CompassEngine(runtime)
        outputs = []
        for index, message in enumerate(messages, 1):
            output = engine.run({"user_id": "full-growth-demo", "message": message})["data"]
            outputs.append(output)
            print(f"\n[{index}] 用户：{message}\nCompass：{output['text']}")

        resumed = CompassEngine(runtime).run({"user_id": "full-growth-demo", "message": "继续上次。"})["data"]
        print(f"\n[新会话] 用户：继续上次。\nCompass：{resumed['text']}")

        assert outputs[4]["archive"]["onboarding_complete"] is True
        assert outputs[5]["response"]["details"]["business"]["improvement"]
        assert outputs[6]["archive"]["current_growth_stage"] == "EXAM_SPRINT_STAGE"
        assert outputs[6]["response"]["details"]["business"]["review"]
        assert "小宇" in resumed["text"] and "怎么称呼" not in resumed["text"]
    print("\n[PASS] 建档、规划、降载、考试优先与新会话恢复全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
