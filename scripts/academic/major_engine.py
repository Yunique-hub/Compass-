"""Natural-language academic profile identification with family fallback."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .taxonomy import classify_taxonomy_domain

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "reference" / "academic_profiles.json"


class MajorMentionType(str, Enum):
    EXPLICIT_MAJOR = "EXPLICIT_MAJOR"
    EXPLICIT_PREVIOUS_MAJOR = "EXPLICIT_PREVIOUS_MAJOR"
    EXPLICIT_SECONDARY_MAJOR = "EXPLICIT_SECONDARY_MAJOR"
    EXPLICIT_MINOR = "EXPLICIT_MINOR"
    TARGET_MAJOR = "TARGET_MAJOR"
    DOMAIN_TOPIC = "DOMAIN_TOPIC"
    AMBIGUOUS_MAJOR = "AMBIGUOUS_MAJOR"
    NONE = "NONE"


@dataclass
class MajorMention:
    mention_type: MajorMentionType = MajorMentionType.NONE
    raw_major: str = ""
    normalized_major: str = ""
    discipline_family: str = "other_emerging"
    current_topic: str = ""
    learning_domain: str = ""
    confidence: float = 0.0
    source: str = "none"
    persistable: bool = False
    subject: str = "unknown"
    polarity: str = "unknown"
    temporality: str = "unknown"
    role: str = "none"


@dataclass
class AcademicProfile:
    raw_major: str = ""
    normalized_major: str = ""
    discipline_family: str = "other_emerging"
    taxonomy_domain: str = "other_emerging"
    specialization: str = ""
    degree_level: str = ""
    academic_year: str = ""
    secondary_major: str = ""
    minor: str = ""
    institution_context: str = ""
    region: str = ""
    confidence: float = 0.5
    profile_source: str = "fallback"
    knowledge_source: str = "fallback"
    major_status: str = "unknown"
    learning_domain: str = ""
    current_topic: str = ""
    previous_majors: list[str] = field(default_factory=list)
    transition_target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_profiles() -> dict[str, Any]:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _clean_major(value: str) -> str:
    value = re.sub(r"^(?:我现在是(?:一名)?|我是|我学|我读|本科读|主修|专业是|学的是|读的是)", "", value.strip())
    value = re.sub(r"^(?:一名)?(?:专科生?|本科生?|研究生|博士生?)", "", value)
    value = re.sub(r"^(?:大一|大二|大三|大四|研一|研二|研三)", "", value)
    value = re.sub(r"(?:大一|大二|大三|大四|研一|研二|研三)$", "", value)
    value = re.sub(r"(?:本科|专科|研究生|学生|专业)$", "", value)
    return value.strip(" ，。；;、")


def _curated_match(text: str, profiles: Mapping[str, Any]) -> tuple[str, str, str] | None:
    matches: list[tuple[int, str, str, str]] = []
    for major_id, profile in profiles["majors"].items():
        for alias in profile.get("aliases", []):
            if alias in text:
                matches.append((len(alias), str(alias), major_id, str(profile["discipline_family"])))
    if not matches:
        return None
    _, alias, major_id, family = max(matches)
    return alias, major_id, family


def infer_discipline_family(major: str) -> str:
    text = major.casefold()
    rules = (
        ("medicine_health", ("医", "护理", "药学", "康复", "卫生")),
        ("law", ("法学", "法律")),
        ("finance_accounting", ("金融", "会计", "审计", "财务")),
        ("economics", ("经济", "贸易")),
        ("psychology", ("心理",)),
        ("education", ("教育", "师范")),
        ("business_management", ("工商管理", "市场营销", "人力资源", "旅游管理", "酒店管理")),
        ("languages_linguistics", ("语言", "英语", "翻译")),
        ("journalism_communication", ("新闻", "传播", "媒体")),
        ("art_design", ("设计", "美术", "艺术")),
        ("architecture_built_environment", ("建筑", "规划")),
        ("engineering", ("电子", "电气", "通信")),
        ("computer_information", ("计算机", "软件", "信息", "数据科学", "人工智能")),
        ("mathematics_statistics", ("数学", "统计", "物理", "化学")),
        ("life_sciences", ("生物", "生命", "生态")),
        ("agriculture_environment", ("农业", "农学", "动物", "海洋", "环境", "地质", "葡萄")),
        ("engineering", ("工程", "机械", "材料", "土木", "自动化", "航空", "电气")),
        ("social_humanities", ("历史", "哲学", "文学", "社会", "政治", "公共管理", "文物")),
    )
    return next((family for family, hints in rules if any(hint in text for hint in hints)), "other_emerging")


def _extract_explicit_major(text: str) -> str:
    """Extract a major only from a declaration span, never from the whole text."""
    patterns = (
        r"(?:我的专业是|本科专业是|专业是|我是|我学|我读|本科读|我主修|主修|学的是|读的是|我现在学)\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业|学生|大[一二三四]|研[一二三]|，|。|；|;|但|同时|辅修|专业方向|现在|准备|想|$)",
        r"(?:^|[，。；;])\s*(?:大[一二三四]|研[一二三])\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=(?:专业)?(?:[，。；;]|$))",
        r"(?:^|[，。；;])\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业(?:[，。；;]|$)|(?:大[一二三四]|研[一二三])(?:[，。；;]|$))",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = _clean_major(match.group(1))
            if value:
                return value
    return ""


_DIFFICULTY_SUFFIX = (
    r"(?:学得)?(?:很|太|特别|相当)?(?:痛苦|难|困难|吃力)|学不会|不会|完全看不懂|"
    r"做题总错|看懂了?但不会做|记不住|越学越乱|基础(?:特别)?差|卡了?很久"
)


def _extract_topic(text: str, *, explicit_major: str = "") -> str:
    patterns = (
        rf"(?:^|[，。；;])\s*([\u4e00-\u9fffA-Za-z0-9+#./&·]{{2,30}}?)(?=(?:{_DIFFICULTY_SUFFIX}))",
        rf"(?:^|[，。；;])\s*(?:我)?(?:最近|目前|现在)?(?:正在|在)?(?:学习|学|想学|想了解)\s*([\u4e00-\u9fffA-Za-z0-9+#./&·]{{2,30}}?)(?=(?:{_DIFFICULTY_SUFFIX})|[，。；;]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        topic = match.group(1).strip(" ，。；;、")
        topic = re.sub(r"^(?:我|最近|目前|现在)", "", topic).strip()
        topic = re.sub(r"(?:最近|目前|现在|也|还)$", "", topic).strip()
        if "学不会" in text[match.end(1):] and _curated_match(f"{topic}学", load_profiles()):
            topic = f"{topic}学"
        if topic and topic != explicit_major:
            return topic
    return ""


def _normalize_major(raw_major: str, profiles: Mapping[str, Any]) -> tuple[str, str, str]:
    curated = _curated_match(raw_major, profiles) if raw_major else None
    if curated:
        _, normalized, family = curated
        return normalized, family, "curated"
    if raw_major:
        return raw_major, infer_discipline_family(raw_major), "family_fallback"
    return "", "other_emerging", "fallback"


def classify_major_mention(message: str) -> MajorMention:
    """Classify a mention before deciding whether it may become a durable fact."""
    text = str(message or "").strip()
    profiles = load_profiles()
    third_party = re.search(
        r"(?:我的|我)?(?:同学|朋友|室友|同事|老师|家人|亲戚|哥哥|姐姐|弟弟|妹妹)(?:的)?(?:专业是|是|学|读)\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业|，|。|；|;|$)",
        text,
    )
    negative = re.search(
        r"(?:我(?:的专业)?|我的专业)(?:并)?不(?:是|学|读)\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业|，|。|；|;|$)",
        text,
    )
    transition = re.search(
        r"(?:我)?从\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?:专业)?\s*转(?:专业)?(?:到|入|成)(?:了)?\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?:了)?(?=专业|，|。|；|;|现在|$)",
        text,
    )
    target = re.search(
        r"(?:我)?(?:想|计划|准备|考虑)(?:要)?(?:以后|之后|毕业后)?\s*转(?:专业)?(?:到|入|成)?\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业|，|。|；|;|$)",
        text,
    )
    explicit = _extract_explicit_major(text)
    previous = re.search(r"(?:以前|原来|之前)(?:的)?(?:专业是|学|读)\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业|，|。|；|;|$)", text)
    minor = re.search(r"辅修\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?=专业|，|。|；|;|$)", text)
    double = re.search(r"([\u4e00-\u9fffA-Za-z]{2,15})\s*(?:和|与|\+)\s*([\u4e00-\u9fffA-Za-z]{2,15})双专业", text)
    topic = _extract_topic(text, explicit_major=explicit)

    mention_type = MajorMentionType.NONE
    raw_major = ""
    persistable = False
    source = "none"
    confidence = 0.0
    subject, polarity, temporality, role = "unknown", "unknown", "unknown", "none"
    if third_party:
        raw_major = _clean_major(third_party.group(1))
        subject, polarity, temporality, role = "third_party", "positive", "current", "current_major"
    elif negative:
        raw_major = _clean_major(negative.group(1))
        subject, polarity, temporality, role = "user", "negative", "current", "current_major"
    elif transition:
        raw_major = _clean_major(transition.group(2))
        mention_type, persistable, source, confidence = MajorMentionType.EXPLICIT_MAJOR, True, "user_explicit", 1.0
        subject, polarity, temporality, role = "user", "positive", "current", "current_major"
    elif double:
        raw_major = _clean_major(double.group(1))
        mention_type, persistable, source, confidence = MajorMentionType.EXPLICIT_SECONDARY_MAJOR, True, "user_explicit", 1.0
        subject, polarity, temporality, role = "user", "positive", "current", "secondary_major"
    elif explicit:
        raw_major = explicit
        mention_type, persistable, source, confidence = MajorMentionType.EXPLICIT_MAJOR, True, "user_explicit", 1.0
        subject, polarity, temporality, role = "user", "positive", "current", "current_major"
    elif previous:
        raw_major = _clean_major(previous.group(1))
        mention_type, persistable, source, confidence = MajorMentionType.EXPLICIT_PREVIOUS_MAJOR, True, "user_explicit", 1.0
        subject, polarity, temporality, role = "user", "positive", "past", "previous_major"
    elif minor:
        raw_major = _clean_major(minor.group(1))
        mention_type, persistable, source, confidence = MajorMentionType.EXPLICIT_MINOR, True, "user_explicit", 1.0
    elif target:
        raw_major = _clean_major(target.group(1))
        mention_type, source, confidence = MajorMentionType.TARGET_MAJOR, "user_explicit_target", 1.0
        subject, polarity, temporality, role = "user", "positive", "future", "target_major"
    elif topic:
        mention_type, source, confidence = MajorMentionType.DOMAIN_TOPIC, "user_explicit_topic", 1.0
        subject, polarity, temporality, role = "user", "positive", "current", "topic"

    normalized, family, _ = _normalize_major(raw_major, profiles)
    topic_normalized, topic_family, _ = _normalize_major(topic, profiles)
    learning_domain = topic_family if topic and topic_family != "other_emerging" else (topic_normalized if topic else "")
    return MajorMention(
        mention_type=mention_type,
        raw_major=raw_major,
        normalized_major=normalized,
        discipline_family=family,
        current_topic=topic,
        learning_domain=learning_domain,
        confidence=confidence,
        source=source,
        persistable=persistable,
        subject=subject,
        polarity=polarity,
        temporality=temporality,
        role=role,
    )


def identify_academic_profile(message: str, previous: Mapping[str, Any] | None = None) -> AcademicProfile:
    text = str(message or "").strip()
    profiles = load_profiles()
    previous = previous or {}
    mention = classify_major_mention(text)
    prior_major = str(previous.get("raw_major", ""))
    previous_majors = list(previous.get("previous_majors", []))
    degree = next((item for item in ("专科", "本科", "硕士", "研究生", "博士") if item in text), str(previous.get("degree_level", "")))
    year = next((item for item in ("大一", "大二", "大三", "大四", "研一", "研二", "研三") if item in text), str(previous.get("academic_year", "")))

    if any(term in text for term in ("没分流", "未分流", "还没选专业")):
        return AcademicProfile(raw_major="未分流", normalized_major="undecided", discipline_family="undecided", taxonomy_domain="undecided", degree_level=degree, academic_year=year, confidence=1.0, profile_source="explicit", knowledge_source="curated", major_status="confirmed", previous_majors=previous_majors)

    transition_match = re.search(r"(?:我)?从\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?:专业)?\s*转(?:专业)?(?:到|入|成)(?:了)?\s*([\u4e00-\u9fffA-Za-z&+·]{2,30}?)(?:了)?(?=专业|，|。|；|;|现在|$)", text)
    double_match = re.search(r"([\u4e00-\u9fffA-Za-z]{2,15})\s*(?:和|与|\+)\s*([\u4e00-\u9fffA-Za-z]{2,15})双专业", text)
    minor_match = re.search(r"辅修\s*([\u4e00-\u9fffA-Za-z&+]{2,20}?)(?=专业|，|。|；|;|$)", text)
    specialization_match = re.search(r"(?:专业方向|专业内方向)\s*(?:是|为)?\s*([\u4e00-\u9fffA-Za-z/+]{2,24}?)(?=，|。|；|;|$)", text)
    transition_target_match = re.search(r"(?:准备|想要?|计划)?转(?:行|向|到)?\s*([\u4e00-\u9fffA-Za-z/+]{2,24}?)(?=。|，|$)", text)

    secondary = ""
    transition_target = ""
    if transition_match:
        old_major, raw_major = map(_clean_major, transition_match.groups())
        if old_major and old_major not in previous_majors:
            previous_majors.append(old_major)
        declared_current = True
    elif double_match:
        raw_major, secondary = map(_clean_major, double_match.groups())
        declared_current = True
    else:
        explicit = mention.raw_major if mention.mention_type is MajorMentionType.EXPLICIT_MAJOR else ""
        raw_major = explicit or prior_major
        declared_current = bool(explicit)
        if mention.mention_type is MajorMentionType.EXPLICIT_PREVIOUS_MAJOR and mention.raw_major and mention.raw_major not in previous_majors:
            previous_majors.append(mention.raw_major)
        if mention.mention_type is MajorMentionType.TARGET_MAJOR:
            transition_target = mention.raw_major
        elif transition_target_match and "转专业到" not in text:
            transition_target = _clean_major(transition_target_match.group(1))

    if prior_major and raw_major and prior_major != raw_major and prior_major not in previous_majors:
        previous_majors.append(prior_major)
    normalized, family, knowledge_source = _normalize_major(raw_major, profiles)
    if declared_current:
        confidence, source, major_status = 1.0, "explicit", "confirmed"
    elif raw_major:
        confidence = float(previous.get("confidence", 1.0))
        source = str(previous.get("profile_source", "explicit"))
        knowledge_source = str(previous.get("knowledge_source", knowledge_source))
        major_status = str(previous.get("major_status", "confirmed"))
    else:
        normalized = str(previous.get("normalized_major", ""))
        family = str(previous.get("discipline_family", "other_emerging"))
        confidence, source = float(previous.get("confidence", 0.5)), str(previous.get("profile_source", "fallback"))
        knowledge_source = str(previous.get("knowledge_source", "fallback"))
        major_status = str(previous.get("major_status", "unknown"))
    minor = _clean_major(minor_match.group(1)) if minor_match else str(previous.get("minor", ""))
    specialization = specialization_match.group(1).strip() if specialization_match else str(previous.get("specialization", ""))
    taxonomy_domain = classify_taxonomy_domain(raw_major, family) if raw_major else str(previous.get("taxonomy_domain", classify_taxonomy_domain("", family)))
    return AcademicProfile(raw_major=raw_major, normalized_major=normalized, discipline_family=family, taxonomy_domain=taxonomy_domain, specialization=specialization, degree_level=degree, academic_year=year, secondary_major=secondary or str(previous.get("secondary_major", "")), minor=minor, confidence=confidence, profile_source=source, knowledge_source=knowledge_source, major_status=major_status, learning_domain=mention.learning_domain, current_topic=mention.current_topic, previous_majors=previous_majors, transition_target=transition_target or str(previous.get("transition_target", "")))


def resolve_profile_knowledge(profile: AcademicProfile) -> dict[str, Any]:
    data = load_profiles()
    family = dict(data["families"].get(profile.discipline_family, data["families"]["other_emerging"]))
    major = dict(data["majors"].get(profile.normalized_major, {}))
    return {**family, **{key: value for key, value in major.items() if key not in {"aliases"}}, "major_id": profile.normalized_major, "raw_major": profile.raw_major, "discipline_family": profile.discipline_family, "profile_source": profile.profile_source, "knowledge_source": profile.knowledge_source}
