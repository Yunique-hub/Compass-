"""Translate profile facts into a user-visible growth stage."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping

from .known_facts import fact_value


class GrowthStage(str, Enum):
    ADAPTATION_STAGE = "ADAPTATION_STAGE"
    FOUNDATION_STAGE = "FOUNDATION_STAGE"
    CAREER_EXPLORATION_STAGE = "CAREER_EXPLORATION_STAGE"
    INTERNSHIP_PREPARATION_STAGE = "INTERNSHIP_PREPARATION_STAGE"
    INTERNSHIP_STAGE = "INTERNSHIP_STAGE"
    JOB_SEARCH_PREPARATION_STAGE = "JOB_SEARCH_PREPARATION_STAGE"
    JOB_SEARCH_STAGE = "JOB_SEARCH_STAGE"
    EXAM_SPRINT_STAGE = "EXAM_SPRINT_STAGE"
    PROJECT_SPRINT_STAGE = "PROJECT_SPRINT_STAGE"
    GRADUATION_TRANSITION_STAGE = "GRADUATION_TRANSITION_STAGE"


STAGE_LABELS = {
    GrowthStage.ADAPTATION_STAGE: "大学适应期",
    GrowthStage.FOUNDATION_STAGE: "基础能力建设期",
    GrowthStage.CAREER_EXPLORATION_STAGE: "职业探索期",
    GrowthStage.INTERNSHIP_PREPARATION_STAGE: "实习准备期",
    GrowthStage.INTERNSHIP_STAGE: "实习实践期",
    GrowthStage.JOB_SEARCH_PREPARATION_STAGE: "求职准备期",
    GrowthStage.JOB_SEARCH_STAGE: "求职行动期",
    GrowthStage.EXAM_SPRINT_STAGE: "考试冲刺期",
    GrowthStage.PROJECT_SPRINT_STAGE: "项目冲刺期",
    GrowthStage.GRADUATION_TRANSITION_STAGE: "毕业过渡期",
}


@dataclass
class StageDetectionResult:
    stage: GrowthStage
    label: str
    confidence: float
    evidence: list[str]
    secondary_stages: list[str]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["stage"] = self.stage.value
        return value


def detect_stage(facts: Mapping[str, Any]) -> StageDetectionResult:
    grade = str(fact_value(facts, "grade", ""))
    need = str(fact_value(facts, "primary_need", ""))
    deadline = str(fact_value(facts, "deadline_time", ""))
    exam_days = fact_value(facts, "exam_days")
    evidence: list[str] = []
    secondary: list[str] = []

    if isinstance(exam_days, (int, float)) and exam_days <= 5:
        stage = GrowthStage.EXAM_SPRINT_STAGE
        evidence.append(f"距离考试 {int(exam_days)} 天")
    elif "正在实习" in str(fact_value(facts, "current_activity", "")):
        stage = GrowthStage.INTERNSHIP_STAGE
        evidence.append("正在实习")
    elif need == "实习准备" or deadline == "明年":
        stage = GrowthStage.INTERNSHIP_PREPARATION_STAGE
        evidence.extend(item for item in (grade, "明年实习" if deadline == "明年" else "实习目标") if item)
    elif need == "就业准备" and any(token in grade for token in ("大四", "研三")):
        stage = GrowthStage.JOB_SEARCH_STAGE
        evidence.extend(item for item in (grade, "正在求职/校招") if item)
    elif need == "就业准备":
        stage = GrowthStage.JOB_SEARCH_PREPARATION_STAGE
        evidence.extend(item for item in (grade, "就业目标") if item)
    elif need == "成长方向" or (grade == "大一" and not fact_value(facts, "career_direction")):
        stage = GrowthStage.CAREER_EXPLORATION_STAGE
        evidence.extend(item for item in (grade, "方向尚未明确") if item)
        if grade == "大一":
            secondary.append(GrowthStage.FOUNDATION_STAGE.value)
    elif fact_value(facts, "project_deadline"):
        stage = GrowthStage.PROJECT_SPRINT_STAGE
        evidence.append("存在明确项目截止时间")
    elif grade in {"大四", "研三"}:
        stage = GrowthStage.GRADUATION_TRANSITION_STAGE
        evidence.append(grade)
    elif grade == "大一":
        stage = GrowthStage.ADAPTATION_STAGE
        evidence.append(grade)
    else:
        stage = GrowthStage.FOUNDATION_STAGE
        evidence.extend(item for item in (grade, str(fact_value(facts, "major", ""))) if item)
    confidence = 0.9 if len(evidence) >= 2 else (0.75 if evidence else 0.5)
    return StageDetectionResult(stage, STAGE_LABELS[stage], confidence, evidence, secondary)
