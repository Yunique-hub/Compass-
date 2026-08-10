"""Manual cross-major acceptance matrix for Compass 2.5."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from scripts.compass_engine import CompassEngine


SCENARIOS = [
    ("计算机", "计算机大二，想找 Python 后端实习。", ["法考", "临床轮转"]),
    ("金融", "金融大二，以后想进投行。", ["FastAPI", "临床轮转"]),
    ("法学", "法学大三，准备法考并找律所实习。", ["FastAPI", "金融建模"]),
    ("医学", "临床医学大二，想提升内科学临床推理。", ["LeetCode", "投行"]),
    ("机械", "机械大三，准备机器人相关实习。", ["法考", "临床病例"]),
    ("生物", "生物大二，准备申请研究生，科研经历为零。", ["FastAPI", "投行"]),
    ("心理", "心理学大二，准备申请研究生。", ["后端", "法考"]),
    ("设计", "视觉传达大二，想做 UI/UX。", ["SQLAlchemy", "临床轮转"]),
    ("语言", "英语专业，不知道以后做什么。", ["必须当老师", "FastAPI"]),
    ("教育", "教育学大二，想提升教学设计并积累实践。", ["投行", "后端 API"]),
    ("未知小众专业", "葡萄与葡萄酒工程大二，想知道现在该怎么规划。", ["不支持", "FastAPI"]),
    ("跨专业转行", "我学土木，但不想做土木，想转数据分析。", ["必须继续土木"]),
    ("双专业", "我是数学和经济双专业，不知道走量化还是经济学研究。", ["必须只选数学"]),
    ("未定方向", "大一还没分流，也没想好以后做什么。", ["必须做程序员"]),
]


def run_matrix(runtime_dir: str | Path | None = None) -> dict[str, Any]:
    temporary = tempfile.TemporaryDirectory(prefix="compass-v24-matrix-") if runtime_dir is None else None
    root = Path(runtime_dir or temporary.name)
    engine = CompassEngine(root)
    reports = []
    for index, (case, message, forbidden) in enumerate(SCENARIOS, 1):
        data = engine.run({"user_id": f"matrix-{index}", "message": message})["data"]
        business = data["response"]["details"]["business"]
        context = business["growth_context"]
        profile = context["academic_profile"]
        first_action = (data["response"].get("do_now") or [""])[0]
        corpus = data["text"] + json.dumps(context, ensure_ascii=False)
        leaks = [term for term in forbidden if term in corpus]
        reports.append({
            "case": case,
            "detected_major": profile["raw_major"] or profile["normalized_major"],
            "discipline_family": profile["discipline_family"],
            "pathway": context["target_pathway"],
            "core_competency": context["competencies"][:5],
            "first_stage_action": first_action,
            "domain_leakage": leaks,
            "passed": not leaks and bool(first_action),
        })
    if temporary is not None:
        temporary.cleanup()
    return {"scenario_count": len(reports), "all_passed": all(item["passed"] for item in reports), "scenarios": reports}


if __name__ == "__main__":
    report = run_matrix()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["all_passed"] else 2)
