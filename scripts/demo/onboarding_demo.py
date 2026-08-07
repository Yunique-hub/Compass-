"""Human-readable action-first onboarding demonstration."""
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
        "我是专科大二计算机网络技术专业，明年实习，现在该怎么准备？",
        "学过路由交换、网络安全、服务器配置，想做IT支持，会一点Python，每天6小时。",
    ]
    with TemporaryDirectory(prefix="compass-onboarding-") as runtime:
        engine = CompassEngine(runtime)
        outputs = []
        for index, message in enumerate(messages, 1):
            output = engine.run({"user_id": "onboarding-demo", "message": message})["data"]
            outputs.append(output)
            print(f"\n===== 第 {index} 轮 =====\n用户：{message}\nCompass：\n{output['text']}")

        assert outputs[0]["state"] == "ASKING_PREFERRED_NAME"
        assert outputs[1]["archive"]["preferred_name"] == "小宇"
        assert outputs[2]["archive"]["current_growth_stage"] == "INTERNSHIP_PREPARATION_STAGE"
        assert outputs[3]["archive"]["profile_sufficiency"]["action_ready"] is True
        assert len(outputs[3]["response"]["details"]["business"]["goal_plan"]["weekly_core_tasks"]) <= 3
    print("\n[PASS] 称呼 → 最小画像 → 阶段判断 → 立即规划。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
