"""Create auditable evidence only from observable submissions/assessments."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from .profile import CompetencyProfile


class EvidenceEngine:
    VERIFICATION_TRUST = {
        "SELF_REPORTED": 0.1,
        "TEXT_SUPPORTED": 0.3,
        "ARTIFACT_SUBMITTED": 0.4,
        "ARTIFACT_ASSESSED": 0.7,
        "EXECUTION_VERIFIED": 0.9,
        "EXTERNAL_VERIFIED": 1.0,
    }
    VERIFIED_LEVELS = {"ARTIFACT_ASSESSED", "EXECUTION_VERIFIED", "EXTERNAL_VERIFIED"}
    ALLOWED_TYPES = {
        "exercise", "quiz", "project", "code", "lab_report", "github", "coursework", "competition", "configuration", "screenshot", "public_work", "assessment",
        "financial_model", "investment_research", "case_analysis", "excel_model", "certification", "internship", "legal_memo", "legal_research", "moot_court", "qualification_exam",
        "experiment", "research_poster", "paper", "research_assistantship", "clinical_case", "clinical_reasoning", "skills_checklist", "rotation_feedback", "portfolio", "design_case", "prototype", "user_research",
        "engineering_design", "cad_model", "simulation", "prototype_test", "technical_report", "problem_set", "research_proposal", "survey_analysis", "behavioral_experiment", "fieldwork", "publication", "presentation", "writing", "translation", "teaching_demo", "proof", "modeling_report", "research_paper",
        "article", "business_case", "classroom_observation", "clinical_skill", "course_assessment", "critique", "data_analysis", "design_project", "design_report", "drawing", "econometrics_project", "essay", "exploration_log", "interview", "lesson_plan", "market_analysis", "model", "operations_project", "reflection", "report", "research", "rotation", "source_analysis", "teaching_practice", "technical_project", "video", "visual_work",
    }

    def create(
        self, *, skill: str, evidence_type: str, source: str, description: str,
        assessment: Mapping[str, Any] | None = None, verification_level: str = "",
    ) -> dict[str, Any]:
        if evidence_type not in self.ALLOWED_TYPES: raise ValueError("UNSUPPORTED_EVIDENCE_TYPE")
        assessment = assessment or {}; passed = bool(assessment.get("passed", False))
        if not verification_level:
            verification_level = "ARTIFACT_ASSESSED" if passed and assessment.get("verification_basis") == "structured_criteria" else ("TEXT_SUPPORTED" if description else "SELF_REPORTED")
        verification_level = verification_level.upper()
        if verification_level not in self.VERIFICATION_TRUST:
            raise ValueError("UNSUPPORTED_VERIFICATION_LEVEL")
        if not passed and verification_level in self.VERIFIED_LEVELS:
            verification_level = "ARTIFACT_SUBMITTED"
        trust = self.VERIFICATION_TRUST[verification_level]
        strength = max(0.0, min(1.0, float(assessment.get("score", 0.0)))) * trust if passed else 0.0
        if verification_level in self.VERIFIED_LEVELS and passed:
            status = "verified"
        elif verification_level == "TEXT_SUPPORTED" and passed:
            status = "supported"
        elif verification_level == "ARTIFACT_SUBMITTED":
            status = "submitted"
        elif verification_level == "SELF_REPORTED":
            status = "self_reported"
        else:
            status = "pending"
        return {
            "evidence_id": str(uuid.uuid4()), "skill": skill, "type": evidence_type, "source": source,
            "description": description, "verification_level": verification_level, "verification_status": status,
            "source_trust": trust, "strength": round(strength, 4), "assessment_id": assessment.get("assessment_id", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def update_competency(self, current: Mapping[str, Any] | None, evidence: Mapping[str, Any]) -> dict[str, Any]: return CompetencyProfile.apply_evidence(current, evidence)
