"""Compass 核心数据模型。"""
from __future__ import annotations

import json
import types
from dataclasses import asdict, dataclass, fields
from enum import Enum
from typing import Any, ClassVar, Mapping, TypeVar, Union, get_args, get_origin, get_type_hints

T = TypeVar("T", bound="Serializable")


class ConversationState(str, Enum):
    PROFILE_INCOMPLETE = "PROFILE_INCOMPLETE"
    DIRECTION_ANALYSIS = "DIRECTION_ANALYSIS"
    AWAITING_DIRECTION_CONFIRMATION = "AWAITING_DIRECTION_CONFIRMATION"
    AWAITING_DESTINATION = "AWAITING_DESTINATION"
    RECRUITMENT_ANALYSIS = "RECRUITMENT_ANALYSIS"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    PLAN_READY = "PLAN_READY"
    REVIEW = "REVIEW"
    SAFETY_ROUTED = "SAFETY_ROUTED"


class DirectionStatus(str, Enum):
    UNCONFIRMED = "UNCONFIRMED"
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"
    CONFIRMED = "CONFIRMED"
    CHANGED = "CHANGED"
    EXPIRED = "EXPIRED"


class MemoryAction(str, Enum):
    IGNORE = "ignore"
    TEMP = "temp"
    LONG_TERM_STRUCTURED = "long_term_structured"
    LONG_TERM_VECTOR = "long_term_vector"
    NEEDS_CONFIRMATION = "needs_confirmation"
    DELETE = "delete"


