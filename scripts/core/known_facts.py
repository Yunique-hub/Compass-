"""Extract and merge explicit, field-level facts for interaction decisions."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping


def _fact(value: Any, confidence: float = 1.0, source: str = "user_explicit") -> dict[str, Any]:
    return {"value": value, "confidence": confidence, "source": source, "updated_at": datetime.now(timezone.utc).isoformat()}


def fact_value(facts: Mapping[str, Any], key: str, default: Any = None) -> Any:
    item = facts.get(key)
    return item.get("value", default) if isinstance(item, Mapping) else default


def _first(text: str, values: tuple[str, ...]) -> str:
    return next((value for value in values if value.casefold() in text.casefold()), "")


def extract_known_facts(message: str, request: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Extract only observable facts; inferred stages are handled separately."""
    request = request or {}
    text = str(message or "").strip()
    lowered = text.casefold()
    facts: dict[str, dict[str, Any]] = {}

    if any(phrase in text for phrase in ("不要叫我名字", "别叫我名字", "不用称呼我", "不要称呼我")):
        facts["preferred_name_usage"] = _fact(False)
    else:
        name_match = re.search(r"(?:以后)?(?:叫我|称呼我)\s*([A-Za-z\u4e00-\u9fff·]{1,20})", text)
        if not name_match:
            name_match = re.search(r"我叫\s*([A-Za-z\u4e00-\u9fff·]{1,20})", text)
        if name_match:
            facts["preferred_name"] = _fact(name_match.group(1))
            facts["preferred_name_usage"] = _fact(True)

    education = _first(text, ("专科", "本科", "硕士", "研究生", "高中"))
    if education:
        facts["education_level"] = _fact(education)
    grade = _first(text, ("大一", "大二", "大三", "大四", "研一", "研二", "研三"))
    if grade:
        facts["grade"] = _fact(grade)

    majors = (
        "计算机网络技术", "计算机科学与技术", "软件工程", "网络工程", "信息安全",
        "数据科学", "人工智能", "电子信息", "大数据", "计算机",
    )
    major = _first(text, majors)
    if not major:
        major_match = re.search(r"([A-Za-z\u4e00-\u9fff+#]{2,18})专业", text)
        major = major_match.group(1) if major_match else ""
    if major:
        facts["major"] = _fact(major)

    skills = [
        skill for skill in (
            "路由交换", "网络安全", "服务器配置", "服务器", "网络故障排查", "Linux",
            "Windows", "Python", "PyCharm", "PowerShell", "Shell", "Git", "Java", "SQL",
            "数据库", "数据结构", "测试", "数据分析",
        ) if skill.casefold() in lowered
    ]
    if skills:
        facts["skills"] = _fact(list(dict.fromkeys(skills)))

    if "明年实习" in text:
        facts["deadline_event"] = _fact("实习")
        facts["deadline_time"] = _fact("明年")
        facts["primary_need"] = _fact("实习准备")
    elif any(term in text for term in ("准备实习", "怎么准备实习", "找实习", "实习就业")):
        facts["primary_need"] = _fact("实习准备")
    elif any(term in text for term in ("秋招", "春招", "找工作", "求职", "直接就业")):
        facts["primary_need"] = _fact("就业准备")
    elif any(term in text for term in ("考试", "期末", "复习")):
        facts["primary_need"] = _fact("考试复习")
    elif any(term in text for term in ("学习", "课程")):
        facts["primary_need"] = _fact("学习提升")
    elif any(term in text for term in ("迷茫", "不知道现在该干什么", "现在该怎么", "我现在该做什么")):
        facts["primary_need"] = _fact("成长方向")

    if "毕业后直接就业" in text or "毕业直接就业" in text:
        facts["post_graduation_goal"] = _fact("直接就业")

    direction_change = any(
        phrase in lowered
        for phrase in ("不想做it支持", "不做it支持", "不考虑it支持", "放弃it支持")
    )
    if direction_change:
        facts["career_direction"] = _fact("")
        facts["excluded_direction"] = _fact("IT支持")
        facts["direction_status"] = _fact("changed")
    else:
        directions: list[str] = []
        if "it支持" in lowered or "it 支持" in lowered or "技术支持" in text:
            directions.append("IT支持")
        if "网络运维" in text:
            directions.append("网络运维")
        if "devops" in lowered:
            directions.append("DevOps Support")
        if directions:
            candidate_language = len(directions) > 1 or any(term in text for term in ("都可以", "或者", "都行", "初步"))
            facts["career_direction"] = _fact(directions if candidate_language else directions[0])
            facts["direction_status"] = _fact("candidate" if candidate_language else "confirmed")

    daily_match = re.search(r"每天[^，。；;\n]{0,12}?(\d+(?:\.\d+)?)\s*(?:个)?小时", text)
    weekly_match = re.search(r"每周[^，。；;\n]{0,12}?(\d+(?:\.\d+)?)\s*(?:个)?小时", text)
    if daily_match:
        facts["daily_learning_hours"] = _fact(float(daily_match.group(1)))
    if weekly_match:
        facts["weekly_learning_hours"] = _fact(float(weekly_match.group(1)))

    exam_match = re.search(r"(?:考试|期末)(?:还有|剩|在)?\s*(\d+)\s*天", text)
    if exam_match:
        facts["exam_days"] = _fact(int(exam_match.group(1)))

    if "互联网公司" in text or "互联网企业" in text:
        facts["company_preference"] = _fact("互联网公司")
    if any(term in text for term in ("喜欢写代码", "喜欢编程", "对编程感兴趣")):
        facts["coding_interest"] = _fact(True)
    if "python" in lowered and any(term in text for term in ("项目经验", "简单项目", "做过项目")):
        facts["python_project_experience"] = _fact(True)

    city_match = re.search(r"(?:目标城市(?:是|为)?|准备去|毕业(?:后)?(?:准备|想)?去|想去|希望去|去)\s*([\u4e00-\u9fff]{2,12}?)(?:市)?(?=做|从事|当|找|的|\s|，|。|$)|在\s*([\u4e00-\u9fff]{2,12}市)(?=做|从事|当|找)", text)
    if city_match:
        facts["target_city"] = _fact((city_match.group(1) or city_match.group(2)).removesuffix("市"))

    target_job_match = re.search(r"(?:目标(?:岗位|职位|工作)?(?:是|为)?|想做|做|从事|当|找(?:一份)?)([A-Za-z0-9+#.\-\u4e00-\u9fff /]{2,40}?)(?=岗位|职位|工作|方向|[，。；;！!？?]|$)", text, re.I)
    if target_job_match:
        target_job = target_job_match.group(1).strip("，。；;、：: ")
        if target_job:
            facts["target_job"] = _fact(target_job)

    course = str(request.get("course", "")).strip()
    if course:
        facts["course"] = _fact(course)
    if request.get("weekly_hours") is not None:
        facts["weekly_learning_hours"] = _fact(float(request["weekly_hours"]))
    if request.get("exam_days") is not None:
        facts["exam_days"] = _fact(int(request["exam_days"]))
    if request.get("actual_hours") is not None:
        facts["last_actual_hours"] = _fact(float(request["actual_hours"]))
    if request.get("completed_weeks") is not None:
        facts["completed_weeks"] = _fact(int(request["completed_weeks"]))
    if request.get("target_city"):
        facts["target_city"] = _fact(str(request["target_city"]).strip())
    if request.get("target_job"):
        facts["target_job"] = _fact(str(request["target_job"]).strip())
    return facts


def merge_known_facts(existing: Mapping[str, Any] | None, incoming: Mapping[str, Any]) -> dict[str, Any]:
    merged = {key: dict(value) if isinstance(value, Mapping) else value for key, value in (existing or {}).items()}
    for key, value in incoming.items():
        if key == "skills" and key in merged:
            old = list(fact_value(merged, key, []))
            new = list(value.get("value", []))
            merged[key] = _fact(list(dict.fromkeys([*old, *new])), max(float(merged[key].get("confidence", 0)), float(value.get("confidence", 0))))
        else:
            merged[key] = dict(value)
    return merged
