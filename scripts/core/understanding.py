"""Composable deterministic understanding with a bounded semantic fallback."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from scripts.academic.major_engine import MajorMentionType, classify_major_mention

from .intent_router import Intent, route_intent


DIFFICULTY_SIGNALS = (
    "学不会", "学得很痛苦", "很痛苦", "完全看不懂", "做题总错", "看懂了但不会做", "看懂但不会做",
    "记不住", "越学越乱", "基础特别差", "基础差", "卡了很久", "卡很久", "很难", "很吃力",
)
ASSESSMENT_SIGNALS = (
    "FCFF", "WACC", "终值", "敏感性", "IRAC", "法条", "鉴别诊断", "/health", "返回 200", "测试通过",
)
ROLE_SIGNALS = ("Python 后端", "后端", "投行", "律所", "UI/UX", "用户研究", "机器人", "数据分析", "量化", "教师")


@dataclass
class Understanding:
    primary_intent: str
    secondary_intents: list[str] = field(default_factory=list)
    academic_major: str | None = None
    learning_domain: str | None = None
    current_topic: str | None = None
    target_domain: str | None = None
    user_goal: str | None = None
    target_role: str | None = None
    difficulty_signal: str | None = None
    emotional_signal: str | None = None
    known: dict[str, Any] = field(default_factory=dict)
    inferred: dict[str, Any] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)
    confidence: float = 0.0
    fallback_used: bool = False
    multi_intent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fallback_topic(text: str) -> str:
    patterns = (
        r"(?:^|[，。；;])\s*([\u4e00-\u9fffA-Za-z0-9+#./&·]{2,20}?)(?=最近(?:学得)?(?:很)?痛苦)",
        r"(?:^|[，。；;])\s*([\u4e00-\u9fffA-Za-z0-9+#./&·]{2,20}?)(?=(?:完全看不懂|做题总错|记不住|越学越乱|卡了?很久))",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()
    return ""


def understand_message(
    message: str,
    attachments: Sequence[Any] | None = None,
    *,
    active_exercise: bool = False,
) -> Understanding:
    text = str(message or "").strip()
    deterministic = route_intent(text, attachments)
    mention = classify_major_mention(text)
    difficulty = next((signal for signal in DIFFICULTY_SIGNALS if signal.casefold() in text.casefold()), "")
    topic = mention.current_topic or _fallback_topic(text)
    target_role = next((role for role in ROLE_SIGNALS if role.casefold() in text.casefold()), "")
    decision_signal = bool(re.search(r"(?:先.+还是.+|应该.+还是.+|优先.+还是.+)", text))
    internship_signal = any(signal in text for signal in ("实习", "找工作", "求职", "秋招", "春招"))
    assessment_signal = active_exercise and any(signal.casefold() in text.casefold() for signal in ASSESSMENT_SIGNALS)

    secondary: list[str] = []
    primary = deterministic
    fallback_used = False
    if assessment_signal and deterministic is Intent.GENERAL_SUPPORT:
        primary, fallback_used = Intent.SUBMIT_EXERCISE, True
    elif decision_signal and (difficulty or internship_signal):
        primary, fallback_used = Intent.LEARNING_PLAN, deterministic is not Intent.LEARNING_PLAN
        if difficulty:
            secondary.append(Intent.START_LEARNING.value)
        if internship_signal:
            secondary.append(Intent.CAREER_GAP.value)
    elif deterministic is Intent.GENERAL_SUPPORT and difficulty:
        primary, fallback_used = Intent.START_LEARNING, True

    academic_major = mention.raw_major if mention.mention_type in {
        MajorMentionType.EXPLICIT_MAJOR,
        MajorMentionType.EXPLICIT_SECONDARY_MAJOR,
    } and mention.persistable else None
    known: dict[str, Any] = {}
    if academic_major:
        known["academic_major"] = academic_major
    if topic:
        known["current_topic"] = topic
    if difficulty:
        known["learning_difficulty"] = difficulty
    if target_role:
        known["target_role"] = target_role

    inferred: dict[str, Any] = {}
    unknown: list[str] = []
    if difficulty:
        inferred["difficulty_cause"] = "可能涉及先修知识、任务难度或练习反馈方式，需要诊断"
        unknown.extend(["actual_mastery_level", "specific_blocker"])
    if internship_signal:
        inferred["career_preparation_needed"] = True
    if not academic_major:
        unknown.append("academic_major")

    goal = ""
    if decision_signal:
        goal = "在学习补弱与职业准备之间确定当前优先级"
    elif internship_signal:
        goal = f"准备{target_role or '目标方向'}实习"
    elif difficulty:
        goal = f"诊断并改善{topic or '当前内容'}的学习困难"

    emotional = "frustrated" if any(signal in text for signal in ("痛苦", "越学越乱", "卡了很久", "完全看不懂")) else ""
    confidence = 0.95 if deterministic is not Intent.GENERAL_SUPPORT and not fallback_used else (0.82 if fallback_used else 0.55)
    secondary = list(dict.fromkeys(item for item in secondary if item != primary.value))
    return Understanding(
        primary_intent=primary.value,
        secondary_intents=secondary,
        academic_major=academic_major,
        learning_domain=mention.learning_domain or (topic or None),
        current_topic=topic or None,
        target_domain=target_role or None,
        user_goal=goal or None,
        target_role=target_role or None,
        difficulty_signal=difficulty or None,
        emotional_signal=emotional or None,
        known=known,
        inferred=inferred,
        unknown=list(dict.fromkeys(unknown)),
        confidence=confidence,
        fallback_used=fallback_used,
        multi_intent=bool(secondary),
    )