class SafetyType(str, Enum):
    NORMAL = "normal"
    STRESS = "stress"
    HIGH_RISK = "high_risk"
    OUT_OF_SCOPE = "out_of_scope"


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _convert(annotation: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (list, tuple) and args:
        return [_convert(args[0], item) for item in value]
    if origin is dict and len(args) == 2:
        return {str(key): _convert(args[1], item) for key, item in value.items()}
    if origin in (Union, types.UnionType):
        choices = [item for item in args if item is not type(None)]
        return _convert(choices[0], value) if choices else value
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if isinstance(annotation, type) and issubclass(annotation, Serializable):
        return annotation.from_dict(value)
    return value


@dataclass
class Serializable:
    required_fields: ClassVar[tuple[str, ...]] = ()

    def validate(self) -> None:
        for name in self.required_fields:
            if getattr(self, name, None) in (None, "", []):
                raise ValueError(f"字段 {name} 不能为空")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return _plain(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls: type[T], data: Mapping[str, Any], *, strict: bool = False) -> T:
        if not isinstance(data, Mapping):
            raise TypeError(f"{cls.__name__} 输入必须是对象")
        valid = {field.name for field in fields(cls)}
        unknown = set(data) - valid
        if strict and unknown:
            raise ValueError(f"未知字段: {', '.join(sorted(unknown))}")
        hints = get_type_hints(cls)
        kwargs = {key: _convert(hints.get(key, Any), value) for key, value in data.items() if key in valid}
        instance = cls(**kwargs)
        instance.validate()
        return instance


@dataclass
class UserProfile(Serializable):
    user_id: str = ""
    name: str = ""
    major: str = ""
    grade: str = ""
    gpa_range: str = ""
    courses: list[str] = None  # type: ignore[assignment]
    verified_skills: list[dict[str, Any]] = None  # type: ignore[assignment]
    projects: list[dict[str, Any]] = None  # type: ignore[assignment]
    competitions: list[dict[str, Any]] = None  # type: ignore[assignment]
    internships: list[dict[str, Any]] = None  # type: ignore[assignment]
    interests: list[str] = None  # type: ignore[assignment]
    preferred_tasks: list[str] = None  # type: ignore[assignment]
    disliked_work_styles: list[str] = None  # type: ignore[assignment]
    career_constraints: list[str] = None  # type: ignore[assignment]
    target_deadline: str = ""
    weekly_hours: float = 0.0
    learning_preferences: list[str] = None  # type: ignore[assignment]
    communication_preference: str = ""
    known_facts: dict[str, Any] = None  # type: ignore[assignment]
    pending_confirmations: list[str] = None  # type: ignore[assignment]
    inferred_facts: dict[str, Any] = None  # type: ignore[assignment]
    required_fields: ClassVar[tuple[str, ...]] = ("user_id",)

    def __post_init__(self) -> None:
        for name in ("courses", "verified_skills", "projects", "competitions", "internships", "interests", "preferred_tasks", "disliked_work_styles", "career_constraints", "learning_preferences", "pending_confirmations"):
            if getattr(self, name) is None:
                setattr(self, name, [])
        if self.known_facts is None:
            self.known_facts = {}
        if self.inferred_facts is None:
            self.inferred_facts = {}
        if self.weekly_hours < 0:
            raise ValueError("weekly_hours 不能为负数")


@dataclass
class CareerDirectionResult(Serializable):
    direction_id: str = ""
    direction_name: str = ""
    fit_score: float = 0.0
    fit_breakdown: dict[str, float] = None  # type: ignore[assignment]
    evidence: dict[str, list[str]] = None  # type: ignore[assignment]
    missing_evidence: list[str] = None  # type: ignore[assignment]
    current_strengths: list[str] = None  # type: ignore[assignment]
    risks: list[str] = None  # type: ignore[assignment]
    entry_cost: float = 0.0
    exploration_task: str = ""
    is_confirmed: bool = False

    def __post_init__(self) -> None:
        self.fit_score, self.entry_cost = clamp(self.fit_score), clamp(self.entry_cost)
        self.fit_breakdown = self.fit_breakdown or {}
        self.evidence = self.evidence or {}
        self.missing_evidence = self.missing_evidence or []
        self.current_strengths = self.current_strengths or []
        self.risks = self.risks or []


@dataclass
class DirectionConfirmation(Serializable):
    primary_direction: str = ""
    backup_direction: str = ""
    target_city: str = ""
    target_region: str = ""
    graduation_date: str = ""
    job_search_period: str = ""
    enterprise_preferences: list[str] = None  # type: ignore[assignment]
    confirmed_at: str = ""
    status: DirectionStatus = DirectionStatus.UNCONFIRMED
    history: list[dict[str, Any]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.enterprise_preferences = self.enterprise_preferences or []
        self.history = self.history or []


@dataclass
class JobRecord(Serializable):
    job_id: str = ""
    job_title_raw: str = ""
    job_title_normalized: str = ""
    city: str = ""
    region: str = ""
    career_direction: str = ""
    company: str = ""
    industry_type: str = ""
    education: str = ""
    major_requirements: list[str] = None  # type: ignore[assignment]
    experience: str = ""
    hard_skills: list[str] = None  # type: ignore[assignment]
    project_requirements: list[str] = None  # type: ignore[assignment]
    soft_skills: list[str] = None  # type: ignore[assignment]
    salary_range: str = ""
    published_at: str = ""
    collected_at: str = ""
    source: str = ""
    source_key: str = ""
    snapshot_version: str = ""
    validity_flag: str = "valid"
    required_fields: ClassVar[tuple[str, ...]] = ("job_id", "job_title_raw", "city", "source", "snapshot_version")

    def __post_init__(self) -> None:
        self.major_requirements = self.major_requirements or []
        self.hard_skills = self.hard_skills or []
        self.project_requirements = self.project_requirements or []
        self.soft_skills = self.soft_skills or []


@dataclass
class RecruitmentSnapshot(Serializable):
    snapshot_version: str = ""
    city: str = ""
    career_direction: str = ""
    collected_at: str = ""
    date_range: dict[str, str] = None  # type: ignore[assignment]
    source_types: list[str] = None  # type: ignore[assignment]
    source_count: int = 0
    sample_count: int = 0
    valid_sample_count: int = 0
    confidence_level: str = "low_confidence"
    synthetic: bool = False
    limitations: list[str] = None  # type: ignore[assignment]
    jobs: list[JobRecord] = None  # type: ignore[assignment]
    usage_notice: str = ""
    required_fields: ClassVar[tuple[str, ...]] = ("snapshot_version", "city", "career_direction", "collected_at")

    def __post_init__(self) -> None:
        self.date_range = self.date_range or {}
        self.source_types = self.source_types or []
        self.limitations = self.limitations or []
        self.jobs = self.jobs or []


@dataclass
class CompetencyGap(Serializable):
    competency_id: str = ""
    competency_name: str = ""
    category: str = ""
    job_evidence: list[str] = None  # type: ignore[assignment]
    job_frequency: float = 0.0
    requirement_weight: float = 0.0
    user_evidence: list[str] = None  # type: ignore[assignment]
    user_level: float = 0.0
    target_level: float = 1.0
    gap_level: float = 0.0
    deadline_urgency: float = 0.5
    evidence_value: float = 0.5
    learning_cost: float = 0.5
    priority_score: float = 0.0
    validation_method: str = ""
    priority_breakdown: dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        for name in ("job_frequency", "requirement_weight", "user_level", "target_level", "gap_level", "deadline_urgency", "evidence_value", "learning_cost", "priority_score"):
            setattr(self, name, clamp(getattr(self, name)))
        self.job_evidence = self.job_evidence or []
        self.user_evidence = self.user_evidence or []
        self.priority_breakdown = self.priority_breakdown or {}


@dataclass
class LearningTask(Serializable):
    task_id: str = ""
    title: str = ""
    priority: float = 0.0
    category: str = ""
    estimated_hours: float = 0.0
    output: str = ""
    acceptance_criteria: list[str] = None  # type: ignore[assignment]
    dependencies: list[str] = None  # type: ignore[assignment]
    resources: list[dict[str, Any]] = None  # type: ignore[assignment]
    fallback: str = ""
    status: str = "pending"

    def __post_init__(self) -> None:
        self.priority = clamp(self.priority)
        self.acceptance_criteria = self.acceptance_criteria or []
        self.dependencies = self.dependencies or []
        self.resources = self.resources or []
        if self.estimated_hours < 0:
            raise ValueError("estimated_hours 不能为负数")


@dataclass
class LearningPlan(Serializable):
    basis: dict[str, Any] = None  # type: ignore[assignment]
    snapshot_version: str = ""
    quarter_or_semester_milestones: list[dict[str, Any]] = None  # type: ignore[assignment]
    monthly_milestones: list[dict[str, Any]] = None  # type: ignore[assignment]
    weekly_core_tasks: list[LearningTask] = None  # type: ignore[assignment]
    optional_tasks: list[LearningTask] = None  # type: ignore[assignment]
    total_weekly_hours: float = 0.0
    capacity_limit: float = 0.0
    risks: list[str] = None  # type: ignore[assignment]
    adjustment_notes: list[str] = None  # type: ignore[assignment]
    status: str = "active"

    def __post_init__(self) -> None:
        self.basis = self.basis or {}
        self.quarter_or_semester_milestones = self.quarter_or_semester_milestones or []
        self.monthly_milestones = self.monthly_milestones or []
        self.weekly_core_tasks = self.weekly_core_tasks or []
        self.optional_tasks = self.optional_tasks or []
        self.risks = self.risks or []
        self.adjustment_notes = self.adjustment_notes or []


@dataclass
class MemoryCandidate(Serializable):
    candidate_id: str = ""
    user_id: str = ""
    memory_type: str = ""
    content: Any = ""
    importance: float = 0.5
    stability: float = 0.0
    future_relevance: float = 0.0
    user_explicitness: float = 0.0
    recurrence: float = 0.0
    confidence: float = 0.0
    task_value: float = 0.0
    sensitivity: str = "none"
    suggested_storage: str = ""
    expires_at: str = ""
    requires_confirmation: bool = False
    action: str = ""
    reason: str = ""
    source_turn_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
    user_intent: str = ""
    required_fields: ClassVar[tuple[str, ...]] = ("candidate_id", "user_id", "memory_type")

    def __post_init__(self) -> None:
        for name in ("importance", "stability", "future_relevance", "user_explicitness", "recurrence", "confidence", "task_value"):
            setattr(self, name, clamp(getattr(self, name)))


@dataclass
class MemoryRecord(MemoryCandidate):
    record_id: str = ""
    status: str = "active"
    usage_count: int = 0


@dataclass
class GrowthArchive(Serializable):
    archive_version: str = "1.0.0"
    updated_at: str = ""
    explicit_profile: dict[str, Any] = None  # type: ignore[assignment]
    career_directions: list[dict[str, Any]] = None  # type: ignore[assignment]
    confirmed_goal: dict[str, Any] = None  # type: ignore[assignment]
    capability_evidence: list[dict[str, Any]] = None  # type: ignore[assignment]
    recruitment_snapshot: dict[str, Any] = None  # type: ignore[assignment]
    skill_graph: list[dict[str, Any]] = None  # type: ignore[assignment]
    current_plan: dict[str, Any] = None  # type: ignore[assignment]
    important_events: list[dict[str, Any]] = None  # type: ignore[assignment]
    achievements: list[dict[str, Any]] = None  # type: ignore[assignment]
    memory_change_summary: dict[str, Any] = None  # type: ignore[assignment]
    pending_confirmations: list[str] = None  # type: ignore[assignment]
    extensions: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.explicit_profile = self.explicit_profile or {}
        self.career_directions = self.career_directions or []
        self.confirmed_goal = self.confirmed_goal or {}
        self.capability_evidence = self.capability_evidence or []
        self.recruitment_snapshot = self.recruitment_snapshot or {}
        self.skill_graph = self.skill_graph or []
        self.current_plan = self.current_plan or {}
        self.important_events = self.important_events or []
        self.achievements = self.achievements or []
        self.memory_change_summary = self.memory_change_summary or {}
        self.pending_confirmations = self.pending_confirmations or []
        self.extensions = self.extensions or {}
