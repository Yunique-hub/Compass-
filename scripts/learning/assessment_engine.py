"""Evidence-first assessment for structured and natural-language submissions."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


STATUS_WEIGHT = {"MET": 1.0, "PARTIAL": 0.5, "UNCLEAR": 0.25, "MISSING": 0.0}
VAGUE_SIGNALS = ("应该", "可能", "差不多", "大概", "记不清", "好像")
PARTIAL_SIGNALS = ("只做了一半", "做了一半", "只完成一半", "部分完成", "没完全", "还差")
UNCERTAIN_SIGNALS = ("不确定", "不清楚", "不知道", "对不对", "有没有问题")
NEGATIVE_SIGNALS = ("还没", "尚未", "没有", "没做", "未做", "未完成", "没有完成", "没开始")


def _submission_text(submission: Mapping[str, Any]) -> str:
    values = [submission.get(key) for key in ("text", "description", "answer", "content", "message")]
    return "\n".join(str(value).strip() for value in values if value not in (None, "", [], {}))


def _contains(text: str, *signals: str) -> list[str]:
    lowered = text.casefold()
    matches: list[str] = []
    for signal in signals:
        start = lowered.find(signal.casefold())
        while start >= 0:
            prefix = text[max(0, start - 10):start]
            negated = bool(re.search(r"(?:还没|尚未|未|没有|没)(?:有|做|完成|进行|包含|提供|实现|计算)?\s*$", prefix))
            if not negated:
                matches.append(signal)
                break
            start = lowered.find(signal.casefold(), start + 1)
    return matches


def _local_clause(text: str, start: int, end: int) -> str:
    boundaries = ("，", ",", "。", "；", ";", "\n", "但是", "不过", "然而", "但")
    left = 0
    right = len(text)
    for boundary in boundaries:
        position = text.rfind(boundary, 0, start)
        if position >= left:
            left = position + len(boundary)
        position = text.find(boundary, end)
        if position >= 0:
            right = min(right, position)
    return text[left:right]


def _group_state(text: str, signals: tuple[str, ...]) -> tuple[str, list[str]]:
    occurrences: list[tuple[str, str]] = []
    lowered = text.casefold()
    for signal in signals:
        start = lowered.find(signal.casefold())
        while start >= 0:
            occurrences.append((signal, _local_clause(text, start, start + len(signal))))
            start = lowered.find(signal.casefold(), start + 1)
    if not occurrences:
        return "MISSING", []
    states: list[str] = []
    evidence: list[str] = []
    for signal, clause in occurrences:
        if any(marker in clause for marker in NEGATIVE_SIGNALS):
            states.append("MISSING")
        elif any(marker in clause for marker in PARTIAL_SIGNALS):
            states.append("PARTIAL")
            evidence.append(signal)
        elif any(marker in clause for marker in UNCERTAIN_SIGNALS):
            states.append("UNCLEAR")
            evidence.append(signal)
        else:
            states.append("MET")
            evidence.append(signal)
    if "MET" in states:
        return "MET", list(dict.fromkeys(evidence))
    if "PARTIAL" in states:
        return "PARTIAL", list(dict.fromkeys(evidence))
    if "UNCLEAR" in states:
        return "UNCLEAR", list(dict.fromkeys(evidence))
    return "MISSING", []


def _criterion_groups(criterion: str, skill: str) -> list[tuple[str, ...]]:
    lowered = f"{skill} {criterion}".casefold()
    if "fcff" in lowered:
        return [("FCFF", "自由现金流")]
    if "wacc" in lowered:
        return [("WACC",), ("折现", "discount")]
    if "终值" in lowered or "敏感性" in lowered:
        groups: list[tuple[str, ...]] = []
        if "终值" in lowered:
            groups.append(("终值", "永续增长", "terminal value", "退出倍数"))
        if "敏感性" in lowered:
            groups.append(("敏感性", "sensitivity"))
        return groups
    if "健康检查" in lowered or "health" in lowered:
        return (("/health", "健康检查", "health endpoint"), ("200", "ok", "正常响应"))
    if "参数校验" in lowered:
        return [("参数校验", "Pydantic", "validation", "422")]
    if "自动化测试" in lowered or "异常响应" in lowered:
        return [("自动化测试", "pytest", "TestClient", "测试用例"), ("异常", "错误响应", "4xx", "422")]
    if "irac" in lowered:
        return [("IRAC",), ("争点", "issue"), ("规则", "rule"), ("适用", "application"), ("结论", "conclusion")]
    if "法条" in lowered:
        return [("法条", "第"), ("适用", "依据", "关系")]
    if "阳性" in lowered or "阴性" in lowered:
        return [("阳性",), ("阴性",)]
    if "鉴别诊断" in lowered:
        return [("鉴别诊断",), ("依据", "理由", "因为")]
    if "下一步检查" in lowered or "处理" in lowered:
        return [("检查", "处理"), ("依据", "理由", "因为")]
    return []


def _generic_signals(criterion: str) -> list[str]:
    vocabulary = (
        "假设", "预测", "折现", "终值", "敏感性", "接口", "参数", "校验", "测试", "异常",
        "争点", "规则", "适用", "结论", "法条", "病例", "鉴别诊断", "检查", "处理", "证据",
        "结果", "复盘", "文献", "引用", "数据", "图表", "模型", "代码", "运行",
    )
    signals = _contains(criterion, *vocabulary)
    signals.extend(re.findall(r"[A-Za-z][A-Za-z0-9_./+#-]{1,20}", criterion))
    return list(dict.fromkeys(signals))


def _assess_criterion(text: str, criterion: str, skill: str) -> tuple[str, list[str], float]:
    groups = _criterion_groups(criterion, skill)
    evidence: list[str] = []
    if "法条" in criterion:
        article_refs = re.findall(r"第[一二三四五六七八九十百千万零〇两\d]+条", text)
        law_refs = re.findall(r"《[^》]{2,30}》", text)
        if len(set(article_refs)) >= 2:
            evidence.extend(article_refs[:3])
            if law_refs:
                evidence.extend(law_refs[:2])
            relation = _contains(text, "适用", "依据", "关系", "因为")
            evidence.extend(relation)
            return ("MET" if relation else "PARTIAL", list(dict.fromkeys(evidence)), 0.95 if relation else 0.75)
        if article_refs or law_refs:
            return "PARTIAL", list(dict.fromkeys([*law_refs, *article_refs])), 0.7

    if groups:
        group_states: list[str] = []
        for group in groups:
            group_status, matches = _group_state(text, group)
            group_states.append(group_status)
            evidence.extend(matches)
        if all(state == "MET" for state in group_states):
            return "MET", list(dict.fromkeys(evidence)), 0.95
        if all(state == "MISSING" for state in group_states):
            return "MISSING", [], 0.95
        if "PARTIAL" in group_states or ("MET" in group_states and "MISSING" in group_states):
            return "PARTIAL", list(dict.fromkeys(evidence)), 0.72
        if "UNCLEAR" in group_states:
            return "UNCLEAR", list(dict.fromkeys(evidence)), 0.55
        return "MISSING", [], 0.9

    signals = _generic_signals(criterion)
    matches = _contains(text, *signals) if signals else []
    if signals and len(matches) == len(signals):
        return "MET", matches, 0.82
    if matches:
        return "PARTIAL", matches, 0.62
    if any(signal in text for signal in VAGUE_SIGNALS):
        return "UNCLEAR", [], 0.35
    return "MISSING", [], 0.65


class AssessmentEngine:
    def __init__(self, *, passing_score: float = 0.7) -> None:
        self.passing_score = passing_score

    def evaluate(self, *, skill: str, submission: Mapping[str, Any], criteria: Sequence[str]) -> dict[str, Any]:
        structured = submission.get("criteria_met", [])
        explicitly_met = set(structured if isinstance(structured, list) else [])
        force_pass = submission.get("passed") is True and submission.get("trusted_structured") is True
        text = _submission_text(submission)
        checks: list[dict[str, Any]] = []

        for criterion in criteria:
            if force_pass or criterion in explicitly_met:
                status, evidence, confidence = "MET", ["structured confirmation"], 1.0
            elif text:
                status, evidence, confidence = _assess_criterion(text, criterion, skill)
            else:
                status, evidence, confidence = "MISSING", [], 1.0
            if status == "MET":
                feedback = "提交中有可观察信息支持该标准。"
                next_action = "保留当前证据。"
            elif status == "PARTIAL":
                feedback = "已有部分相关证据，但尚未覆盖该标准的全部要求。"
                next_action = f"补充并明确：{criterion}。"
            elif status == "UNCLEAR":
                feedback = "当前只有模糊完成声明，无法核验具体结果。"
                next_action = f"提供可检查的过程或结果来证明：{criterion}。"
            else:
                feedback = "提交中未找到支持该标准的证据。"
                next_action = f"完成或补交：{criterion}。"
            checks.append(
                {
                    "criterion": criterion,
                    "status": status,
                    "met": status == "MET",
                    "supporting_evidence": evidence,
                    "feedback": feedback,
                    "next_action": next_action,
                    "confidence": round(confidence, 2),
                }
            )

        score = sum(STATUS_WEIGHT[item["status"]] for item in checks) / len(checks) if checks else 0.0
        passed = bool(checks) and score >= self.passing_score and all(item["status"] == "MET" for item in checks)
        pending = [item for item in checks if item["status"] != "MET"]
        next_action = "；".join(item["next_action"] for item in pending[:2]) or "进入下一项练习，并继续保留可检查证据。"
        confidence = sum(float(item["confidence"]) for item in checks) / len(checks) if checks else 0.0
        feedback = "已达到验收标准，可形成能力证据。" if passed else f"本次证据得分 {score:.0%}；{next_action}"
        structured_complete = bool(checks) and all(item["criterion"] in explicitly_met for item in checks)
        return {
            "assessment_id": str(uuid.uuid4()),
            "skill": skill,
            "score": round(score, 4),
            "passed": passed,
            "criteria": checks,
            "feedback": feedback,
            "next_action": next_action,
            "confidence": round(confidence, 4),
            "submission_evidence": text,
            "verification_basis": "structured_criteria" if structured_complete or force_pass else "natural_language",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
