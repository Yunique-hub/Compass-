"""Demonstrate traceable market evidence driving a learning task."""
from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in {None, ""}: sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.competency.gap_engine import GapEngine
from scripts.learning.adaptive_planner import AdaptivePlanner
from scripts.recruitment.recruitment_engine import RecruitmentEngine


def main() -> int:
    jds = [{"job_id": f"hz-{index}", "title": "IT支持", "city": "杭州", "text": f"IT支持岗位，要求 Active Directory、Windows Server、PowerShell、网络排障和用户沟通；需要完成实验并记录故障处理。样本{index}", "synthetic": True} for index in range(1, 6)]
    with TemporaryDirectory(prefix="compass-market-demo-") as runtime:
        market = RecruitmentEngine(extractor=__import__("scripts.recruitment.skill_extractor", fromlist=["SkillExtractor"]).SkillExtractor(Path(runtime) / "skills.json")).analyze({"target_city": "杭州", "target_job": "IT支持", "jds": jds})
        gaps = GapEngine().calculate(market["skill_statistics"], {})
        plan = AdaptivePlanner().build(goal={"target_city": "杭州", "target_job_normalized": "IT支持", "job_search_time": "明年实习"}, market=market, gaps=gaps, weekly_hours=10)
        print("用户：计算机网络技术大二，目标杭州 IT支持，每周 10 小时")
        print(f"功能夹具：{market['valid_sample_count']} 份 synthetic JD；status={market['market_data_status']}")
        print("技能：" + "、".join(item["skill"] for item in market["skill_statistics"][:5]))
        print("最高 Gap：" + gaps[0]["skill"])
        print("任务：" + plan["weekly_core_tasks"][0]["title"])
        print("为什么现在学这个：" + plan["weekly_core_tasks"][0]["why"])
        print("真实性声明：" + market["usage_notice"])
        assert market["market_data_status"] == "insufficient" and not plan["formal_plan_generated"]
        assert market["synthetic"] and "仅用于功能测试" in market["usage_notice"]
        assert plan["weekly_core_tasks"][0]["market_evidence"]
    print("[PASS] Target → Query → JD → Skill → Market → Gap → Plan")
    return 0


if __name__ == "__main__": raise SystemExit(main())
