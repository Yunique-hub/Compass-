"""Create auditable evidence only from observable submissions/assessments."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from .profile import CompetencyProfile


class EvidenceEngine:
    ALLOWED_TYPES = {"exercise", "quiz", "project", "code", "lab_report", "github", "coursework", "competition", "configuration", "screenshot", "public_work", "assessment"}

    def create(self, *, skill: str, evidence_type: str, source: str, description: str, assessment: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if evidence_type not in self.ALLOWED_TYPES: raise ValueError("UNSUPPORTED_EVIDENCE_TYPE")
        assessment = assessment or {}; passed = bool(assessment.get("passed", False))
        strength = max(0.0, min(1.0, float(assessment.get("score", 0.0)))) if passed else 0.0
        return {"evidence_id": str(uuid.uuid4()), "skill": skill, "type": evidence_type, "source": source, "description": description, "verification_status": "verified" if passed else "pending", "strength": strength, "assessment_id": assessment.get("assessment_id", ""), "created_at": datetime.now(timezone.utc).isoformat()}

    def update_competency(self, current: Mapping[str, Any] | None, evidence: Mapping[str, Any]) -> dict[str, Any]: return CompetencyProfile.apply_evidence(current, evidence)
